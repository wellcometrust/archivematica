# -*- coding: utf-8 -*-
"""Archivematica MCPServer API (Gearman RPC).

We have plans to replace this server with gRPC.
"""

# This file is part of Archivematica.
#
# Copyright 2010-2018 Artefactual Systems Inc. <http://artefactual.com>
#
# Archivematica is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Archivematica is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Archivematica.  If not, see <http://www.gnu.org/licenses/>.

import cPickle
import inspect
import logging
from socket import gethostname
import re
import time

from django.conf import settings as django_settings
from django.utils.six.moves import configparser
from django.utils.six import StringIO
from gearman import GearmanWorker
from gearman.errors import ServerUnavailable
from lxml import etree

from databaseFunctions import auto_close_db
from linkTaskManagerChoice import choicesAvailableForUnits
from package import create_package, get_approve_transfer_chain_id
from processing_config import get_processing_fields
from main.models import Job


logger = logging.getLogger("archivematica.mcp.server.rpcserver")


class RPCServerError(Exception):
    """Base exception of RPCServer.

    This exception and its subclasses are meant to be raised by RPC handlers.
    """


class UnexpectedPayloadError(RPCServerError):
    """Missing parameters in payload."""


class NotFoundError(RPCServerError):
    """Generic NotFound exception."""


class RPCServer(GearmanWorker):
    """RPCServer is the API server implemented as a Gearman worker.

    Handlers are implemented as methods in this class. They have access to
    shared state in this class, e.g. ``self.workflow``. For a method to be
    promoted as handler it needs to meet the following conditions:

    1. The name of the method starts with an underscore (``_``) and ends with
       the string ``_handler``, e.g. ``_do_something_handler``.

    2. The method docstrings ends with a configuration snippet in INI format,
       e.g.::

           [config]
           name = doSomething
           raise_exc = yes

       Supported configuration attributes:

       - ``name`` (string) is the name of the function name or ability as
         Gearman refers to the type of a job in its protocol.

       - ``raise_exc`` (boolean) - when enabled, exceptions that occur inside
         the handler are not caught which causes the Gearman worker library to
         report the error to Gearman which results in terminating the job as
         failed. The Gearman client (in our context, the API consumer) will not
         receive additional information about the error other than its status.
         Disable ``raise_exc`` when you want the client to receive a detailed
         error.

    3. Handler methods have at least three arguments:

       - ``self``: instance of the RPCServer class.

       - ``worker``: instance of the worker class which is a subclass of
         ``gearman.job.GearmanWorker``.

       - ``job``: instance of ``gearman.job.GearmanJob``.

       Additionally, a method handler can have an argument named ``payload``.
       If present, it will carry the data embedded in the payload of the job
       already unserialized. This is useful when the handler wants to read
       data sent by the client.

    """
    # Regular expression to match handler configurations in method docstrings.
    ability_regex = re.compile(
        r"(?P<docstring>.*)(?P<config>\[config\].*)$",
        re.DOTALL | re.MULTILINE)

    # To some extent, application logic in Archivematica is coupled to certain
    # values in our workflow data. This is mostly true to things related to
    # types of transfers and its approvals. This value in particular supports
    # the partial approval of AIP reingest.
    APPROVE_AIP_REINGEST_CHAIN_ID = "9520386f-bb6d-4fb9-a6b6-5845ef39375f"

    def __init__(self, workflow):
        super(RPCServer, self).__init__(
            host_list=[django_settings.GEARMAN_SERVER])
        self.workflow = workflow
        self._register_tasks()
        self.set_client_id(gethostname() + "_MCPServer")

    def _register_tasks(self):
        for ability, handler in self._handlers():
            logger.debug("Registering ability %s", ability)
            self.register_task(ability, handler)

    def _handlers(self):
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        for name, handler in members:
            if name[0] != "_":
                continue
            if not name.endswith("_handler"):
                continue
            name, opts = self._get_ability_details(handler)
            yield name, self._wrap_handler_method(handler, **opts)

    def _get_ability_details(self, handler):
        docstring = str(inspect.getdoc(handler))
        match = self.ability_regex.search(docstring)
        err = ValueError("Unexpected docstring format: {}".format(docstring))
        if match is None:
            raise err
        try:
            config = match.group("config")
        except IndexError:
            raise err
        parser = configparser.SafeConfigParser({
            "name": None, "raise_exc": False,
        })
        parser.readfp(StringIO(config))
        return parser.get("config", "name"), {
            "raise_exc": parser.getboolean("config", "raise_exc"),
            "expect_payload": "payload" in inspect.getargspec(handler).args,
        }

    @auto_close_db
    def _wrap_handler_method(self, handler, **opts):
        def wrap(worker, job):
            args = [worker, job]
            if opts["expect_payload"]:
                payload = cPickle.loads(job.data)
                if not isinstance(payload, dict):
                    raise UnexpectedPayloadError("Payload is not a dictionary")
                args.append(payload)
            try:
                res = handler(*args)
            except Exception as err:
                is_handler_err = isinstance(err, RPCServerError)
                logger.error("Exception raised by handler %s: %s",
                             handler.__name__, err,
                             exc_info=not is_handler_err)
                if opts["raise_exc"]:
                    raise  # So GearmanWorker knows that it failed.
                return {
                    "error": True,
                    "handler": handler.__name__,
                    "message": str(err),
                }
            return cPickle.dumps(res)
        return wrap

    #
    # Handlers
    #

    def _job_approve_handler(self, worker, job, payload):
        """Approve a job awaiting for approval.

        [config]
        name = approveJob
        raise_exc = yes
        """
        job_id = payload["jobUUID"]
        chain = payload["chain"]
        user_id = str(payload["uid"])
        logger.debug("Approving: %s %s %s", job_id, chain, user_id)
        if job_id in choicesAvailableForUnits:
            choicesAvailableForUnits[job_id].proceedWithChoice(chain, user_id)
        return "approving: ", job_id, chain

    def _job_awaiting_approval_handler(self, worker, job):
        """List jobs awaiting for approval.

        [config]
        name = getJobsAwaitingApproval
        raise_exc = yes
        """
        ret = etree.Element("choicesAvailableForUnits")
        for uuid, choice in choicesAvailableForUnits.items():
            ret.append(choice.xmlify())
        return etree.tostring(ret, pretty_print=True)

    def _package_create_handler(self, worker, job, payload):
        """Create a new package.

        [config]
        name = packageCreate
        raise_exc = yes
        """
        args = (
            payload.get("name"),
            payload.get("type"),
            payload.get("accession"),
            payload.get("access_system_id"),
            payload.get("path"),
            payload.get("metadata_set_id"),
        )
        kwargs = {
            "auto_approve": payload.get("auto_approve"),
            "wait_until_complete": payload.get("wait_until_complete"),
        }
        processing_config = payload.get("processing_config")
        if processing_config is not None:
            kwargs["processing_config"] = processing_config
        return create_package(*args, **kwargs).pk

    def _approve_transfer_by_path_handler(self, worker, job, payload):
        """Approve a transfer matched by its path.

        [config]
        name = approveTransferByPath
        raise_exc = no
        """
        db_transfer_path = payload.get("db_transfer_path")
        transfer_type = payload.get("transfer_type", "standard")
        user_id = payload.get("user_id")
        job = Job.objects.filter(
            directory=db_transfer_path,
            currentstep=Job.STATUS_AWAITING_DECISION
        ).first()
        if not job:
            raise NotFoundError("There is no job awaiting for a decision.")
        chain_id = get_approve_transfer_chain_id(transfer_type)
        try:
            choicesAvailableForUnits[job.pk].proceedWithChoice(
                chain_id, user_id)
        except IndexError:
            raise NotFoundError("Could not find choice for unit")
        return job.sipuuid

    def _approve_partial_reingest_handler(self, worker, job, payload):
        """Approve a partial reingest.

        TODO: (from the old api/views.py function) this is just a temporary way
        of getting the API to do the equivalent of clicking "Approve AIP
        reingest" in the dashboard when faced with "Approve AIP reingest". This
        is non-dry given ``approve_transfer_by_path_handler`` above.

        [config]
        name = approvePartialReingest
        raise_exc = no
        """
        sip_uuid = payload.get("sip_uuid")
        user_id = payload.get("user_id")
        job = Job.objects.filter(
            sipuuid=sip_uuid,
            microservicegroup="Reingest AIP",
            currentstep=Job.STATUS_AWAITING_DECISION,
        ).first()
        if not job:  # No job to be found.
            raise NotFoundError(
                'There is no "Reingest AIP" job awaiting a'
                " decision for SIP {}".format(sip_uuid))
        not_found = NotFoundError(
            "Could not find choice for approve AIP reingest")
        try:
            chain = self.workflow.get_chain(self.APPROVE_AIP_REINGEST_CHAIN_ID)
        except KeyError:
            raise not_found
        try:
            choicesAvailableForUnits[job.pk].proceedWithChoice(
                chain.id, user_id)
        except IndexError:
            raise not_found

    def _get_processing_config_fields_handler(self, worker, job):
        """List processing configuration fields.

        [config]
        name = getProcessingConfigFields
        raise_exc = no
        """
        return get_processing_fields(self.workflow)


def start(workflow):
    worker = RPCServer(workflow)
    failMaxSleep = 30
    failSleep = 1
    failSleepIncrementor = 2
    while True:
        try:
            worker.work()
        except ServerUnavailable:
            time.sleep(failSleep)
            if failSleep < failMaxSleep:
                failSleep += failSleepIncrementor

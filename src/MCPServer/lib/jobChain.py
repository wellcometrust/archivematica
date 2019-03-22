# This file is part of Archivematica.
#
# Copyright 2010-2013 Artefactual Systems Inc. <http://artefactual.com>
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

# @package Archivematica
# @subpackage MCPServer
# @author Joseph Perry <joseph@artefactual.com>

import logging

from jobChainLink import jobChainLink

from dicts import ReplacementDict

from main.models import UnitVariable

# Holds:
# -UNIT
# -Job chain link
# -Job chain description
#
# potentialToHold/getFromDB
# -previous chain links

LOGGER = logging.getLogger('archivematica.mcp.server')


def fetchUnitVariableForUnit(unit_uuid):
    """
    Returns a dict combining all of the replacementDict unit variables for the
    specified unit.
    """

    results = ReplacementDict()
    variables = UnitVariable.objects.filter(unituuid=unit_uuid, variable="replacementDict").values_list('variablevalue')

    for replacement_dict, in variables:
        rd = ReplacementDict.fromstring(replacement_dict)
        results.update(rd)

    LOGGER.debug("Replacement dict for unit %s: %s", unit_uuid, results)

    return results


class jobChain:
    def __init__(self, unit, chain, workflow, starting_link=None):
        """Create an instance of a chain from the MicroServiceChains table"""
        LOGGER.debug('Creating jobChain %s for chain %s', unit, chain.id)
        if chain is None:
            return None
        self.unit = unit
        self.workflow = workflow

        LOGGER.debug('Chain: %s', chain)

        if starting_link is None:
            starting_link = chain.link

        # Migrate over unit variables containing replacement dicts from
        # previous chains but prioritize any values contained in passVars
        # passed in as kwargs.
        rd = fetchUnitVariableForUnit(unit.UUID)

        # Run!
        jobChainLink(self, starting_link, workflow, unit, passVar=rd)

    def nextChainLink(self, link, passVar=None):
        """Proceed to next link."""
        if link is None:
            LOGGER.debug('Done with unit %s', self.unit.UUID)
            return
        jobChainLink(self, link, self.workflow, self.unit, passVar=passVar)

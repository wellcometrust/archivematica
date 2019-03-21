FROM artefactual/archivematica-mcp-client-base:20180924.01.aa9649a1

# This is already included in the installs set up in MCPClient-base already but we
# don't source a local copy of that - the above `FROM` command uses the Artefactual
# version. So keep the unzip install here until there's a "FROM"-able image that
# includes it!
RUN apt-get update && apt-get install -y --no-install-recommends unzip

ENV DJANGO_SETTINGS_MODULE settings.common
ENV PYTHONPATH /src/MCPClient/lib/:/src/archivematicaCommon/lib/:/src/dashboard/src/
ENV ARCHIVEMATICA_MCPCLIENT_MCPCLIENT_ARCHIVEMATICACLIENTMODULES /src/MCPClient/lib/archivematicaClientModules
ENV ARCHIVEMATICA_MCPCLIENT_MCPCLIENT_CLIENTASSETSDIRECTORY /src/MCPClient/lib/assets/
ENV ARCHIVEMATICA_MCPCLIENT_MCPCLIENT_CLIENTSCRIPTSDIRECTORY /src/MCPClient/lib/clientScripts/

COPY archivematicaCommon/requirements/ /src/archivematicaCommon/requirements/
COPY dashboard/src/requirements/ /src/dashboard/src/requirements/
COPY MCPClient/requirements/ /src/MCPClient/requirements/
RUN pip install -r /src/archivematicaCommon/requirements/production.txt -r /src/archivematicaCommon/requirements/dev.txt
RUN pip install -r /src/dashboard/src/requirements/production.txt -r /src/dashboard/src/requirements/dev.txt
RUN pip install -r /src/MCPClient/requirements/production.txt -r /src/MCPClient/requirements/dev.txt

COPY archivematicaCommon/ /src/archivematicaCommon/
COPY dashboard/ /src/dashboard/
COPY MCPClient/ /src/MCPClient/

# Some scripts in archivematica-fpr-admin executed by MCPClient rely on certain
# files being available in this image (e.g. see https://git.io/vA1wF).
COPY archivematicaCommon/lib/externals/fido/ /usr/lib/archivematica/archivematicaCommon/externals/fido/
COPY archivematicaCommon/lib/externals/fiwalk_plugins/ /usr/lib/archivematica/archivematicaCommon/externals/fiwalk_plugins/

USER archivematica

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT
COPY run_mcpclient.sh /

ENTRYPOINT ["/run_mcpclient.sh"]

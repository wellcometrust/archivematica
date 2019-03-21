#!/usr/bin/env bash

set -o errexit
set -o nounset

echo "== WELLCOME: starting version $GIT_COMMIT =="

/src/MCPClient/lib/archivematicaClient.py $@

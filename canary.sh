#!/bin/bash

# everything must pass
set -e

. install.sh

# upgrade all deps to latest version
pip install pip-review
pip-review --pre # preview the upgrades
echo "[any key to continue ...]"
read -p "$*"
pip-review --auto --pre # update everything

pip freeze > new-requirements.txt

echo "wrote new-requirements.txt"

# run the tests
. .test.sh

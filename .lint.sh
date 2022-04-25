#!/bin/bash
# lints code using pylint and pyflakes and then reformats code use autopep8 in the `.scrub.sh` script
set -e

# remove any old compiled python files
# pylint likes to lint them
find src/ -name '*.py[c|~]' -delete
find src/ -regex "\(.*__pycache__.*\|*.py[co]\)" -delete

echo "pyflakes"
pyflakes ./src/

echo "pylint"

export DJANGO_SETTINGS_MODULE=core.settings

# E1103 - a variable is accessed for a nonexistent member, but astng was not able to interpret all possible types of this variable.
pylint -E ./src --disable=E1103

# specific warnings we're interested in, comma separated with no spaces
# presence of these warnings are a failure
pylint ./src \
    --disable=all --reports=n --score=n \
    --enable=redefined-builtin,pointless-string-statement,no-else-return,redefined-outer-name

echo "scrubbing"
. .scrub.sh

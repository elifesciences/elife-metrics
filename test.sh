#!/bin/bash
set -e
if [ ! -d venv ]; then
    virtualenv --python=`which python2` venv
    pip install -r requirements.txt
fi
source venv/bin/activate
pylint -E src/metrics/** --load-plugins=pylint_django --disable=E1103
./src/manage.py test src/

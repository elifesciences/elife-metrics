#!/bin/bash

set -e # everything must pass

echo "[-] .test-green.sh"

pyflakes src/

args="$@"
module="src"
if [ ! -z "$args" ]; then
    module="$args"
fi

# remove any old compiled python files
find src/ -name '*.pyc' -delete
GREEN_CONFIG=.green ./src/manage.py test "$module" \
    --testrunner=green.djangorunner.DjangoRunner \
    --no-input \
    -v 3

echo "[✓] .test-green.sh"

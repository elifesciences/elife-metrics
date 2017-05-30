#!/bin/bash

set -e # everything must pass

pyflakes src/

args="$@"
module="src"
print_coverage=1
if [ ! -z "$args" ]; then
    module="$args"
    print_coverage=0
fi

# remove any old compiled python files
find src/ -name '*.pyc' -delete

coverage run --source='src/' --omit='*/tests/*,*/migrations/*,*/core/*' src/manage.py test "$module" --no-input -v 2
echo "* passed tests"

# run coverage test
# only report coverage if we're running a complete set of tests
if [ $print_coverage -eq 1 ]; then
    coverage report
    # is only run if tests pass
    covered=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
    if [ $covered -lt 84 ]; then
        echo
        echo "FAILED this project requires at least 84% coverage, got $covered"
        echo
        exit 1
    fi
fi


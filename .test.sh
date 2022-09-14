#!/bin/bash
set -e

args=$*
module="src"
print_coverage=1
if [ -n "$args" ]; then
    module="$args"
    print_coverage=0
fi

# remove any old compiled python files
find src/ -name '*.pyc' -delete

export DJANGO_SETTINGS_MODULE=core.settings
pytest "$module" \
    -vvv \
    --no-migrations \
    --cov=src --cov-config=.coveragerc --cov-report=html \
    --disable-socket

echo "* passed tests"

# run coverage test
# only report coverage if we're running a complete set of tests
if [ $print_coverage -eq 1 ]; then
    coverage report
    # is only run if tests pass
    covered=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
    if [ "$covered" -lt "81" ]; then
        echo
        echo "FAILED this project requires at least 81% coverage, got $covered"
        echo
        exit 1
    fi
fi


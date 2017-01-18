#!/bin/bash
# @description convenience wrapper around Django's manage.py command
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
. install.sh > /dev/null
./src/manage.py $@

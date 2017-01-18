#!/bin/bash
# Returns the daily views and downloads for the last day.
#set -e # all commands must pass
#source install.sh
#if [ -f .env ]; then 
#    set -a # all vars are exported
#    source .env
#fi
#python -m elife_ga_metrics.core
./manage.sh ga --action run

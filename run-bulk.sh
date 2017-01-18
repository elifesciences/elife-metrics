#!/bin/bash
# Returns daily and monthly views and downloads 
# for the last week
#set -e
#source install.sh
#if [ -f .env ]; then 
#    set -a # all vars are exported
#    source .env
#fi
#python -m elife_ga_metrics.bulk
./manage.sh ga --action run-bulk

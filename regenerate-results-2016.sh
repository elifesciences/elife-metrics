#!/bin/bash
# Regenerates all views and downloads since we started 
# capturing them.
# Call this whenever the query or table changes or when
# code changes affect the results output.
#set -e
#source install.sh &> /dev/null
#if [ -f .env ]; then 
#    set -a # all vars are exported
#    source .env
#fi
#python -c "import os; from elife_ga_metrics import bulk; bulk.regenerate_results_2016(os.environ['GA_TABLE']);"
./manage.sh ga --action regenerate-2016

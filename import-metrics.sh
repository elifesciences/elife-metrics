#!/bin/bash
# pulls in daily stats for the last two days.
# monthly stats for the last two months.
set -e

source install.sh
source venv/bin/activate

if [ ! -e newrelic.ini ]; then
    ./src/manage.py import_metrics
else
    if ! grep 'import-hook:django' newrelic.ini; then
        printf "\n[import-hook:django]\ninstrumentation.scripts.django_admin = import_metrics\n" >> newrelic.ini
    fi
    NEW_RELIC_CONFIG_FILE=newrelic.ini ./venv/bin/newrelic-admin run-python ./src/manage.py import_metrics
fi

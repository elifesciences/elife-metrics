#!/bin/bash
# pulls in daily stats for the last two days.
# monthly stats for the last two months.
set -e

source install.sh
source venv/bin/activate

./src/manage.py import_metrics

exit 0

# lsh@2022-06-07
# below appears to work, but NewRelic is holding on to a lot of memory and it's already starved for that.
# try again on something other than a t2.small

if [ ! -e newrelic.ini ]; then
    ./src/manage.py import_metrics
else
    if ! grep 'import-hook:django' newrelic.ini; then
        printf "\n[import-hook:django]\ninstrumentation.scripts.django_admin = import_metrics\n" >> newrelic.ini
    fi
    NEW_RELIC_CONFIG_FILE=newrelic.ini ./venv/bin/newrelic-admin run-python ./src/manage.py import_metrics
fi

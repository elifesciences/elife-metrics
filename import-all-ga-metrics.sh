#!/bin/bash
set -e
source install.sh
# this script can take a little while to complete
# --days    number of days back in time to import from
# --months  number of months back in time to import from
./manage.sh import_metrics --days=9999 --months=9999 --just-source=ga --only-cached --cached

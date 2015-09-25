#!/bin/bash
set -e
source install.sh
# pulls in daily stats for the last two days
# monthly stats for the last two months
./manage.sh import_metrics

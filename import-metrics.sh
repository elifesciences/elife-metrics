#!/bin/bash
# pulls in daily stats for the last two days.
# monthly stats for the last two months.
set -e

source install.sh
source venv/bin/activate

./src/manage.py import_metrics

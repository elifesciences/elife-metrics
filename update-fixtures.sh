#!/bin/bash
# updates test fixtures
set -e

# non-article metrics
source venv/bin/activate
./src/manage.py update_fixtures

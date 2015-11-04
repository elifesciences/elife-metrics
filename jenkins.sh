#!/bin/bash
set -e
cd src/core/
ln -sfT dev_settings.py settings.py
cd ../../
source test.sh
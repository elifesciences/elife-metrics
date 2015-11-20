#!/bin/bash
set -e
rm -rf venv/
cd src/core/
ln -sfT dev_settings.py settings.py
cd ../../
source test.sh

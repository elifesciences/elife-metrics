#!/bin/bash
set -e
cd src/core/
ln -s dev_settings.py settings.py
cd ../../
source test.sh
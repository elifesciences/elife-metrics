#!/bin/bash
set -e
rm -rf venv/
. install.sh
. .lint.sh
. .test.sh

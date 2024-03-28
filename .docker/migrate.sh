#!/bin/bash
set -e # everything must succeed.
echo "[-] migrate.sh"

python src/manage.py migrate --no-input

echo "[✓] migrate.sh"

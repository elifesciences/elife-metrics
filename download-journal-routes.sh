#!/bin/bash
set -e

sha=024702b4130f3d2e8209a1801c9a594d655a8a03
url="https://raw.githubusercontent.com/elifesciences/journal/$sha/app/config/routing.yml"
schema_path="./schema/api-raml/journal"

mkdir -p "$schema_path"

file_path="$schema_path/routing.yml"

curl --silent "$url" > "$file_path"
echo "$(du --bytes $file_path | cut -f1) bytes written to $file_path"

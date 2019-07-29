#!/bin/bash
# removes expired entries from the requests_cache db, shrinks db 
set -e
source venv/bin/activate

# clear expired entries
output_path=$(echo 'from article_metrics import handler
print(handler.clear_expired())' | ./src/manage.py shell)

# call VACUUM on the sqlite db to shrink it
du -sh "$output_path"
sqlite3 "$output_path" -line "VACUUM"
du -sh "$output_path"

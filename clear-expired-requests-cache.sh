#!/bin/bash
# removes expired entries from the requests_cache db, then shrinks the db.
set -e
source venv/bin/activate

# clear expired entries
output_path=$(echo 'from article_metrics import handler
print(handler.clear_expired())' | ./src/manage.py shell)

# call VACUUM on the sqlite db to shrink it
printf "before: "
du -sh "$output_path"
sqlite3 "$output_path" -line "VACUUM"
printf "after:  "
du -sh "$output_path"

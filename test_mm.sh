#!/bin/bash

echo "Using python at '$(which python)'"

for file in test_payloads/*; do
    echo "Testing $file"
    json_data=$(cat "$file")
    json_data="${json_data//MM_URL/$1}"
    echo "$json_data" | python ./mattermost_alerts/bin/mattermost.py --execute
done

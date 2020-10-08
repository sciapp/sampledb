#!/bin/sh
chown sampledb:sampledb "${SAMPLEDB_FILE_STORAGE_PATH}"
exec su sampledb -c 'env/bin/python -m sampledb "$0" "$@"' -- "$@"

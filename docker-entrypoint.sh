#!/bin/sh
chown sampledb:sampledb "${SAMPLEDB_FILE_STORAGE_PATH}"
exec /usr/local/bin/sampledb "$@"

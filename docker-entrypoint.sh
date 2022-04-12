#!/bin/sh
chown sampledb:sampledb "${SAMPLEDB_FILE_STORAGE_PATH}"
/usr/local/bin/sdb "$@"

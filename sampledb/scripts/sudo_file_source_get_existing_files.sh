#!/bin/bash
set -e

# change directory so sampledb can be found
cd "${0%/*}"
cd ../..
read -r PYTHON;
read -r USERNAME;
read -r USERID;
read -r DIRECTORY;
read -r RELATIVE_PATH;
read -r MAX_DEPTH;

set +e
getent passwd $USERNAME > /dev/null
USER_EXISTS=$?
set -e
if [ $USER_EXISTS -ne 0 ]; then
    useradd -u $USERID -G sampledb -M $USERNAME > /dev/null
fi

sudo -u $USERNAME $PYTHON -m sampledb sudo_file_source_get_existing_files $DIRECTORY $RELATIVE_PATH $MAX_DEPTH

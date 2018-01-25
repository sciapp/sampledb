#!/bin/bash
set -e

# change directory so sampledb can be found
cd "${0%/*}"
cd ../..
read -r PYTHON;
read -r B64_JSON_ENV;
read -r USERNAME;
read -r USER_ID;
read -r OBJECT_ID;
read -r DIRECTORY;
read -r FILE_NAME;

sudo -u $USERNAME SAMPLEDB_B64_JSON_ENV=$B64_JSON_ENV $PYTHON -m sampledb sudo_file_source_copy_file $USER_ID $OBJECT_ID $DIRECTORY $FILE_NAME

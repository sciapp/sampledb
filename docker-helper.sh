#!/usr/bin/env bash
# This script is a wrapper for running SampleDB
exec su sampledb -c 'python -m sampledb "$0" "$@"' -- "$@"

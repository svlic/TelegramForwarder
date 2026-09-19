#!/bin/sh
set -eu

for directory in /app/db /app/logs /app/sessions /app/temp /app/config; do
    mkdir -p "$directory"
    chown -R appuser:appuser "$directory"
done

exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"

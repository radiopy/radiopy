#!/bin/bash

trap "service cron stop && exit 0" SIGTERM

# Replace config.toml if RADIOPY_CONFIG is set
if [ -n "$RADIOPY_CONFIG" ]; then
    echo "$RADIOPY_CONFIG" > /app/config.toml
fi


# truncate the log file before tailing it
> /app/radiopy.log
tail -f /app/radiopy.log &

crontab /app/cronfile
service cron start


# Keep the container running without blocking SIGTERM
wait

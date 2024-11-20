#!/bin/bash

trap "service cron stop && exit 0" SIGTERM

# truncate the log file before tailing it
> /app/radiopy.log
tail -f /app/radiopy.log &

crontab /app/cronfile
service cron start


# Keep the container running without blocking SIGTERM
wait

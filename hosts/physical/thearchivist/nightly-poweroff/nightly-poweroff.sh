#!/bin/bash
set -euo pipefail
RTC=/sys/class/rtc/rtc0/wakealarm
EPOCH=$(date -d 'tomorrow 07:45' +%s)
echo 0 > "$RTC"
echo "$EPOCH" > "$RTC"
logger -t nightly-poweroff "Wake alarm set for $(date -d @"$EPOCH")"
/sbin/shutdown -h +5 "Scheduled shutdown. Wake at $(date -d @"$EPOCH" '+%H:%M'). Abort: shutdown -c"

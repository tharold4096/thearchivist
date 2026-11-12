#!/bin/bash

# --- tuning ---
THRESHOLD=75           # Celsius, CPU die temp. NOT ambient - see notes.
FAN_PERCENT=0x0a       # hex. 0x14=20%, 0x0f=15%, 0x1e=30%
CHECK_INTERVAL=30      # seconds
SANITY_MIN=10          # reject readings below this as garbage
SANITY_MAX=150         # reject readings above this as garbage

set_manual() {
    ipmitool raw 0x30 0x30 0x01 0x00
    ipmitool raw 0x30 0x30 0x02 0xff $FAN_PERCENT
    echo "$(date): manual mode, fans at $FAN_PERCENT"
}

set_auto() {
    ipmitool raw 0x30 0x30 0x01 0x01
    echo "$(date): automatic fan control restored"
}

# revert to auto if this script is stopped, killed, or crashes
trap 'echo "$(date): exiting, failing safe"; set_auto; exit 0' SIGTERM SIGINT

read_max_cpu_temp() {
    sensors -u 2>/dev/null \
        | grep 'temp[0-9]*_input' \
        | awk '{print $2}' \
        | cut -d. -f1 \
        | grep -E '^[0-9]+$' \
        | sort -rn \
        | head -1
}

read_ambient() {
    ipmitool sdr type Temperature 2>/dev/null \
        | grep -i 'Ambient Temp' \
        | awk -F'|' '{print $5}' \
        | grep -oE '[0-9]+' \
        | head -1
}

set_manual

while true; do
    MAXTEMP=$(read_max_cpu_temp)
    AMBIENT=$(read_ambient)

    if [ -z "$MAXTEMP" ]; then
        echo "$(date): CPU temp unreadable - failing safe to auto"
        set_auto
        exit 1
    fi

    if [ "$MAXTEMP" -lt "$SANITY_MIN" ] || [ "$MAXTEMP" -gt "$SANITY_MAX" ]; then
        echo "$(date): implausible reading ${MAXTEMP}C - failing safe to auto"
        set_auto
        exit 1
    fi

    echo "$(date): CPU max ${MAXTEMP}C, ambient ${AMBIENT:-n/a}C"

    if [ "$MAXTEMP" -ge "$THRESHOLD" ]; then
        echo "$(date): ${MAXTEMP}C >= ${THRESHOLD}C threshold"
        set_auto
        exit 0
    fi

    sleep $CHECK_INTERVAL
done

#!/bin/bash

WESTON_DIR="/etc/xdg/weston"
# Check if weston.ini backup exists
if [ -f "$WESTON_DIR/weston.ini.bak" ]; then
    echo "Restoring weston.ini from backup..."
    cp -f "$WESTON_DIR/weston.ini.bak" "$WESTON_DIR/weston.ini"
    if [ $? -ne 0 ]; then
        echo "Restore failed"
        exit 1
    else
        echo "Restore successful"
    fi
else
    echo "No backup file found to restore. Skipping restore step, while removing the current weston.ini"
    yes | rm "$WESTON_DIR/weston.ini"
    if [ $? -ne 0 ]
    then
        echo "Failed to remove weston.ini"
    fi
fi

exec  /usr/sbin/shutdown now
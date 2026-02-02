#!/bin/bash
# Linux/Unix shell script to run sync scheduler
# Make executable: chmod +x run_sync_scheduler.sh

cd "$(dirname "$0")"
python3 run_sync_scheduler.py

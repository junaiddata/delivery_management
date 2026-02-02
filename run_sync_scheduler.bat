@echo off
REM Windows batch file to run sync scheduler
REM Run this file to start the scheduler

cd /d "%~dp0"
python run_sync_scheduler.py
pause

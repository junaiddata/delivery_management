@echo off
REM =========================================
REM Run sync scheduler using pythonw (no console)
REM =========================================

cd /d "D:\dataanalyst\IMPORTANT\DO DATABASE BACKUP\do_complete_from_pa\delivery_management"

"C:\Python313\pythonw.exe" run_sync_non_one_scheduler.py >> logs\non_one_scheduler_script.log 2>&1
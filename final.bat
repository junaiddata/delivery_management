@echo off
REM =========================================
REM Run sync scheduler using pythonw (no console)
REM =========================================

cd /d "D:\dataanalyst\IMPORTANT\DO DATABASE BACKUP\do_complete_from_pa\delivery_management"

"C:\Python313\pythonw.exe" run_sync_scheduler.py >> logs\scheculer.log 2>&1
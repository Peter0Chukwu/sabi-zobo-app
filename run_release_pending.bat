@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
echo ---- %date% %time% ---- >> logs\release_pending.log
venv\Scripts\python.exe manage.py release_pending >> logs\release_pending.log 2>&1
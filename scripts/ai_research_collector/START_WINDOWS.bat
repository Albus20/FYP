@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
set "COLLECTOR_PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "COLLECTOR_PY=py -3"
if defined COLLECTOR_PY goto create_env
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "COLLECTOR_PY=python"
if not defined COLLECTOR_PY (
    echo Python 3.10+ was not found. Install it from https://www.python.org/downloads/
    echo Enable "Add python.exe to PATH", then reopen this file.
    goto end
)
:create_env
if exist .venv\Scripts\python.exe goto check_env
echo Preparing local Python environment...
%COLLECTOR_PY% -m venv .venv > logs\setup.log 2>&1
if errorlevel 1 goto setup_failed
:check_env
.venv\Scripts\python.exe -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 goto setup_failed
.venv\Scripts\python.exe -c "import requests, bs4" >nul 2>&1
if not errorlevel 1 goto launch
echo Installing dependencies; please wait. Details: logs\setup.log
.venv\Scripts\python.exe -m pip install --retries 1 --timeout 20 -r requirements.txt >> logs\setup.log 2>&1
if errorlevel 1 goto setup_failed
:launch
.venv\Scripts\python.exe -u launch.py
goto end
:setup_failed
echo Setup failed. See logs\setup.log for details.
echo Check your network/proxy and Python installation, then run this again.
:end
pause
endlocal

@echo off
title AI Coding Agent Framework
:: Always run from this script's folder (fixes double-click from ZIP/downloads)
cd /d "%~dp0"

:: ── Find a Python interpreter ─────────────────────────────
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py"
if not defined PY goto :nopython

:: ── First-run check: install dependencies if missing ─────
%PY% -c "import openai" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ============================================
    echo  First run - installing dependencies...
    echo  This takes a minute. Please wait.
    echo ============================================
    %PY% -m pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo  ERROR: dependency install failed. See message above.
        pause
        exit /b 1
    )
)

:: ── Verify the app imports cleanly (errors shown here) ───
%PY% -c "import aicoder.gui" 2>import_error.tmp
if %ERRORLEVEL% NEQ 0 (
    echo ============================================
    echo  ERROR: the app failed to load:
    echo ============================================
    type import_error.tmp
    del import_error.tmp >nul 2>&1
    pause
    exit /b 1
)
del import_error.tmp >nul 2>&1

:: ── Launch without a console window ───────────────────────
where pythonw >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" pythonw -m aicoder.gui
    exit
)
where pyw >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" pyw -m aicoder.gui
    exit
)
:: Fallback: console python (window stays open)
start "" %PY% -m aicoder.gui
exit

:nopython
echo ============================================
echo  Python is not installed on this machine.
echo.
echo  To run this app, you need Python 3.9+:
echo    1. Download from https://python.org
echo    2. Check "Add Python to PATH" during install
echo    3. Then double-click run.bat again
echo ============================================
pause

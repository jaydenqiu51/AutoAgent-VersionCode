@echo off
title AI Coding Agent Framework

:: Launch GUI without a console window (pythonw / pyw)
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

:: Fallback: try python.exe (console will stay open)
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" python -m aicoder.gui
    exit
)

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" py -m aicoder.gui
    exit
)

:: No Python found
echo ============================================
echo  Python is not installed on this machine.
echo.
echo  To run this app, you need Python 3.9+:
echo    1. Download from https://python.org
echo    2. Check "Add Python to PATH" during install
echo    3. Then open a terminal here and run:
echo       pip install -e .
echo       aicoder --gui
echo.
echo  Once built, you can create a standalone .exe:
echo       pip install pyinstaller
echo       python build.py
echo       Then double-click dist\AICoder.exe anytime
echo ============================================
pause

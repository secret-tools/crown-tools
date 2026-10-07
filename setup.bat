@echo off
setlocal
cd /d "%~dp0"
title CROWN-TOOLS - Installation
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Crown\lib\launch.ps1" -Setup
set "CROWN_EXIT=%ERRORLEVEL%"
pause
exit /b %CROWN_EXIT%

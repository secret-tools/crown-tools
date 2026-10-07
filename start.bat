@echo off
setlocal
cd /d "%~dp0"
title CROWN-TOOLS
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Crown\lib\launch.ps1" %*
set "CROWN_EXIT=%ERRORLEVEL%"
if not "%CROWN_EXIT%"=="0" pause
exit /b %CROWN_EXIT%

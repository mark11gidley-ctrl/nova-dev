@echo off
rem install-deps.bat: installs what nova-dev needs on Windows.
rem Asks before each program. Uses winget (built into Windows 10 and 11).
rem Run it from the nova-dev folder, or double-click it.

setlocal
cd /d "%~dp0"

where winget >nul 2>nul
if errorlevel 1 (
  echo winget is not available. Install "App Installer" from the Microsoft Store, then run this again.
  pause
  exit /b 1
)

echo.
echo nova-dev dependency installer
echo ------------------------------
echo Each item below asks for y or N. Nothing installs without your answer.
echo.

call :ask "Python 3.13 - required" Python.Python.3.13 PY
call :ask "Git - required" Git.Git GIT
call :ask "Node.js LTS - needed for Codex" OpenJS.NodeJS.LTS NODE
call :ask "ffmpeg - optional, for video tools" Gyan.FFmpeg FFMPEG

echo.
where npm >nul 2>nul
if errorlevel 1 (
  echo npm is not on PATH yet. Open a new window after Node.js is installed, then run this again for the Codex CLI.
) else (
  set /p CODEX=Install the Codex CLI with npm? [y/N]:
  if /i "%CODEX%"=="y" call npm install -g @openai/codex
)

echo.
echo Done. Open a NEW terminal so the new programs are on PATH.
echo Then check the install with:  py -3 -I scripts\doctor.py
echo.
pause
exit /b 0

:ask
rem %1 = label, %2 = winget package id, %3 = variable name for the answer
set "ANSWER="
set /p ANSWER=Install %~1? [y/N]:
if /i "%ANSWER%"=="y" (
  winget install -e --id %2 --silent --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (echo   winget reported a problem for %~1. See the messages above.) else (echo   %~1: done)
) else (
  echo   skipped %~1
)
echo.
goto :eof

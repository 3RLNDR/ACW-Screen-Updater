@echo off
cd /d "%~dp0"
start "" http://localhost:8080/
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Start-AcwDisplay.ps1"

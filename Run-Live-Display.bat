@echo off
cd /d "C:\Users\chris\Documents\ACW Screen Updater"
start "" http://localhost:8080/
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Start-AcwDisplay.ps1"

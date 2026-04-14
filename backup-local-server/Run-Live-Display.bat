@echo off
cd /d "C:\Users\chris\OneDrive\Documents\ACW Screen Updater"
start "" http://localhost:8080/
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Start-AcwDisplay.ps1"

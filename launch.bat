@echo off
cd /d "%~dp0"
if exist "release-v08\RiffTonic\RiffTonic.exe" (
    start "" "release-v08\RiffTonic\RiffTonic.exe"
) else (
    ".venv\Scripts\pythonw.exe" "app.py"
)

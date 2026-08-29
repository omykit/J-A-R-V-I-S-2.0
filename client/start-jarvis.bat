@echo off
cd /d "%~dp0\.."
set "LOGFILE=%~dp0..\jarvis_startup.log"
echo [%date% %time%] Jarvis client startup requested>>"%LOGFILE%"

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "client\desktop_app.py"
    echo [%date% %time%] Launched with project .venv pythonw.exe>>"%LOGFILE%"
    exit /b 0
)

where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw "client\desktop_app.py"
    echo [%date% %time%] Launched with PATH pythonw>>"%LOGFILE%"
    exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    start "Jarvis Launcher" cmd /c py "client\desktop_app.py"
    echo [%date% %time%] Fell back to py launcher>>"%LOGFILE%"
    exit /b 0
)

echo [%date% %time%] No Python launcher found>>"%LOGFILE%"

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================
echo InputMonitor - Desktop Installer
echo ================================
echo.

python -c "import pynput,customtkinter" 2>nul
if errorlevel 1 (
    pip install -r requirements.txt
    if errorlevel 1 (
        echo pip install failed. Run manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

powershell -Command ^
$ws=New-Object -ComObject WScript.Shell;^
$sc=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\InputMonitor.lnk');^
$sc.TargetPath='pythonw.exe';^
$sc.Arguments='main.py';^
$sc.WorkingDirectory='%~dp0';^
$sc.Save()

if errorlevel 1 (
    echo Shortcut created (or failed - check Desktop).
) else (
    echo Shortcut created on Desktop.
)

echo.
echo Done! Double-click InputMonitor.lnk on Desktop to start.
pause

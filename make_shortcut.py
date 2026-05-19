#!/usr/bin/env python3
"""Create InputMonitor desktop shortcut"""
import os, sys, subprocess

desktop = os.path.join(os.path.expanduser("~"), "Desktop")
sandbox = sys.path[0] if sys.path[0] else os.getcwd()

ps = """
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\\InputMonitor.lnk')
$sc.TargetPath = 'pythonw.exe'
$sc.Arguments = 'launcher.py'
$sc.WorkingDirectory = '""" + sandbox + """'
$sc.Description = 'InputMonitor'
$sc.Save()
Write-Host 'Shortcut created'
"""

r = subprocess.run(['powershell', '-Command', ps], capture_output=True, text=True)
print(r.stdout)
if r.returncode != 0:
    # Fallback: create a batch file instead
    bat = os.path.join(desktop, 'InputMonitor.bat')
    with open(bat, 'w') as f:
        f.write('@echo off\r\n')
        f.write('cd /d "' + sandbox + '"\r\n')
        f.write('start "" pythonw launcher.py\r\n')
    print('Batch file created as fallback:', bat)

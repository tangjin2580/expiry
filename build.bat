@echo off
chcp 65001 >nul 2>&1
title Expiry Reminder Builder

set "ROOT=%~dp0"
set "PYTHON=%ROOT%venv\Scripts\python.exe"
set "PIP=%ROOT%venv\Scripts\pip.exe"

echo ==========================================

echo   Expiry Reminder - PyInstaller Builder
echo ==========================================
echo.

echo [1/4] Installing dependencies...
"%PIP%" install openpyxl xlrd pyinstaller pystray Pillow -q

echo.
echo [2/4] Locating Tcl/Tk (Python 3.13+ fix)...
for /f "delims=" %%a in ('"%PYTHON%" -c "import sys,os;cfg=os.path.join(os.path.dirname(sys.executable),'..','pyvenv.cfg');h='';f=open(cfg);[(h:=l.split('=',1)[1].strip()) for l in f if l.startswith('home')];f.close();tcl=os.path.join(h,'tcl','tcl8.6') if h else '';tk=os.path.join(h,'tcl','tk8.6') if h else '';print(tcl+';'+tk if os.path.isdir(tcl) else 'NONE')"') do set "TCL_TK=%%a"
if "%TCL_TK%"=="NONE" (
    echo   WARNING: Tcl/Tk not found, tkinter may be excluded!
    set "ADD_TCL="
    set "TCL_LIBRARY="
    set "TK_LIBRARY="
) else (
    for /f "tokens=1,2 delims=;" %%x in ("%TCL_TK%") do (
        set "TCL_LIBRARY=%%x"
        set "TK_LIBRARY=%%y"
        set "ADD_TCL=--add-data %%x;tcl\tcl8.6 --add-data %%y;tcl\tk8.6"
        echo   TCL: %%x
        echo   TK:  %%y
    )
)

:: venv 下 _tkinter.pyd 和 DLL 在 Scripts/ 而非 DLLs/，需手动添加
set "VENV_BIN=%ROOT%venv\Scripts"
set "ADD_TK_BIN=--add-binary %VENV_BIN%\_tkinter.pyd;. --add-binary %VENV_BIN%\tcl86t.dll;. --add-binary %VENV_BIN%\tk86t.dll;."

:: 自动检测桌面路径（兼容自定义桌面）
for /f "tokens=2*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop 2^>nul') do set "DESKTOP_DIR=%%b"
if not defined DESKTOP_DIR set "DESKTOP_DIR=%USERPROFILE%\Desktop"
echo   Desktop: %DESKTOP_DIR%

echo.
echo [3/4] Building single exe (please wait)...
cd /d "%ROOT%"
"%PYTHON%" -m PyInstaller --name 九九到期提醒工具 --windowed --onefile --icon=assets/icon.ico --add-data "assets;assets" --add-data "README.md;." %ADD_TCL% %ADD_TK_BIN% --hidden-import modules --hidden-import modules.config --hidden-import modules.utils --hidden-import modules.widgets --hidden-import modules.history_panel --hidden-import modules.analysis_panel --hidden-import modules.file_ops --hidden-import modules.notify_panel --hidden-import modules.robot_sync --hidden-import modules.tray_handler --hidden-import modules.update_panel --distpath "%DESKTOP_DIR%" expiry_reminder.py

echo.
echo [4/4] Cleanup...
rmdir /s /q build 2>nul
del /f 九九到期提醒工具.spec 2>nul

echo.
echo ==========================================
echo   Build complete!
echo   Desktop ^> 九九到期提醒工具.exe
echo ==========================================
pause

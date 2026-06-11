@echo off
chcp 65001 >nul 2>&1
title Expiry Reminder Builder

echo ==========================================
echo   Expiry Reminder - PyInstaller Builder
echo ==========================================
echo.
echo NOTE: Put build.bat AND expiry_reminder.py
echo       in the same folder, then run this.
echo.

echo [1/4] Installing dependencies...
pip install openpyxl xlrd pyinstaller win10toast 2>nul

echo.
echo [2/4] Building single exe (please wait)...
pyinstaller --name 九九到期提醒工具 --windowed --onefile --icon=1.ico --distpath %USERPROFILE%\Desktop --hidden-import robot_sync --hidden-import notify_panel --hidden-import history_panel --hidden-import analysis_panel --hidden-import file_ops --hidden-import widgets --hidden-import config --hidden-import utils expiry_reminder.py

echo.
echo [3/4] Cleanup...
rmdir /s /q build 2>nul
del /f 九九到期提醒工具.spec 2>nul

echo.
echo ==========================================
echo   Build complete!
echo   Desktop ^> 九九到期提醒工具.exe
echo ==========================================
pause
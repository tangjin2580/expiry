@echo off
chcp 65001 >nul 2>&1
title Expiry Reminder Builder

echo ==========================================
echo   Expiry Reminder - PyInstaller Builder
echo ==========================================
echo.

echo [1/4] Installing dependencies...
pip install openpyxl xlrd pyinstaller win10toast 2>nul

echo.
echo [2/4] Building single exe (please wait)...
pyinstaller --name 九九到期提醒工具 --windowed --onefile --icon=assets/icon.ico --add-data "assets;assets" --hidden-import modules --hidden-import modules.config --hidden-import modules.utils --hidden-import modules.widgets --hidden-import modules.history_panel --hidden-import modules.analysis_panel --hidden-import modules.file_ops --hidden-import modules.notify_panel --hidden-import modules.robot_sync --distpath %USERPROFILE%\Desktop expiry_reminder.py

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

@echo off
chcp 65001 >nul 2>&1
title 到期提醒工具

:: 定位系统 Python 的 Tcl/Tk 目录（修复 venv 路径问题）
for /f "delims=" %%I in ('where python') do (
    set "_PY_HOME=%%~dpI"
    goto :found
)
:found
if exist "%_PY_HOME%tcl\tcl8.6\init.tcl" (
    set "TCL_LIBRARY=%_PY_HOME%tcl\tcl8.6"
    set "TK_LIBRARY=%_PY_HOME%tcl\tk8.6"
)

:: 检查是否带了 --background 参数，透传给 Python
if "%~1"=="--background" (
    "%~dp0venv\Scripts\python.exe" "%~dp0expiry_reminder.py" --background
) else (
    "%~dp0venv\Scripts\python.exe" "%~dp0expiry_reminder.py" %*
)

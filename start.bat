@echo off
title CutFlow Studio Launcher
echo ========================================================
echo   CutFlow Studio - AI Video Prep ^& Smart Editor
echo ========================================================
echo.
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe run.py
) else (
    python run.py
)
pause

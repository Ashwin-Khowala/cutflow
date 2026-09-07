#!/usr/bin/env bash
echo "========================================================"
echo "  CutFlow Studio - AI Video Prep & Smart Editor"
echo "========================================================"
echo ""

if [ -f ".venv/Scripts/python.exe" ]; then
    .venv/Scripts/python.exe run.py
elif [ -f ".venv/bin/python" ]; then
    .venv/bin/python run.py
else
    python3 run.py || python run.py
fi

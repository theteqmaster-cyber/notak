#!/bin/bash
# --- Notak Production Launcher ---
# (Handles environment setup and execution for a seamless study session)

# 1. Navigate to script directory
cd "$(dirname "$0")"

# 2. Check for virtual environment and create if missing
if [ ! -d "venv" ]; then
    echo "First time setup: Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 3. Launch the Hub
python3 main.py

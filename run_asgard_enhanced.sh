#!/bin/bash
# Launch Asgard Enhanced GUI
# Linux/Mac shell script

echo "========================================"
echo "Asgard Enhanced - Thor Robotic Arm"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run: python3 -m venv venv"
    echo "Then: source venv/bin/activate"
    echo "Then: pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Launch GUI
echo "Starting Asgard Enhanced GUI..."
echo ""
python3 asgard_enhanced.py

# Deactivate on exit
deactivate

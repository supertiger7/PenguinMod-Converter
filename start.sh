#!/bin/bash
# PenguinMod File Converter - Unix/Linux/Mac Launcher

echo ""
echo "🐧 PenguinMod File Converter"
echo "=================================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo ""
    echo "Please install Python 3.8 or higher:"
    echo "  Ubuntu/Debian: sudo apt-get install python3"
    echo "  Fedora: sudo dnf install python3"
    echo "  macOS: brew install python3"
    exit 1
fi

echo "✓ Python 3 is installed"
echo ""

# Run the launcher script
python3 run.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Application encountered an error"
    exit 1
fi

echo ""
echo "Application closed successfully"

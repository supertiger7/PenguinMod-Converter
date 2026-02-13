#!/usr/bin/env python3
"""
PenguinMod File Converter - Launcher
Simple launcher script with error handling
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is sufficient"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    return True

def check_tkinter():
    """Check if tkinter is available"""
    try:
        import tkinter
        return True
    except ImportError:
        print("❌ Error: tkinter is not installed")
        print("\nInstallation instructions:")
        print("  Ubuntu/Debian: sudo apt-get install python3-tk")
        print("  Fedora: sudo dnf install python3-tkinter")
        print("  macOS: Should be included with Python")
        print("  Windows: Should be included with Python")
        return False

def main():
    """Main launcher function"""
    print("🐧 PenguinMod File Converter")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    print("✓ Python version OK")
    
    # Check tkinter
    if not check_tkinter():
        sys.exit(1)
    print("✓ tkinter available")
    
    # Check if main file exists
    main_file = Path(__file__).parent / "pmp_converter.py"
    if not main_file.exists():
        print(f"❌ Error: {main_file} not found")
        sys.exit(1)
    print("✓ Main file found")
    
    print("\n🚀 Starting PenguinMod File Converter...")
    print("=" * 50)
    
    # Run the main application
    try:
        import pmp_converter
        pmp_converter.main()
    except KeyboardInterrupt:
        print("\n\n👋 Application closed by user")
    except Exception as e:
        print(f"\n❌ Error running application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

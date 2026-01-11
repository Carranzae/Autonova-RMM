"""
Autonova RMM Agent - PyInstaller Entry Point
This file is the entry point when running as a compiled .exe
"""

import sys
import os

# Add the src directory to path
if getattr(sys, 'frozen', False):
    # Running as compiled
    base_path = sys._MEIPASS
else:
    # Running as script
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)
sys.path.insert(0, os.path.join(base_path, 'src'))

# Now import and run
from src.main import run

if __name__ == '__main__':
    run()

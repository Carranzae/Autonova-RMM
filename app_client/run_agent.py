"""
Autonova RMM Agent - PyInstaller Entry Point
This is the main entry point when running as a compiled .exe
"""

import sys
import os
from pathlib import Path

def setup_paths():
    """Setup paths for both frozen and normal execution."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - use _MEIPASS
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script
        base_path = Path(__file__).parent
    
    # Add paths
    src_path = base_path / 'src'
    if src_path.exists():
        sys.path.insert(0, str(src_path))
    sys.path.insert(0, str(base_path))
    
    return base_path

def main():
    """Main entry point."""
    setup_paths()
    
    # Import and run
    try:
        from src.main import run
        run()
    except ImportError:
        # Fallback for when running inside src directory
        try:
            from main import run
            run()
        except ImportError as e:
            print(f"Import Error: {e}")
            print("Could not import main module.")
            input("Press Enter to exit...")
            sys.exit(1)

if __name__ == '__main__':
    main()

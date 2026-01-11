"""
Autonova RMM - Build Windows Executable
Creates a standalone .exe for the Windows agent.
"""

import os
import sys
import subprocess
from pathlib import Path

# Configuration
APP_NAME = "AutonovaAgent"
ICON_PATH = None  # Add path to .ico file if you have one
ONE_FILE = True
CONSOLE = False  # Set to True for debugging

def build():
    """Build the executable using PyInstaller."""
    
    print("=" * 50)
    print("  AUTONOVA RMM - Building Windows Executable")
    print("=" * 50)
    
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check PyInstaller is installed
    try:
        import PyInstaller
        print(f"[✓] PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--clean",
        "--noconfirm",
    ]
    
    if ONE_FILE:
        cmd.append("--onefile")
    
    if not CONSOLE:
        cmd.append("--noconsole")
    else:
        cmd.append("--console")
    
    if ICON_PATH and Path(ICON_PATH).exists():
        cmd.extend(["--icon", ICON_PATH])
    
    # Hidden imports for the agent
    hidden_imports = [
        "psutil",
        "socketio",
        "aiohttp",
        "cryptography",
        "winreg",
        "ctypes",
        "asyncio",
        "json",
        "logging",
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    # Add data files
    cmd.extend([
        "--add-data", ".env;.",
    ])
    
    # Entry point
    cmd.append("run_agent.py")
    
    print("\n[*] Building executable...")
    print(f"    Command: {' '.join(cmd)}\n")
    
    # Run PyInstaller
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        exe_path = script_dir / "dist" / f"{APP_NAME}.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 50)
            print(f"  [✓] BUILD SUCCESSFUL!")
            print(f"  [✓] Executable: {exe_path}")
            print(f"  [✓] Size: {size_mb:.1f} MB")
            print("=" * 50)
        else:
            print("\n[!] Build completed but executable not found")
    else:
        print("\n[!] Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    build()

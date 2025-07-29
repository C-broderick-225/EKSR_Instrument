#!/usr/bin/env python3
"""
Launcher script for FarDriver Monitor
"""

import sys
import os
import subprocess

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import bleak
        import tkinter
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install -r requirements_FarDriver_Monitor.txt")
        print("or run: python install_FarDriver_Monitor.py")
        return False

def main():
    """Main launcher function"""
    print("FarDriver Monitor")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check if FarDriver Monitor file exists
    monitor_file = "FarDriver_Monitor.py"
    if not os.path.exists(monitor_file):
        print(f"Error: {monitor_file} not found!")
        print("Please ensure you're running this from the pc_display directory.")
        sys.exit(1)
    
    # Launch the FarDriver Monitor application
    print("Starting FarDriver Monitor...")
    print("Press Ctrl+C to exit")
    print("-" * 50)
    
    try:
        subprocess.run([sys.executable, monitor_file], check=True)
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except subprocess.CalledProcessError as e:
        print(f"Error running application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
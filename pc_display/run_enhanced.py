#!/usr/bin/env python3
"""
Launcher script for EKSR Instrument PC Display - Enhanced Version
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
        print("pip install -r requirements_enhanced.txt")
        return False

def main():
    """Main launcher function"""
    print("EKSR Instrument PC Display - Enhanced Version")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check if enhanced display file exists
    enhanced_file = "pc_display_enhanced.py"
    if not os.path.exists(enhanced_file):
        print(f"Error: {enhanced_file} not found!")
        print("Please ensure you're running this from the pc_display directory.")
        sys.exit(1)
    
    # Launch the enhanced application
    print("Starting enhanced PC display...")
    print("Press Ctrl+C to exit")
    print("-" * 50)
    
    try:
        subprocess.run([sys.executable, enhanced_file], check=True)
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except subprocess.CalledProcessError as e:
        print(f"Error running application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
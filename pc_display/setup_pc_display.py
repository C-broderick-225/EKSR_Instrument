#!/usr/bin/env python3
"""
Setup script for EKSR Instrument PC Display
This script helps set up the environment to run the EKSR Instrument on a PC.
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required Python packages"""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install packages: {e}")
        return False

def check_bluetooth():
    """Check if Bluetooth is available"""
    print("\nChecking Bluetooth support...")
    
    # Check if bleak can import
    try:
        import bleak
        print("✓ Bleak library available")
    except ImportError:
        print("✗ Bleak library not found. Please install it first.")
        return False
    
    # Try to import platform-specific modules
    try:
        if sys.platform.startswith('win'):
            import win32api
            print("✓ Windows Bluetooth support available")
        elif sys.platform.startswith('linux'):
            print("✓ Linux Bluetooth support available")
        elif sys.platform.startswith('darwin'):
            print("✓ macOS Bluetooth support available")
        else:
            print("⚠ Unknown platform, Bluetooth support may be limited")
    except ImportError:
        print("⚠ Platform-specific Bluetooth modules not available")
    
    return True

def print_instructions():
    """Print setup and usage instructions"""
    print("\n" + "="*60)
    print("EKSR INSTRUMENT PC DISPLAY SETUP")
    print("="*60)
    
    print("\nSETUP STEPS:")
    print("1. Flash the FarDriver emulator to an ESP32:")
    print("   - Open emulator/FarDriverEmulator/FarDriverEmulator.ino in Arduino IDE")
    print("   - Install ESP32 board support and NimBLE-Arduino library")
    print("   - Upload to your ESP32 board")
    
    print("\n2. Run the PC display application:")
    print("   python pc_display.py")
    
    print("\n3. The application will:")
    print("   - Scan for 'FarDriver_Emu' BLE device")
    print("   - Connect automatically when found")
    print("   - Display real-time data in a GUI window")
    
    print("\nTROUBLESHOOTING:")
    print("- Make sure Bluetooth is enabled on your computer")
    print("- Ensure the ESP32 emulator is powered and advertising")
    print("- Check that no other BLE applications are connected")
    print("- On Windows, you may need to run as administrator")
    
    print("\nALTERNATIVE OPTIONS:")
    print("- Use a web-based interface (see web_display.py)")
    print("- Use a terminal-based display (see terminal_display.py)")
    print("- Modify the original firmware to output to serial instead of TFT")

def main():
    """Main setup function"""
    print("EKSR Instrument PC Display Setup")
    print("="*40)
    
    # Install requirements
    if not install_requirements():
        print("\nPlease install the requirements manually:")
        print("pip install -r requirements.txt")
        return
    
    # Check Bluetooth support
    if not check_bluetooth():
        print("\nBluetooth support issues detected.")
        print("You may need to install additional drivers or libraries.")
    
    # Print instructions
    print_instructions()
    
    print("\nSetup complete! You can now run:")
    print("python pc_display.py")

if __name__ == "__main__":
    main() 
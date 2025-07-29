#!/usr/bin/env python3
"""
Installation script for FarDriver Monitor
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a Python package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("FarDriver Monitor - Installation")
    print("=" * 50)
    
    # Core dependencies
    print("\n1. Installing core dependencies...")
    core_packages = ["bleak>=0.20.0"]
    
    for package in core_packages:
        print(f"Installing {package}...")
        if install_package(package):
            print(f"✓ {package} installed successfully")
        else:
            print(f"✗ Failed to install {package}")
            return False
    
    # Optional dependencies
    print("\n2. Optional dependencies (for enhanced features):")
    print("   - psutil: Full performance monitoring (memory, CPU)")
    print("   - matplotlib: Real-time charts and graphs")
    print("   - pandas: Advanced data analysis")
    
    install_optional = input("\nInstall optional dependencies? (y/n): ").lower().strip()
    
    if install_optional in ['y', 'yes']:
        optional_packages = [
            "psutil>=5.9.0",
            "matplotlib>=3.5.0",
            "pandas>=1.3.0"
        ]
        
        for package in optional_packages:
            print(f"Installing {package}...")
            if install_package(package):
                print(f"✓ {package} installed successfully")
            else:
                print(f"✗ Failed to install {package}")
    
    print("\n3. Installation complete!")
    print("\nTo run the application:")
    print("   python FarDriver_Monitor.py")
    print("   or use the launcher: python run_enhanced.py")
    
    print("\nFeatures available:")
    print("   ✓ BLE communication and data display")
    print("   ✓ Data recording and export")
    print("   ✓ Packet inspector and analysis")
    print("   ✓ Performance monitoring (basic)")
    
    if install_optional in ['y', 'yes']:
        print("   ✓ Enhanced performance monitoring")
        print("   ✓ Real-time charts (if matplotlib installed)")
        print("   ✓ Advanced data analysis (if pandas installed)")
    
    return True

if __name__ == "__main__":
    main() 
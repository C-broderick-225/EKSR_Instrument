#!/usr/bin/env python3
"""
Simple BLE Scanner for debugging EKSR Instrument connection
"""

import asyncio
from bleak import BleakScanner
import time

async def scan_devices():
    """Scan for BLE devices and display them"""
    print("Scanning for BLE devices...")
    print("=" * 50)
    
    try:
        devices = await BleakScanner.discover(timeout=10.0)
        
        if not devices:
            print("No devices found!")
            return
        
        print(f"Found {len(devices)} device(s):")
        print("-" * 50)
        
        for i, device in enumerate(devices, 1):
            print(f"{i}. Name: {device.name or 'Unknown'}")
            print(f"   Address: {device.address}")
            print(f"   RSSI: {device.rssi} dBm")
            if device.metadata:
                print(f"   Metadata: {device.metadata}")
            print()
            
        # Look specifically for FarDriver devices
        fardriver_devices = [d for d in devices if d.name and "FarDriver" in d.name]
        
        if fardriver_devices:
            print("✓ FarDriver devices found:")
            for device in fardriver_devices:
                print(f"   - {device.name} ({device.address})")
        else:
            print("✗ No FarDriver devices found")
            print("   Make sure the ESP32 is powered and advertising")
            print("   Check that the emulator code is running correctly")
            
    except Exception as e:
        print(f"Error scanning: {e}")

def main():
    """Main function"""
    print("EKSR Instrument BLE Scanner")
    print("This will help debug connection issues")
    print()
    
    try:
        asyncio.run(scan_devices())
    except KeyboardInterrupt:
        print("\nScan interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 
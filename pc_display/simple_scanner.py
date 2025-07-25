#!/usr/bin/env python3
"""
Simple BLE Scanner for ESP32 detection
"""

import asyncio
from bleak import BleakScanner
import sys

async def simple_scan():
    """Simple scan for all BLE devices"""
    print("Simple BLE Scanner")
    print("=" * 30)
    
    try:
        print("Scanning for BLE devices (15 seconds)...")
        devices = await BleakScanner.discover(timeout=15.0)
        
        if not devices:
            print("No devices found!")
            return
        
        print(f"\nFound {len(devices)} device(s):")
        print("-" * 30)
        
        for i, device in enumerate(devices, 1):
            name = device.name or "Unknown"
            address = device.address
            
            # Try to get RSSI safely
            try:
                rssi = device.rssi
                rssi_str = f"RSSI: {rssi} dBm"
            except:
                rssi_str = "RSSI: Unknown"
            
            print(f"{i:2d}. {name}")
            print(f"     Address: {address}")
            print(f"     {rssi_str}")
            
            # Highlight potential ESP32 devices
            if "FarDriver" in name:
                print(f"     *** FARDRIVER DEVICE FOUND! ***")
            elif "ESP32" in name or "esp32" in name:
                print(f"     *** ESP32 DEVICE FOUND! ***")
            elif not name and ":" in address:
                print(f"     *** UNNAMED DEVICE (could be ESP32) ***")
            
            print()
        
        # Summary
        fardriver_count = sum(1 for d in devices if d.name and "FarDriver" in d.name)
        esp32_count = sum(1 for d in devices if d.name and ("ESP32" in d.name or "esp32" in d.name))
        unnamed_count = sum(1 for d in devices if not d.name)
        
        print("Summary:")
        print(f"  FarDriver devices: {fardriver_count}")
        print(f"  ESP32 devices: {esp32_count}")
        print(f"  Unnamed devices: {unnamed_count}")
        
        if fardriver_count == 0:
            print("\n⚠️  No FarDriver devices found!")
            print("   The ESP32 might be advertising with a different name")
            print("   Try looking for unnamed devices or ESP32 devices")
        
    except Exception as e:
        print(f"Scan error: {e}")
        print(f"Error type: {type(e)}")

def main():
    """Main function"""
    try:
        asyncio.run(simple_scan())
    except KeyboardInterrupt:
        print("\nScan interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 
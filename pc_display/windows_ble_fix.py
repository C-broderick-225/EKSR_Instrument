#!/usr/bin/env python3
"""
Windows-specific BLE connection fix for EKSR Instrument
Handles common Windows Bluetooth issues
"""

import asyncio
import sys
import time
from bleak import BleakScanner, BleakClient
import os

# BLE Service and Characteristic UUIDs
FARDRIVER_SERVICE_UUID = "ffe0"
FARDRIVER_CHARACTERISTIC_UUID = "ffec"

async def scan_with_retry(max_attempts=5):
    """Scan for devices with multiple attempts"""
    print("Scanning for FarDriver ESP32...")
    
    for attempt in range(max_attempts):
        print(f"Attempt {attempt + 1}/{max_attempts}")
        
        try:
            # Use longer timeout and different scan parameters
            devices = await BleakScanner.discover(timeout=15.0)
            
            # Look for any device that might be our ESP32
            potential_devices = []
            for device in devices:
                name = device.name or ""
                address = device.address
                
                # Check for exact match
                if "FarDriver" in name:
                    potential_devices.append(("exact", device))
                # Check for ESP32 devices
                elif "ESP32" in name or "esp32" in name:
                    potential_devices.append(("esp32", device))
                # Check for devices with no name but good signal
                elif not name and device.rssi > -60:
                    potential_devices.append(("unknown", device))
            
            if potential_devices:
                print(f"Found {len(potential_devices)} potential device(s):")
                for match_type, device in potential_devices:
                    print(f"  {match_type}: {device.name or 'Unknown'} ({device.address}) RSSI: {device.rssi}")
                return potential_devices
            
            print("No FarDriver devices found. Available devices:")
            for device in devices:
                print(f"  - {device.name or 'Unknown'} ({device.address}) RSSI: {device.rssi}")
                
        except Exception as e:
            print(f"Scan error: {e}")
        
        if attempt < max_attempts - 1:
            print("Waiting 3 seconds before retry...")
            await asyncio.sleep(3)
    
    return []

async def connect_with_retry(device, max_attempts=3):
    """Try to connect with multiple attempts"""
    print(f"\nAttempting to connect to {device.name or device.address}...")
    
    for attempt in range(max_attempts):
        try:
            print(f"Connection attempt {attempt + 1}/{max_attempts}")
            
            # Create client with specific parameters for Windows
            client = BleakClient(device.address)
            
            # Try to connect with longer timeout
            await client.connect(timeout=20.0)
            print("✅ Connected successfully!")
            
            # Test the connection
            if await test_services(client):
                return client
            else:
                await client.disconnect()
                print("Service test failed, retrying...")
                
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                print("Waiting 2 seconds before retry...")
                await asyncio.sleep(2)
    
    return None

async def test_services(client):
    """Test if the required services are available"""
    try:
        print("Testing services...")
        
        # Wait a moment for services to be discovered
        await asyncio.sleep(1)
        
        services = client.services
        fardriver_service_found = False
        
        for service in services:
            print(f"  Service: {service.uuid}")
            if service.uuid.lower() == FARDRIVER_SERVICE_UUID.lower():
                fardriver_service_found = True
                print(f"    ✅ FarDriver service found!")
                
                for char in service.characteristics:
                    print(f"    Characteristic: {char.uuid}")
                    if char.uuid.lower() == FARDRIVER_CHARACTERISTIC_UUID.lower():
                        print(f"      ✅ FarDriver characteristic found!")
                        return True
        
        if not fardriver_service_found:
            print("  ❌ FarDriver service not found")
            return False
            
    except Exception as e:
        print(f"Service test error: {e}")
        return False

async def main():
    """Main connection function"""
    print("EKSR Instrument Windows BLE Connection Fix")
    print("=" * 50)
    
    # Check if running on Windows
    if not sys.platform.startswith('win'):
        print("This script is designed for Windows")
        return
    
    print("Windows detected - applying Windows-specific fixes...")
    
    # Scan for devices
    devices = await scan_with_retry()
    
    if not devices:
        print("\n❌ No suitable devices found!")
        print("\nTroubleshooting tips:")
        print("1. Make sure Bluetooth is enabled")
        print("2. Try running as Administrator")
        print("3. Check Windows Bluetooth settings")
        print("4. Restart the ESP32")
        return
    
    # Try to connect to the best candidate
    best_device = None
    for match_type, device in devices:
        if match_type == "exact":
            best_device = device
            break
        elif match_type == "esp32" and not best_device:
            best_device = device
    
    if not best_device and devices:
        best_device = devices[0][1]
    
    if best_device:
        client = await connect_with_retry(best_device)
        
        if client:
            print("\n🎉 Successfully connected!")
            print("You can now run the display applications:")
            print("  python terminal_display.py")
            print("  python pc_display.py")
            
            # Keep connection alive for a moment
            try:
                await asyncio.sleep(5)
            except KeyboardInterrupt:
                pass
            finally:
                await client.disconnect()
                print("Disconnected")
        else:
            print("\n❌ Failed to connect to any device")
    else:
        print("\n❌ No suitable devices to connect to")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}") 
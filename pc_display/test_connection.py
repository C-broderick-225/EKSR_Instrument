#!/usr/bin/env python3
"""
Test connection to FarDriver ESP32 emulator
"""

import asyncio
from bleak import BleakScanner, BleakClient
import time

# BLE Service and Characteristic UUIDs
FARDRIVER_SERVICE_UUID = "ffe0"
FARDRIVER_CHARACTERISTIC_UUID = "ffec"

async def test_connection():
    """Test connection to FarDriver emulator"""
    print("Testing FarDriver ESP32 connection...")
    print("=" * 50)
    
    # First, scan for devices
    print("1. Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=10.0)
    
    fardriver_devices = []
    for device in devices:
        if device.name and "FarDriver" in device.name:
            fardriver_devices.append(device)
    
    if not fardriver_devices:
        print("❌ No FarDriver devices found!")
        print("Available devices:")
        for device in devices:
            print(f"   - {device.name or 'Unknown'} ({device.address})")
        return False
    
    print(f"✅ Found {len(fardriver_devices)} FarDriver device(s):")
    for device in fardriver_devices:
        print(f"   - {device.name} ({device.address})")
    
    # Try to connect to the first FarDriver device
    device = fardriver_devices[0]
    print(f"\n2. Attempting to connect to {device.name}...")
    
    try:
        client = BleakClient(device.address)
        await client.connect(timeout=10.0)
        print("✅ Connected successfully!")
        
        # Check if the service exists
        print("\n3. Checking services...")
        services = client.services
        for service in services:
            print(f"   Service: {service.uuid}")
            for char in service.characteristics:
                print(f"     Characteristic: {char.uuid} - Properties: {char.properties}")
        
        # Try to subscribe to notifications
        print("\n4. Testing notification subscription...")
        notification_received = False
        
        def notification_handler(sender, data):
            nonlocal notification_received
            notification_received = True
            print(f"✅ Received notification: {data.hex()}")
        
        await client.start_notify(FARDRIVER_CHARACTERISTIC_UUID, notification_handler)
        print("✅ Notification subscription successful!")
        
        # Wait for a notification
        print("\n5. Waiting for data (10 seconds)...")
        for i in range(10):
            if notification_received:
                break
            print(f"   Waiting... {i+1}/10")
            await asyncio.sleep(1)
        
        if notification_received:
            print("✅ Data received successfully!")
        else:
            print("⚠️  No data received in 10 seconds")
        
        # Send keep-alive packet
        print("\n6. Testing keep-alive packet...")
        keep_alive = bytes([0xAA, 0x13, 0xEC, 0x07, 0x01, 0xF1, 0xA2, 0x5D])
        await client.write_gatt_char(FARDRIVER_CHARACTERISTIC_UUID, keep_alive)
        print("✅ Keep-alive packet sent!")
        
        # Disconnect
        await client.disconnect()
        print("✅ Disconnected successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def main():
    """Main function"""
    try:
        success = asyncio.run(test_connection())
        if success:
            print("\n🎉 All tests passed! The ESP32 is working correctly.")
        else:
            print("\n❌ Tests failed. Check the ESP32 and try again.")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 
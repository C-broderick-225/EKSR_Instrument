#!/usr/bin/env python3
"""
EKSR Instrument Terminal Display
A simple terminal-based display for the EKSR Instrument data.
Works on any system with a terminal, no GUI required.
"""

import asyncio
import threading
import time
import os
import sys
from bleak import BleakScanner, BleakClient

# BLE Service and Characteristic UUIDs
FARDRIVER_SERVICE_UUID = "ffe0"
FARDRIVER_CHARACTERISTIC_UUID = "ffec"

# Data structure to hold controller data
class ControllerData:
    def __init__(self):
        self.throttle = 0
        self.gear = 0
        self.rpm = 0
        self.controller_temp = 0
        self.motor_temp = 0
        self.speed = 0
        self.power = 0
        self.voltage = 0

# Global variables
ctr_data = ControllerData()
is_connected = False
client = None

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the application header"""
    print("=" * 60)
    print("           EKSR INSTRUMENT TERMINAL DISPLAY")
    print("=" * 60)

def print_status():
    """Print connection status"""
    status = "CONNECTED" if is_connected else "DISCONNECTED"
    color = "\033[92m" if is_connected else "\033[91m"  # Green if connected, red if not
    reset = "\033[0m"
    print(f"{color}Status: {status}{reset}")

def print_power_meter():
    """Print a simple power meter"""
    power = abs(ctr_data.power)
    max_power = 20.0
    bar_length = 40
    filled_length = int((power / max_power) * bar_length)
    
    # Create the bar
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    # Color based on power type
    if ctr_data.power == 0:
        color = "\033[37m"  # White
    elif ctr_data.power < 0:
        color = "\033[92m"  # Green (driving)
    else:
        color = "\033[91m"  # Red (regen)
    
    reset = "\033[0m"
    
    print(f"\n{color}POWER: {ctr_data.power:6.1f} kW{reset}")
    print(f"[{color}{bar}{reset}]")
    print(f"     0{' ' * (bar_length-10)}20 kW")

def print_battery():
    """Print battery voltage and level"""
    voltage = ctr_data.voltage
    low_limit = 84.0
    high_limit = 96.0
    
    # Calculate battery level
    level = max(0.0, min(1.0, (voltage - low_limit) / (high_limit - low_limit)))
    bar_length = 20
    filled_length = int(level * bar_length)
    
    # Color based on level
    if level > 0.5:
        color = "\033[92m"  # Green
    elif level > 0.2:
        color = "\033[93m"  # Yellow
    else:
        color = "\033[91m"  # Red
    
    reset = "\033[0m"
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    print(f"\n{color}BATTERY: {voltage:5.1f}V{reset}")
    print(f"[{color}{bar}{reset}]")
    print(f"    {low_limit}V{' ' * (bar_length-8)}{high_limit}V")

def print_speed():
    """Print speed display"""
    speed = ctr_data.speed
    print(f"\n\033[96mSPEED: {speed:5.1f} km/h\033[0m")

def print_rpm():
    """Print RPM with progress bar"""
    rpm = ctr_data.rpm
    max_rpm = 8000
    bar_length = 30
    filled_length = int((rpm / max_rpm) * bar_length)
    
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    print(f"\n\033[96mRPM: {rpm:4d}\033[0m")
    print(f"[{bar}]")
    print(f"   0{' ' * (bar_length-5)}{max_rpm}")

def print_temperatures():
    """Print temperature readings"""
    print(f"\n\033[93mMotor Temp:     {ctr_data.motor_temp:5.1f}°C\033[0m")
    print(f"\033[93mController Temp: {ctr_data.controller_temp:5.1f}°C\033[0m")

def print_controls():
    """Print gear and throttle information"""
    gear = ctr_data.gear
    throttle = ctr_data.throttle
    throttle_percent = (throttle / 5000.0) * 100
    
    # Throttle bar
    bar_length = 20
    filled_length = int((throttle_percent / 100.0) * bar_length)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    print(f"\n\033[95mGear: {gear}\033[0m")
    print(f"\033[95mThrottle: {throttle_percent:5.1f}%\033[0m")
    print(f"[{bar}]")
    print(f"   0%{' ' * (bar_length-5)}100%")

def print_data():
    """Print all data in a formatted way"""
    clear_screen()
    print_header()
    print_status()
    print_power_meter()
    print_battery()
    print_speed()
    print_rpm()
    print_temperatures()
    print_controls()
    print("\n" + "=" * 60)
    print("Press Ctrl+C to exit")

def message_handler(data):
    """Process incoming BLE data packets"""
    global ctr_data
    
    if len(data) < 16:
        return
    
    # Check for 0xAA header
    if data[0] != 0xAA:
        return
    
    index = data[1]
    
    # Process different packet types
    if index == 0:  # Main data
        ctr_data.rpm = (data[6] << 8) | data[7]
        ctr_data.gear = ((data[4] >> 2) & 0x03)
        ctr_data.gear = max(1, min(3, ctr_data.gear))
        
        # Calculate power from current values
        iq = ((data[10] << 8) | data[11]) / 100.0
        id = ((data[12] << 8) | data[13]) / 100.0
        is_mag = (iq * iq + id * id) ** 0.5
        ctr_data.power = -is_mag * ctr_data.voltage / 1000.0
        
        if iq < 0 or id < 0:
            ctr_data.power = -ctr_data.power
        
        # Calculate speed (simplified)
        wheel_circumference = 1.350  # meters
        rear_wheel_rpm = ctr_data.rpm / 4.0
        distance_per_min = rear_wheel_rpm * wheel_circumference
        ctr_data.speed = distance_per_min * 0.06  # km/h
        
    elif index == 1:  # Voltage
        ctr_data.voltage = ((data[2] << 8) | data[3]) / 10.0
        
    elif index == 4:  # Controller temperature
        ctr_data.controller_temp = data[4]
        
    elif index == 13:  # Motor temperature and throttle
        ctr_data.motor_temp = data[2]
        ctr_data.throttle = (data[4] << 8) | data[5]

async def scan_and_connect():
    """Scan for and connect to FarDriver emulator"""
    global client, is_connected
    
    print("Scanning for FarDriver emulator...")
    
    while True:
        try:
            # Scan for devices
            devices = await BleakScanner.discover()
            
            for device in devices:
                if device.name and "FarDriver" in device.name:
                    print(f"Found FarDriver device: {device.name} ({device.address})")
                    
                    # Try to connect
                    try:
                        client = BleakClient(device.address)
                        await client.connect()
                        is_connected = True
                        print("Connected to FarDriver emulator!")
                        
                        # Subscribe to notifications
                        await client.start_notify(FARDRIVER_CHARACTERISTIC_UUID, 
                                                lambda sender, data: message_handler(data))
                        
                        # Keep connection alive
                        while is_connected:
                            try:
                                # Send keep-alive packet every 2 seconds
                                keep_alive = bytes([0xAA, 0x13, 0xEC, 0x07, 0x01, 0xF1, 0xA2, 0x5D])
                                await client.write_gatt_char(FARDRIVER_CHARACTERISTIC_UUID, keep_alive)
                                await asyncio.sleep(2)
                            except Exception as e:
                                print(f"Connection lost: {e}")
                                is_connected = False
                                break
                        
                    except Exception as e:
                        print(f"Failed to connect: {e}")
                        is_connected = False
                        
        except Exception as e:
            print(f"Scan error: {e}")
        
        print("Retrying in 5 seconds...")
        await asyncio.sleep(5)

def run_ble_loop():
    """Run the BLE event loop in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(scan_and_connect())

def main():
    """Main application entry point"""
    print("EKSR Instrument Terminal Display")
    print("Starting BLE scanner...")
    
    # Start BLE scanning in background thread
    ble_thread = threading.Thread(target=run_ble_loop, daemon=True)
    ble_thread.start()
    
    try:
        # Main display loop
        while True:
            print_data()
            time.sleep(0.5)  # Update every 500ms
            
    except KeyboardInterrupt:
        print("\n\nApplication terminated by user")
        if client and is_connected:
            asyncio.run(client.disconnect())
        sys.exit(0)

if __name__ == "__main__":
    main() 
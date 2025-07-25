#!/usr/bin/env python3
"""
EKSR Instrument PC Display
A Python application that connects to the FarDriver BLE emulator and displays
the EKSR Instrument data on a computer screen using tkinter.

This simulates the TFT display functionality without requiring the physical hardware.
"""

import tkinter as tk
from tkinter import ttk
import asyncio
import threading
import time
from bleak import BleakScanner, BleakClient
import struct

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

class EKSRDisplay:
    def __init__(self, root):
        self.root = root
        self.root.title("EKSR Instrument Display")
        self.root.geometry("400x600")
        self.root.configure(bg='black')
        
        # Create main frame
        self.main_frame = tk.Frame(root, bg='black')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Connection status
        self.status_label = tk.Label(self.main_frame, text="Disconnected", 
                                   fg='red', bg='black', font=('Arial', 12, 'bold'))
        self.status_label.pack(pady=5)
        
        # Power display (center)
        self.power_frame = tk.Frame(self.main_frame, bg='black')
        self.power_frame.pack(pady=20)
        
        self.power_label = tk.Label(self.power_frame, text="kW", 
                                  fg='white', bg='black', font=('Arial', 14))
        self.power_label.pack()
        
        self.power_value = tk.Label(self.power_frame, text="0.0", 
                                  fg='white', bg='black', font=('Arial', 36, 'bold'))
        self.power_value.pack()
        
        # Battery voltage
        self.voltage_frame = tk.Frame(self.main_frame, bg='black')
        self.voltage_frame.pack(pady=10)
        
        self.voltage_label = tk.Label(self.voltage_frame, text="Battery Voltage", 
                                    fg='white', bg='black', font=('Arial', 10))
        self.voltage_label.pack()
        
        self.voltage_value = tk.Label(self.voltage_frame, text="0.0V", 
                                    fg='white', bg='black', font=('Arial', 24, 'bold'))
        self.voltage_value.pack()
        
        # Battery bar
        self.battery_canvas = tk.Canvas(self.main_frame, width=200, height=30, 
                                      bg='black', highlightthickness=0)
        self.battery_canvas.pack(pady=5)
        
        # Temperature and RPM info
        self.info_frame = tk.Frame(self.main_frame, bg='black')
        self.info_frame.pack(pady=10)
        
        # Motor temp
        self.motor_temp_label = tk.Label(self.info_frame, text="Motor Temp:", 
                                       fg='white', bg='black', font=('Arial', 10))
        self.motor_temp_label.grid(row=0, column=0, sticky='w', padx=5)
        
        self.motor_temp_value = tk.Label(self.info_frame, text="0°C", 
                                       fg='white', bg='black', font=('Arial', 10))
        self.motor_temp_value.grid(row=0, column=1, padx=5)
        
        # Controller temp
        self.controller_temp_label = tk.Label(self.info_frame, text="Controller Temp:", 
                                            fg='white', bg='black', font=('Arial', 10))
        self.controller_temp_label.grid(row=1, column=0, sticky='w', padx=5)
        
        self.controller_temp_value = tk.Label(self.info_frame, text="0°C", 
                                            fg='white', bg='black', font=('Arial', 10))
        self.controller_temp_value.grid(row=1, column=1, padx=5)
        
        # RPM
        self.rpm_label = tk.Label(self.info_frame, text="RPM:", 
                                fg='white', bg='black', font=('Arial', 10))
        self.rpm_label.grid(row=2, column=0, sticky='w', padx=5)
        
        self.rpm_value = tk.Label(self.info_frame, text="0", 
                                fg='white', bg='black', font=('Arial', 10))
        self.rpm_value.grid(row=2, column=1, padx=5)
        
        # RPM bar
        self.rpm_canvas = tk.Canvas(self.main_frame, width=300, height=20, 
                                  bg='black', highlightthickness=0)
        self.rpm_canvas.pack(pady=5)
        
        # Speed display
        self.speed_frame = tk.Frame(self.main_frame, bg='black')
        self.speed_frame.pack(pady=10)
        
        self.speed_label = tk.Label(self.speed_frame, text="Speed", 
                                  fg='white', bg='black', font=('Arial', 14))
        self.speed_label.pack()
        
        self.speed_value = tk.Label(self.speed_frame, text="0 km/h", 
                                  fg='white', bg='black', font=('Arial', 28, 'bold'))
        self.speed_value.pack()
        
        # Gear and throttle
        self.controls_frame = tk.Frame(self.main_frame, bg='black')
        self.controls_frame.pack(pady=10)
        
        self.gear_label = tk.Label(self.controls_frame, text="Gear:", 
                                 fg='white', bg='black', font=('Arial', 10))
        self.gear_label.grid(row=0, column=0, sticky='w', padx=5)
        
        self.gear_value = tk.Label(self.controls_frame, text="0", 
                                 fg='white', bg='black', font=('Arial', 10))
        self.gear_value.grid(row=0, column=1, padx=5)
        
        # Throttle bar
        self.throttle_canvas = tk.Canvas(self.main_frame, width=20, height=100, 
                                       bg='black', highlightthickness=0)
        self.throttle_canvas.pack(pady=5)
        
        # Start update loop
        self.update_display()
    
    def update_display(self):
        """Update the display with current data"""
        # Reset data when disconnected
        if not is_connected:
            ctr_data.throttle = 0
            ctr_data.gear = 0
            ctr_data.rpm = 0
            ctr_data.controller_temp = 0
            ctr_data.motor_temp = 0
            ctr_data.speed = 0
            ctr_data.power = 0
            ctr_data.voltage = 0
        
        # Update power
        if ctr_data.power == 0:
            self.power_value.config(fg='white')
        elif ctr_data.power < 0:
            self.power_value.config(fg='green')
        else:
            self.power_value.config(fg='red')
        
        self.power_value.config(text=f"{abs(ctr_data.power):.1f}")
        
        # Update voltage
        self.voltage_value.config(text=f"{ctr_data.voltage:.1f}V")
        
        # Update battery bar
        self.update_battery_bar()
        
        # Update temperatures and RPM
        self.motor_temp_value.config(text=f"{ctr_data.motor_temp:.0f}°C")
        self.controller_temp_value.config(text=f"{ctr_data.controller_temp:.0f}°C")
        self.rpm_value.config(text=f"{ctr_data.rpm}")
        
        # Update RPM bar
        self.update_rpm_bar()
        
        # Update speed
        self.speed_value.config(text=f"{ctr_data.speed:.0f} km/h")
        
        # Update gear
        self.gear_value.config(text=f"{ctr_data.gear}")
        
        # Update throttle bar
        self.update_throttle_bar()
        
        # Update connection status
        if is_connected:
            self.status_label.config(text="Connected", fg='green')
        else:
            self.status_label.config(text="Disconnected", fg='red')
        
        # Schedule next update
        self.root.after(100, self.update_display)
    
    def update_battery_bar(self):
        """Update the battery level indicator"""
        self.battery_canvas.delete("all")
        
        # Battery bar dimensions
        bar_width = 180
        bar_height = 20
        x_start = 10
        
        # Calculate battery level (84V-96V range)
        low_limit = 84.0
        high_limit = 96.0
        voltage = max(low_limit, min(high_limit, ctr_data.voltage))
        level = (voltage - low_limit) / (high_limit - low_limit)
        
        # Draw battery outline
        self.battery_canvas.create_rectangle(x_start, 5, x_start + bar_width, 5 + bar_height, 
                                           outline='white', width=2)
        
        # Draw battery level
        fill_width = int(bar_width * level)
        if level > 0.5:
            color = 'green'
        elif level > 0.2:
            color = 'yellow'
        else:
            color = 'red'
        
        self.battery_canvas.create_rectangle(x_start + 2, 7, x_start + 2 + fill_width, 3 + bar_height, 
                                           fill=color, outline='')
    
    def update_rpm_bar(self):
        """Update the RPM progress bar"""
        self.rpm_canvas.delete("all")
        
        # RPM bar dimensions
        bar_width = 280
        bar_height = 15
        x_start = 10
        
        # Calculate RPM level (0-8000 RPM)
        rpm_level = min(1.0, ctr_data.rpm / 8000.0)
        
        # Draw bar outline
        self.rpm_canvas.create_rectangle(x_start, 2, x_start + bar_width, 2 + bar_height, 
                                       outline='white', width=1)
        
        # Draw RPM level
        fill_width = int(bar_width * rpm_level)
        self.rpm_canvas.create_rectangle(x_start + 1, 3, x_start + 1 + fill_width, 1 + bar_height, 
                                       fill='cyan', outline='')
    
    def update_throttle_bar(self):
        """Update the throttle position indicator"""
        self.throttle_canvas.delete("all")
        
        # Throttle bar dimensions
        bar_width = 15
        bar_height = 80
        x_start = 2
        
        # Calculate throttle level (0-5000 range)
        throttle_level = min(1.0, max(0.0, ctr_data.throttle / 5000.0))
        
        # Draw bar outline
        self.throttle_canvas.create_rectangle(x_start, 10, x_start + bar_width, 10 + bar_height, 
                                           outline='white', width=1)
        
        # Draw throttle level (from bottom up)
        fill_height = int(bar_height * throttle_level)
        self.throttle_canvas.create_rectangle(x_start + 1, 10 + bar_height - fill_height, 
                                           x_start + bar_width - 1, 10 + bar_height, 
                                           fill='magenta', outline='')

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
    # Start BLE scanning in background thread
    ble_thread = threading.Thread(target=run_ble_loop, daemon=True)
    ble_thread.start()
    
    # Create and run GUI
    root = tk.Tk()
    app = EKSRDisplay(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application terminated by user")
    finally:
        if client and is_connected:
            asyncio.run(client.disconnect())

if __name__ == "__main__":
    main() 
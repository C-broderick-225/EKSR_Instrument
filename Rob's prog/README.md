# ESP32 Fardriver BLE Controller

A stripped-down Arduino sketch for ESP32 devices that connects to Fardriver motor controllers via Bluetooth Low Energy (BLE) and outputs parsed data to the Serial Monitor for testing and debugging purposes.

## Overview

This project provides a basic framework for communicating with Fardriver motor controllers over BLE. It's designed as a starting point for developers who want to integrate Fardriver controllers into their projects without the complexity of display interfaces or persistent storage.

## Features

- **BLE Communication**: Connects to Fardriver controllers using specific service and characteristic UUIDs
- **Data Parsing**: Decodes various sensor readings from the controller
- **Real-time Monitoring**: Continuously receives and processes data packets
- **Serial Output**: Displays formatted data in the Serial Monitor
- **Regeneration Detection**: Identifies when the motor is regenerating (negative current)
- **CRC Validation**: Ensures data packet integrity

## Data Parameters

The controller monitors and displays:

| Parameter | Unit | Description |
|-----------|------|-------------|
| Voltage | V | Battery voltage |
| Line Current | A | Motor current (positive = driving, negative = regen) |
| Power | W | Calculated power consumption |
| RPM | - | Motor rotational speed |
| Gear | - | Current gear position (1-4) |
| Speed | km/h | Calculated vehicle speed |
| Controller Temp | °C | Controller temperature |
| Motor Temp | °C | Motor temperature |
| SOC | % | State of charge |
| Trip | km | Current trip distance |
| Odo | km | Total odometer distance |
| Regen | Yes/No | Regeneration status |

## Hardware Requirements

- **ESP32 Development Board** (any variant)
- **Fardriver Motor Controller** with BLE capability
- **USB Cable** for programming and power
- **Computer** with Arduino IDE or PlatformIO

## Software Requirements

- **Arduino IDE** (version 1.8.x or later) or **PlatformIO**
- **ESP32 Board Support Package**
- **BLE Libraries** (included with ESP32 core)

## Installation & Setup

### 1. Install ESP32 Board Support

1. Open Arduino IDE
2. Go to **File > Preferences**
3. Add this URL to **Additional Board Manager URLs**:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Go to **Tools > Board > Boards Manager**
5. Search for "ESP32" and install the latest version

### 2. Select Board

1. Go to **Tools > Board > ESP32 Arduino**
2. Select your specific ESP32 board (e.g., "ESP32 Dev Module")

### 3. Upload Code

1. Open `ESP32_Fardriver_BLE_Controller.ino`
2. Connect your ESP32 via USB
3. Select the correct COM port
4. Click **Upload**

## Usage

### 1. Power Up

1. Connect your ESP32 to a computer via USB
2. Open the **Serial Monitor** (Tools > Serial Monitor)
3. Set baud rate to **115200**
4. Reset the ESP32 if needed

### 2. Connection Process

The ESP32 will automatically:
1. **Scan** for nearby Fardriver controllers
2. **Connect** to the first compatible device found
3. **Begin receiving data** and displaying it in the Serial Monitor

### 3. Data Output

Once connected, you'll see output like:
```
--- Fardriver Controller Data ---
Voltage: 48.2 V
Line Current: 12.5 A
Power: 602 W
RPM: 1250
Gear: 2
Speed: 25.3 km/h
Controller Temp: 45 C
Motor Temp: 52 C
SOC: 85 %
Trip: 0.5 km
Odo: 1250.2 km
Regen (Current): No
--------------------------------
```

## Configuration

### BLE UUIDs

The default UUIDs are set for standard Fardriver controllers:
```cpp
#define SERVICE_UUID        "0000ffe0-0000-1000-8000-00805f9b34fb"
#define CHARACTERISTIC_UUID "0000ffec-0000-1000-8000-00805f9b34fb"
```

### Update Intervals

Change the data output frequency by modifying:
```cpp
const unsigned long printInterval = 500; // Print data every 500ms
```

### Wheel Configuration

Adjust for your specific vehicle:
```cpp
const float wheel_circumference_m = 1.416;  // Wheel circumference in meters
const int motor_pole_pairs = 20;            // Motor pole pairs
```

## Troubleshooting

### Common Issues

1. **"Scanning for Fardriver Controller..."**
   - Ensure your Fardriver controller has BLE enabled
   - Check that the controller is powered on and advertising
   - Verify the UUIDs match your controller

2. **"Failed to connect, retrying..."**
   - Move the ESP32 closer to the controller
   - Check for interference from other BLE devices
   - Restart both devices

3. **No data received**
   - Verify the connection is established
   - Check that the controller is sending data
   - Monitor the Serial Monitor for error messages

### Debug Information

Enable additional debugging by adding Serial prints in the `processPacket()` function or checking the connection status variables.

## Extending the Code

This base code can be extended with:

- **Display Interface**: Add TFT, OLED, or e-paper displays
- **Data Logging**: Save data to SD card or flash memory
- **Web Interface**: Create a local web server for remote monitoring
- **Data Transmission**: Send data to cloud services or other devices
- **User Controls**: Add buttons for configuration and control

## Technical Details

### Packet Structure

Data packets are 16 bytes with CRC validation:
- Byte 0: Packet header
- Byte 1: Address ID (masked with 0x3F)
- Bytes 2-13: Data payload
- Bytes 14-15: CRC checksum

### Memory Addresses

The code reads from specific Fardriver memory addresses:
- `0xE2`: Gear and RPM data
- `0xE8`: Voltage and current data
- `0xD6`: Controller temperature
- `0xF4`: Motor temperature and SOC

### CRC Algorithm

Uses a modified CRC-16 algorithm with:
- Initial value: `0x7F3C`
- Polynomial: `0xA001`
- Applied to first 14 bytes of each packet

## License

This project is provided as-is for educational and development purposes. Please ensure compliance with your local regulations when using this code with motor vehicles.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this project.

## Disclaimer

This software is provided without warranty. Always test thoroughly before using in production environments, especially with motor vehicles where safety is critical.

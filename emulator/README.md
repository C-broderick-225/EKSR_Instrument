# FarDriver BLE Emulator

This directory contains a comprehensive BLE emulator for the FarDriver controller, designed to work with the EKSR Instrument project. It allows you to use an ESP32 (e.g., ESP-WROVER-E) as a BLE peripheral that mimics the FarDriver controller, so you can test the EKSR Instrument firmware without the real controller hardware.

## Features
- **Dual Service Support**: Emulates both the FarDriver BLE protocol (service UUID `FFE0`, characteristic UUID `FFEC`) and the standard Nordic UART Service (NUS)
- **Realistic Data Simulation**: Sends cyclic data packets with dynamic values including:
  - RPM with sine wave variation (1000-1400 RPM)
  - Voltage (90.0V)
  - Controller temperature (40°C)
  - Motor temperature (50°C)
  - Throttle position (mid-range: 2048)
  - Current values (iq: 5.00A, id: 2.00A)
- **Visual Status Indication**: Built-in LED (pin 2) shows connection status:
  - Blinking: Advertising/disconnected
  - Solid ON: Connected
- **Comprehensive Debugging**: Serial output with packet data, connection events, and status updates
- **Bidirectional Communication**: Supports both notifications and write operations
- **Robust Connection Handling**: Automatic connection detection and recovery

## File Overview
- `FarDriverEmulator.ino` — Main Arduino sketch for the emulator

## How It Works
- The emulator advertises as "FarDriver_Emu" with both FarDriver and Nordic UART services
- It cycles through four packet indices (0, 1, 4, 13) every 30ms when connected
- Each packet contains 16 bytes with realistic simulated data
- The emulator sends data to both services simultaneously for maximum compatibility
- Connection status is monitored continuously with automatic LED state management

## Building and Flashing
1. **Install the ESP32 Arduino core** in your Arduino IDE (or PlatformIO)
2. **Install the NimBLE-Arduino library** (required for BLE functionality)
3. Open `FarDriverEmulator.ino` in your IDE
4. Select your ESP32 board (e.g., ESP-WROVER-E)
5. Compile and upload the sketch to your board
6. Open Serial Monitor at 115200 baud to see debug output

## Customizing the Emulation
- The `fill_packet` function controls the data sent for each packet index
- You can modify simulated values in the switch statement:
  - `INDEX_MAIN_DATA` (0): RPM, gear, current values
  - `INDEX_VOLTAGE` (1): Battery voltage
  - `INDEX_CONTROLLER_TEMP` (4): Controller temperature
  - `INDEX_MOTOR_THROTTLE` (13): Motor temperature and throttle position
- Adjust `PACKET_UPDATE_INTERVAL` to change transmission frequency
- Modify `LED_BLINK_INTERVAL` to change LED blink rate

## Protocol Details
### FarDriver Service
- **Service UUID:** `FFE0`
- **Characteristic UUID:** `FFEC` (notify, write)
- **Device Name:** `FarDriver_Emu`

### Nordic UART Service
- **Service UUID:** `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`
- **TX Characteristic:** `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (notify)
- **RX Characteristic:** `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` (write)

### Packet Format
- **Size:** 16 bytes
- **Header:** `data[0] = 0xAA`
- **Index:** `data[1]` (0, 1, 4, 13)
- **Data:** Remaining bytes contain simulated values (see `fill_packet` function)

## Example Use Case
1. Power up the ESP32 running this emulator
2. Watch the LED blink while advertising
3. Start the EKSR Instrument client (ESP32-S3-WROOM-1 with the original firmware)
4. The client should connect and the LED will turn solid ON
5. Monitor Serial output to see packet transmission and connection status
6. The client will display the emulated data as if connected to a real FarDriver controller

## Debug Output
The emulator provides comprehensive debug information via Serial:
- Connection/disconnection events with client MAC addresses
- Packet data in hexadecimal format
- Periodic status updates
- MTU size changes
- Received data from clients

---

For more details on the EKSR Instrument project, see the main project README. 
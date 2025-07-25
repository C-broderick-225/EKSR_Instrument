# FarDriver BLE Emulator

This directory contains a comprehensive BLE emulator for the FarDriver controller, designed to work with the EKSR Instrument project. It allows you to use an ESP32 (e.g., ESP-WROVER-E) as a BLE peripheral that mimics the FarDriver controller, so you can test the EKSR Instrument firmware without the real controller hardware.

## Features
- **Dual Service Support**: Emulates both the FarDriver BLE protocol (service UUID `FFE0`, characteristic UUID `FFEC`) and the standard Nordic UART Service (NUS)
- **Dynamic Ebike Simulation**: Realistic acceleration and deceleration patterns that cycle every 30 seconds:
  - **Acceleration Phase** (10s): Accelerate from 0 to 25 km/h at 2 km/h per second
  - **Maintain Phase** (10s): Hold speed at 25 km/h with slight variations
  - **Deceleration Phase** (10s): Decelerate from 25 to 0 km/h at 1.5 km/h per second
- **Realistic Data Relationships**: All parameters are dynamically calculated based on speed and throttle:
  - **RPM**: Calculated from speed using realistic gear ratios and wheel circumference
  - **Current (iq/id)**: Varies with throttle position and power demand
  - **Voltage**: Slight voltage drop under load (up to 5%)
  - **Temperature**: Increases with power usage (35-50°C controller, 40-60°C motor)
  - **Throttle**: Dynamic position that follows acceleration/deceleration patterns
- **Visual Status Indication**: Built-in LED (pin 2) shows connection status:
  - Blinking: Advertising/disconnected
  - Solid ON: Connected
- **Comprehensive Debugging**: Serial output with packet data, connection events, and simulation state
- **Bidirectional Communication**: Supports both notifications and write operations
- **Robust Connection Handling**: Automatic connection detection and recovery

## File Overview
- `FarDriverEmulator.ino` — Main Arduino sketch for the emulator with dynamic ebike simulation

## How It Works
- The emulator advertises as "FarDriver_Emu" with both FarDriver and Nordic UART services
- It cycles through four packet indices (0, 1, 4, 13) every 30ms when connected
- Each packet contains 16 bytes with dynamically calculated realistic data
- The ebike simulation updates continuously, creating realistic acceleration/deceleration patterns
- The emulator sends data to both services simultaneously for maximum compatibility
- Connection status is monitored continuously with automatic LED state management

## Building and Flashing
1. **Install the ESP32 Arduino core** in your Arduino IDE (or PlatformIO)
2. **Install the NimBLE-Arduino library** (required for BLE functionality)
3. Open `FarDriverEmulator.ino` in your IDE
4. Select your ESP32 board (e.g., ESP-WROVER-E)
5. Compile and upload the sketch to your board
6. Open Serial Monitor at 115200 baud to see debug output and simulation state

## Customizing the Emulation
- The `update_ebike_simulation()` function controls the acceleration/deceleration patterns
- The `fill_packet()` function calculates realistic data based on the simulation state
- You can modify simulation parameters in the `EbikeState` struct:
  - `acceleration_rate`: How fast the bike accelerates/decelerates
  - `target_speed`: Maximum speed during acceleration phase
  - Cycle timing: Currently 30 seconds total (10s each phase)
- Adjust `PACKET_UPDATE_INTERVAL` to change transmission frequency
- Modify `LED_BLINK_INTERVAL` to change LED blink rate

## Simulation Details
### Ebike Physics
- **Wheel Circumference**: 1.35 meters (typical for 26" wheel)
- **Gear Ratio**: 4:1 (motor to wheel)
- **Speed Calculation**: RPM = (Speed × 1000) / (60 × 1.35) × 4
- **Power Relationship**: Current varies with throttle position and speed

### Data Relationships
- **RPM Range**: 100-3000 RPM (with realistic variation)
- **Current Range**: 3-7A (iq), 1-3A (id) based on power demand
- **Voltage**: 90V base with up to 5% drop under load
- **Temperature**: 35-50°C controller, 40-60°C motor
- **Throttle**: 0-4095 raw ADC values (0-100% position)

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
- **Data:** `data[2-13]` (12 bytes of packet-specific data)
- **Checksum:** `data[14]` (XOR of bytes 1-13)
- **Reserved:** `data[15]` (0x00)

### Packet Data Layout
- **Index 0 (Main Data):**
  - `data[2]`: Gear bits (bits 2-3: 00=high, 11=mid, 10=low)
  - `data[4-5]`: RPM (16-bit)
  - `data[8-9]`: iq current (16-bit, 0.01A resolution)
  - `data[10-11]`: id current (16-bit, 0.01A resolution)

- **Index 1 (Voltage):**
  - `data[2-3]`: Battery voltage (16-bit, 0.1V resolution)

- **Index 4 (Controller Temp):**
  - `data[2]`: Controller temperature (°C)

- **Index 13 (Motor/Throttle):**
  - `data[2]`: Motor temperature (°C)
  - `data[4-5]`: Throttle position (16-bit, 0-4095 raw ADC)

## Example Use Case
1. Power up the ESP32 running this emulator
2. Watch the LED blink while advertising
3. Start the EKSR Instrument client (ESP32-S3-WROOM-1 with the original firmware)
4. The client should connect and the LED will turn solid ON
5. Monitor Serial output to see packet transmission, connection status, and simulation state
6. The client will display dynamic data showing realistic ebike acceleration/deceleration
7. Watch the speed, RPM, and power values change in real-time as the simulation cycles

## Debug Output
The emulator provides comprehensive debug information via Serial:
- Connection/disconnection events with client MAC addresses
- Packet data in hexadecimal format
- Periodic status updates with connection state
- Ebike simulation state (speed, throttle, cycle count)
- MTU size changes
- Received data from clients

## Simulation Pattern
The emulator follows a repeating 30-second cycle:
1. **0-10s**: Accelerate from 0 to 25 km/h (throttle increases)
2. **10-20s**: Maintain 25 km/h (throttle varies slightly)
3. **20-30s**: Decelerate from 25 to 0 km/h (throttle decreases)
4. **Repeat**: Cycle continues indefinitely

This creates a realistic demonstration of ebike operation that's perfect for testing displays and monitoring systems.

---

For more details on the EKSR Instrument project, see the main project README. 
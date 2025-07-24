# FarDriver BLE Emulator

This directory contains a simple BLE emulator for the FarDriver controller, designed to work with the EKSR Instrument project. It allows you to use an ESP32 (e.g., ESP-WROVER-E) as a BLE peripheral that mimics the FarDriver controller, so you can test the EKSR Instrument firmware without the real controller hardware.

## Features
- Emulates the FarDriver BLE protocol (service UUID `FFE0`, characteristic UUID `FFEC`)
- Sends realistic, cyclic data packets for rpm, voltage, temperature, throttle, etc.
- Compatible with the EKSR Instrument client firmware (ESP32-S3)

## File Overview
- `FarDriverEmulator.cpp` — Main Arduino sketch for the emulator

## How It Works
- The emulator advertises a BLE service with UUID `FFE0` and a characteristic `FFEC` that supports notifications.
- It cycles through the main FarDriver packet indices (0, 1, 4, 13) and sends 16-byte packets with plausible data every 30 ms.
- The EKSR Instrument client connects as a BLE central and receives these packets as if from a real controller.

## Building and Flashing
1. **Install the ESP32 Arduino core** in your Arduino IDE (or PlatformIO).
2. **Install the NimBLE-Arduino library** (if not already present).
3. Open `FarDriverEmulator.cpp` in your IDE.
4. Select your ESP32 board (e.g., ESP-WROVER-E).
5. Compile and upload the sketch to your board.

## Customizing the Emulation
- The `fill_packet` function in `FarDriverEmulator.cpp` controls the data sent for each packet index.
- You can adjust the simulated values (rpm, voltage, temperature, etc.) or add more indices as needed.
- To mimic real-world behavior, you can randomize or pattern the values over time.

## Protocol Summary
- **Service UUID:** `FFE0`
- **Characteristic UUID:** `FFEC` (notify, write)
- **Packet format:** 16 bytes
    - `data[0]`: 0xAA (header)
    - `data[1]`: index (0, 1, 4, 13, ...)
    - Remaining bytes: values for rpm, voltage, temperature, throttle, etc. (see `fill_packet` for details)

## Example Use Case
- Power up the ESP32 running this emulator.
- Start the EKSR Instrument client (ESP32-S3-WROOM-1 with the original firmware).
- The client should connect and display the emulated data as if it were connected to a real FarDriver controller.

---

For more details on the EKSR Instrument project, see the main project README. 
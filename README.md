# EKSR_Instrument (Fork)

**This repository is a fork of the original [EKSR_Instrument](https://github.com/magicmicros/EKSR_Instrument) project.**

## Overview
This project serves as the foundation for a new product based on the EKSR_Instrument hardware and firmware. It utilizes an ESP32-S3 microcontroller to receive and decode messages from FarDriver motor controllers over BLE, and displays the processed data on a 2.4" TFT touchscreen display.

## ESP32-S3 BLE Multi-Role Support
The ESP32-S3 (including the ESP32-S3-WROOM-1 module) is capable of acting as both a BLE client (central) and a BLE server (peripheral) simultaneously. This allows the device to connect to a BLE peripheral (such as a Far Driver controller) while also advertising its own BLE service for other clients (such as an Android phone) to connect and receive forwarded data. This multi-role (dual-role) capability is officially supported by Espressif and is useful for BLE proxy/bridge applications.

**Key facts:**
- The ESP32-S3 can operate as both a BLE client and server at the same time (multi-role topology).
- This is supported by the ESP-IDF and ESP-NimBLE host stack.
- Example use case: ESP32-S3 connects to a Far Driver controller as a client, and simultaneously acts as a server to forward data to a mobile app.

**Official documentation:**
- [ESP-IDF BLE Introduction: Bluetooth LE Network Topology](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/ble/get-started/ble-introduction.html#bluetooth-le-network-topology)
- [ESP-NimBLE API Reference](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/bluetooth/esp-nimble/index.html)

## Purpose
The goal of this fork is to extend and adapt the original EKSR_Instrument platform for new applications and features. All original design and implementation credit belongs to the original author. This repository will introduce new features, modifications, and documentation specific to the goals of the new product.

## FarDriver BLE Emulator
A FarDriver BLE emulator is included in the `emulator/` directory. This tool allows you to use an ESP32 (such as ESP-WROVER-E) as a BLE peripheral that mimics the FarDriver controller. It is useful for testing the EKSR Instrument firmware without requiring the actual controller hardware.

- The emulator advertises the same BLE service and characteristic UUIDs as the real controller.
- It sends realistic, cyclic data packets for rpm, voltage, temperature, throttle, and more.
- The EKSR Instrument client can connect and display the emulated data as if it were connected to a real FarDriver controller.

For build instructions, customization, and protocol details, see [`emulator/README.md`](emulator/README.md).

## License
See the LICENSE file for details.

# EKSR Instrument Emulator Suite

This directory contains a comprehensive suite of emulators and testing tools for the EKSR Instrument project. These tools allow you to test and develop the EKSR Instrument firmware without requiring the actual hardware components.

## Overview

The emulator suite includes:
- **FarDriver BLE Emulators** - Simulate the FarDriver controller's BLE communication
- **Hall Motor Emulator** - Simulate BLDC motor Hall sensor signals
- **Testing Tools** - Python scripts for validating emulator behavior and packet formats

## Components

### 1. FarDriver BLE Emulator

#### FarDriverEmulator (Enhanced)
- **Location**: `FarDriverEmulator/FarDriverEmulator.ino`
- **Features**: Enhanced FarDriver BLE protocol emulation with CRC-16/MODBUS checksums and dynamic ebike simulation
- **Use Case**: Accurate protocol emulation with proper error checking and realistic simulation

**Key Features**:
- CRC-16/MODBUS checksums for robust error detection
- Enhanced packet validation and error handling
- Improved timing and connection management
- Realistic ebike simulation with dynamic acceleration/deceleration patterns

### 2. Hall Motor Emulator

#### HallMotorEmulator
- **Location**: `MotorEmulator/HallMotorEmulator/HallMotorEmulator.ino`
- **Purpose**: Simulates BLDC motor Hall sensor signals for motor controller testing
- **Use Case**: Bench testing motor controllers without physical motors

**Features**:
- Generates standard 6-step commutation sequence
- Prevents "Hall Sensor Fault" errors during testing
- Configurable simulated motor speed
- Real-time debug output

### 3. Testing Tools

#### test_emulator_rpm.py
- **Purpose**: Validates RPM calculation logic between emulator and firmware
- **Tests**: Speed-to-RPM conversion accuracy and packet generation
- **Use Case**: Debugging speed display issues

#### test_packet_format.py
- **Purpose**: Validates packet format compliance with FarDriver protocol
- **Tests**: Packet structure, checksums, and data parsing
- **Use Case**: Ensuring emulator generates correct packet formats

#### test_speed_calculation.py
- **Purpose**: Tests speed calculation logic and identifies display issues
- **Tests**: Speed-to-RPM conversion and firmware parsing
- **Use Case**: Debugging speed calculation problems

## Quick Start Guide

### Setting Up FarDriver BLE Emulator

1. **Hardware Requirements**:
   - ESP32 development board (e.g., ESP-WROVER-E)
   - USB cable for programming and power

2. **Software Setup**:
   ```bash
   # Install Arduino IDE with ESP32 support
   # Install NimBLE-Arduino library
   ```

3. **Flashing**:
   - Open `FarDriverEmulator/FarDriverEmulator.ino` in Arduino IDE
   - Select your ESP32 board
   - Upload the sketch
   - Open Serial Monitor at 115200 baud

### Setting Up Hall Motor Emulator

1. **Hardware Requirements**:
   - ESP32 development board
   - Multimeter for pin identification
   - Jumper wires

2. **Wiring** (see MotorEmulator/README.md for detailed instructions):
   ```
   ESP32 Pin | Controller Hall Connector
   GND       | Ground
   GPIO 25   | Hall A Signal
   GPIO 26   | Hall B Signal
   GPIO 27   | Hall C Signal
   ```

3. **Flashing**:
   - Open `MotorEmulator/HallMotorEmulator/HallMotorEmulator.ino`
   - Upload to ESP32
   - Power on motor controller

### Running Tests

```bash
# Test RPM calculations
python test_emulator_rpm.py

# Test packet formats
python test_packet_format.py

# Test speed calculations
python test_speed_calculation.py
```

## FarDriver BLE Protocol Details

### Service Configuration
- **FarDriver Service**: UUID `FFE0`, Characteristic `FFEC`
- **Nordic UART Service**: Standard NUS implementation
- **Device Name**: `FarDriver_Emu`

### Packet Format
- **Size**: 16 bytes
- **Header**: `0xAA`
- **Indices**: 0, 1, 4, 13 (cycled every 30ms)
- **Checksum**: XOR (v1) or CRC-16/MODBUS (v2)

### Packet Types
- **Index 0**: Main data (RPM, gear, current iq/id)
- **Index 1**: Battery voltage
- **Index 4**: Controller temperature
- **Index 13**: Motor temperature and throttle position

### Ebike Simulation
The emulators provide realistic ebike simulation with:
- **30-second cycles**: Acceleration → Maintain → Deceleration
- **Dynamic data relationships**: All parameters calculated from speed
- **Realistic physics**: Proper gear ratios and wheel circumference
- **Visual feedback**: LED status indication

## Hall Motor Emulation Details

### 6-Step Commutation Sequence
```
Step | Hall A | Hall B | Hall C
-----|--------|--------|--------
1    | 1      | 0      | 1
2    | 0      | 0      | 1
3    | 0      | 1      | 1
4    | 0      | 1      | 0
5    | 1      | 1      | 0
6    | 1      | 0      | 0
```

### Configuration
- **Default Speed**: 500 RPM (20ms step delay)
- **Adjustable**: Modify `STEP_DELAY_MS` constant
- **RPM Calculation**: `RPM = 60,000 / (STEP_DELAY_MS × 6)`

## Testing and Validation

### Automated Testing
The Python test scripts validate:
- **Packet format compliance** with FarDriver protocol
- **RPM calculation accuracy** between emulator and firmware
- **Speed calculation logic** and display issues
- **Data relationships** and realistic simulation

### Manual Testing
1. **BLE Connection**: Verify device appears as "FarDriver_Emu"
2. **Data Reception**: Monitor Serial output for packet transmission
3. **Display Testing**: Connect to EKSR Instrument firmware
4. **Hall Signals**: Verify controller powers on without fault codes

## Troubleshooting

### Common Issues

#### BLE Connection Problems
- **Device not found**: Check ESP32 power and LED blinking
- **Connection drops**: Verify NimBLE library version
- **Data not received**: Check packet format and timing

#### Hall Emulator Issues
- **Controller still faults**: Verify wiring and pin identification
- **Unstable signals**: Check wire quality and ground connection
- **Wrong speed**: Adjust `STEP_DELAY_MS` value

#### Speed Display Issues
- **Speed shows 0**: Run `test_speed_calculation.py` to debug
- **Incorrect values**: Check RPM calculation and packet parsing
- **No updates**: Verify packet transmission frequency

### Debug Output
All emulators provide comprehensive Serial output:
- Connection events and client MAC addresses
- Packet data in hexadecimal format
- Simulation state and timing information
- Error conditions and status updates

## Development Guidelines

### Adding New Features
1. **Maintain protocol compatibility** with existing firmware
2. **Add comprehensive testing** for new functionality
3. **Update documentation** for any protocol changes
4. **Test with real hardware** when possible

### Protocol Extensions
- **New packet types**: Add to packet index enumeration
- **Additional services**: Follow BLE service guidelines
- **Enhanced simulation**: Maintain realistic data relationships

## Related Documentation

- **MotorEmulator/README.md**: Detailed Hall emulator documentation
- **Main project README**: EKSR Instrument overview
- **Firmware documentation**: EKSR Instrument firmware details
- **Hardware documentation**: PCB and assembly information

## Contributing

When contributing to the emulator suite:
1. **Test thoroughly** with both emulator versions
2. **Validate packet formats** using test scripts
3. **Update documentation** for any changes
4. **Maintain backward compatibility** when possible

---

For more information about the complete EKSR Instrument project, see the main project README. 
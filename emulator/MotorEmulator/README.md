# ESP32 Hall Sensor Emulator for BLDC Motor Controllers

This project provides a simple yet effective way to emulate the Hall sensor signals of a Brushless DC (BLDC) motor using an ESP32 development board. It is designed for developers and hobbyists who need to bench test motor controllers (such as Sabvoton, FarDriver, Kelly, etc.) without a physical motor attached.

## Primary Goal

The primary goal is to prevent the common "Hall Sensor Fault" error (often indicated by a single repeating beep) that controllers report when they are powered on without receiving valid Hall signals.

## Features

- **Generates the standard 6-step commutation sequence** for BLDC motors
- **Simulates a slowly spinning motor** to satisfy the controller's self-test
- **Prevents common Hall sensor fault codes** during bench testing
- **Configurable simulated motor speed** via a single delay parameter
- **Outputs the current emulation state** to the Serial Monitor for easy debugging

## Why You Need This

This tool is essential for several common development tasks:

### Bench Testing
Power on and test a controller's basic functions (like BLE connectivity or parameter saving) without the noise and bulk of a physical motor.

### Protocol Reverse Engineering
To sniff and decode the data protocol (e.g., UART or CAN bus), the controller must be in a "healthy," non-faulted state. This emulator tricks the controller into this state, allowing you to capture normal operating data packets.

### Peripheral Firmware Development
If you are building a custom display or Human Interface Module (HIM), this provides a stable and predictable signal source without needing a full e-bike setup on your desk.

## Hardware Requirements

- **ESP32 Development Board** (any common model will work)
- **Multimeter** (essential for safely identifying controller pins)
- **Jumper wires** for making connections
- **Micro-USB cable** to power and program the ESP32

## Wiring and Connections

**WARNING: Incorrect wiring can permanently damage your motor controller or your ESP32. Proceed with caution and always verify pinouts with a multimeter.**

### Step 1: Identify Controller Pins

Before connecting anything, you must identify the pins on your controller's Hall sensor connector.

1. **Power on the motor controller**
2. **Using your multimeter set to DC Volts**, carefully probe the pins in the Hall connector
3. **Find the Ground (GND) pin**
4. **Find the +5V Power pin** (it should read approximately 5V relative to GND)
5. **The remaining three pins are the Hall signals** (Hall A, Hall B, Hall C)

### Step 2: Connect the ESP32

**Important: The ESP32 should be powered by its own USB cable, not by the controller.**

| ESP32 Pin | Controller Hall Connector | Typical Wire Color |
|-----------|---------------------------|-------------------|
| GND       | Ground                   | Black             |
| GPIO 25   | Hall A Signal            | Yellow / Green / Blue |
| GPIO 26   | Hall B Signal            | Yellow / Green / Blue |
| GPIO 27   | Hall C Signal            | Yellow / Green / Blue |

**DO NOT CONNECT ANYTHING TO THE CONTROLLER'S +5V HALL POWER PIN** (typically Red). The ESP32 is self-powered, and the controller has its own internal pull-up resistors for the signal lines.

## Software Setup

1. **Install the Arduino IDE**
2. **Add ESP32 board support** to the Arduino IDE. Follow [this guide from Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html)
3. **Open the `HallMotorEmulator.ino` file** in the Arduino IDE
4. **Select your ESP32 board** from the Tools > Board menu
5. **Select the correct COM port** from the Tools > Port menu
6. **Click the "Upload" button**

## Usage Procedure

1. **Flash the emulator sketch** to your ESP32. You can open the Serial Monitor (baud rate 115200) to see the debug output confirming it is running
2. **Power down the motor controller**
3. **Make the physical connections** as described in the wiring section
4. **Power on the ESP32** via its USB cable
5. **Power on the motor controller**
6. **Listen**: The controller should now power on without the repeating beep of a Hall fault
7. **You can now proceed** with your primary task, such as sniffing the data lines for reverse engineering

## Configuration

The simulated speed of the motor can be adjusted by changing a single constant in the code:

```cpp
// Define the delay between steps. This controls the simulated RPM.
// 20ms is a good starting point, simulating a slow, healthy spin.
#define STEP_DELAY_MS 20
```

- **Smaller value** (e.g., 10) simulates a faster motor
- **Larger value** (e.g., 50) simulates a slower motor
- **For most testing purposes**, the default value of 20 is sufficient

## How It Works

The emulator works by cycling through the standard 6-step commutation sequence required by BLDC motors. The ESP32 sets its GPIO pins to HIGH (3.3V) or LOW (0V) in a specific pattern. The motor controller's Hall sensor inputs have internal pull-up resistors connected to their 5V line. The ESP32's GPIOs are strong enough to pull these signal lines down to ground (LOW), creating a valid signal that the controller can read.

### 6-Step Commutation Sequence

The emulator cycles through these 6 states continuously:

| Step | Hall A | Hall B | Hall C |
|------|--------|--------|--------|
| 1    | 1      | 0      | 1      |
| 2    | 0      | 0      | 1      |
| 3    | 0      | 1      | 1      |
| 4    | 0      | 1      | 0      |
| 5    | 1      | 1      | 0      |
| 6    | 1      | 0      | 0      |

### RPM Calculation

The approximate simulated RPM can be calculated as:
```
RPM = 60,000 / (STEP_DELAY_MS × 6)
```

For example, with `STEP_DELAY_MS = 20`:
```
RPM = 60,000 / (20 × 6) = 60,000 / 120 = 500 RPM
```

## Debug Output

The emulator provides real-time feedback via the Serial Monitor:

```
=== ESP32 Hall Sensor Emulator for BLDC Motor Controllers ===
Starting ESP32 Hall Sensor Emulator...
Step delay: 20 ms (simulated RPM: ~500)
Emulator running. Connect to controller and power cycle it.
Expected behavior: Controller should power on without Hall fault beeps.
Debug output will show current Hall sensor states.
---
Step 1: Hall A=1, Hall B=0, Hall C=1 (Cycle 1)
Step 2: Hall A=0, Hall B=0, Hall C=1 (Cycle 1)
Step 3: Hall A=0, Hall B=1, Hall C=1 (Cycle 1)
...
```

## Troubleshooting

### Controller Still Shows Hall Fault
- **Check wiring**: Ensure all three Hall signal pins are connected
- **Verify pin identification**: Use a multimeter to confirm you've identified the correct pins
- **Check ESP32 power**: Ensure the ESP32 is powered via USB, not from the controller
- **Try different speed**: Increase `STEP_DELAY_MS` to 30 or 50 for slower simulation

### ESP32 Not Responding
- **Check USB connection**: Ensure the ESP32 is properly connected and recognized
- **Verify board selection**: Make sure you've selected the correct ESP32 board in Arduino IDE
- **Check COM port**: Ensure the correct serial port is selected

### Unstable Signals
- **Check wire quality**: Use good quality jumper wires with proper connections
- **Verify ground connection**: Ensure the ESP32 GND is connected to the controller GND
- **Check for interference**: Keep wires away from power cables and motors

## Safety Notes

- **Never connect the ESP32 to the controller's +5V power pin**
- **Always power down both devices before making connections**
- **Use a multimeter to verify pin identification before connecting**
- **Start with conservative timing values** (20-30ms) to avoid stressing the controller
- **Monitor the controller for any unusual behavior** during testing

## Related Projects

This emulator is part of the larger EKSR Instrument project, which includes:
- **FarDriver BLE Emulator**: For testing BLE communication protocols
- **EKSR Instrument Firmware**: The main instrument firmware for ESP32-S3
- **PC Display Software**: For monitoring and data visualization

For more information about the complete project, see the main project README. 
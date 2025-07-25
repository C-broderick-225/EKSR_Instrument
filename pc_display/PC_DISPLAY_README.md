# EKSR Instrument PC Display Options

Since you don't have the physical TFT display, here are several ways to run your EKSR Instrument on a computer:

## Option 1: Use the Existing FarDriver Emulator (Recommended)

### Setup Steps:
1. **Flash the emulator to an ESP32:**
   - Open `emulator/FarDriverEmulator/FarDriverEmulator.ino` in Arduino IDE
   - Install ESP32 board support and NimBLE-Arduino library
   - Upload to your ESP32 board

2. **Choose a display application:**

   **A. GUI Display (Windows/macOS/Linux):**
   ```bash
   python setup_pc_display.py  # Install dependencies
   python pc_display.py        # Run GUI application
   ```

   **B. Terminal Display (Any OS):**
   ```bash
   pip install bleak
   python terminal_display.py  # Run terminal application
   ```

## Option 2: Web-Based Interface

Create a web server that displays the data in a browser:

```bash
# Install Flask
pip install flask bleak

# Run web server
python web_display.py
```

Then open `http://localhost:5000` in your browser.

## Option 3: Serial Output Modification

Modify the original firmware to output data via serial instead of TFT:

1. Comment out TFT-related code
2. Add Serial.print() statements for data output
3. Use the existing `other/main.py` to view serial data

## Option 4: ESP32 Simulator

Use an ESP32 simulator like:
- **ESP-IDF Simulator**
- **QEMU with ESP32 support**
- **PlatformIO with simulation**

## Quick Start (Recommended)

1. **Install Python dependencies:**
   ```bash
   python setup_pc_display.py
   ```

2. **Flash the emulator:**
   - Use Arduino IDE with ESP32 board support
   - Upload `emulator/FarDriverEmulator/FarDriverEmulator.ino`

3. **Run the display:**
   ```bash
   python terminal_display.py  # Simple terminal version
   # OR
   python pc_display.py        # GUI version
   ```

## Troubleshooting

- **Bluetooth issues:** Make sure Bluetooth is enabled
- **Connection problems:** Check that no other BLE apps are connected
- **Windows issues:** Run as administrator if needed
- **Permission errors:** Install required drivers for your Bluetooth adapter

## Files Created

- `pc_display.py` - GUI application using tkinter
- `terminal_display.py` - Terminal-based display
- `setup_pc_display.py` - Setup and dependency installer
- `requirements.txt` - Python dependencies
- `PC_DISPLAY_README.md` - This file

The terminal version is the most reliable and works on any system with Python and Bluetooth support. 
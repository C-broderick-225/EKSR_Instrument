# FarDriver Monitor

## Overview

FarDriver Monitor provides a modern, polished interface with improved visual design, animations, and user experience for monitoring FarDriver BLE data.

## Key Enhancements

### 🎨 **Modern UI Design**
- **Dark Theme**: Professional dark color scheme with carefully chosen colors
- **Typography**: Modern fonts (Segoe UI) with proper hierarchy
- **Layout**: Grid-based layout with proper spacing and alignment
- **Sidebar**: Dedicated control panel with terminal and connection status

### 📊 **Interactive Gauges**
- **Animated Gauges**: Smooth circular gauges for RPM, throttle, and power
- **Real-time Updates**: 20 FPS smooth animations
- **Color Coding**: Dynamic colors based on values (green/yellow/red)
- **Visual Feedback**: Immediate response to data changes

### 🎯 **Improved Data Visualization**
- **Large Displays**: Prominent speed and voltage displays
- **Battery Indicator**: Visual battery level bar with color coding
- **Temperature Monitoring**: Clear temperature displays for motor and controller
- **Gear Display**: Prominent gear indicator

### 🔧 **Enhanced Controls**
- **Modern Buttons**: Hover effects and consistent styling
- **Connection Status**: Real-time connection indicator with status text
- **Terminal Controls**: Pause/resume and clear functionality
- **Status Bar**: Time display and application information

### 📱 **Responsive Design**
- **Resizable Window**: Minimum size constraints for usability
- **Grid Layout**: Flexible layout that adapts to window size
- **Proper Spacing**: Consistent padding and margins throughout

### 🎨 **Visual Polish**
- **Gradient Effects**: Subtle background gradients
- **Smooth Animations**: 60 FPS gauge animations
- **Color Consistency**: Unified color scheme across all elements
- **Professional Appearance**: Clean, modern interface design

## Features

### Connection Management
- Automatic BLE device scanning
- Real-time connection status
- Manual connect/disconnect controls
- Connection retry logic

### Data Display
- **Power Gauge**: Circular gauge showing power output (0-5000W)
- **Speed Display**: Large digital speedometer (km/h)
- **Voltage Monitor**: Battery voltage with visual indicator
- **RPM Gauge**: Engine RPM with color-coded levels
- **Throttle Gauge**: Throttle position indicator
- **Temperature Monitoring**: Motor and controller temperatures
- **Gear Display**: Current gear position

### Terminal Features
- **Real-time Logging**: Live data packet logging
- **Color-coded Messages**: Different colors for different message types
- **Pause/Resume**: Control terminal output
- **Auto-scroll**: Automatic scrolling to latest messages
- **Message Filtering**: Limit message history to prevent memory issues
- **Search Functionality**: Search through terminal content with highlighting
- **Packet Inspector**: Detailed packet analysis and statistics

### Data Recording
- **Auto-Save CSV**: Data is automatically saved to CSV files during recording
- **Organized Storage**: All data files saved in dedicated `data/` directory
- **Timestamped Files**: Automatic filename generation with timestamps
- **Data Folder Access**: Quick access to data directory via folder button
- **Settings Control**: Auto-save option available in settings
- **Multiple Formats**: Support for CSV and JSON export formats

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements_FarDriver_Monitor.txt
```

2. Run the FarDriver Monitor application:
```bash
python FarDriver_Monitor.py
```

## Usage

1. **Start the Application**: Launch the FarDriver Monitor
2. **Connect to Device**: The app will automatically scan for FarDriver devices
3. **Monitor Data**: View real-time data through the various gauges and displays
4. **Terminal Logging**: Monitor raw data packets in the terminal panel
5. **Control Display**: Use pause/resume and clear controls as needed
6. **Record Data**: Click "Start Recording" to begin auto-saving data to CSV files
7. **Access Data**: Click the folder button (📁) to open the data directory

## Data Directory Structure

The application automatically creates and manages a `data/` directory for all recorded files:

```
pc_display/
├── data/                          # Data storage directory
│   ├── eksr_data_20250725_143307.csv
│   ├── eksr_data_20250725_143353.csv
│   └── eksr_data_20250725_143400.json
├── FarDriver_Monitor.py           # Main application
├── requirements_FarDriver_Monitor.txt  # Dependencies
├── run_FarDriver_Monitor.py       # Launcher script
├── install_FarDriver_Monitor.py   # Installation script
└── FarDriver_Monitor_README.md    # Documentation
```

### Data File Format

CSV files contain the following columns:
- **Timestamp**: ISO format timestamp
- **Throttle**: Throttle position (0-4095)
- **Gear**: Current gear (1-3)
- **RPM**: Engine RPM
- **Controller_Temp_C**: Controller temperature in Celsius
- **Motor_Temp_C**: Motor temperature in Celsius
- **Speed_kmh**: Calculated speed in km/h
- **Power_W**: Power output in watts
- **Voltage_V**: Battery voltage
- **Packet_Count**: Total packets received
- **Latency_ms**: Average packet latency

## Technical Improvements

### Performance
- **Optimized Updates**: 20 FPS display updates for smooth animations
- **Memory Management**: Limited terminal history to prevent memory issues
- **Efficient Rendering**: Optimized canvas drawing for gauges

### Code Quality
- **Modular Design**: Separate classes for different UI components
- **Consistent Styling**: Centralized color and font definitions
- **Error Handling**: Improved error handling and user feedback
- **Documentation**: Comprehensive code comments and documentation

### User Experience
- **Intuitive Layout**: Logical arrangement of controls and displays
- **Visual Feedback**: Immediate response to user actions
- **Professional Appearance**: Clean, modern interface design
- **Accessibility**: Clear labels and consistent styling

## Comparison with Original

| Feature | Original | Enhanced |
|---------|----------|----------|
| Layout | Basic frame layout | Grid-based responsive layout |
| Colors | Basic black/white | Professional dark theme |
| Gauges | Simple bars | Animated circular gauges |
| Typography | Arial fonts | Modern Segoe UI fonts |
| Animations | None | Smooth 20 FPS animations |
| Controls | Basic buttons | Modern buttons with hover effects |
| Terminal | Basic text widget | Enhanced with color coding |
| Status | Simple labels | Interactive status indicators |

## Future Enhancements

Potential improvements for future versions:
- **Data Logging**: Save data to files for analysis
- **Graphs**: Real-time plotting of data trends
- **Alerts**: Configurable alerts for temperature/power limits
- **Themes**: Multiple color themes
- **Fullscreen Mode**: Dedicated fullscreen display mode
- **Data Export**: Export data in various formats
- **Configuration**: User-configurable display options

## Requirements

- Python 3.7+
- bleak library for BLE communication
- tkinter (usually included with Python)
- FarDriver BLE emulator or compatible device

## Troubleshooting

### Connection Issues
- Ensure FarDriver emulator is running
- Check Bluetooth is enabled
- Verify device is discoverable

### Display Issues
- Ensure minimum window size (1000x700)
- Check Python and tkinter installation
- Verify all dependencies are installed

### Performance Issues
- Close other applications to free system resources
- Reduce terminal logging if experiencing lag
- Check system Bluetooth performance 
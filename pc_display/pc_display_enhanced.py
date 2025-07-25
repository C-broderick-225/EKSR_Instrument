#!/usr/bin/env python3
"""
EKSR Instrument PC Display - Enhanced Version
A polished Python application that connects to the FarDriver BLE emulator and displays
the EKSR Instrument data on a computer screen using tkinter with modern UI elements.

This simulates the TFT display functionality without requiring the physical hardware.

LAG OPTIMIZATION IMPROVEMENTS:
- Increased display update frequency from 20 FPS to 60 FPS (16ms intervals)
- Increased gauge animation frequency from 60 FPS to 120 FPS (8ms intervals)
- Added data change tracking to avoid unnecessary UI updates
- Increased gauge animation speed from 0.1 to 0.3 for faster response
- Reduced animation completion threshold for quicker settling
- Emulator packet rate increased from 30ms to 20ms intervals

DEVELOPMENT FEATURES:
- CSV data export for analysis
- Packet inspector with detailed breakdown
- Performance monitoring (FPS, latency)
- Settings panel for configuration
- Data recording with timestamps
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import asyncio
import threading
import time
import math
import csv
import json
import os
from datetime import datetime
from bleak import BleakScanner, BleakClient
import struct

# Optional imports with fallbacks
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Performance monitoring will be limited.")
import gc

# BLE Service and Characteristic UUIDs
FARDRIVER_SERVICE_UUID = "ffe0"
FARDRIVER_CHARACTERISTIC_UUID = "ffec"

# Color scheme and styling - Modern 2024 Design System
COLORS = {
    # Background colors - Modern dark theme with better contrast
    'bg_dark': '#0f0f23',      # Deep dark blue-black
    'bg_medium': '#1a1a2e',    # Dark blue-grey
    'bg_light': '#16213e',     # Medium blue-grey
    'bg_lighter': '#0f3460',   # Lighter blue-grey for hover states
    
    # Primary accent colors - Modern, vibrant, accessible
    'primary': '#6366f1',      # Modern indigo (primary action)
    'primary_hover': '#4f46e5', # Darker indigo for hover
    'secondary': '#8b5cf6',    # Modern violet (secondary action)
    'secondary_hover': '#7c3aed', # Darker violet for hover
    
    # Semantic colors - High contrast, accessible
    'success': '#10b981',      # Modern emerald green
    'success_hover': '#059669', # Darker emerald
    'warning': '#f59e0b',      # Modern amber
    'warning_hover': '#d97706', # Darker amber
    'error': '#ef4444',        # Modern red
    'error_hover': '#dc2626',  # Darker red
    'info': '#3b82f6',         # Modern blue
    'info_hover': '#2563eb',   # Darker blue
    
    # Text colors - High contrast for accessibility
    'text_primary': '#f8fafc',   # Almost white
    'text_secondary': '#cbd5e1', # Light grey
    'text_muted': '#94a3b8',     # Medium grey
    'text_disabled': '#64748b',  # Dark grey for disabled
    
    # Button colors - Semantic mapping
    'btn_primary': '#6366f1',    # Connect button
    'btn_primary_hover': '#4f46e5',
    'btn_danger': '#ef4444',     # Disconnect button
    'btn_danger_hover': '#dc2626',
    'btn_success': '#10b981',    # Recording start
    'btn_success_hover': '#059669',
    'btn_warning': '#f59e0b',    # Recording stop
    'btn_warning_hover': '#d97706',
    'btn_secondary': '#8b5cf6',  # Settings button
    'btn_secondary_hover': '#7c3aed',
    
    # Legacy compatibility (mapped to new colors)
    'accent_blue': '#3b82f6',
    'accent_green': '#10b981',
    'accent_red': '#ef4444',
    'accent_orange': '#f59e0b',
    'accent_purple': '#8b5cf6'
}

# Fonts
FONTS = {
    'title': ('Segoe UI', 16, 'bold'),
    'heading': ('Segoe UI', 14, 'bold'),
    'subheading': ('Segoe UI', 12, 'bold'),
    'body': ('Segoe UI', 10),
    'display_large': ('Segoe UI', 48, 'bold'),
    'display_medium': ('Segoe UI', 32, 'bold'),
    'display_small': ('Segoe UI', 24, 'bold'),
    'mono': ('Consolas', 9)
}

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
        self.last_update = time.time()
        # Add data change tracking for immediate updates
        self._last_values = {}
        self._has_changes = False
        
        # Data recording features
        self.recording = False
        self.recorded_data = []
        self.csv_file = None
        self.csv_writer = None
        self.recording_start_time = None
        
        # Performance monitoring
        self.packet_count = 0
        self.packet_errors = 0
        self.last_packet_time = 0
        self.avg_latency = 0
        self.latency_samples = []
    
    def update_value(self, key, value):
        """Update a value and track if it changed"""
        if key not in self._last_values or self._last_values[key] != value:
            self._last_values[key] = value
            self._has_changes = True
            setattr(self, key, value)
            self.last_update = time.time()
            
            # Record data if recording is active
            if self.recording:
                self.record_data_point()
    
    def has_changes(self):
        """Check if any values have changed since last check"""
        has_changes = self._has_changes
        self._has_changes = False
        return has_changes
    
    def start_recording(self, filename=None):
        """Start recording data to CSV file"""
        if self.recording:
            return False
        
        # Check if auto-save is enabled
        if not settings.get('auto_save', True):
            # Just start recording in memory without file
            self.recording = True
            self.recording_start_time = time.time()
            self.recorded_data = []
            log_to_terminal("Recording started (memory only - auto-save disabled)", "INFO")
            return True
        
        # Create data directory if it doesn't exist
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"eksr_data_{timestamp}.csv"
        
        # Ensure filename is in the data directory
        if not os.path.dirname(filename):
            filename = os.path.join(data_dir, filename)
        
        try:
            self.csv_file = open(filename, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Write header with descriptive column names
            header = ['Timestamp', 'Throttle', 'Gear', 'RPM', 'Controller_Temp_C', 
                     'Motor_Temp_C', 'Speed_kmh', 'Power_W', 'Voltage_V', 'Packet_Count', 'Latency_ms']
            self.csv_writer.writerow(header)
            
            self.recording = True
            self.recording_start_time = time.time()
            self.recorded_data = []
            
            # Log the filename being used
            log_to_terminal(f"Recording started - saving to: {filename}", "INFO")
            
            return True
        except Exception as e:
            log_to_terminal(f"Failed to start recording: {e}", "ERROR")
            return False
    
    def stop_recording(self):
        """Stop recording data"""
        if not self.recording:
            return
        
        self.recording = False
        
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
        
        # Handle different recording modes
        if self.recorded_data:
            if settings.get('auto_save', True):
                log_to_terminal(f"Recording stopped. CSV data saved with {len(self.recorded_data)} data points in data/ directory.", "INFO")
            else:
                log_to_terminal(f"Recording stopped. {len(self.recorded_data)} data points stored in memory (auto-save was disabled).", "INFO")
    
    def record_data_point(self):
        """Record current data point"""
        if not self.recording:
            return
        
        timestamp = datetime.now().isoformat()
        data_point = {
            'timestamp': timestamp,
            'throttle': self.throttle,
            'gear': self.gear,
            'rpm': self.rpm,
            'controller_temp': self.controller_temp,
            'motor_temp': self.motor_temp,
            'speed': self.speed,
            'power': self.power,
            'voltage': self.voltage,
            'packet_count': self.packet_count,
            'latency': self.avg_latency
        }
        
        self.recorded_data.append(data_point)
        
        # Write to CSV only if auto-save is enabled
        if settings.get('auto_save', True) and self.csv_writer:
            row = [timestamp, self.throttle, self.gear, self.rpm, 
                   self.controller_temp, self.motor_temp, self.speed, 
                   self.power, self.voltage, self.packet_count, self.avg_latency]
            self.csv_writer.writerow(row)
            self.csv_file.flush()  # Ensure data is written immediately
    
    def update_performance_metrics(self, packet_time, latency):
        """Update performance monitoring metrics"""
        self.packet_count += 1
        self.last_packet_time = packet_time
        
        # Update latency tracking (keep last 100 samples)
        self.latency_samples.append(latency)
        if len(self.latency_samples) > 100:
            self.latency_samples.pop(0)
        
        self.avg_latency = sum(self.latency_samples) / len(self.latency_samples)
    
    def get_performance_stats(self):
        """Get current performance statistics"""
        return {
            'packet_count': self.packet_count,
            'packet_errors': self.packet_errors,
            'avg_latency': self.avg_latency,
            'packet_rate': self.packet_count / max(1, time.time() - self.recording_start_time) if self.recording_start_time else 0,
            'error_rate': self.packet_errors / max(1, self.packet_count)
        }

class PacketInspector:
    """Packet analysis and inspection tool"""
    
    def __init__(self):
        self.packet_history = []
        self.max_history = 1000
        self.current_packet = None
    
    def analyze_packet(self, data):
        """Analyze a BLE packet and return detailed information"""
        if len(data) < 16:
            return {
                'valid': False,
                'error': f'Invalid packet length: {len(data)} (expected 16)',
                'raw_data': ' '.join([f"{b:02X}" for b in data])  # Exact format from FarDriver
            }
        
        # Check header
        if data[0] != 0xAA:
            return {
                'valid': False,
                'error': f'Invalid header: 0x{data[0]:02X} (expected 0xAA)',
                'raw_data': ' '.join([f"{b:02X}" for b in data])  # Exact format from FarDriver
            }
        
        index = data[1]
        checksum = data[14]
        reserved = data[15]
        
        # Calculate expected checksum
        expected_checksum = 0
        for i in range(1, 14):
            expected_checksum ^= data[i]
        
        # Parse packet based on index
        packet_info = {
            'valid': True,
            'index': index,
            'raw_data': ' '.join([f"{b:02X}" for b in data]),  # Exact format from FarDriver
            'checksum_valid': checksum == expected_checksum,
            'checksum': f'0x{checksum:02X}',
            'expected_checksum': f'0x{expected_checksum:02X}',
            'reserved': f'0x{reserved:02X}',
            'timestamp': datetime.now().isoformat(),
            'parsed_data': {}
        }
        
        # Parse data based on packet type
        if index == 0:  # Main data
            packet_info['parsed_data'] = self._parse_main_data(data)
        elif index == 1:  # Voltage
            packet_info['parsed_data'] = self._parse_voltage_data(data)
        elif index == 4:  # Controller temperature
            packet_info['parsed_data'] = self._parse_controller_temp_data(data)
        elif index == 13:  # Motor temperature and throttle
            packet_info['parsed_data'] = self._parse_motor_throttle_data(data)
        else:
            packet_info['parsed_data'] = {'unknown_index': f'Index {index} not recognized'}
        
        # Store in history
        self.packet_history.append(packet_info)
        if len(self.packet_history) > self.max_history:
            self.packet_history.pop(0)
        
        self.current_packet = packet_info
        return packet_info
    
    def _parse_main_data(self, data):
        """Parse main data packet (index 0)"""
        gear_bits = (data[2] >> 2) & 0x03
        gear_map = {0: 'High', 1: 'Mid', 2: 'Low', 3: 'Mid'}
        gear = gear_map.get(gear_bits, 'Unknown')
        
        rpm = (data[4] << 8) | data[5]
        iq = ((data[8] << 8) | data[9]) / 100.0
        id = ((data[10] << 8) | data[11]) / 100.0
        is_mag = (iq * iq + id * id) ** 0.5
        
        return {
            'gear_bits': f'0b{gear_bits:02b}',
            'gear': gear,
            'rpm': rpm,
            'iq_current': f'{iq:.2f}A',
            'id_current': f'{id:.2f}A',
            'current_magnitude': f'{is_mag:.2f}A',
            'data_bytes': {
                'gear_byte': f'0x{data[2]:02X}',
                'rpm_high': f'0x{data[4]:02X}',
                'rpm_low': f'0x{data[5]:02X}',
                'iq_high': f'0x{data[8]:02X}',
                'iq_low': f'0x{data[9]:02X}',
                'id_high': f'0x{data[10]:02X}',
                'id_low': f'0x{data[11]:02X}'
            }
        }
    
    def _parse_voltage_data(self, data):
        """Parse voltage data packet (index 1)"""
        voltage_raw = (data[2] << 8) | data[3]
        voltage = voltage_raw / 10.0
        
        return {
            'voltage_raw': voltage_raw,
            'voltage': f'{voltage:.1f}V',
            'data_bytes': {
                'voltage_high': f'0x{data[2]:02X}',
                'voltage_low': f'0x{data[3]:02X}'
            }
        }
    
    def _parse_controller_temp_data(self, data):
        """Parse controller temperature data packet (index 4)"""
        temp = data[2]
        
        return {
            'temperature': f'{temp}°C',
            'data_bytes': {
                'temp_byte': f'0x{data[2]:02X}'
            }
        }
    
    def _parse_motor_throttle_data(self, data):
        """Parse motor temperature and throttle data packet (index 13)"""
        motor_temp = data[2]
        throttle_raw = (data[4] << 8) | data[5]
        throttle_percent = (throttle_raw / 4095.0) * 100
        
        return {
            'motor_temperature': f'{motor_temp}°C',
            'throttle_raw': throttle_raw,
            'throttle_percent': f'{throttle_percent:.1f}%',
            'data_bytes': {
                'motor_temp': f'0x{data[2]:02X}',
                'throttle_high': f'0x{data[4]:02X}',
                'throttle_low': f'0x{data[5]:02X}'
            }
        }
    
    def get_packet_statistics(self):
        """Get statistics about packet history"""
        if not self.packet_history:
            return {}
        
        index_counts = {}
        checksum_errors = 0
        total_packets = len(self.packet_history)
        
        for packet in self.packet_history:
            if packet['valid']:
                index = packet['index']
                index_counts[index] = index_counts.get(index, 0) + 1
                if not packet['checksum_valid']:
                    checksum_errors += 1
        
        return {
            'total_packets': total_packets,
            'valid_packets': sum(1 for p in self.packet_history if p['valid']),
            'checksum_errors': checksum_errors,
            'index_distribution': index_counts,
            'error_rate': checksum_errors / total_packets if total_packets > 0 else 0
        }
    
    def get_recent_packets(self, count=10):
        """Get the most recent packets"""
        return self.packet_history[-count:] if self.packet_history else []

# Global variables
ctr_data = ControllerData()
packet_inspector = PacketInspector()
is_connected = False
client = None
terminal_widget = None
terminal_paused = False
should_disconnect = False

# Performance monitoring
fps_counter = 0
last_fps_time = time.time()
display_fps = 0
memory_usage = 0
cpu_usage = 0

# Settings
settings = {
    'display_fps': 60,
    'gauge_animation_fps': 120,
    'terminal_max_lines': 1000,
    'packet_history_size': 1000,
    'auto_record': False,
    'auto_save': True,  # Automatically save CSV files
    'record_interval': 1.0,  # seconds
    'show_performance': True,
    'show_packet_details': True,
    'theme': 'dark'
}

def log_to_terminal(message, level="INFO"):
    """Global function to log messages to terminal"""
    global terminal_paused
    if terminal_widget and hasattr(terminal_widget, 'log_to_terminal') and not terminal_paused:
        # Check if message should be shown based on filters
        if hasattr(terminal_widget, 'should_show_message'):
            if terminal_widget.should_show_message(level, message):
                terminal_widget.log_to_terminal(message, level)
        else:
            # Fallback if filter system not available
            terminal_widget.log_to_terminal(message, level)

class ModernButton(tk.Button):
    """Custom modern button with hover effects"""
    def __init__(self, parent, **kwargs):
        # Store original background color if provided
        self.original_bg = kwargs.get('bg', COLORS['bg_medium'])
        self._is_hovered = False
        
        super().__init__(parent, **kwargs)
        self.config(
            relief='flat',
            borderwidth=0,
            font=FONTS['body'],
            cursor='hand2',
            bg=self.original_bg
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
    
    def on_enter(self, event):
        """Handle mouse enter - only change color if button is enabled"""
        if self['state'] != 'disabled':
            self._is_hovered = True
            try:
                # Create a lighter version of the original color for hover effect
                hover_bg = self._lighten_color(self.original_bg)
                self.config(bg=hover_bg)
            except tk.TclError:
                pass  # Ignore platform-specific errors
    
    def on_leave(self, event):
        """Handle mouse leave - restore original color"""
        if self['state'] != 'disabled':
            self._is_hovered = False
            try:
                self.config(bg=self.original_bg)
            except tk.TclError:
                pass  # Ignore platform-specific errors
    
    def config(self, **kwargs):
        """Override config to track background color changes"""
        try:
            if 'bg' in kwargs:
                self.original_bg = kwargs['bg']
                # Always update the background color, but if hovering, 
                # the hover effect will override it until mouse leaves
                super().config(**kwargs)
            else:
                super().config(**kwargs)
        except tk.TclError as e:
            # Handle platform-specific configuration errors
            if "unknown option" not in str(e):
                raise  # Re-raise if it's not an unknown option error
    
    def configure(self, **kwargs):
        """Alias for config method"""
        return self.config(**kwargs)
    
    def _lighten_color(self, color):
        """Create a darker version of the given color for hover effects (better contrast)"""
        try:
            # Handle hex colors
            if color.startswith('#'):
                # Remove # and convert to RGB
                hex_color = color[1:]
                if len(hex_color) == 3:
                    hex_color = ''.join([c*2 for c in hex_color])
                
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                
                # Darken by 15% for better contrast (instead of lightening)
                r = max(0, int(r * 0.85))
                g = max(0, int(g * 0.85))
                b = max(0, int(b * 0.85))
                
                return f'#{r:02x}{g:02x}{b:02x}'
            else:
                # For named colors, return a default darker color
                return COLORS['bg_lighter']
        except:
            # Fallback to default darker color
            return COLORS['bg_lighter']

class ModernCheckbox(tk.Checkbutton):
    """Custom modern checkbox with hover effects"""
    def __init__(self, parent, **kwargs):
        # Store original background color if provided
        self.original_bg = kwargs.get('bg', COLORS['bg_medium'])
        self._is_hovered = False
        
        super().__init__(parent, **kwargs)
        self.config(
            relief='flat',
            borderwidth=0,
            font=FONTS['body'],
            cursor='hand2',
            bg=self.original_bg,
            fg=COLORS['text_primary'],
            selectcolor=COLORS['bg_dark'],
            activebackground=self.original_bg,
            activeforeground=COLORS['text_primary'],
            offrelief='flat',
            overrelief='flat'
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
    
    def on_enter(self, event):
        """Handle mouse enter"""
        if self['state'] != 'disabled':
            self._is_hovered = True
            try:
                hover_bg = self._lighten_color(self.original_bg)
                self.config(bg=hover_bg, activebackground=hover_bg)
            except tk.TclError:
                pass
    
    def on_leave(self, event):
        """Handle mouse leave"""
        if self['state'] != 'disabled':
            self._is_hovered = False
            try:
                self.config(bg=self.original_bg, activebackground=self.original_bg)
            except tk.TclError:
                pass
    
    def _lighten_color(self, color):
        """Create a darker version of the given color for hover effects"""
        try:
            if color.startswith('#'):
                hex_color = color[1:]
                if len(hex_color) == 3:
                    hex_color = ''.join([c*2 for c in hex_color])
                
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                
                r = max(0, int(r * 0.85))
                g = max(0, int(g * 0.85))
                b = max(0, int(b * 0.85))
                
                return f'#{r:02x}{g:02x}{b:02x}'
            else:
                return COLORS['bg_lighter']
        except:
            return COLORS['bg_lighter']

class GradientCanvas(tk.Canvas):
    """Canvas with gradient background"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.create_gradient()
    
    def create_gradient(self):
        """Create a subtle gradient background"""
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        
        for i in range(height):
            # Create a subtle gradient from dark to slightly lighter
            ratio = i / height
            r = int(26 + (45 - 26) * ratio)
            g = int(26 + (45 - 26) * ratio)
            b = int(26 + (45 - 26) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            self.create_line(0, i, width, i, fill=color, width=1)

class AnimatedGauge(tk.Canvas):
    """Animated circular gauge widget"""
    def __init__(self, parent, size=120, **kwargs):
        super().__init__(parent, width=size, height=size, **kwargs)
        self.size = size
        self.center = size // 2
        self.radius = (size - 20) // 2
        self.value = 0
        self.max_value = 100
        self.animation_speed = 0.3  # Increased from 0.1 for faster response
        self.target_value = 0
        self.is_animating = False
        
        self.config(bg=COLORS['bg_dark'], highlightthickness=0)
        self.draw_gauge()
    
    def set_value(self, value, max_value=None):
        """Set the gauge value with animation"""
        if max_value is not None:
            self.max_value = max_value
        self.target_value = min(value, self.max_value)
        
        # If value changed significantly, start animation
        if abs(self.value - self.target_value) > 1.0:
            if not self.is_animating:
                self.is_animating = True
                self.animate()
    
    def animate(self):
        """Animate the gauge to target value"""
        if abs(self.value - self.target_value) > 0.5:  # Reduced threshold for faster completion
            self.value += (self.target_value - self.value) * self.animation_speed
            self.draw_gauge()
            self.after(8, self.animate)  # Increased from 16ms to 8ms (~120 FPS)
        else:
            # Ensure we reach the exact target value
            self.value = self.target_value
            self.draw_gauge()
            self.is_animating = False
    
    def draw_gauge(self):
        """Draw the gauge with current value"""
        self.delete("all")
        
        # Draw background circle
        self.create_arc(
            self.center - self.radius, self.center - self.radius,
            self.center + self.radius, self.center + self.radius,
            start=135, extent=270, fill=COLORS['bg_medium'], outline=COLORS['bg_light'], width=3
        )
        
        # Calculate angle for current value
        angle = 135 + (self.value / self.max_value) * 270
        
        # Draw value arc
        if self.value > 0:
            color = self.get_gauge_color()
            self.create_arc(
                self.center - self.radius, self.center - self.radius,
                self.center + self.radius, self.center + self.radius,
                start=135, extent=(self.value / self.max_value) * 270,
                fill=color, outline=color, width=3
            )
        
        # Draw center circle
        self.create_oval(
            self.center - self.radius + 10, self.center - self.radius + 10,
            self.center + self.radius - 10, self.center + self.radius - 10,
            fill=COLORS['bg_dark'], outline=COLORS['bg_light'], width=2
        )
        
        # Draw value text
        self.create_text(
            self.center, self.center,
            text=f"{self.value:.0f}",
            font=FONTS['display_small'],
            fill=COLORS['text_primary']
        )
    
    def get_gauge_color(self):
        """Get color based on value percentage"""
        percentage = self.value / self.max_value
        if percentage < 0.3:
            return COLORS['success']
        elif percentage < 0.7:
            return COLORS['warning']
        else:
            return COLORS['error']

class EKSRDisplayEnhanced:
    def __init__(self, root):
        self.root = root
        self.root.title("EKSR Instrument Display - Enhanced")
        self.root.geometry("1200x800")
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.minsize(1000, 700)
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Initialize terminal filter settings (before creating UI)
        self.terminal_filters = {
            'show_info': tk.BooleanVar(value=True),
            'show_warning': tk.BooleanVar(value=True),
            'show_error': tk.BooleanVar(value=True),
            'show_success': tk.BooleanVar(value=True),
            'show_data': tk.BooleanVar(value=True),
            'show_connection': tk.BooleanVar(value=True),
            'show_recording': tk.BooleanVar(value=True),
            'show_performance': tk.BooleanVar(value=True)
        }
        
        # Initialize search variables
        self.search_active = False
        self.search_frame = None
        self.search_entry = None
        self.search_results = []
        self.current_search_index = -1
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.create_main_content()
        
        # Create status bar
        self.create_status_bar()
        
        # Set global terminal reference
        global terminal_widget
        terminal_widget = self
        
        # Load settings
        self.load_settings()
        
        # Start update loop
        self.update_display()
        
        # Apply window styling
        self.style_window()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-f>', lambda e: self.toggle_search())
        self.root.bind('<F3>', lambda e: self.search_next())
        self.root.bind('<Shift-F3>', lambda e: self.search_previous())
        self.root.bind('<Escape>', lambda e: self.hide_search() if self.search_active else None)
    
    def style_window(self):
        """Apply modern window styling"""
        try:
            # Try to set window icon (if available)
            if os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure custom styles
        style.configure('Modern.TFrame', background=COLORS['bg_dark'])
        style.configure('Modern.TLabel', background=COLORS['bg_dark'], foreground=COLORS['text_primary'])
        style.configure('Modern.TButton', background=COLORS['btn_primary'], foreground=COLORS['text_primary'])
    
    def create_sidebar(self):
        """Create the sidebar with controls and terminal"""
        self.sidebar = tk.Frame(self.root, bg=COLORS['bg_medium'], width=350)
        self.sidebar.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
        self.sidebar.grid_propagate(False)
        
        # Sidebar title
        title_frame = tk.Frame(self.sidebar, bg=COLORS['bg_medium'])
        title_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(title_frame, text="EKSR Instrument", 
                font=FONTS['title'], fg=COLORS['text_primary'], bg=COLORS['bg_medium']).pack()
        tk.Label(title_frame, text="Control Panel", 
                font=FONTS['body'], fg=COLORS['text_secondary'], bg=COLORS['bg_medium']).pack()
        
        # Connection controls
        connection_frame = tk.Frame(self.sidebar, bg=COLORS['bg_medium'])
        connection_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        self.connect_btn = ModernButton(connection_frame, text="Connect", 
                                      bg=COLORS['btn_primary'], fg=COLORS['text_primary'],
                                      command=self.toggle_connection)
        self.connect_btn.pack(fill='x')
        
        # Update button states
        self.update_connection_buttons()
        
        # Recording controls
        self.create_recording_section()
        
        # Performance monitoring
        self.create_performance_section()
        
        # Settings button
        self.create_settings_button()
        
        # Terminal section
        self.create_terminal_section()
    
    def create_recording_section(self):
        """Create recording controls section"""
        recording_frame = tk.Frame(self.sidebar, bg=COLORS['bg_medium'])
        recording_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        # Recording header with info about data directory
        recording_header = tk.Frame(recording_frame, bg=COLORS['bg_medium'])
        recording_header.pack(fill='x', pady=(0, 5))
        
        tk.Label(recording_header, text="Data Recording", 
                font=FONTS['subheading'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_medium']).pack(side='left')
        
        # Add info about data directory
        self.data_info = tk.Label(recording_header, text="(auto-saves to data/ folder)", 
                                 font=FONTS['body'], fg=COLORS['text_muted'], 
                                 bg=COLORS['bg_medium'])
        self.data_info.pack(side='right')
        
        self.record_btn = ModernButton(recording_frame, text="Start Recording", 
                                      bg=COLORS['btn_success'], fg=COLORS['text_primary'],
                                      command=self.toggle_recording)
        self.record_btn.pack(fill='x')
    
    def create_performance_section(self):
        """Create performance monitoring section"""
        performance_frame = tk.Frame(self.sidebar, bg=COLORS['bg_medium'])
        performance_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        tk.Label(performance_frame, text="Performance", 
                font=FONTS['subheading'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_medium']).pack(side='left')
        
        self.fps_label = tk.Label(performance_frame, text="FPS: 0", 
                                  font=FONTS['body'], fg=COLORS['text_secondary'], 
                                  bg=COLORS['bg_medium'])
        self.fps_label.pack(side='left', padx=5)
        
        self.latency_label = tk.Label(performance_frame, text="Latency: 0ms", 
                                     font=FONTS['body'], fg=COLORS['text_secondary'], 
                                     bg=COLORS['bg_medium'])
        self.latency_label.pack(side='left', padx=5)
        
        self.memory_label = tk.Label(performance_frame, text="Memory: 0MB", 
                                    font=FONTS['body'], fg=COLORS['text_secondary'], 
                                    bg=COLORS['bg_medium'])
        self.memory_label.pack(side='left', padx=5)
        
        self.cpu_label = tk.Label(performance_frame, text="CPU: 0%", 
                                  font=FONTS['body'], fg=COLORS['text_secondary'], 
                                  bg=COLORS['bg_medium'])
        self.cpu_label.pack(side='left', padx=5)
    
    def create_settings_button(self):
        """Create settings button"""
        settings_btn = ModernButton(self.sidebar, text="Settings", 
                                    bg=COLORS['btn_secondary'], fg=COLORS['text_primary'],
                                    command=self.show_settings)
        settings_btn.pack(fill='x', padx=10, pady=10)
    
    def create_terminal_section(self):
        """Create terminal section"""
        terminal_frame = tk.Frame(self.sidebar, bg=COLORS['bg_medium'])
        terminal_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Terminal header
        terminal_header = tk.Frame(terminal_frame, bg=COLORS['bg_medium'])
        terminal_header.pack(fill='x', pady=(0, 5))
        
        tk.Label(terminal_header, text="Data Terminal", 
                font=FONTS['subheading'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_medium']).pack(side='left')
        
        # Terminal controls
        controls_frame = tk.Frame(terminal_header, bg=COLORS['bg_medium'])
        controls_frame.pack(side='right')
        
        self.pause_btn = ModernButton(controls_frame, text="⏸", 
                                    bg=COLORS['warning'], fg=COLORS['text_primary'],
                                    command=self.toggle_pause)
        self.pause_btn.pack(side='left', padx=2)
        
        self.clear_btn = ModernButton(controls_frame, text="🗑", 
                                    bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                                    command=self.clear_terminal)
        self.clear_btn.pack(side='left', padx=2)
        
        # Search functionality
        self.search_btn = ModernButton(controls_frame, text="🔍", 
                                     bg=COLORS['accent_blue'], fg=COLORS['text_primary'],
                                     command=self.toggle_search)
        self.search_btn.pack(side='left', padx=2)
        
        # Packet inspector button
        self.inspector_btn = ModernButton(controls_frame, text="📊", 
                                        bg=COLORS['accent_purple'], fg=COLORS['text_primary'],
                                        command=self.show_packet_inspector)
        self.inspector_btn.pack(side='left', padx=2)
        
        # Data folder button
        self.data_folder_btn = ModernButton(controls_frame, text="📁", 
                                          bg=COLORS['btn_success'], fg=COLORS['text_primary'],
                                          command=self.open_data_folder)
        self.data_folder_btn.pack(side='left', padx=2)
        
        # Terminal widget
        self.terminal = scrolledtext.ScrolledText(
            terminal_frame,
            bg=COLORS['bg_dark'],
            fg=COLORS['text_primary'],
            font=FONTS['mono'],
            insertbackground=COLORS['text_primary'],
            selectbackground=COLORS['accent_blue'],
            relief='flat',
            borderwidth=0
        )
        self.terminal.pack(fill='both', expand=True)
        
        # Configure terminal colors
        self.terminal.tag_configure("error", foreground=COLORS['error'])
        self.terminal.tag_configure("warning", foreground=COLORS['warning'])
        self.terminal.tag_configure("info", foreground=COLORS['info'])
        self.terminal.tag_configure("success", foreground=COLORS['success'])
        self.terminal.tag_configure("data", foreground=COLORS['accent_green'])
        self.terminal.tag_configure("search_highlight", background=COLORS['warning'], foreground=COLORS['text_primary'])
    

    
    def update_terminal_filters(self):
        """Update terminal display based on filter settings"""
        # This will be called when checkboxes are toggled
        # For now, we'll just log the current filter state
        active_filters = [key for key, var in self.terminal_filters.items() if var.get()]
        self.log_to_terminal(f"Terminal filters updated: {', '.join(active_filters)}", "INFO")
    
    def should_show_message(self, level, message):
        """Determine if a message should be shown based on filter settings"""
        # Always show filter update messages to avoid confusion
        if "Terminal filters updated" in message:
            return True
        
        # Check level-based filters
        if level == "INFO":
            return self.terminal_filters['show_info'].get()
        elif level == "WARNING":
            return self.terminal_filters['show_warning'].get()
        elif level == "ERROR":
            return self.terminal_filters['show_error'].get()
        elif level == "SUCCESS":
            return self.terminal_filters['show_success'].get()
        elif level == "DATA":
            return self.terminal_filters['show_data'].get()
        
        # Check content-based filters
        if "connected" in message.lower() or "disconnected" in message.lower():
            return self.terminal_filters['show_connection'].get()
        elif "recording" in message.lower() or "recorded" in message.lower():
            return self.terminal_filters['show_recording'].get()
        elif "fps" in message.lower() or "latency" in message.lower() or "performance" in message.lower():
            return self.terminal_filters['show_performance'].get()
        
        # Default to showing if no specific filter applies
        return True
    
    def select_all_filters(self):
        """Select all terminal filters"""
        for var in self.terminal_filters.values():
            var.set(True)
        self.log_to_terminal("All terminal filters enabled", "INFO")
    
    def clear_all_filters(self):
        """Clear all terminal filters"""
        for var in self.terminal_filters.values():
            var.set(False)
        self.log_to_terminal("All terminal filters disabled", "INFO")
    
    def create_main_content(self):
        """Create the main content area with gauges and displays"""
        self.main_content = tk.Frame(self.root, bg=COLORS['bg_dark'])
        self.main_content.grid(row=0, column=1, sticky='nsew', padx=2, pady=2)
        
        # Configure grid
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(1, weight=1)
        self.main_content.grid_columnconfigure(2, weight=1)
        
        # Top row - Power and Speed
        self.create_power_section()
        self.create_speed_section()
        self.create_voltage_section()
        
        # Middle row - Gauges
        self.create_rpm_gauge()
        self.create_throttle_gauge()
        self.create_temp_section()
        
        # Bottom row - Additional info
        self.create_info_panel()
    
    def create_power_section(self):
        """Create power display section"""
        power_frame = tk.Frame(self.main_content, bg=COLORS['bg_dark'])
        power_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        
        # Power gauge
        self.power_gauge = AnimatedGauge(power_frame, size=150)
        self.power_gauge.pack(pady=10)
        
        # Power label
        tk.Label(power_frame, text="POWER (W)", 
                font=FONTS['subheading'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack()
    
    def create_speed_section(self):
        """Create speed display section"""
        speed_frame = tk.Frame(self.main_content, bg=COLORS['bg_dark'])
        speed_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        
        # Speed display
        self.speed_display = tk.Label(speed_frame, text="0", 
                                    font=FONTS['display_large'], fg=COLORS['accent_blue'], 
                                    bg=COLORS['bg_dark'])
        self.speed_display.pack(pady=20)
        
        # Speed label
        tk.Label(speed_frame, text="SPEED (km/h)", 
                font=FONTS['subheading'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack()
    
    def create_voltage_section(self):
        """Create voltage display section"""
        voltage_frame = tk.Frame(self.main_content, bg=COLORS['bg_dark'])
        voltage_frame.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')
        
        # Voltage display
        self.voltage_display = tk.Label(voltage_frame, text="0.0V", 
                                      font=FONTS['display_medium'], fg=COLORS['accent_green'], 
                                      bg=COLORS['bg_dark'])
        self.voltage_display.pack(pady=10)
        
        # Battery bar
        self.battery_bar = tk.Canvas(voltage_frame, width=200, height=25, 
                                   bg=COLORS['bg_dark'], highlightthickness=0)
        self.battery_bar.pack(pady=5)
        
        # Voltage label
        tk.Label(voltage_frame, text="BATTERY VOLTAGE", 
                font=FONTS['subheading'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack()
    
    def create_rpm_gauge(self):
        """Create RPM gauge section"""
        rpm_frame = tk.Frame(self.main_content, bg=COLORS['bg_dark'])
        rpm_frame.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')
        
        # RPM gauge
        self.rpm_gauge = AnimatedGauge(rpm_frame, size=120)
        self.rpm_gauge.pack(pady=10)
        
        # RPM label
        tk.Label(rpm_frame, text="RPM", 
                font=FONTS['subheading'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack()
    
    def create_throttle_gauge(self):
        """Create throttle gauge section"""
        throttle_frame = tk.Frame(self.main_content, bg=COLORS['bg_dark'])
        throttle_frame.grid(row=1, column=1, padx=10, pady=10, sticky='nsew')
        
        # Throttle gauge
        self.throttle_gauge = AnimatedGauge(throttle_frame, size=120)
        self.throttle_gauge.pack(pady=10)
        
        # Throttle label
        tk.Label(throttle_frame, text="THROTTLE", 
                font=FONTS['subheading'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack()
    
    def create_temp_section(self):
        """Create temperature section"""
        temp_frame = tk.Frame(self.main_content, bg=COLORS['bg_dark'])
        temp_frame.grid(row=1, column=2, padx=10, pady=10, sticky='nsew')
        
        # Motor temperature
        motor_temp_frame = tk.Frame(temp_frame, bg=COLORS['bg_dark'])
        motor_temp_frame.pack(fill='x', pady=5)
        
        tk.Label(motor_temp_frame, text="Motor:", 
                font=FONTS['body'], fg=COLORS['text_secondary'], 
                bg=COLORS['bg_dark']).pack(side='left')
        
        self.motor_temp_label = tk.Label(motor_temp_frame, text="0°C", 
                                       font=FONTS['subheading'], fg=COLORS['accent_orange'], 
                                       bg=COLORS['bg_dark'])
        self.motor_temp_label.pack(side='right')
        
        # Controller temperature
        controller_temp_frame = tk.Frame(temp_frame, bg=COLORS['bg_dark'])
        controller_temp_frame.pack(fill='x', pady=5)
        
        tk.Label(controller_temp_frame, text="Controller:", 
                font=FONTS['body'], fg=COLORS['text_secondary'], 
                bg=COLORS['bg_dark']).pack(side='left')
        
        self.controller_temp_label = tk.Label(controller_temp_frame, text="0°C", 
                                            font=FONTS['subheading'], fg=COLORS['accent_orange'], 
                                            bg=COLORS['bg_dark'])
        self.controller_temp_label.pack(side='right')
        
        # Gear display
        gear_frame = tk.Frame(temp_frame, bg=COLORS['bg_dark'])
        gear_frame.pack(fill='x', pady=10)
        
        tk.Label(gear_frame, text="Gear:", 
                font=FONTS['body'], fg=COLORS['text_secondary'], 
                bg=COLORS['bg_dark']).pack(side='left')
        
        self.gear_label = tk.Label(gear_frame, text="0", 
                                 font=FONTS['display_small'], fg=COLORS['accent_purple'], 
                                 bg=COLORS['bg_dark'])
        self.gear_label.pack(side='right')
    
    def create_info_panel(self):
        """Create information panel"""
        info_frame = tk.Frame(self.main_content, bg=COLORS['bg_medium'])
        info_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky='ew')
        
        # Info labels
        self.info_label = tk.Label(info_frame, text="Ready to connect...", 
                                 font=FONTS['body'], fg=COLORS['text_secondary'], 
                                 bg=COLORS['bg_medium'])
        self.info_label.pack(pady=5)
    
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = tk.Frame(self.root, bg=COLORS['bg_medium'], height=25)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.status_bar.grid_propagate(False)
        
        # Status text
        self.status_text = tk.Label(self.status_bar, text="EKSR Instrument Display v2.0", 
                                  font=FONTS['body'], fg=COLORS['text_muted'], 
                                  bg=COLORS['bg_medium'])
        self.status_text.pack(side='left', padx=10, pady=2)
        
        # Time display
        self.time_label = tk.Label(self.status_bar, text="", 
                                 font=FONTS['body'], fg=COLORS['text_muted'], 
                                 bg=COLORS['bg_medium'])
        self.time_label.pack(side='right', padx=10, pady=2)
    

    
    def update_connection_buttons(self):
        """Update the state of the connection button based on current status"""
        has_recent_data = (time.time() - ctr_data.last_update) < 5.0
        actual_connected = is_connected or has_recent_data
        
        # Only update if state has changed
        if not hasattr(self, '_last_connection_state'):
            self._last_connection_state = None
        
        if self._last_connection_state != actual_connected:
            self._last_connection_state = actual_connected
            
            if actual_connected:
                self.connect_btn.config(text="Disconnect", bg=COLORS['btn_danger'], state='normal')
            else:
                self.connect_btn.config(text="Connect", bg=COLORS['btn_primary'], state='normal')
    
    def update_recording_info(self):
        """Update the recording info text based on auto-save setting"""
        if hasattr(self, 'data_info'):
            if settings.get('auto_save', True):
                self.data_info.config(text="(auto-saves to data/ folder)")
            else:
                self.data_info.config(text="(stores in memory only)")
    
    def toggle_connection(self):
        """Toggle connection status - connect or disconnect from BLE device"""
        global is_connected, should_disconnect, client
        
        if is_connected:
            # Disconnect
            self.disconnect_device()
        else:
            # Connect - reset disconnect flag to allow reconnection
            log_to_terminal("Manual connect requested", "INFO")
            should_disconnect = False
            self.connect_btn.config(state='disabled', text="Connecting...")
    
    def disconnect_device(self):
        """Disconnect from the BLE device"""
        global is_connected, should_disconnect, client
        
        log_to_terminal("Manual disconnect requested", "INFO")
        should_disconnect = True
        is_connected = False
        
        # Update button states immediately
        self.connect_btn.config(text="Connect", bg=COLORS['btn_primary'], state='normal')
        
        # Disconnect the client
        if client:
            try:
                # Run disconnect in a separate thread to avoid blocking
                def disconnect_client():
                    try:
                        # Check if client is still connected before trying to disconnect
                        if client and hasattr(client, 'is_connected') and client.is_connected:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(client.disconnect())
                            loop.close()
                            log_to_terminal("Client disconnected successfully", "INFO")
                        else:
                            log_to_terminal("Client was already disconnected", "INFO")
                    except Exception as e:
                        error_msg = str(e) if e else "Unknown error"
                        error_type = type(e).__name__
                        log_to_terminal(f"Error during disconnect: {error_type}: {error_msg}", "ERROR")
                
                disconnect_thread = threading.Thread(target=disconnect_client, daemon=True)
                disconnect_thread.start()
                
            except Exception as e:
                error_msg = str(e) if e else "Unknown error"
                error_type = type(e).__name__
                log_to_terminal(f"Error disconnecting: {error_type}: {error_msg}", "ERROR")
        
        log_to_terminal("Disconnected from FarDriver emulator", "INFO")
    
    def toggle_pause(self):
        """Toggle pause/resume of terminal logging and display updates"""
        global terminal_paused
        terminal_paused = not terminal_paused
        
        if terminal_paused:
            self.pause_btn.config(text="▶", bg=COLORS['success'])
            self.log_to_terminal("Display paused - logging and updates stopped", "INFO")
        else:
            self.pause_btn.config(text="⏸", bg=COLORS['warning'])
            self.log_to_terminal("Display resumed - logging and updates active", "INFO")
    
    def clear_terminal(self):
        """Clear the terminal display"""
        self.terminal.delete(1.0, tk.END)
        self.log_to_terminal("Terminal cleared", "INFO")
    
    def toggle_search(self):
        """Toggle search functionality on/off"""
        if self.search_active:
            self.hide_search()
        else:
            self.show_search()
    
    def show_search(self):
        """Show search interface"""
        if self.search_active:
            return
        
        self.search_active = True
        self.search_btn.config(text="✕", bg=COLORS['error'])
        
        # Create search frame
        self.search_frame = tk.Frame(self.sidebar, bg=COLORS['bg_medium'])
        self.search_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        # Search entry
        search_entry_frame = tk.Frame(self.search_frame, bg=COLORS['bg_medium'])
        search_entry_frame.pack(fill='x', pady=2)
        
        tk.Label(search_entry_frame, text="Search:", 
                font=FONTS['body'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_medium']).pack(side='left')
        
        self.search_entry = tk.Entry(search_entry_frame, 
                                   bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
                                   font=FONTS['body'], relief='flat', 
                                   insertbackground=COLORS['text_primary'])
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(5, 5))
        self.search_entry.bind('<Return>', self.perform_search)
        self.search_entry.bind('<KeyRelease>', self.on_search_key_release)
        self.search_entry.focus()
        
        # Search controls
        search_controls = tk.Frame(self.search_frame, bg=COLORS['bg_medium'])
        search_controls.pack(fill='x', pady=2)
        
        self.prev_btn = ModernButton(search_controls, text="↑", 
                                   bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                                   command=self.search_previous, width=3)
        self.prev_btn.pack(side='left', padx=2)
        
        self.next_btn = ModernButton(search_controls, text="↓", 
                                   bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                                   command=self.search_next, width=3)
        self.next_btn.pack(side='left', padx=2)
        
        self.search_count_label = tk.Label(search_controls, text="0 results", 
                                         font=FONTS['body'], fg=COLORS['text_secondary'], 
                                         bg=COLORS['bg_medium'])
        self.search_count_label.pack(side='left', padx=10)
        
        # Clear search button
        self.clear_search_btn = ModernButton(search_controls, text="Clear", 
                                           bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                                           command=self.clear_search)
        self.clear_search_btn.pack(side='right')
    
    def hide_search(self):
        """Hide search interface"""
        if not self.search_active:
            return
        
        self.search_active = False
        self.search_btn.config(text="🔍", bg=COLORS['btn_primary'])
        
        if self.search_frame:
            self.search_frame.destroy()
            self.search_frame = None
            self.search_entry = None
        
        # Clear search highlights
        self.clear_search_highlights()
    
    def on_search_key_release(self, event):
        """Handle search entry key release for real-time search"""
        # Debounce search to avoid too many searches while typing
        if hasattr(self, '_search_after_id'):
            self.root.after_cancel(self._search_after_id)
        
        # If search entry is empty, clear highlights immediately
        if not self.search_entry.get().strip():
            self.clear_search_highlights()
            self.search_count_label.config(text="0 results")
            return
        
        self._search_after_id = self.root.after(300, self.perform_search)
    
    def perform_search(self, event=None):
        """Perform search in terminal content"""
        if not self.search_entry:
            return
        
        search_text = self.search_entry.get().strip()
        if not search_text:
            self.clear_search_highlights()
            self.search_count_label.config(text="0 results")
            return
        
        # Clear previous highlights
        self.clear_search_highlights()
        
        # Get terminal content
        content = self.terminal.get(1.0, tk.END)
        
        # Find all matches
        self.search_results = []
        start_pos = 1.0
        
        while True:
            pos = self.terminal.search(search_text, start_pos, tk.END, nocase=True)
            if not pos:
                break
            
            # Calculate end position
            end_pos = f"{pos}+{len(search_text)}c"
            self.search_results.append((pos, end_pos))
            start_pos = end_pos
        
        # Update count
        count = len(self.search_results)
        self.search_count_label.config(text=f"{count} result{'s' if count != 1 else ''}")
        
        # Highlight all matches
        for pos, end_pos in self.search_results:
            self.terminal.tag_add("search_highlight", pos, end_pos)
        
        # Go to first match if any found
        if self.search_results:
            self.current_search_index = 0
            self.highlight_current_match()
        else:
            self.current_search_index = -1
    
    def search_next(self):
        """Go to next search result"""
        if not self.search_results:
            return
        
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        self.highlight_current_match()
    
    def search_previous(self):
        """Go to previous search result"""
        if not self.search_results:
            return
        
        self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
        self.highlight_current_match()
    
    def highlight_current_match(self):
        """Highlight the current search match and scroll to it"""
        if not self.search_results or self.current_search_index < 0:
            return
        
        # Remove previous current highlight
        self.terminal.tag_remove("search_highlight", 1.0, tk.END)
        
        # Re-add all search highlights
        search_text = self.search_entry.get().strip()
        start_pos = 1.0
        while True:
            pos = self.terminal.search(search_text, start_pos, tk.END, nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(search_text)}c"
            self.terminal.tag_add("search_highlight", pos, end_pos)
            start_pos = end_pos
        
        # Highlight current match with different color
        current_pos, current_end = self.search_results[self.current_search_index]
        self.terminal.tag_add("search_highlight", current_pos, current_end)
        
        # Scroll to current match
        self.terminal.see(current_pos)
        
        # Update count label to show current position
        count = len(self.search_results)
        current = self.current_search_index + 1
        self.search_count_label.config(text=f"{current}/{count} result{'s' if count != 1 else ''}")
    
    def clear_search(self):
        """Clear search and highlights"""
        if self.search_entry:
            self.search_entry.delete(0, tk.END)
        self.clear_search_highlights()
        self.search_results = []
        self.current_search_index = -1
        self.search_count_label.config(text="0 results")
    
    def clear_search_highlights(self):
        """Clear all search highlights"""
        self.terminal.tag_remove("search_highlight", 1.0, tk.END)
    
    def toggle_recording(self):
        """Toggle data recording on/off"""
        if ctr_data.recording:
            # Stop recording
            ctr_data.stop_recording()
            self.record_btn.config(text="Start Recording", bg=COLORS['btn_success'])
            
            # Show appropriate message based on auto-save setting
            if settings.get('auto_save', True):
                self.log_to_terminal("Data recording stopped - file saved automatically", "INFO")
            else:
                self.log_to_terminal("Data recording stopped - data stored in memory", "INFO")
        else:
            # Start recording
            if ctr_data.start_recording():
                self.record_btn.config(text="Stop Recording", bg=COLORS['btn_warning'])
                # Message is already logged in start_recording method
            else:
                messagebox.showerror("Recording Error", "Failed to start recording")
    
    def save_recorded_data(self):
        """Save recorded data to a file"""
        if not ctr_data.recorded_data:
            messagebox.showinfo("No Data", "No recorded data to save")
            return
        
        # Create data directory if it doesn't exist
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Set initial directory to data folder
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Recorded Data",
            initialdir=data_dir
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'w') as f:
                        json.dump(ctr_data.recorded_data, f, indent=2)
                else:
                    with open(filename, 'w', newline='') as f:
                        writer = csv.writer(f)
                        # Write standardized header
                        header = ['Timestamp', 'Throttle', 'Gear', 'RPM', 'Controller_Temp_C', 
                                 'Motor_Temp_C', 'Speed_kmh', 'Power_W', 'Voltage_V', 'Packet_Count', 'Latency_ms']
                        writer.writerow(header)
                        
                        # Write data rows
                        if ctr_data.recorded_data:
                            for data_point in ctr_data.recorded_data:
                                row = [data_point['timestamp'], data_point['throttle'], data_point['gear'], 
                                       data_point['rpm'], data_point['controller_temp'], data_point['motor_temp'],
                                       data_point['speed'], data_point['power'], data_point['voltage'], 
                                       data_point['packet_count'], data_point['latency']]
                                writer.writerow(row)
                
                self.log_to_terminal(f"Data saved to {filename}", "SUCCESS")
            except Exception as e:
                self.log_to_terminal(f"Failed to save data: {e}", "ERROR")
                messagebox.showerror("Save Error", f"Failed to save data: {e}")
    
    def update_performance_display(self):
        """Update performance monitoring display"""
        global fps_counter, last_fps_time, display_fps, memory_usage, cpu_usage
        
        # Update FPS counter
        fps_counter += 1
        current_time = time.time()
        if current_time - last_fps_time >= 1.0:
            display_fps = fps_counter
            fps_counter = 0
            last_fps_time = current_time
        
        # Update system metrics (with fallback if psutil not available)
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                cpu_usage = process.cpu_percent()
            except:
                memory_usage = 0
                cpu_usage = 0
        else:
            # Fallback values when psutil is not available
            memory_usage = 0
            cpu_usage = 0
        
        # Update labels
        self.fps_label.config(text=f"FPS: {display_fps}")
        self.latency_label.config(text=f"Latency: {ctr_data.avg_latency:.1f}ms")
        
        if PSUTIL_AVAILABLE:
            self.memory_label.config(text=f"Memory: {memory_usage:.1f}MB")
            self.cpu_label.config(text=f"CPU: {cpu_usage:.1f}%")
        else:
            self.memory_label.config(text="Memory: N/A")
            self.cpu_label.config(text="CPU: N/A")
        
        # Update packet statistics
        stats = ctr_data.get_performance_stats()
        packet_stats = packet_inspector.get_packet_statistics()
        
        # Log performance metrics periodically
        if fps_counter % 60 == 0:  # Every 60 frames
            perf_msg = f"Performance - FPS: {display_fps}, Packets: {stats['packet_count']}, Errors: {stats['packet_errors']}, Latency: {ctr_data.avg_latency:.1f}ms"
            if PSUTIL_AVAILABLE:
                perf_msg += f", Memory: {memory_usage:.1f}MB, CPU: {cpu_usage:.1f}%"
            self.log_to_terminal(perf_msg, "INFO")
    
    def open_data_folder(self):
        """Open the data folder in file explorer"""
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        try:
            # Open folder in file explorer
            if os.name == 'nt':  # Windows
                os.startfile(data_dir)
            elif os.name == 'posix':  # macOS and Linux
                import subprocess
                subprocess.run(['open', data_dir] if os.uname().sysname == 'Darwin' else ['xdg-open', data_dir])
            
            self.log_to_terminal(f"Opened data folder: {os.path.abspath(data_dir)}", "INFO")
        except Exception as e:
            self.log_to_terminal(f"Failed to open data folder: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to open data folder: {e}")
    
    def show_packet_inspector(self):
        """Show packet inspector window"""
        if not packet_inspector.current_packet:
            messagebox.showinfo("No Data", "No packets received yet")
            return
        
        # Create packet inspector window
        inspector_window = tk.Toplevel(self.root)
        inspector_window.title("Packet Inspector")
        inspector_window.geometry("800x600")
        inspector_window.configure(bg=COLORS['bg_dark'])
        
        # Create notebook for tabs
        notebook = ttk.Notebook(inspector_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Current packet tab
        current_frame = tk.Frame(notebook, bg=COLORS['bg_dark'])
        notebook.add(current_frame, text="Current Packet")
        
        # Packet details
        packet = packet_inspector.current_packet
        details_text = scrolledtext.ScrolledText(
            current_frame, bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
            font=FONTS['mono'], height=20
        )
        details_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Format packet details
        details = f"""Packet Analysis Report
{'='*50}

Timestamp: {packet['timestamp']}
Valid: {packet['valid']}
Index: {packet['index']}
Checksum Valid: {packet['checksum_valid']}
Checksum: {packet['checksum']} (Expected: {packet['expected_checksum']})
Reserved: {packet['reserved']}

Raw Data: {packet['raw_data']}

Parsed Data:
"""
        
        for key, value in packet['parsed_data'].items():
            if isinstance(value, dict):
                details += f"\n{key}:\n"
                for subkey, subvalue in value.items():
                    details += f"  {subkey}: {subvalue}\n"
            else:
                details += f"{key}: {value}\n"
        
        details_text.insert(tk.END, details)
        details_text.config(state='disabled')
        
        # Statistics tab
        stats_frame = tk.Frame(notebook, bg=COLORS['bg_dark'])
        notebook.add(stats_frame, text="Statistics")
        
        stats_text = scrolledtext.ScrolledText(
            stats_frame, bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
            font=FONTS['mono'], height=20
        )
        stats_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Format statistics
        stats = packet_inspector.get_packet_statistics()
        stats_details = f"""Packet Statistics
{'='*50}

Total Packets: {stats.get('total_packets', 0)}
Valid Packets: {stats.get('valid_packets', 0)}
Checksum Errors: {stats.get('checksum_errors', 0)}
Error Rate: {stats.get('error_rate', 0):.2%}

Index Distribution:
"""
        
        for index, count in stats.get('index_distribution', {}).items():
            stats_details += f"  Index {index}: {count} packets\n"
        
        stats_text.insert(tk.END, stats_details)
        stats_text.config(state='disabled')
        
        # Recent packets tab
        recent_frame = tk.Frame(notebook, bg=COLORS['bg_dark'])
        notebook.add(recent_frame, text="Recent Packets")
        
        recent_text = scrolledtext.ScrolledText(
            recent_frame, bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
            font=FONTS['mono'], height=20
        )
        recent_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Format recent packets
        recent_packets = packet_inspector.get_recent_packets(20)
        recent_details = "Recent Packets (Last 20)\n" + "="*50 + "\n\n"
        
        for i, packet in enumerate(reversed(recent_packets)):
            recent_details += f"Packet {len(recent_packets) - i}:\n"
            recent_details += f"  Time: {packet['timestamp']}\n"
            recent_details += f"  Index: {packet['index']}\n"
            recent_details += f"  Valid: {packet['valid']}\n"
            recent_details += f"  Raw: {packet['raw_data']}\n"
            if packet['valid']:
                recent_details += f"  Checksum: {packet['checksum_valid']}\n"
            recent_details += "\n"
        
        recent_text.insert(tk.END, recent_details)
        recent_text.config(state='disabled')
    
    def log_to_terminal(self, message, level="INFO"):
        """Add a message to the terminal with timestamp and level"""
        global terminal_paused
        
        # Don't log if terminal is paused (except for pause/resume messages)
        if terminal_paused and "Display paused" not in message and "Display resumed" not in message:
            return
        
        # Check filter settings
        if not self.should_show_message(level, message):
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        # Color coding based on level
        tag = "info"
        if level == "ERROR":
            tag = "error"
        elif level == "WARNING":
            tag = "warning"
        elif level == "DATA":
            tag = "data"
        elif level == "SUCCESS":
            tag = "success"
        
        # Store current search state - safely check if search_entry exists
        current_search_text = ""
        if hasattr(self, 'search_entry') and self.search_entry:
            try:
                current_search_text = self.search_entry.get().strip()
            except (tk.TclError, AttributeError):
                current_search_text = ""
        
        self.terminal.insert(tk.END, formatted_message, tag)
        
        # Auto-scroll to bottom
        self.terminal.see(tk.END)
        
        # Limit terminal size to prevent memory issues
        lines = self.terminal.get(1.0, tk.END).split('\n')
        if len(lines) > settings['terminal_max_lines']:
            self.terminal.delete(1.0, f"{len(lines) - settings['terminal_max_lines']//2}.0")
            # Re-apply search highlighting after content deletion
            if current_search_text and hasattr(self, 'search_active') and self.search_active:
                self.perform_search()
        
        # Apply search highlighting to new content if search is active
        if current_search_text and hasattr(self, 'search_active') and self.search_active:
            # Find and highlight any matches in the new content
            start_pos = f"{len(lines) - 1}.0"
            while True:
                pos = self.terminal.search(current_search_text, start_pos, tk.END, nocase=True)
                if not pos:
                    break
                end_pos = f"{pos}+{len(current_search_text)}c"
                self.terminal.tag_add("search_highlight", pos, end_pos)
                start_pos = end_pos
    
    def on_closing(self):
        """Handle window closing - disconnect and cleanup"""
        global is_connected, should_disconnect, client
        
        log_to_terminal("Application closing - disconnecting...", "INFO")
        
        # Set disconnect flag
        should_disconnect = True
        is_connected = False
        
        # Disconnect client if connected
        if client:
            try:
                def disconnect_client():
                    try:
                        # Check if client is still connected before trying to disconnect
                        if client and hasattr(client, 'is_connected') and client.is_connected:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(client.disconnect())
                            loop.close()
                            print("Client disconnected successfully")
                        else:
                            print("Client was already disconnected")
                    except Exception as e:
                        error_msg = str(e) if e else "Unknown error"
                        error_type = type(e).__name__
                        print(f"Error during disconnect: {error_type}: {error_msg}")
                
                disconnect_thread = threading.Thread(target=disconnect_client, daemon=True)
                disconnect_thread.start()
                
            except Exception as e:
                error_msg = str(e) if e else "Unknown error"
                error_type = type(e).__name__
                print(f"Error disconnecting: {error_type}: {error_msg}")
        
        # Destroy the window
        self.root.destroy()
    
    def update_display(self):
        """Update the display with current data"""
        global terminal_paused
        
        # Update time (always update, even when paused)
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        
        # Update performance monitoring
        self.update_performance_display()
        
        # If paused, only update time and schedule next update
        if terminal_paused:
            # Schedule next update
            self.root.after(16, self.update_display)  # Increased from 50ms to 16ms (~60 FPS)
            return
        
        # Check if data has changed to avoid unnecessary updates
        data_changed = ctr_data.has_changes()
        
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
            data_changed = True  # Force update when disconnecting
        
        # Only update displays if data changed or we need to update connection status
        if data_changed:
            # Update power gauge (max 5000W)
            self.power_gauge.set_value(abs(ctr_data.power), 5000)
            
            # Update speed display
            self.speed_display.config(text=f"{ctr_data.speed:.0f}")
            
            # Update voltage display
            self.voltage_display.config(text=f"{ctr_data.voltage:.1f}V")
            
            # Update battery bar
            self.update_battery_bar()
            
            # Update RPM gauge (max 8000 RPM)
            self.rpm_gauge.set_value(ctr_data.rpm, 8000)
            
            # Update throttle gauge (max 5000)
            self.throttle_gauge.set_value(ctr_data.throttle, 5000)
            
            # Update temperatures
            self.motor_temp_label.config(text=f"{ctr_data.motor_temp}°C")
            self.controller_temp_label.config(text=f"{ctr_data.controller_temp}°C")
            
            # Update gear
            self.gear_label.config(text=f"{ctr_data.gear}")
        
        # Update connection buttons (less frequently)
        if not hasattr(self, '_last_button_update') or time.time() - self._last_button_update > 0.5:
            self.update_connection_buttons()
            self._last_button_update = time.time()
        
        # Update info panel (always check)
        if terminal_paused:
            self.info_label.config(text="DISPLAY PAUSED - Click Resume to continue", fg=COLORS['warning'])
        else:
            has_recent_data = (time.time() - ctr_data.last_update) < 5.0
            actual_connected = is_connected or has_recent_data
            
            if actual_connected:
                time_since_update = time.time() - ctr_data.last_update
                if time_since_update < 5.0:
                    self.info_label.config(text=f"Connected - Last update: {time_since_update:.1f}s ago", fg=COLORS['text_secondary'])
                else:
                    self.info_label.config(text="Connected - No recent data", fg=COLORS['text_secondary'])
            else:
                self.info_label.config(text="Ready to connect...", fg=COLORS['text_secondary'])
        
        # Schedule next update at higher frequency
        self.root.after(16, self.update_display)  # Increased from 50ms to 16ms (~60 FPS)
    
    def update_battery_bar(self):
        """Update the battery level indicator"""
        self.battery_bar.delete("all")
        
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
        self.battery_bar.create_rectangle(x_start, 2, x_start + bar_width, 2 + bar_height, 
                                        outline=COLORS['text_secondary'], width=2)
        
        # Draw battery level
        fill_width = int(bar_width * level)
        if level > 0.5:
            color = COLORS['success']
        elif level > 0.2:
            color = COLORS['warning']
        else:
            color = COLORS['error']
        
        if fill_width > 0:
            self.battery_bar.create_rectangle(x_start + 2, 4, x_start + 2 + fill_width, bar_height, 
                                            fill=color, outline='')
    
    def show_settings(self):
        """Show settings panel"""
        # Create settings window
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x600")
        settings_window.configure(bg=COLORS['bg_dark'])
        
        # Create main frame
        main_frame = tk.Frame(settings_window, bg=COLORS['bg_dark'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        tk.Label(main_frame, text="Display Settings", 
                font=FONTS['title'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack(pady=(0, 20))
        
        # Create settings sections
        self.create_display_settings(main_frame)
        self.create_recording_settings(main_frame)
        self.create_terminal_settings(main_frame)
        self.create_debug_settings(main_frame)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg=COLORS['bg_dark'])
        button_frame.pack(fill='x', pady=20)
        
        ModernButton(button_frame, text="Save", 
                    bg=COLORS['success'], fg=COLORS['text_primary'],
                    command=lambda: self.save_settings(settings_window)).pack(side='left', padx=5)
        
        ModernButton(button_frame, text="Cancel", 
                    bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                    command=settings_window.destroy).pack(side='right', padx=5)
    
    def create_display_settings(self, parent):
        """Create display settings section"""
        frame = tk.LabelFrame(parent, text="Display", 
                             font=FONTS['subheading'], fg=COLORS['text_primary'],
                             bg=COLORS['bg_dark'], relief='flat', bd=1)
        frame.pack(fill='x', pady=10)
        
        # Display FPS
        fps_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        fps_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(fps_frame, text="Display FPS:", 
                font=FONTS['body'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack(side='left')
        
        self.fps_var = tk.StringVar(value=str(settings['display_fps']))
        fps_entry = tk.Entry(fps_frame, textvariable=self.fps_var, 
                           bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                           font=FONTS['body'], width=10)
        fps_entry.pack(side='right')
        
        # Gauge Animation FPS
        gauge_fps_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        gauge_fps_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(gauge_fps_frame, text="Gauge Animation FPS:", 
                font=FONTS['body'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack(side='left')
        
        self.gauge_fps_var = tk.StringVar(value=str(settings['gauge_animation_fps']))
        gauge_fps_entry = tk.Entry(gauge_fps_frame, textvariable=self.gauge_fps_var, 
                                 bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                                 font=FONTS['body'], width=10)
        gauge_fps_entry.pack(side='right')
        
        # Terminal max lines
        terminal_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        terminal_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(terminal_frame, text="Terminal Max Lines:", 
                font=FONTS['body'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack(side='left')
        
        self.terminal_lines_var = tk.StringVar(value=str(settings['terminal_max_lines']))
        terminal_entry = tk.Entry(terminal_frame, textvariable=self.terminal_lines_var, 
                                bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                                font=FONTS['body'], width=10)
        terminal_entry.pack(side='right')
    
    def create_recording_settings(self, parent):
        """Create recording settings section"""
        frame = tk.LabelFrame(parent, text="Recording", 
                             font=FONTS['subheading'], fg=COLORS['text_primary'],
                             bg=COLORS['bg_dark'], relief='flat', bd=1)
        frame.pack(fill='x', pady=10)
        
        # Auto record
        auto_record_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        auto_record_frame.pack(fill='x', padx=10, pady=5)
        
        self.auto_record_var = tk.BooleanVar(value=settings['auto_record'])
        auto_record_check = tk.Checkbutton(auto_record_frame, text="Auto-record on connection", 
                                          variable=self.auto_record_var,
                                          font=FONTS['body'], fg=COLORS['text_primary'],
                                          bg=COLORS['bg_dark'], selectcolor=COLORS['bg_medium'])
        auto_record_check.pack(side='left')
        
        # Auto save
        auto_save_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        auto_save_frame.pack(fill='x', padx=10, pady=5)
        
        self.auto_save_var = tk.BooleanVar(value=settings['auto_save'])
        auto_save_check = tk.Checkbutton(auto_save_frame, text="Auto-save CSV files", 
                                        variable=self.auto_save_var,
                                        font=FONTS['body'], fg=COLORS['text_primary'],
                                        bg=COLORS['bg_dark'], selectcolor=COLORS['bg_medium'])
        auto_save_check.pack(side='left')
        
        # Record interval
        interval_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        interval_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(interval_frame, text="Record Interval (s):", 
                font=FONTS['body'], fg=COLORS['text_primary'], 
                bg=COLORS['bg_dark']).pack(side='left')
        
        self.interval_var = tk.StringVar(value=str(settings['record_interval']))
        interval_entry = tk.Entry(interval_frame, textvariable=self.interval_var, 
                                bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                                font=FONTS['body'], width=10)
        interval_entry.pack(side='right')
    
    def create_terminal_settings(self, parent):
        """Create terminal settings section"""
        frame = tk.LabelFrame(parent, text="Terminal Filters", 
                             font=FONTS['subheading'], fg=COLORS['text_primary'],
                             bg=COLORS['bg_dark'], relief='flat', bd=1)
        frame.pack(fill='x', pady=10)
        
        # Filter control buttons
        filter_controls = tk.Frame(frame, bg=COLORS['bg_dark'])
        filter_controls.pack(fill='x', padx=10, pady=5)
        
        select_all_btn = ModernButton(filter_controls, text="Select All", 
                                     bg=COLORS['btn_primary'], fg=COLORS['text_primary'],
                                     command=self.select_all_filters)
        select_all_btn.pack(side='left', padx=2)
        
        clear_all_btn = ModernButton(filter_controls, text="Clear All", 
                                    bg=COLORS['btn_danger'], fg=COLORS['text_primary'],
                                    command=self.clear_all_filters)
        clear_all_btn.pack(side='left', padx=2)
        
        # Filter checkboxes in two columns
        checkbox_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        checkbox_frame.pack(fill='x', padx=10, pady=5)
        
        # Left column
        left_column = tk.Frame(checkbox_frame, bg=COLORS['bg_dark'])
        left_column.pack(side='left', fill='x', expand=True)
        
        # Right column
        right_column = tk.Frame(checkbox_frame, bg=COLORS['bg_dark'])
        right_column.pack(side='right', fill='x', expand=True)
        
        # Create checkboxes
        filters = [
            ('show_info', 'Info Messages', left_column),
            ('show_warning', 'Warnings', left_column),
            ('show_error', 'Errors', left_column),
            ('show_success', 'Success', left_column),
            ('show_data', 'Data Updates', right_column),
            ('show_connection', 'Connection', right_column),
            ('show_recording', 'Recording', right_column),
            ('show_performance', 'Performance', right_column)
        ]
        
        for filter_key, label, column in filters:
            checkbox = ModernCheckbox(
                column,
                text=label,
                variable=self.terminal_filters[filter_key],
                bg=COLORS['bg_dark'],
                command=self.update_terminal_filters
            )
            checkbox.pack(anchor='w', pady=1)
    
    def create_debug_settings(self, parent):
        """Create debug settings section"""
        frame = tk.LabelFrame(parent, text="Debug", 
                             font=FONTS['subheading'], fg=COLORS['text_primary'],
                             bg=COLORS['bg_dark'], relief='flat', bd=1)
        frame.pack(fill='x', pady=10)
        
        # Show performance
        perf_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        perf_frame.pack(fill='x', padx=10, pady=5)
        
        self.show_perf_var = tk.BooleanVar(value=settings['show_performance'])
        perf_check = tk.Checkbutton(perf_frame, text="Show performance metrics", 
                                   variable=self.show_perf_var,
                                   font=FONTS['body'], fg=COLORS['text_primary'],
                                   bg=COLORS['bg_dark'], selectcolor=COLORS['bg_medium'])
        perf_check.pack(side='left')
        
        # Show packet details
        packet_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        packet_frame.pack(fill='x', padx=10, pady=5)
        
        self.show_packet_var = tk.BooleanVar(value=settings['show_packet_details'])
        packet_check = tk.Checkbutton(packet_frame, text="Show detailed packet info", 
                                     variable=self.show_packet_var,
                                     font=FONTS['body'], fg=COLORS['text_primary'],
                                     bg=COLORS['bg_dark'], selectcolor=COLORS['bg_medium'])
        packet_check.pack(side='left')
    
    def save_settings(self, window):
        """Save settings and close window"""
        try:
            # Update settings from UI
            settings['display_fps'] = int(self.fps_var.get())
            settings['gauge_animation_fps'] = int(self.gauge_fps_var.get())
            settings['terminal_max_lines'] = int(self.terminal_lines_var.get())
            settings['auto_record'] = self.auto_record_var.get()
            settings['auto_save'] = self.auto_save_var.get()
            settings['record_interval'] = float(self.interval_var.get())
            settings['show_performance'] = self.show_perf_var.get()
            settings['show_packet_details'] = self.show_packet_var.get()
            
            # Save to file
            with open('eksr_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            
            # Update UI to reflect new settings
            self.update_recording_info()
            
            self.log_to_terminal("Settings saved successfully", "SUCCESS")
            window.destroy()
            
        except ValueError as e:
            messagebox.showerror("Invalid Value", f"Please enter valid numbers: {e}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings: {e}")
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('eksr_settings.json'):
                with open('eksr_settings.json', 'r') as f:
                    loaded_settings = json.load(f)
                    settings.update(loaded_settings)
                self.log_to_terminal("Settings loaded from file", "INFO")
                
                # Update UI to reflect loaded settings
                self.update_recording_info()
        except Exception as e:
            self.log_to_terminal(f"Failed to load settings: {e}", "WARNING")

def message_handler(data):
    """Process incoming BLE data packets"""
    global ctr_data, is_connected
    
    packet_start_time = time.time()
    
    # Analyze packet with inspector
    packet_info = packet_inspector.analyze_packet(data)
    
    if len(data) < 16:
        log_to_terminal(f"Invalid packet length: {len(data)}", "ERROR")
        ctr_data.packet_errors += 1
        return
    
    # Check for 0xAA header
    if data[0] != 0xAA:
        log_to_terminal(f"Invalid header: 0x{data[0]:02X}", "ERROR")
        ctr_data.packet_errors += 1
        return
    
    index = data[1]
    ctr_data.last_update = time.time()
    
    # Update connection status when we receive data
    if not is_connected:
        is_connected = True
        log_to_terminal("Connection status updated - data received", "INFO")
    
    # Log raw data to terminal - display exactly as received from FarDriver
    hex_data = ' '.join([f"{b:02X}" for b in data])
    log_to_terminal(f"DATA: {hex_data}", "DATA")
    
    # Log detailed packet info if enabled
    if settings['show_packet_details'] and packet_info['valid']:
        log_to_terminal(f"Packet {index}: {packet_info['parsed_data']}", "INFO")
    
    # Calculate latency
    latency = (time.time() - packet_start_time) * 1000  # Convert to ms
    ctr_data.update_performance_metrics(packet_start_time, latency)
    
    # Process different packet types
    if index == 0:  # Main data
        rpm = (data[4] << 8) | data[5]
        gear = ((data[2] >> 2) & 0x03)
        gear = max(1, min(3, gear))
        
        # Calculate power from current values
        iq = ((data[8] << 8) | data[9]) / 100.0
        id = ((data[10] << 8) | data[11]) / 100.0
        is_mag = (iq * iq + id * id) ** 0.5
        power = -is_mag * ctr_data.voltage  # Power in watts
        
        if iq < 0 or id < 0:
            power = -power
        
        # Calculate speed (simplified)
        wheel_circumference = 1.350  # meters
        rear_wheel_rpm = rpm / 4.0
        distance_per_min = rear_wheel_rpm * wheel_circumference
        speed = distance_per_min * 0.06  # km/h
        
        # Update values using the new method for change tracking
        ctr_data.update_value('rpm', rpm)
        ctr_data.update_value('gear', gear)
        ctr_data.update_value('power', power)
        ctr_data.update_value('speed', speed)
        
        log_to_terminal(
            f"Main Data - RPM: {rpm}, Gear: {gear}, "
            f"Power: {power:.0f}W, Speed: {speed:.1f}km/h", "INFO"
        )
        
    elif index == 1:  # Voltage
        voltage = ((data[2] << 8) | data[3]) / 10.0
        ctr_data.update_value('voltage', voltage)
        log_to_terminal(f"Voltage: {voltage:.1f}V", "INFO")
        
    elif index == 4:  # Controller temperature
        controller_temp = data[2]
        ctr_data.update_value('controller_temp', controller_temp)
        log_to_terminal(f"Controller Temp: {controller_temp}°C", "INFO")
        
    elif index == 13:  # Motor temperature and throttle
        motor_temp = data[2]
        throttle = (data[4] << 8) | data[5]
        ctr_data.update_value('motor_temp', motor_temp)
        ctr_data.update_value('throttle', throttle)
        log_to_terminal(
            f"Motor Temp: {motor_temp}°C, Throttle: {throttle}", "INFO"
        )
    
    else:
        log_to_terminal(f"Unknown packet type: {index}", "WARNING")

async def scan_and_connect():
    """Scan for and connect to FarDriver emulator"""
    global client, is_connected, should_disconnect
    
    log_to_terminal("Scanning for FarDriver emulator...", "INFO")
    
    while not should_disconnect:
        try:
            # Ensure client is properly cleaned up before scanning
            if client:
                try:
                    if client.is_connected:
                        await client.disconnect()
                except Exception as e:
                    log_to_terminal(f"Error cleaning up previous client: {e}", "WARNING")
                finally:
                    client = None
                    is_connected = False
            
            # Scan for devices
            devices = await BleakScanner.discover()
            
            for device in devices:
                if device.name and "FarDriver" in device.name:
                    log_to_terminal(
                        f"Found FarDriver device: {device.name} ({device.address})", "INFO"
                    )
                    
                    # Try to connect
                    try:
                        client = BleakClient(device.address)
                        
                        # Set connection timeout
                        await asyncio.wait_for(client.connect(), timeout=10.0)
                        
                        if client.is_connected:
                            is_connected = True
                            log_to_terminal("Connected to FarDriver emulator!", "SUCCESS")
                            
                            # Wait a moment for services to be fully discovered
                            await asyncio.sleep(0.5)
                            
                            # Subscribe to notifications with retry
                            try:
                                await client.start_notify(FARDRIVER_CHARACTERISTIC_UUID, 
                                                        lambda sender, data: message_handler(data))
                                log_to_terminal("Successfully subscribed to FarDriver characteristic", "SUCCESS")
                            except Exception as e:
                                log_to_terminal(f"Failed to subscribe to characteristic: {e}", "ERROR")
                                # Try to disconnect and let it retry
                                try:
                                    await client.disconnect()
                                except:
                                    pass
                                is_connected = False
                                continue
                            
                            # Keep connection alive
                            while is_connected and not should_disconnect:
                                try:
                                    # Send keep-alive packet every 2 seconds
                                    keep_alive = bytes([0xAA, 0x13, 0xEC, 0x07, 0x01, 0xF1, 0xA2, 0x5D])
                                    await client.write_gatt_char(FARDRIVER_CHARACTERISTIC_UUID, keep_alive)
                                    await asyncio.sleep(2)
                                except Exception as e:
                                    log_to_terminal(f"Connection lost: {e}", "ERROR")
                                    is_connected = False
                                    break
                            
                            # If we should disconnect, break out of device loop
                            if should_disconnect:
                                break
                        else:
                            log_to_terminal("Connection failed - client not connected", "ERROR")
                            is_connected = False
                        
                    except asyncio.TimeoutError:
                        log_to_terminal("Connection timeout - device may be busy", "ERROR")
                        is_connected = False
                    except Exception as e:
                        log_to_terminal(f"Failed to connect: {e}", "ERROR")
                        is_connected = False
                        
        except Exception as e:
            log_to_terminal(f"Scan error: {e}", "ERROR")
        
        # If we should disconnect, don't retry
        if should_disconnect:
            log_to_terminal("Disconnect requested - stopping scan", "INFO")
            break
            
        log_to_terminal("Retrying in 5 seconds...", "INFO")
        await asyncio.sleep(5)
    
    # If we get here and should_disconnect is True, we're done
    if should_disconnect:
        log_to_terminal("BLE scanning stopped due to disconnect request", "INFO")
    else:
        log_to_terminal("BLE scanning stopped", "INFO")

def run_ble_loop():
    """Run the BLE event loop in a separate thread"""
    global should_disconnect, client, is_connected
    
    while True:
        # Reset disconnect flag for new connection attempts
        should_disconnect = False
        
        # Clean up any existing client
        if client:
            try:
                if client.is_connected:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(client.disconnect())
                    loop.close()
            except Exception as e:
                log_to_terminal(f"Error cleaning up client: {e}", "WARNING")
            finally:
                client = None
                is_connected = False
        
        # Start new connection attempt
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scan_and_connect())
        loop.close()
        
        # Small delay before next attempt to let BLE stack reset
        time.sleep(1)
        
        # If we disconnected manually, wait for user to request reconnection
        if should_disconnect:
            log_to_terminal("Waiting for manual reconnection...", "INFO")
            # Wait until should_disconnect becomes False (user clicked Connect)
            while should_disconnect:
                time.sleep(0.5)

def main():
    """Main application entry point"""
    # Start BLE scanning in background thread
    ble_thread = threading.Thread(target=run_ble_loop, daemon=True)
    ble_thread.start()
    
    # Create and run GUI
    root = tk.Tk()
    app = EKSRDisplayEnhanced(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application terminated by user")
    finally:
        # Cleanup is handled in on_closing method
        pass

if __name__ == "__main__":
    main() 
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
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import asyncio
import threading
import time
import math
from datetime import datetime
from bleak import BleakScanner, BleakClient
import struct
import json
import os

# BLE Service and Characteristic UUIDs
FARDRIVER_SERVICE_UUID = "ffe0"
FARDRIVER_CHARACTERISTIC_UUID = "ffec"

# Color scheme and styling
COLORS = {
    'bg_dark': '#1a1a1a',
    'bg_medium': '#2d2d2d',
    'bg_light': '#404040',
    'accent_blue': '#00b4d8',
    'accent_green': '#00d4aa',
    'accent_red': '#ff6b6b',
    'accent_orange': '#ffa726',
    'accent_purple': '#ab47bc',
    'text_primary': '#ffffff',
    'text_secondary': '#b0b0b0',
    'text_muted': '#808080',
    'success': '#4caf50',
    'warning': '#ff9800',
    'error': '#f44336',
    'info': '#2196f3'
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
    
    def update_value(self, key, value):
        """Update a value and track if it changed"""
        if key not in self._last_values or self._last_values[key] != value:
            self._last_values[key] = value
            self._has_changes = True
            setattr(self, key, value)
            self.last_update = time.time()
    
    def has_changes(self):
        """Check if any values have changed since last check"""
        has_changes = self._has_changes
        self._has_changes = False
        return has_changes

# Global variables
ctr_data = ControllerData()
is_connected = False
client = None
terminal_widget = None
terminal_paused = False
should_disconnect = False

def log_to_terminal(message, level="INFO"):
    """Global function to log messages to terminal"""
    global terminal_paused
    if terminal_widget and hasattr(terminal_widget, 'log_to_terminal') and not terminal_paused:
        terminal_widget.log_to_terminal(message, level)

class ModernButton(tk.Button):
    """Custom modern button with hover effects"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(
            relief='flat',
            borderwidth=0,
            font=FONTS['body'],
            cursor='hand2'
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
    
    def on_enter(self, event):
        self.config(bg=COLORS['bg_light'])
    
    def on_leave(self, event):
        self.config(bg=COLORS['bg_medium'])

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
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.create_main_content()
        
        # Create status bar
        self.create_status_bar()
        
        # Set global terminal reference
        global terminal_widget
        terminal_widget = self
        
        # Initialize search variables
        self.search_active = False
        self.search_frame = None
        self.search_entry = None
        self.search_results = []
        self.current_search_index = -1
        
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
        style.configure('Modern.TButton', background=COLORS['accent_blue'], foreground=COLORS['text_primary'])
    
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
                                      bg=COLORS['accent_blue'], fg=COLORS['text_primary'],
                                      command=self.toggle_connection)
        self.connect_btn.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        self.disconnect_btn = ModernButton(connection_frame, text="Disconnect", 
                                         bg=COLORS['error'], fg=COLORS['text_primary'],
                                         command=self.disconnect_device)
        self.disconnect_btn.pack(side='right', fill='x', expand=True, padx=(5, 0))
        
        # Update button states
        self.update_connection_buttons()
        
        # Terminal section
        self.create_terminal_section()
    

    
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
                                    command=self.toggle_pause, width=3)
        self.pause_btn.pack(side='left', padx=2)
        
        self.clear_btn = ModernButton(controls_frame, text="🗑", 
                                    bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                                    command=self.clear_terminal, width=3)
        self.clear_btn.pack(side='left', padx=2)
        
        # Search functionality
        self.search_btn = ModernButton(controls_frame, text="🔍", 
                                     bg=COLORS['accent_blue'], fg=COLORS['text_primary'],
                                     command=self.toggle_search, width=3)
        self.search_btn.pack(side='left', padx=2)
        
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
        self.terminal.tag_configure("search_highlight", background=COLORS['accent_orange'], foreground=COLORS['text_primary'])
    
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
        """Update the state of connection buttons based on current status"""
        has_recent_data = (time.time() - ctr_data.last_update) < 5.0
        actual_connected = is_connected or has_recent_data
        
        if actual_connected:
            self.connect_btn.config(text="Reconnect", bg=COLORS['warning'], state='normal')
            self.disconnect_btn.config(state='normal')
        else:
            self.connect_btn.config(text="Connect", bg=COLORS['accent_blue'], state='normal')
            self.disconnect_btn.config(state='disabled')
    
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
        self.connect_btn.config(text="Connect", bg=COLORS['accent_blue'], state='normal')
        self.disconnect_btn.config(state='disabled')
        
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
        self.search_btn.config(text="🔍", bg=COLORS['accent_blue'])
        
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
    
    def log_to_terminal(self, message, level="INFO"):
        """Add a message to the terminal with timestamp and level"""
        global terminal_paused
        
        # Don't log if terminal is paused (except for pause/resume messages)
        if terminal_paused and "Display paused" not in message and "Display resumed" not in message:
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
        
        # Store current search state
        current_search_text = self.search_entry.get().strip() if self.search_entry else ""
        
        self.terminal.insert(tk.END, formatted_message, tag)
        
        # Auto-scroll to bottom
        self.terminal.see(tk.END)
        
        # Limit terminal size to prevent memory issues
        lines = self.terminal.get(1.0, tk.END).split('\n')
        if len(lines) > 1000:
            self.terminal.delete(1.0, f"{len(lines) - 500}.0")
            # Re-apply search highlighting after content deletion
            if current_search_text and self.search_active:
                self.perform_search()
        
        # Apply search highlighting to new content if search is active
        if current_search_text and self.search_active:
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
        
        # Update connection buttons
        self.update_connection_buttons()
        
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

def message_handler(data):
    """Process incoming BLE data packets"""
    global ctr_data, is_connected
    
    if len(data) < 16:
        log_to_terminal(f"Invalid packet length: {len(data)}", "ERROR")
        return
    
    # Check for 0xAA header
    if data[0] != 0xAA:
        log_to_terminal(f"Invalid header: 0x{data[0]:02X}", "ERROR")
        return
    
    index = data[1]
    ctr_data.last_update = time.time()
    
    # Update connection status when we receive data
    if not is_connected:
        is_connected = True
        log_to_terminal("Connection status updated - data received", "INFO")
    
    # Log raw data to terminal
    hex_data = ' '.join([f"{b:02X}" for b in data])
    log_to_terminal(f"Raw: {hex_data}", "DATA")
    
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
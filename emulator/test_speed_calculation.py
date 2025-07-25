#!/usr/bin/env python3
"""
Speed Calculation Test Script

This script tests the speed calculation logic to identify why speed
might be showing as 0 on the display.
"""

def test_speed_calculation():
    """Test the speed calculation logic"""
    print("Testing Speed Calculation Logic")
    print("=" * 40)
    
    # Constants from firmware
    wheel_circumference = 1.350  # meters
    gear_ratio = 4.0  # motor to wheel ratio
    
    # Test cases with different speeds
    test_speeds = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
    
    for speed_kmh in test_speeds:
        print(f"\nSpeed: {speed_kmh} km/h")
        
        # Emulator RPM calculation (reverse of firmware calculation)
        # Speed km/h -> m/min -> wheel RPM -> motor RPM
        wheel_rpm = (speed_kmh * 1000.0) / (60.0 * wheel_circumference)
        motor_rpm = wheel_rpm * gear_ratio
        
        print(f"  Wheel RPM: {wheel_rpm:.1f}")
        print(f"  Motor RPM: {motor_rpm:.1f}")
        
        # Firmware speed calculation (reverse)
        # Motor RPM -> wheel RPM -> m/min -> km/h
        wheel_rpm_back = motor_rpm / gear_ratio
        distance_per_min = wheel_rpm_back * wheel_circumference
        speed_back = distance_per_min * 0.06
        
        print(f"  Calculated back: {speed_back:.2f} km/h")
        
        # Check if values match
        if abs(speed_kmh - speed_back) < 0.01:
            print("  ✓ Calculation is correct")
        else:
            print(f"  ✗ Calculation error: {abs(speed_kmh - speed_back):.2f}")

def test_rpm_ranges():
    """Test RPM ranges and their corresponding speeds"""
    print("\n\nTesting RPM Ranges")
    print("=" * 40)
    
    wheel_circumference = 1.350
    gear_ratio = 4.0
    
    # Test RPM ranges
    rpm_tests = [100, 500, 1000, 1500, 2000, 2500, 3000]
    
    for motor_rpm in rpm_tests:
        # Calculate speed from RPM
        wheel_rpm = motor_rpm / gear_ratio
        distance_per_min = wheel_rpm * wheel_circumference
        speed_kmh = distance_per_min * 0.06
        
        print(f"Motor RPM: {motor_rpm} -> Speed: {speed_kmh:.2f} km/h")

def test_emulator_simulation():
    """Test the emulator's ebike simulation values"""
    print("\n\nTesting Emulator Simulation Values")
    print("=" * 40)
    
    # Simulate the emulator's ebike state
    current_speed = 25.0  # km/h (target speed during acceleration)
    throttle_position = 0.8  # 80% throttle
    
    print(f"Current Speed: {current_speed} km/h")
    print(f"Throttle Position: {throttle_position * 100:.1f}%")
    
    # Calculate RPM as emulator does
    wheel_rpm = (current_speed * 1000.0) / (60.0 * 1.35)
    motor_rpm = wheel_rpm * 4.0
    
    print(f"Calculated Motor RPM: {motor_rpm:.1f}")
    
    # Add some variation as emulator does
    import math
    timestamp = 1000  # ms
    variation = 50 * math.sin(timestamp / 500.0)
    motor_rpm_with_variation = motor_rpm + variation
    
    print(f"Motor RPM with variation: {motor_rpm_with_variation:.1f}")
    
    # Ensure RPM stays in range
    if motor_rpm_with_variation < 100:
        motor_rpm_with_variation = 100
    elif motor_rpm_with_variation > 3000:
        motor_rpm_with_variation = 3000
    
    print(f"Final Motor RPM: {motor_rpm_with_variation:.1f}")
    
    # Calculate speed back from final RPM
    wheel_rpm_back = motor_rpm_with_variation / 4.0
    distance_per_min = wheel_rpm_back * 1.35
    speed_back = distance_per_min * 0.06
    
    print(f"Speed calculated back: {speed_back:.2f} km/h")

def test_packet_generation():
    """Test packet generation with specific values"""
    print("\n\nTesting Packet Generation")
    print("=" * 40)
    
    # Simulate packet generation for speed = 25 km/h
    speed_kmh = 25.0
    
    # Calculate RPM
    wheel_rpm = (speed_kmh * 1000.0) / (60.0 * 1.35)
    motor_rpm = wheel_rpm * 4.0
    
    # Add variation
    import math
    timestamp = 1000
    variation = 50 * math.sin(timestamp / 500.0)
    motor_rpm += variation
    
    # Clamp to range
    motor_rpm = max(100, min(3000, motor_rpm))
    
    print(f"Speed: {speed_kmh} km/h")
    print(f"Motor RPM: {motor_rpm:.1f}")
    
    # Generate packet bytes
    rpm_high = int(motor_rpm) >> 8
    rpm_low = int(motor_rpm) & 0xFF
    
    print(f"RPM bytes: 0x{rpm_high:02X} 0x{rpm_low:02X}")
    
    # Simulate firmware parsing
    rpm_parsed = (rpm_high << 8) | rpm_low
    print(f"Parsed RPM: {rpm_parsed}")
    
    # Calculate speed as firmware does
    wheel_rpm_back = rpm_parsed / 4.0
    distance_per_min = wheel_rpm_back * 1.35
    speed_back = distance_per_min * 0.06
    
    print(f"Firmware calculated speed: {speed_back:.2f} km/h")

def main():
    """Run all tests"""
    test_speed_calculation()
    test_rpm_ranges()
    test_emulator_simulation()
    test_packet_generation()
    
    print("\n" + "=" * 40)
    print("All tests completed!")

if __name__ == "__main__":
    main() 
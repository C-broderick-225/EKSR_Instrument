#!/usr/bin/env python3
"""
Emulator RPM Calculation Test

This script tests the emulator's RPM calculation logic to ensure
it generates reasonable values for different speeds.
"""

def test_emulator_rpm_calculation():
    """Test the emulator's RPM calculation logic"""
    print("Testing Emulator RPM Calculation")
    print("=" * 40)
    
    # Test different speeds
    speeds = [0.0, 1.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
    
    for speed_kmh in speeds:
        # Emulator RPM calculation
        wheel_rpm = (speed_kmh * 1000.0) / (60.0 * 1.35)
        motor_rpm = wheel_rpm * 4.0
        
        # Add variation (simulate emulator)
        import math
        timestamp = 1000
        variation = 50 * math.sin(timestamp / 500.0)
        motor_rpm_with_variation = motor_rpm + variation
        
        # Clamp to range (emulator logic)
        if motor_rpm_with_variation < 50:
            motor_rpm_with_variation = 50
        elif motor_rpm_with_variation > 3000:
            motor_rpm_with_variation = 3000
        
        # Convert to bytes (emulator packet generation)
        rpm_high = int(motor_rpm_with_variation) >> 8
        rpm_low = int(motor_rpm_with_variation) & 0xFF
        
        # Simulate firmware parsing
        rpm_parsed = (rpm_high << 8) | rpm_low
        
        # Calculate speed back (firmware calculation)
        wheel_rpm_back = rpm_parsed / 4.0
        distance_per_min = wheel_rpm_back * 1.35
        speed_back = distance_per_min * 0.06
        
        print(f"Speed: {speed_kmh:5.1f} km/h -> RPM: {motor_rpm_with_variation:6.1f} -> Speed back: {speed_back:5.2f} km/h")
        print(f"  Bytes: 0x{rpm_high:02X} 0x{rpm_low:02X}, Parsed: {rpm_parsed}")

def test_speed_thresholds():
    """Test speed thresholds and their corresponding RPM values"""
    print("\n\nTesting Speed Thresholds")
    print("=" * 40)
    
    # Test very low speeds
    low_speeds = [0.0, 0.1, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0]
    
    for speed_kmh in low_speeds:
        wheel_rpm = (speed_kmh * 1000.0) / (60.0 * 1.35)
        motor_rpm = wheel_rpm * 4.0
        
        # Clamp to range
        if motor_rpm < 50:
            motor_rpm = 50
        
        # Calculate speed back
        wheel_rpm_back = motor_rpm / 4.0
        distance_per_min = wheel_rpm_back * 1.35
        speed_back = distance_per_min * 0.06
        
        print(f"Speed: {speed_kmh:4.1f} km/h -> RPM: {motor_rpm:6.1f} -> Speed back: {speed_back:5.2f} km/h")

def test_connection_scenario():
    """Test the connection scenario - starting from 0 speed"""
    print("\n\nTesting Connection Scenario")
    print("=" * 40)
    
    # Simulate the connection scenario
    print("Initial state: Speed = 0 km/h")
    
    # After 1 second of acceleration (2 km/h per second)
    speed_1s = 2.0
    wheel_rpm = (speed_1s * 1000.0) / (60.0 * 1.35)
    motor_rpm = wheel_rpm * 4.0
    if motor_rpm < 50:
        motor_rpm = 50
    
    wheel_rpm_back = motor_rpm / 4.0
    distance_per_min = wheel_rpm_back * 1.35
    speed_back = distance_per_min * 0.06
    
    print(f"After 1s: Speed = {speed_1s} km/h -> RPM = {motor_rpm:.1f} -> Speed back = {speed_back:.2f} km/h")
    
    # After 5 seconds of acceleration
    speed_5s = 10.0
    wheel_rpm = (speed_5s * 1000.0) / (60.0 * 1.35)
    motor_rpm = wheel_rpm * 4.0
    
    wheel_rpm_back = motor_rpm / 4.0
    distance_per_min = wheel_rpm_back * 1.35
    speed_back = distance_per_min * 0.06
    
    print(f"After 5s: Speed = {speed_5s} km/h -> RPM = {motor_rpm:.1f} -> Speed back = {speed_back:.2f} km/h")
    
    # After 12.5 seconds (target speed)
    speed_target = 25.0
    wheel_rpm = (speed_target * 1000.0) / (60.0 * 1.35)
    motor_rpm = wheel_rpm * 4.0
    
    wheel_rpm_back = motor_rpm / 4.0
    distance_per_min = wheel_rpm_back * 1.35
    speed_back = distance_per_min * 0.06
    
    print(f"Target: Speed = {speed_target} km/h -> RPM = {motor_rpm:.1f} -> Speed back = {speed_back:.2f} km/h")

def main():
    """Run all tests"""
    test_emulator_rpm_calculation()
    test_speed_thresholds()
    test_connection_scenario()
    
    print("\n" + "=" * 40)
    print("All tests completed!")

if __name__ == "__main__":
    main() 
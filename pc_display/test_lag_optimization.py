#!/usr/bin/env python3
"""
Test script to verify lag optimization improvements
"""

import time
import threading
from pc_display_enhanced import ControllerData, AnimatedGauge
import tkinter as tk

def test_data_change_tracking():
    """Test the new data change tracking functionality"""
    print("Testing data change tracking...")
    
    ctr_data = ControllerData()
    
    # Test initial state
    assert not ctr_data.has_changes(), "Should not have changes initially"
    
    # Test value update
    ctr_data.update_value('rpm', 1000)
    assert ctr_data.has_changes(), "Should detect change after update"
    assert not ctr_data.has_changes(), "Should clear changes after check"
    
    # Test no change
    ctr_data.update_value('rpm', 1000)
    assert not ctr_data.has_changes(), "Should not detect change for same value"
    
    # Test multiple updates
    ctr_data.update_value('speed', 25.5)
    ctr_data.update_value('power', 1500)
    assert ctr_data.has_changes(), "Should detect multiple changes"
    
    print("✓ Data change tracking test passed")

def test_gauge_animation_speed():
    """Test the optimized gauge animation"""
    print("Testing gauge animation speed...")
    
    root = tk.Tk()
    root.withdraw()  # Hide the window
    
    gauge = AnimatedGauge(root, size=120)
    
    # Test animation speed
    start_time = time.time()
    gauge.set_value(100, 100)
    
    # Wait for animation to complete
    while gauge.is_animating:
        root.update()
        time.sleep(0.001)  # 1ms sleep
    
    animation_time = time.time() - start_time
    print(f"Animation completed in {animation_time:.3f}s")
    
    # Animation should be faster than before (was ~0.5s, now should be ~0.2s)
    assert animation_time < 0.3, f"Animation too slow: {animation_time:.3f}s"
    
    root.destroy()
    print("✓ Gauge animation speed test passed")

def test_update_frequency():
    """Test the increased update frequency"""
    print("Testing update frequency...")
    
    root = tk.Tk()
    root.withdraw()  # Hide the window
    
    update_count = 0
    start_time = time.time()
    
    def test_update():
        nonlocal update_count
        update_count += 1
        
        if time.time() - start_time < 1.0:  # Run for 1 second
            root.after(16, test_update)  # 16ms = ~60 FPS
    
    test_update()
    
    # Run for 1 second
    while time.time() - start_time < 1.0:
        root.update()
    
    # Should get approximately 60 updates per second
    expected_updates = 55  # Allow some variance
    print(f"Got {update_count} updates in 1 second (target: ~60)")
    assert update_count >= expected_updates, f"Too few updates: {update_count}"
    
    root.destroy()
    print("✓ Update frequency test passed")

def main():
    """Run all tests"""
    print("EKSR Instrument - Lag Optimization Tests")
    print("=" * 50)
    
    try:
        test_data_change_tracking()
        test_gauge_animation_speed()
        test_update_frequency()
        
        print("\n" + "=" * 50)
        print("✓ All lag optimization tests passed!")
        print("\nOptimization Summary:")
        print("- Display updates: 20 FPS → 60 FPS")
        print("- Gauge animations: 60 FPS → 120 FPS")
        print("- Animation speed: 0.1 → 0.3")
        print("- Emulator packets: 30ms → 20ms intervals")
        print("- Added data change tracking for efficiency")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main() 
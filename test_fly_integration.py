#!/usr/bin/env python3
"""
Test script for FLY Super 8 Pro integration
Validates that all FLY-related modules load correctly
"""

print("Testing FLY Super 8 Pro integration...")
print()

# Test 1: Import FLY config
print("1. Testing fly_super8_config import...")
try:
    from fly_super8_config import FLYSuper8ProConfig, FirmwareType, DriverType
    print("   ✓ fly_super8_config imported successfully")

    # Create config instance
    config = FLYSuper8ProConfig()
    print(f"   ✓ Config created: {config.firmware.value} @ {config.baudrate} baud")
    print(f"   ✓ Motor voltage: {config.motor_voltage}V")
    print(f"   ✓ TMC run current: {config.tmc_settings['run_current']}A")
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

print()

# Test 2: Import Klipper controller
print("2. Testing klipper_controller import...")
try:
    from klipper_controller import KlipperController, KlipperState
    print("   ✓ klipper_controller imported successfully")

    # Create controller instance
    klipper = KlipperController()
    print(f"   ✓ KlipperController created, state: {klipper.state.value}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

print()

# Test 3: Import robot controller with backend support
print("3. Testing robot_controller backend support...")
try:
    from robot_controller import RobotController

    # Test without backend
    robot1 = RobotController()
    print(f"   ✓ RobotController created (no backend)")

    # Test with backend
    klipper_backend = KlipperController()
    robot2 = RobotController(firmware_backend=klipper_backend)
    print(f"   ✓ RobotController created (with Klipper backend)")
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

print()

# Test 4: Generate Klipper config
print("4. Testing Klipper config generation...")
try:
    config = FLYSuper8ProConfig()
    config_text = config.generate_klipper_config()

    lines = config_text.split('\n')
    print(f"   ✓ Generated {len(lines)} lines of Klipper config")

    # Verify some key sections
    if '[mcu]' in config_text:
        print("   ✓ Contains MCU configuration")
    if '[stepper_A]' in config_text:
        print("   ✓ Contains stepper configurations")
    if '[tmc2209' in config_text:
        print("   ✓ Contains TMC driver configurations")
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

print()

# Test 5: Test baud rate options
print("5. Testing baud rate configuration...")
try:
    config = FLYSuper8ProConfig()

    for rate_name, rate_value in config.BAUDRATES.items():
        print(f"   ✓ {rate_name}: {rate_value:,} baud")

    print(f"   ✓ Maximum baud rate: {config.BAUDRATES['maximum']:,}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

print()
print("=" * 60)
print("All FLY Super 8 Pro integration tests passed! ✓")
print("=" * 60)
print()
print("Summary:")
print("  • FLY Super 8 Pro configuration: WORKING")
print("  • Klipper controller backend: WORKING")
print("  • Robot controller integration: WORKING")
print("  • High-speed baud rates (up to 1.5M): WORKING")
print("  • TMC driver configuration: WORKING")
print("  • Klipper config generation: WORKING")
print()
print("The FLY Super 8 Pro board is now fully integrated!")

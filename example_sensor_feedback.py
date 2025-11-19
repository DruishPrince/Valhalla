#!/usr/bin/env python3
"""
Examples for Using ADXL345 Sensor Feedback

Demonstrates how to use accelerometer sensors for joint angle sensing
and closed-loop position control
"""

import time
from sensor_manager import SensorManager, setup_thor_sensors
from sensor_integration import SensorIntegration, create_integrated_system
from robot_controller import RobotController, MovementType
from kinematics import Point3D


def example_1_basic_sensor_reading():
    """Example 1: Basic sensor reading"""
    print("=" * 60)
    print("Example 1: Basic ADXL345 Sensor Reading")
    print("=" * 60 + "\n")

    print("Setting up sensors (simulated)...")
    manager = setup_thor_sensors(simulate=True)

    print("\nCalibrating sensors...")
    manager.calibrate_all()

    print("\nReading sensors for 5 seconds...")
    print("(In real use, mount sensors on joints before calibrating)\n")

    for i in range(50):
        feedback = manager.read_all()

        print("\rJoint Angles: ", end='')
        for joint_id, fb in sorted(feedback.items()):
            print(f"{joint_id}={fb.measured_angle:6.1f}° ", end='')

        time.sleep(0.1)

    manager.disconnect_all()
    print("\n\n✓ Example 1 complete\n")


def example_2_commanded_vs_measured():
    """Example 2: Compare commanded vs measured angles"""
    print("=" * 60)
    print("Example 2: Commanded vs Measured Angles")
    print("=" * 60 + "\n")

    manager = setup_thor_sensors(simulate=True)
    manager.calibrate_all()

    # Define commanded position
    commanded = {
        'A': 45.0,
        'B': 30.0,
        'D': -20.0
    }

    print(f"Commanded position: {commanded}\n")

    # Simulate movement (in real use, robot would move)
    print("Comparing to measured position:\n")

    comparison = manager.compare_to_commanded(commanded)

    print("Joint | Commanded | Measured | Error")
    print("-" * 45)

    for joint_id in sorted(comparison.keys()):
        comp = comparison[joint_id]
        print(f"{joint_id:5} | {comp['commanded']:9.1f}° | {comp['measured']:8.1f}° | {comp['error']:6.1f}°")

    manager.disconnect_all()
    print("\n✓ Example 2 complete\n")


def example_3_integrated_feedback():
    """Example 3: Integrated sensor feedback with robot"""
    print("=" * 60)
    print("Example 3: Integrated Sensor Feedback")
    print("=" * 60 + "\n")

    # Create integrated system
    system = create_integrated_system(simulate_sensors=True)

    print("Calibrating sensors...")
    system.calibrate_sensors_at_home()

    # Define target
    target = {'A': 45.0, 'B': 30.0, 'D': -20.0}
    print(f"\nTarget position: {target}")

    # Update commanded position
    system.update_commanded_position(target)

    # Monitor position
    print("\nMonitoring position:")
    system.monitor_position(duration=3.0)

    # Get status report
    status = system.get_status_report()

    print("\n\nStatus Report:")
    print(f"  Max Position Error: {status['max_error']:.2f}°")

    if status['measured_position']:
        print(f"\n  End Effector (measured):")
        print(f"    X: {status['measured_position']['x']:.1f} mm")
        print(f"    Y: {status['measured_position']['y']:.1f} mm")
        print(f"    Z: {status['measured_position']['z']:.1f} mm")

    system.sensors.disconnect_all()
    print("\n✓ Example 3 complete\n")


def example_4_closed_loop_control():
    """Example 4: Closed-loop position control"""
    print("=" * 60)
    print("Example 4: Closed-Loop Position Control")
    print("=" * 60 + "\n")

    system = create_integrated_system(simulate_sensors=True)

    # Calibrate
    system.calibrate_sensors_at_home()

    # Configure closed-loop control
    system.closed_loop_config.enabled = True
    system.closed_loop_config.max_error = 2.0  # degrees
    system.closed_loop_config.correction_gain = 0.3

    print("Starting closed-loop control...")
    system.start_closed_loop()

    # Set target
    target = {'A': 30.0, 'B': 20.0, 'D': -15.0}
    system.update_commanded_position(target)

    print(f"Target: {target}")
    print("\nMonitoring position with active corrections...\n")

    # Monitor for a while
    time.sleep(5)

    # Get final status
    status = system.get_status_report()

    print("\n\nFinal Status:")
    print("Joint | Error")
    print("-" * 20)

    for joint_id, error in status['position_errors'].items():
        status_symbol = "✓" if abs(error) < 2.0 else "✗"
        print(f"{joint_id:5} | {error:6.1f}° {status_symbol}")

    # Stop closed-loop
    system.stop_closed_loop()
    system.sensors.disconnect_all()

    print("\n✓ Example 4 complete\n")


def example_5_sensor_calibration():
    """Example 5: Sensor calibration procedure"""
    print("=" * 60)
    print("Example 5: Sensor Calibration Procedure")
    print("=" * 60 + "\n")

    manager = SensorManager()

    # Add sensors
    print("Adding sensors...")
    manager.add_sensor('A', 'Base', i2c_address=0x53, simulate=True)
    manager.add_sensor('B', 'Shoulder', i2c_address=0x1D, simulate=True)

    print("\nCalibration Procedure:")
    print("1. Position each joint at 0° (zero position)")
    print("2. Keep joint stationary")
    print("3. Calibrate sensor\n")

    for joint_id in ['A', 'B']:
        config = manager.configs[joint_id]
        print(f"Calibrating {config.joint_name} (Joint {joint_id})...")

        # In real use, user would position joint here
        time.sleep(0.5)

        # Calibrate
        manager.calibrate_joint(joint_id, num_samples=100)

        # Verify
        feedback = manager.read_joint(joint_id)
        print(f"  Verified: {feedback.measured_angle:.2f}° at zero\n")

    # Save calibration
    manager.save_config('example_sensor_config.json')
    print("✓ Calibration saved to example_sensor_config.json")

    manager.disconnect_all()
    print("\n✓ Example 5 complete\n")


def example_6_real_hardware():
    """Example 6: Using real hardware (template)"""
    print("=" * 60)
    print("Example 6: Real Hardware Template")
    print("=" * 60 + "\n")

    print("This example shows the structure for using real hardware\n")

    print("Hardware Setup:")
    print("  1. Connect ADXL345 sensors to I2C bus")
    print("  2. Mount one sensor per joint")
    print("  3. Ensure each sensor has unique address")
    print("     - SDO pin LOW = 0x53")
    print("     - SDO pin HIGH = 0x1D")
    print("  4. Connect robot via USB/serial\n")

    proceed = input("Do you have hardware connected? (y/n): ").strip().lower()

    if proceed != 'y':
        print("\nSkipping hardware test")
        print("Run with real hardware using:")
        print("  manager = setup_thor_sensors(simulate=False)")
        print("\n✓ Example 6 complete\n")
        return

    # Real hardware code
    print("\nConnecting to real hardware...")

    try:
        # Create manager with real hardware
        manager = SensorManager()

        # Add sensors (adjust addresses for your setup)
        print("Adding sensors...")
        manager.add_sensor('A', 'Base', i2c_address=0x53, i2c_bus=1, simulate=False)

        # Calibrate
        print("\nPosition Base joint at 0° and press Enter")
        input()

        manager.calibrate_joint('A')

        # Test reading
        print("\nReading sensor...")
        feedback = manager.read_joint('A')
        print(f"  Angle: {feedback.measured_angle:.1f}°")
        print(f"  Accel: ({feedback.acceleration.x:.3f}, "
              f"{feedback.acceleration.y:.3f}, "
              f"{feedback.acceleration.z:.3f}) g")

        manager.disconnect_all()
        print("\n✓ Hardware test complete")

    except Exception as e:
        print(f"\n✗ Hardware error: {e}")
        print("Make sure smbus2 is installed: pip install smbus2")

    print("\n✓ Example 6 complete\n")


def main():
    """Main menu"""
    print("\n" + "=" * 60)
    print("ADXL345 Sensor Feedback Examples")
    print("=" * 60 + "\n")

    examples = {
        '1': ('Basic Sensor Reading', example_1_basic_sensor_reading),
        '2': ('Commanded vs Measured', example_2_commanded_vs_measured),
        '3': ('Integrated Feedback', example_3_integrated_feedback),
        '4': ('Closed-Loop Control', example_4_closed_loop_control),
        '5': ('Sensor Calibration', example_5_sensor_calibration),
        '6': ('Real Hardware Template', example_6_real_hardware),
    }

    print("Available Examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  a. Run all (non-hardware)")
    print("  q. Quit\n")

    while True:
        choice = input("Select example (1-6, a, q): ").strip().lower()

        if choice == 'q':
            print("\nGoodbye!\n")
            break

        if choice == 'a':
            # Run non-hardware examples
            for i in range(1, 6):
                examples[str(i)][1]()
                input("Press Enter to continue...")
            break

        if choice in examples:
            name, func = examples[choice]
            try:
                func()
            except KeyboardInterrupt:
                print("\n\nExample interrupted\n")
            except Exception as e:
                print(f"\n✗ Error: {e}\n")

            input("Press Enter to return to menu...")
            print("\n")
        else:
            print("Invalid choice\n")


if __name__ == '__main__':
    main()

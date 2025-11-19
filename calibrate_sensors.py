#!/usr/bin/env python3
"""
ADXL345 Sensor Calibration Utility

Interactive tool for calibrating accelerometer sensors on robot joints
"""

import sys
import time
from sensor_manager import SensorManager, setup_thor_sensors
from robot_controller import RobotController


class SensorCalibrationTool:
    """Interactive sensor calibration tool"""

    def __init__(self, simulate: bool = False):
        """
        Initialize calibration tool

        Args:
            simulate: Use simulated sensors if True
        """
        self.simulate = simulate
        self.manager: Optional[SensorManager] = None
        self.robot: Optional[RobotController] = None

    def print_header(self, text: str):
        """Print formatted header"""
        print("\n" + "=" * 60)
        print(f"  {text}")
        print("=" * 60)

    def setup_sensors(self):
        """Setup and connect to sensors"""
        self.print_header("Sensor Setup")

        print("\nHow many sensors do you want to configure?")
        print("  1-3: Basic setup (Base, Shoulder, Elbow)")
        print("  4-6: Full setup (add Wrist joints)")

        num_sensors = input("\nNumber of sensors (1-6): ").strip()

        try:
            num_sensors = int(num_sensors)
            if num_sensors < 1 or num_sensors > 6:
                raise ValueError
        except ValueError:
            print("Invalid number, using 3 sensors")
            num_sensors = 3

        # Joint configurations
        joints = [
            ('A', 'Base', 0x53),
            ('B', 'Shoulder', 0x1D),
            ('D', 'Elbow', 0x53),
            ('X', 'Wrist Pitch', 0x1D),
            ('Y', 'Wrist Roll', 0x53),
            ('Z', 'End Effector', 0x1D),
        ]

        self.manager = SensorManager()

        print("\nSetting up sensors...")
        for i in range(num_sensors):
            joint_id, joint_name, address = joints[i]

            print(f"\nConfiguring sensor {i+1}/{num_sensors}:")
            print(f"  Joint: {joint_name} ({joint_id})")
            print(f"  Default I2C address: 0x{address:02X}")

            # Allow custom address
            custom = input(f"  Use custom address? (y/n): ").strip().lower()

            if custom == 'y':
                addr_input = input(f"  Enter address (hex, e.g., 53): ").strip()
                try:
                    address = int(addr_input, 16)
                except ValueError:
                    print(f"  Invalid address, using default 0x{address:02X}")

            # Add sensor
            success = self.manager.add_sensor(
                joint_id, joint_name,
                i2c_address=address,
                simulate=self.simulate
            )

            if not success:
                print(f"  ✗ Failed to add sensor for {joint_name}")

        print(f"\n✓ {len(self.manager.sensors)} sensors configured")

    def calibrate_individual(self, joint_id: str):
        """Calibrate individual sensor"""
        config = self.manager.configs[joint_id]

        print(f"\n{'=' * 60}")
        print(f"Calibrating: {config.joint_name} (Joint {joint_id})")
        print(f"{'=' * 60}")

        print("\nInstructions:")
        print("  1. Move the joint to its 0° (zero) position")
        print("  2. Keep the joint completely still")
        print("  3. Press Enter when ready")

        input("\nPress Enter to start calibration...")

        # Perform calibration
        self.manager.calibrate_joint(joint_id, num_samples=200)

        # Verify calibration
        print("\nVerifying calibration...")
        time.sleep(0.5)

        feedback = self.manager.read_joint(joint_id)
        if feedback:
            print(f"  Measured angle at zero: {feedback.measured_angle:.2f}°")
            print(f"  Orientation: Roll={feedback.orientation.roll:.1f}° "
                  f"Pitch={feedback.orientation.pitch:.1f}°")

            if abs(feedback.measured_angle) > 2.0:
                print("  ⚠ Warning: Large offset detected. Consider recalibrating.")
            else:
                print("  ✓ Calibration looks good!")

    def calibrate_all_interactive(self):
        """Calibrate all sensors interactively"""
        self.print_header("Interactive Calibration")

        if not self.manager or not self.manager.sensors:
            print("No sensors configured")
            return

        print(f"\nCalibrating {len(self.manager.sensors)} sensors...")
        print("\nYou will be prompted to position each joint at 0°")

        for joint_id in sorted(self.manager.sensors.keys()):
            self.calibrate_individual(joint_id)
            time.sleep(1)

        print("\n✓ All sensors calibrated!")

    def calibrate_with_robot(self):
        """Calibrate using robot homing"""
        self.print_header("Calibration with Robot")

        print("\nThis will use the robot's homing function to calibrate sensors")
        print("Make sure robot is connected and powered on")

        proceed = input("\nProceed? (y/n): ").strip().lower()
        if proceed != 'y':
            return

        # Connect to robot
        port = input("Enter serial port (e.g., /dev/ttyUSB0): ").strip()

        self.robot = RobotController()
        if not self.robot.connect(port, 115200):
            print("✗ Failed to connect to robot")
            return

        print("✓ Connected to robot")

        # Home robot
        print("\nHoming robot...")
        self.robot.send_homing_command()

        print("Waiting for homing to complete (10 seconds)...")
        time.sleep(10)

        # Calibrate all sensors
        print("\nCalibrating sensors at home position...")
        self.manager.calibrate_all(num_samples=200)

        print("\n✓ Calibration complete!")

        # Disconnect
        self.robot.disconnect()

    def test_sensors(self):
        """Test sensor readings"""
        self.print_header("Sensor Testing")

        if not self.manager or not self.manager.sensors:
            print("No sensors configured")
            return

        print("\nReading sensors... (Press Ctrl+C to stop)\n")

        try:
            while True:
                feedback = self.manager.read_all()

                # Clear line and print readings
                print("\r" + " " * 80, end='')
                reading_str = ""

                for joint_id in sorted(feedback.keys()):
                    fb = feedback[joint_id]
                    reading_str += f"{joint_id}={fb.measured_angle:6.1f}° "

                print(f"\r{reading_str}", end='', flush=True)

                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n\nTesting stopped")

    def save_calibration(self):
        """Save calibration to file"""
        self.print_header("Save Calibration")

        if not self.manager:
            print("No sensors configured")
            return

        filename = input("\nEnter filename (default: sensor_config.json): ").strip()
        if not filename:
            filename = "sensor_config.json"

        self.manager.save_config(filename)
        print(f"\n✓ Calibration saved to {filename}")

    def run(self):
        """Run calibration tool"""
        self.print_header("ADXL345 Sensor Calibration Tool")

        print("\nThis tool helps you:")
        print("  • Configure ADXL345 sensors for each joint")
        print("  • Calibrate sensors at zero positions")
        print("  • Verify sensor readings")
        print("  • Save calibration data")

        input("\nPress Enter to begin...")

        try:
            # Setup sensors
            self.setup_sensors()

            # Main menu
            while True:
                print("\n" + "=" * 60)
                print("Main Menu")
                print("=" * 60)
                print("  1. Calibrate all sensors (interactive)")
                print("  2. Calibrate with robot homing")
                print("  3. Calibrate individual sensor")
                print("  4. Test sensors")
                print("  5. Save calibration")
                print("  6. Exit")

                choice = input("\nSelect option (1-6): ").strip()

                if choice == '1':
                    self.calibrate_all_interactive()
                elif choice == '2':
                    self.calibrate_with_robot()
                elif choice == '3':
                    joint_id = input("Enter joint ID (A, B, D, etc.): ").strip().upper()
                    if joint_id in self.manager.sensors:
                        self.calibrate_individual(joint_id)
                    else:
                        print(f"✗ No sensor for joint {joint_id}")
                elif choice == '4':
                    self.test_sensors()
                elif choice == '5':
                    self.save_calibration()
                elif choice == '6':
                    break
                else:
                    print("Invalid option")

            # Cleanup
            if self.manager:
                self.manager.disconnect_all()

            print("\n✓ Calibration tool closed\n")

        except KeyboardInterrupt:
            print("\n\nCalibration interrupted by user")
            if self.manager:
                self.manager.disconnect_all()


def main():
    """Main entry point"""
    print("\nADXL345 Sensor Calibration Tool")
    print("================================\n")

    # Check if hardware available
    try:
        import smbus2
        simulate = False
        print("I2C hardware detected")
    except ImportError:
        print("I2C library not available")
        simulate_input = input("Use simulator? (y/n): ").strip().lower()
        simulate = (simulate_input == 'y')

        if not simulate:
            print("\nInstall smbus2: pip install smbus2")
            return

    # Run calibration tool
    tool = SensorCalibrationTool(simulate=simulate)
    tool.run()


if __name__ == '__main__':
    main()

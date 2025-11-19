#!/usr/bin/env python3
"""
FLY Super ♾️ Pro Board Integration Example

Demonstrates complete setup for Mellow FLY Super ♾️ Pro board with
ADXL345 sensors using Raspberry Pi Zero 2W or Pico gateway.

The FLY board doesn't have exposed I2C pins, so we use an external
gateway (Pi Zero 2W or Pico) to read sensors and transmit data.

Hardware Setup:
1. Mellow FLY Super ♾️ Pro board connected via USB (/dev/ttyUSB0)
2. Raspberry Pi Zero 2W or Pico with ADXL345 sensors (/dev/ttyUSB1)
3. ADXL345 sensors on each moving joint

Software Architecture:
- Main computer runs this script
- Robot controller communicates with FLY board
- Sensor gateway client receives data from Pi/Pico
- Sensor integration provides closed-loop control
"""

import time
import sys
from typing import Dict, Optional

from robot_controller import RobotController, MovementType
from sensor_gateway_client import SensorGatewayClient, GatewayConfig
from sensor_integration import SensorIntegration
from kinematics import ThorKinematics
from config_manager import (
    get_config,
    set_current_board,
    get_board_config,
    get_sensor_gateway_config
)


class FLYBoardSystem:
    """
    Complete system for FLY Super ♾️ Pro board with sensor gateway

    Manages:
    - Robot control via FLY board
    - Sensor data via gateway (Pi Zero 2W or Pico)
    - Integrated kinematics and closed-loop control
    """

    def __init__(self):
        """Initialize FLY board system"""
        self.robot: Optional[RobotController] = None
        self.sensor_gateway: Optional[SensorGatewayClient] = None
        self.integration: Optional[SensorIntegration] = None
        self.kinematics = ThorKinematics()

        # Status
        self.robot_connected = False
        self.sensors_connected = False

    def setup_from_config(self) -> bool:
        """
        Setup system from configuration

        Returns:
            True if setup successful
        """
        print("=" * 60)
        print("FLY Super ♾️ Pro Board Setup")
        print("=" * 60 + "\n")

        # Set current board to FLY
        set_current_board('fly_super_8_pro')

        # Get configurations
        board_config = get_board_config()
        gateway_config_dict = get_sensor_gateway_config()

        print(f"Board: {board_config['description']}")
        print(f"Requires sensor gateway: {board_config['requires_sensor_gateway']}\n")

        # Setup robot controller
        print("1. Setting up robot controller...")
        self.robot = RobotController()

        robot_port = board_config['serial_port']
        robot_baud = board_config['baudrate']

        if self.robot.connect(robot_port, robot_baud):
            self.robot_connected = True
            print(f"   ✓ Robot connected on {robot_port}")
        else:
            print(f"   ✗ Failed to connect robot on {robot_port}")
            return False

        # Setup sensor gateway
        if board_config['requires_sensor_gateway']:
            print("\n2. Setting up sensor gateway...")

            gateway_config = GatewayConfig(
                mode=gateway_config_dict['connection_mode'],
                serial_port=gateway_config_dict['serial_port'],
                serial_baudrate=gateway_config_dict['serial_baudrate'],
                network_host=gateway_config_dict['network_host'],
                network_port=gateway_config_dict['network_port'],
                network_protocol=gateway_config_dict['network_protocol'],
                timeout=gateway_config_dict['timeout']
            )

            self.sensor_gateway = SensorGatewayClient(gateway_config)

            if self.sensor_gateway.connect():
                self.sensors_connected = True
                print(f"   ✓ Sensor gateway connected")

                # Wait for initial data
                print("   Waiting for sensor data...")
                time.sleep(1)

                status = self.sensor_gateway.get_status()
                print(f"   ✓ Receiving data from {status['num_joints']} sensors")
            else:
                print(f"   ✗ Failed to connect sensor gateway")
                print("   Continuing without sensors...")

        # Create integration
        if self.sensors_connected:
            print("\n3. Creating sensor integration...")
            self.integration = SensorIntegration(
                self.robot,
                self.sensor_gateway,  # Acts like SensorManager
                self.kinematics
            )
            print("   ✓ Integration ready\n")
        else:
            print("\n3. Skipping sensor integration (no sensors)\n")

        return True

    def calibrate_sensors(self):
        """Calibrate sensors at home position"""
        if not self.sensors_connected:
            print("No sensors connected")
            return

        print("=" * 60)
        print("Sensor Calibration")
        print("=" * 60 + "\n")

        print("Moving robot to home position...")

        if self.robot_connected:
            self.robot.send_homing_command()
            time.sleep(5)  # Wait for homing
            print("✓ Robot at home position\n")
        else:
            print("Position robot at home manually\n")

        print("Calibrating sensors...")
        print("(Ensure robot is stationary)\n")

        time.sleep(2)

        self.sensor_gateway.calibrate_all()

        print("✓ Calibration complete\n")

    def test_basic_movement(self):
        """Test basic movement with sensor feedback"""
        print("=" * 60)
        print("Basic Movement Test")
        print("=" * 60 + "\n")

        if not self.robot_connected:
            print("Robot not connected")
            return

        # Define test position
        test_angles = {'A': 30.0, 'B': 20.0, 'D': -15.0}

        print(f"Moving to test position: {test_angles}\n")

        # Send movement command
        self.robot.move_all_joints(test_angles, MovementType.G1_LINEAR, feedrate=500)

        # Monitor with sensor feedback
        if self.sensors_connected:
            print("Monitoring position with sensors...\n")
            print("Joint | Commanded | Measured | Error")
            print("-" * 45)

            self.integration.update_commanded_position(test_angles)

            for i in range(50):
                self.integration.update_measured_position()
                errors = self.integration.calculate_errors()

                if errors:
                    for joint_id in sorted(test_angles.keys()):
                        if joint_id in errors:
                            commanded = test_angles[joint_id]
                            measured = self.integration.measured_angles.get(joint_id, 0.0)
                            error = errors[joint_id]

                            status = "✓" if abs(error) < 5.0 else "✗"
                            print(f"\r{joint_id:5} | {commanded:9.1f}° | {measured:8.1f}° | {error:6.1f}° {status}", end='')

                time.sleep(0.1)

            print("\n\n✓ Movement complete\n")
        else:
            print("Moving without sensor feedback...")
            time.sleep(3)
            print("✓ Movement complete (no feedback)\n")

    def test_closed_loop_control(self):
        """Test closed-loop position control"""
        print("=" * 60)
        print("Closed-Loop Control Test")
        print("=" * 60 + "\n")

        if not self.sensors_connected:
            print("Sensors required for closed-loop control")
            return

        # Configure closed-loop
        self.integration.closed_loop_config.enabled = True
        self.integration.closed_loop_config.max_error = 3.0
        self.integration.closed_loop_config.correction_gain = 0.4
        self.integration.closed_loop_config.update_rate = 10.0

        print("Starting closed-loop control...")
        print(f"  Max error: {self.integration.closed_loop_config.max_error}°")
        print(f"  Correction gain: {self.integration.closed_loop_config.correction_gain}")
        print(f"  Update rate: {self.integration.closed_loop_config.update_rate} Hz\n")

        self.integration.start_closed_loop()

        # Set target
        target = {'A': 45.0, 'B': 30.0, 'D': -20.0}
        print(f"Target position: {target}\n")

        self.integration.update_commanded_position(target)
        self.robot.move_all_joints(target, MovementType.G1_LINEAR, feedrate=500)

        # Monitor
        print("Monitoring position with active corrections...\n")

        for i in range(100):
            status = self.integration.get_status_report()

            # Display errors
            errors_str = " ".join([
                f"{jid}={err:+5.1f}°"
                for jid, err in sorted(status['position_errors'].items())
            ])

            freshness = "✓" if self.sensor_gateway.is_data_fresh() else "✗"
            print(f"\r{freshness} Errors: {errors_str}", end='', flush=True)

            time.sleep(0.1)

        # Get final status
        print("\n\nFinal Status:")
        status = self.integration.get_status_report()

        print("\nJoint | Error | Status")
        print("-" * 30)

        for joint_id, error in sorted(status['position_errors'].items()):
            status_icon = "✓" if abs(error) < 3.0 else "✗"
            print(f"{joint_id:5} | {error:+6.1f}° | {status_icon}")

        # Stop closed-loop
        self.integration.stop_closed_loop()
        print("\n✓ Closed-loop test complete\n")

    def get_system_status(self) -> Dict:
        """
        Get comprehensive system status

        Returns:
            Status dictionary
        """
        status = {
            'robot_connected': self.robot_connected,
            'sensors_connected': self.sensors_connected,
            'robot_status': None,
            'sensor_status': None,
            'integration_status': None
        }

        if self.robot_connected:
            status['robot_status'] = {
                'port': self.robot.port,
                'connected': self.robot.is_connected()
            }

        if self.sensors_connected:
            status['sensor_status'] = self.sensor_gateway.get_status()

        if self.integration:
            status['integration_status'] = self.integration.get_status_report()

        return status

    def shutdown(self):
        """Shutdown system gracefully"""
        print("\nShutting down system...")

        if self.integration:
            if self.integration.closed_loop_running:
                self.integration.stop_closed_loop()

        if self.sensor_gateway:
            self.sensor_gateway.disconnect()
            print("  ✓ Sensor gateway disconnected")

        if self.robot:
            self.robot.disconnect()
            print("  ✓ Robot disconnected")

        print("\n✓ Shutdown complete\n")


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("FLY Super ♾️ Pro Board Integration")
    print("=" * 60 + "\n")

    print("This example demonstrates complete integration of:")
    print("  • Mellow FLY Super ♾️ Pro board")
    print("  • Raspberry Pi Zero 2W/Pico sensor gateway")
    print("  • ADXL345 accelerometer sensors")
    print("  • Closed-loop position control\n")

    proceed = input("Continue with setup? (y/n): ").strip().lower()

    if proceed != 'y':
        print("Setup cancelled")
        return

    # Create system
    system = FLYBoardSystem()

    try:
        # Setup
        if not system.setup_from_config():
            print("Setup failed")
            return

        # Main menu
        while True:
            print("\n" + "=" * 60)
            print("Main Menu")
            print("=" * 60)
            print("  1. Calibrate sensors")
            print("  2. Test basic movement")
            print("  3. Test closed-loop control")
            print("  4. Show system status")
            print("  5. Exit")

            choice = input("\nSelect option (1-5): ").strip()

            if choice == '1':
                system.calibrate_sensors()
            elif choice == '2':
                system.test_basic_movement()
            elif choice == '3':
                system.test_closed_loop_control()
            elif choice == '4':
                status = system.get_system_status()
                print("\n=== System Status ===")
                print(f"Robot connected: {status['robot_connected']}")
                print(f"Sensors connected: {status['sensors_connected']}")

                if status['sensor_status']:
                    print(f"Active sensors: {', '.join(status['sensor_status']['joints'])}")
                    print(f"Data freshness: {status['sensor_status']['time_since_update']:.3f}s")

            elif choice == '5':
                break
            else:
                print("Invalid option")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    finally:
        system.shutdown()


if __name__ == '__main__':
    main()

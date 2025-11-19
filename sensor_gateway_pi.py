#!/usr/bin/env python3
"""
Sensor Gateway for Raspberry Pi Zero 2W

Reads ADXL345 sensors via I2C and transmits data via serial/network
to the main control system. Use this when your main controller board
(e.g., FLY Super ♾️ Pro) doesn't have exposed I2C.

Hardware Setup:
- Raspberry Pi Zero 2W with I2C enabled
- ADXL345 sensors connected to I2C bus
- USB serial or network connection to main computer
"""

import sys
import time
import json
import serial
import argparse
from typing import Dict, List, Optional
from dataclasses import asdict

from sensor_manager import SensorManager, JointFeedback


class SensorGateway:
    """
    Gateway for reading sensors and transmitting data

    Supports:
    - Serial communication (USB)
    - Network communication (TCP/UDP)
    """

    def __init__(self, sensor_manager: SensorManager):
        """
        Initialize sensor gateway

        Args:
            sensor_manager: Configured SensorManager instance
        """
        self.sensors = sensor_manager
        self.running = False

        # Communication interfaces
        self.serial_port: Optional[serial.Serial] = None
        self.network_socket = None

    def setup_serial(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200) -> bool:
        """
        Setup serial communication

        Args:
            port: Serial port device
            baudrate: Communication speed

        Returns:
            True if successful
        """
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=1)
            print(f"✓ Serial port opened: {port} @ {baudrate} baud")
            return True
        except Exception as e:
            print(f"✗ Failed to open serial port: {e}")
            return False

    def setup_network(self, host: str = '0.0.0.0', port: int = 5555, protocol: str = 'tcp'):
        """
        Setup network communication

        Args:
            host: Host address to bind
            port: Port number
            protocol: 'tcp' or 'udp'

        Returns:
            True if successful
        """
        import socket

        try:
            if protocol == 'tcp':
                self.network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.network_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.network_socket.bind((host, port))
                self.network_socket.listen(1)
                print(f"✓ TCP server listening on {host}:{port}")
            elif protocol == 'udp':
                self.network_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.network_socket.bind((host, port))
                print(f"✓ UDP server listening on {host}:{port}")
            else:
                print(f"✗ Unknown protocol: {protocol}")
                return False

            return True

        except Exception as e:
            print(f"✗ Failed to setup network: {e}")
            return False

    def send_data(self, data: Dict):
        """
        Send sensor data via available interface

        Args:
            data: Dictionary of sensor data
        """
        # Format as JSON
        message = json.dumps(data) + '\n'

        # Send via serial
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(message.encode('utf-8'))
            except Exception as e:
                print(f"Serial send error: {e}")

        # Send via network
        if self.network_socket:
            try:
                # For UDP, would need client address
                # For TCP, would need to handle connections
                pass
            except Exception as e:
                print(f"Network send error: {e}")

    def read_sensors_once(self) -> Dict:
        """
        Read all sensors once and format data

        Returns:
            Dictionary with sensor readings
        """
        feedback = self.sensors.read_all()

        data = {
            'timestamp': time.time(),
            'joints': {}
        }

        for joint_id, fb in feedback.items():
            data['joints'][joint_id] = {
                'angle': fb.measured_angle,
                'accel_x': fb.acceleration.x,
                'accel_y': fb.acceleration.y,
                'accel_z': fb.acceleration.z,
                'roll': fb.orientation.roll,
                'pitch': fb.orientation.pitch
            }

        return data

    def run_continuous(self, rate: float = 10.0):
        """
        Continuously read and transmit sensor data

        Args:
            rate: Update rate in Hz
        """
        interval = 1.0 / rate
        self.running = True

        print(f"\nSensor Gateway Running @ {rate} Hz")
        print("Press Ctrl+C to stop\n")

        try:
            while self.running:
                start = time.time()

                # Read sensors
                data = self.read_sensors_once()

                # Send data
                self.send_data(data)

                # Print status
                joint_str = " ".join([
                    f"{jid}={data['joints'][jid]['angle']:6.1f}°"
                    for jid in sorted(data['joints'].keys())
                ])
                print(f"\r{joint_str}", end='', flush=True)

                # Maintain rate
                elapsed = time.time() - start
                if elapsed < interval:
                    time.sleep(interval - elapsed)

        except KeyboardInterrupt:
            print("\n\nGateway stopped by user")
            self.running = False

    def handle_commands(self):
        """Handle incoming commands from serial/network"""
        if self.serial_port and self.serial_port.in_waiting:
            try:
                line = self.serial_port.readline().decode('utf-8').strip()
                if line:
                    self.process_command(line)
            except Exception as e:
                print(f"Command error: {e}")

    def process_command(self, command: str):
        """
        Process incoming command

        Commands:
        - CALIBRATE <joint_id>: Calibrate specific joint
        - CALIBRATE_ALL: Calibrate all joints
        - GET <joint_id>: Get specific joint reading
        - STATUS: Get gateway status
        """
        parts = command.split()
        if not parts:
            return

        cmd = parts[0].upper()

        if cmd == 'CALIBRATE' and len(parts) > 1:
            joint_id = parts[1]
            if joint_id in self.sensors.sensors:
                self.sensors.calibrate_joint(joint_id)
                response = {'status': 'ok', 'message': f'Calibrated {joint_id}'}
            else:
                response = {'status': 'error', 'message': f'Unknown joint {joint_id}'}
            self.send_data(response)

        elif cmd == 'CALIBRATE_ALL':
            self.sensors.calibrate_all()
            response = {'status': 'ok', 'message': 'Calibrated all joints'}
            self.send_data(response)

        elif cmd == 'GET' and len(parts) > 1:
            joint_id = parts[1]
            fb = self.sensors.read_joint(joint_id)
            if fb:
                response = {
                    'status': 'ok',
                    'joint_id': joint_id,
                    'angle': fb.measured_angle
                }
            else:
                response = {'status': 'error', 'message': f'Unknown joint {joint_id}'}
            self.send_data(response)

        elif cmd == 'STATUS':
            response = {
                'status': 'ok',
                'num_sensors': len(self.sensors.sensors),
                'joints': list(self.sensors.sensors.keys())
            }
            self.send_data(response)

    def close(self):
        """Close all connections"""
        if self.serial_port:
            self.serial_port.close()
        if self.network_socket:
            self.network_socket.close()
        self.sensors.disconnect_all()


def main():
    """Main entry point for sensor gateway"""
    parser = argparse.ArgumentParser(description='ADXL345 Sensor Gateway for Raspberry Pi')
    parser.add_argument('--serial', type=str, default='/dev/ttyUSB0',
                       help='Serial port (default: /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=115200,
                       help='Serial baud rate (default: 115200)')
    parser.add_argument('--network', action='store_true',
                       help='Enable network mode')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Network host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5555,
                       help='Network port (default: 5555)')
    parser.add_argument('--protocol', type=str, default='tcp', choices=['tcp', 'udp'],
                       help='Network protocol (default: tcp)')
    parser.add_argument('--rate', type=float, default=10.0,
                       help='Update rate in Hz (default: 10)')
    parser.add_argument('--simulate', action='store_true',
                       help='Use simulated sensors')
    parser.add_argument('--config', type=str,
                       help='Sensor configuration file')

    args = parser.parse_args()

    print("=" * 60)
    print("ADXL345 Sensor Gateway for Raspberry Pi Zero 2W")
    print("=" * 60)
    print("\nHardware: Mellow FLY Super ♾️ Pro + Pi Zero 2W")
    print("Purpose: Read I2C sensors and transmit via serial/network")
    print()

    # Setup sensor manager
    from sensor_manager import setup_thor_sensors

    if args.config:
        manager = SensorManager(args.config)
        # Reconnect sensors from config
        for joint_id, config in manager.configs.items():
            manager.add_sensor(
                joint_id,
                config.joint_name,
                config.i2c_address,
                simulate=args.simulate
            )
    else:
        manager = setup_thor_sensors(simulate=args.simulate)

    # Create gateway
    gateway = SensorGateway(manager)

    # Setup communication
    if args.network:
        if not gateway.setup_network(args.host, args.port, args.protocol):
            print("Failed to setup network communication")
            return
    else:
        if not gateway.setup_serial(args.serial, args.baud):
            print("Failed to setup serial communication")
            return

    # Calibrate sensors
    print("\nCalibrating sensors...")
    print("Ensure robot is at home position!")
    time.sleep(2)
    manager.calibrate_all()

    # Run gateway
    try:
        gateway.run_continuous(rate=args.rate)
    finally:
        gateway.close()


if __name__ == '__main__':
    main()

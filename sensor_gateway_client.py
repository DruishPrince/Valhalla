#!/usr/bin/env python3
"""
Sensor Gateway Client

Receives sensor data from remote sensor gateway (Pi Zero 2W or Pico)
and integrates with the main robot control system.

This is needed when using boards like the Mellow FLY Super ♾️ Pro
that don't have exposed I2C pins for direct sensor connection.
"""

import sys
import time
import json
import serial
import socket
import threading
from typing import Dict, Optional, Callable
from dataclasses import dataclass

from sensor_manager import JointFeedback, SensorConfig, Orientation
from kinematics import Vector3D


@dataclass
class GatewayConfig:
    """Configuration for gateway connection"""
    mode: str = 'serial'  # 'serial' or 'network'

    # Serial settings
    serial_port: str = '/dev/ttyUSB1'
    serial_baudrate: int = 115200

    # Network settings
    network_host: str = '192.168.1.100'
    network_port: int = 5555
    network_protocol: str = 'tcp'

    # Data settings
    update_rate: float = 10.0  # Expected update rate (Hz)
    timeout: float = 1.0  # Connection timeout


class SensorGatewayClient:
    """
    Client for receiving sensor data from remote gateway

    Provides the same interface as SensorManager but receives data
    from a remote gateway instead of reading sensors directly.
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        """
        Initialize gateway client

        Args:
            config: Gateway configuration (creates default if None)
        """
        self.config = config if config else GatewayConfig()

        # Connection
        self.serial_port: Optional[serial.Serial] = None
        self.network_socket = None
        self.connected = False

        # Data
        self.latest_data: Dict = {}
        self.joint_feedback: Dict[str, JointFeedback] = {}
        self.last_update_time = 0

        # Background receiver
        self.receiver_thread: Optional[threading.Thread] = None
        self.receiver_running = False

        # Callbacks
        self.on_data_received: Optional[Callable[[Dict], None]] = None
        self.on_connection_lost: Optional[Callable[[], None]] = None

    def connect(self) -> bool:
        """
        Connect to sensor gateway

        Returns:
            True if connection successful
        """
        if self.config.mode == 'serial':
            return self._connect_serial()
        elif self.config.mode == 'network':
            return self._connect_network()
        else:
            print(f"Unknown connection mode: {self.config.mode}")
            return False

    def _connect_serial(self) -> bool:
        """Connect via serial"""
        try:
            self.serial_port = serial.Serial(
                self.config.serial_port,
                self.config.serial_baudrate,
                timeout=self.config.timeout
            )

            # Wait for connection
            time.sleep(0.5)

            # Test connection
            if self.serial_port.is_open:
                self.connected = True
                print(f"✓ Connected to gateway via serial: {self.config.serial_port}")

                # Start receiver
                self._start_receiver()
                return True
            else:
                print("✗ Failed to open serial port")
                return False

        except Exception as e:
            print(f"✗ Serial connection error: {e}")
            return False

    def _connect_network(self) -> bool:
        """Connect via network"""
        try:
            if self.config.network_protocol == 'tcp':
                self.network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.network_socket.settimeout(self.config.timeout)
                self.network_socket.connect((self.config.network_host, self.config.network_port))

                self.connected = True
                print(f"✓ Connected to gateway via TCP: {self.config.network_host}:{self.config.network_port}")

                # Start receiver
                self._start_receiver()
                return True

            elif self.config.network_protocol == 'udp':
                self.network_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.network_socket.settimeout(self.config.timeout)

                self.connected = True
                print(f"✓ Connected to gateway via UDP: {self.config.network_host}:{self.config.network_port}")

                # Start receiver
                self._start_receiver()
                return True

            else:
                print(f"Unknown network protocol: {self.config.network_protocol}")
                return False

        except Exception as e:
            print(f"✗ Network connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from gateway"""
        self._stop_receiver()

        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None

        if self.network_socket:
            self.network_socket.close()
            self.network_socket = None

        self.connected = False
        print("✓ Disconnected from gateway")

    def is_connected(self) -> bool:
        """Check if connected to gateway"""
        return self.connected

    def _start_receiver(self):
        """Start background receiver thread"""
        if self.receiver_running:
            return

        self.receiver_running = True
        self.receiver_thread = threading.Thread(target=self._receiver_worker, daemon=True)
        self.receiver_thread.start()

    def _stop_receiver(self):
        """Stop background receiver thread"""
        self.receiver_running = False

        if self.receiver_thread:
            self.receiver_thread.join(timeout=2.0)
            self.receiver_thread = None

    def _receiver_worker(self):
        """Background worker for receiving data"""
        buffer = ""

        while self.receiver_running:
            try:
                # Read data
                if self.config.mode == 'serial' and self.serial_port:
                    if self.serial_port.in_waiting:
                        data = self.serial_port.readline().decode('utf-8').strip()
                        if data:
                            self._process_received_data(data)
                    else:
                        time.sleep(0.01)

                elif self.config.mode == 'network' and self.network_socket:
                    if self.config.network_protocol == 'tcp':
                        data = self.network_socket.recv(4096).decode('utf-8')
                        buffer += data

                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            if line:
                                self._process_received_data(line)

                    elif self.config.network_protocol == 'udp':
                        data, addr = self.network_socket.recvfrom(4096)
                        self._process_received_data(data.decode('utf-8'))

            except socket.timeout:
                # Timeout is normal, just continue
                pass

            except Exception as e:
                print(f"Receiver error: {e}")
                self.connected = False

                if self.on_connection_lost:
                    self.on_connection_lost()

                break

    def _process_received_data(self, data_str: str):
        """
        Process received JSON data

        Args:
            data_str: JSON string from gateway
        """
        try:
            data = json.loads(data_str)

            # Update latest data
            self.latest_data = data
            self.last_update_time = time.time()

            # Convert to JointFeedback format
            if 'joints' in data:
                for joint_id, joint_data in data['joints'].items():
                    # Create JointFeedback object
                    feedback = JointFeedback(
                        joint_id=joint_id,
                        joint_name=joint_id,  # Gateway doesn't send name
                        measured_angle=joint_data.get('angle', 0.0),
                        acceleration=Vector3D(
                            x=joint_data.get('accel_x', 0.0),
                            y=joint_data.get('accel_y', 0.0),
                            z=joint_data.get('accel_z', 0.0)
                        ),
                        orientation=Orientation(
                            roll=joint_data.get('roll', 0.0),
                            pitch=joint_data.get('pitch', 0.0)
                        ),
                        timestamp=data.get('timestamp', time.time())
                    )

                    self.joint_feedback[joint_id] = feedback

            # Trigger callback
            if self.on_data_received:
                self.on_data_received(data)

        except json.JSONDecodeError as e:
            print(f"Invalid JSON received: {e}")
        except Exception as e:
            print(f"Error processing data: {e}")

    def send_command(self, command: str) -> bool:
        """
        Send command to gateway

        Args:
            command: Command string (e.g., 'CALIBRATE A', 'STATUS')

        Returns:
            True if sent successfully
        """
        if not self.connected:
            return False

        try:
            message = command + '\n'

            if self.config.mode == 'serial' and self.serial_port:
                self.serial_port.write(message.encode('utf-8'))
                return True

            elif self.config.mode == 'network' and self.network_socket:
                if self.config.network_protocol == 'tcp':
                    self.network_socket.send(message.encode('utf-8'))
                    return True
                elif self.config.network_protocol == 'udp':
                    self.network_socket.sendto(
                        message.encode('utf-8'),
                        (self.config.network_host, self.config.network_port)
                    )
                    return True

            return False

        except Exception as e:
            print(f"Error sending command: {e}")
            return False

    def read_all(self) -> Dict[str, JointFeedback]:
        """
        Read all joint feedback

        Returns:
            Dictionary of joint feedback (same interface as SensorManager)
        """
        return self.joint_feedback.copy()

    def read_joint(self, joint_id: str) -> Optional[JointFeedback]:
        """
        Read specific joint feedback

        Args:
            joint_id: Joint identifier

        Returns:
            JointFeedback or None if not available
        """
        return self.joint_feedback.get(joint_id)

    def get_joint_angles(self) -> Dict[str, float]:
        """
        Get current joint angles

        Returns:
            Dictionary of joint angles
        """
        return {
            joint_id: fb.measured_angle
            for joint_id, fb in self.joint_feedback.items()
        }

    def calibrate_joint(self, joint_id: str):
        """
        Request calibration of specific joint

        Args:
            joint_id: Joint to calibrate
        """
        self.send_command(f'CALIBRATE {joint_id}')
        print(f"Calibration request sent for joint {joint_id}")

    def calibrate_all(self):
        """Request calibration of all joints"""
        self.send_command('CALIBRATE_ALL')
        print("Calibration request sent for all joints")

    def get_status(self) -> Dict:
        """
        Get gateway status

        Returns:
            Status dictionary
        """
        return {
            'connected': self.connected,
            'mode': self.config.mode,
            'last_update': self.last_update_time,
            'time_since_update': time.time() - self.last_update_time if self.last_update_time > 0 else 0,
            'num_joints': len(self.joint_feedback),
            'joints': list(self.joint_feedback.keys())
        }

    def is_data_fresh(self, max_age: float = 1.0) -> bool:
        """
        Check if received data is fresh

        Args:
            max_age: Maximum age in seconds

        Returns:
            True if data is fresh
        """
        if self.last_update_time == 0:
            return False

        age = time.time() - self.last_update_time
        return age < max_age


def demo_gateway_client():
    """Demonstrate gateway client usage"""
    print("=== Sensor Gateway Client Demo ===\n")

    # Create client with serial connection
    config = GatewayConfig(
        mode='serial',
        serial_port='/dev/ttyUSB1',  # Gateway on different port than robot
        serial_baudrate=115200
    )

    client = SensorGatewayClient(config)

    # Callbacks
    def on_data(data):
        print(f"Received data from {len(data.get('joints', {}))} joints")

    def on_disconnect():
        print("Connection lost!")

    client.on_data_received = on_data
    client.on_connection_lost = on_disconnect

    # Connect
    print("Connecting to gateway...")
    if not client.connect():
        print("Failed to connect. Make sure gateway is running.")
        return

    # Wait for data
    print("\nWaiting for sensor data...")
    time.sleep(2)

    # Read sensors
    print("\n=== Sensor Readings ===")
    feedback = client.read_all()

    for joint_id, fb in sorted(feedback.items()):
        print(f"\nJoint {joint_id}:")
        print(f"  Angle: {fb.measured_angle:.1f}°")
        print(f"  Accel: ({fb.acceleration.x:.3f}, {fb.acceleration.y:.3f}, {fb.acceleration.z:.3f}) g")

    # Monitor for a while
    print("\n=== Monitoring (10 seconds) ===\n")

    for i in range(100):
        angles = client.get_joint_angles()

        angle_str = " ".join([
            f"{jid}={angle:6.1f}°"
            for jid, angle in sorted(angles.items())
        ])

        status = "✓" if client.is_data_fresh() else "✗"
        print(f"\r{status} {angle_str}", end='', flush=True)

        time.sleep(0.1)

    # Get status
    print("\n\n=== Gateway Status ===")
    status = client.get_status()

    print(f"Connected: {status['connected']}")
    print(f"Mode: {status['mode']}")
    print(f"Joints: {', '.join(status['joints'])}")
    print(f"Time since last update: {status['time_since_update']:.3f}s")

    # Disconnect
    print("\nDisconnecting...")
    client.disconnect()

    print("\n✓ Demo complete")


if __name__ == '__main__':
    demo_gateway_client()

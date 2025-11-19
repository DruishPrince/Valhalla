"""
Sensor Manager for Multiple ADXL345 Sensors

Manages multiple ADXL345 sensors mounted on robot joints
Provides joint angle feedback and calibration
"""

import time
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from adxl345_sensor import ADXL345, create_sensor, AccelData, Orientation


@dataclass
class JointSensorConfig:
    """Configuration for a joint sensor"""
    joint_id: str  # e.g., 'A', 'B', 'D', etc.
    joint_name: str  # e.g., 'Base', 'Shoulder', 'Elbow'
    i2c_address: int  # I2C address of ADXL345
    axis_mapping: Dict[str, str]  # Maps sensor axis to joint axis
    zero_orientation: Dict[str, float]  # Orientation when joint is at 0°

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'JointSensorConfig':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class JointFeedback:
    """Real-time feedback from a joint sensor"""
    joint_id: str
    measured_angle: float  # degrees
    acceleration: AccelData
    orientation: Orientation
    timestamp: float

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'joint_id': self.joint_id,
            'measured_angle': self.measured_angle,
            'acceleration': {
                'x': self.acceleration.x,
                'y': self.acceleration.y,
                'z': self.acceleration.z
            },
            'orientation': self.orientation.to_dict(),
            'timestamp': self.timestamp
        }


class SensorManager:
    """
    Manages multiple ADXL345 sensors for robot joint sensing
    """

    # Default I2C addresses for up to 6 joints
    # ADXL345 can use 0x53 or 0x1D (SDO pin determines address)
    # For more sensors, use I2C multiplexer
    DEFAULT_ADDRESSES = {
        'A': 0x53,  # Base (SDO = LOW)
        'B': 0x1D,  # Shoulder (SDO = HIGH)
        'D': 0x53,  # Elbow (on separate I2C bus or multiplexer)
        'X': 0x1D,  # Wrist pitch
        'Y': 0x53,  # Wrist roll
        'Z': 0x1D,  # End effector
    }

    def __init__(self, config_file: str = "sensor_config.json"):
        """
        Initialize sensor manager

        Args:
            config_file: Path to sensor configuration file
        """
        self.config_file = config_file
        self.sensors: Dict[str, ADXL345] = {}
        self.configs: Dict[str, JointSensorConfig] = {}
        self.latest_feedback: Dict[str, JointFeedback] = {}

        # Load configuration if exists
        if Path(config_file).exists():
            self.load_config()

    def add_sensor(self,
                   joint_id: str,
                   joint_name: str,
                   i2c_address: Optional[int] = None,
                   i2c_bus: int = 1,
                   axis_mapping: Optional[Dict[str, str]] = None,
                   simulate: bool = False) -> bool:
        """
        Add a sensor for a specific joint

        Args:
            joint_id: Joint identifier ('A', 'B', 'D', etc.)
            joint_name: Human-readable name
            i2c_address: I2C address (uses default if None)
            i2c_bus: I2C bus number
            axis_mapping: Axis mapping for orientation
            simulate: Use simulator if True

        Returns:
            True if sensor added successfully
        """
        if i2c_address is None:
            i2c_address = self.DEFAULT_ADDRESSES.get(joint_id, 0x53)

        if axis_mapping is None:
            # Default: use roll for revolute joints
            axis_mapping = {'primary': 'roll', 'secondary': 'pitch'}

        # Create sensor
        sensor = create_sensor(i2c_bus, i2c_address, simulate)

        if sensor.connect():
            self.sensors[joint_id] = sensor

            # Create configuration
            config = JointSensorConfig(
                joint_id=joint_id,
                joint_name=joint_name,
                i2c_address=i2c_address,
                axis_mapping=axis_mapping,
                zero_orientation={'roll': 0.0, 'pitch': 0.0}
            )
            self.configs[joint_id] = config

            print(f"✓ Added sensor for joint {joint_id} ({joint_name}) at 0x{i2c_address:02X}")
            return True
        else:
            print(f"✗ Failed to add sensor for joint {joint_id}")
            return False

    def remove_sensor(self, joint_id: str):
        """Remove a sensor"""
        if joint_id in self.sensors:
            self.sensors[joint_id].disconnect()
            del self.sensors[joint_id]
            del self.configs[joint_id]
            print(f"✓ Removed sensor for joint {joint_id}")

    def calibrate_joint(self, joint_id: str, num_samples: int = 100) -> bool:
        """
        Calibrate a joint sensor at its zero position

        Args:
            joint_id: Joint to calibrate
            num_samples: Number of samples for calibration

        Returns:
            True if calibration successful
        """
        if joint_id not in self.sensors:
            print(f"✗ No sensor for joint {joint_id}")
            return False

        sensor = self.sensors[joint_id]
        config = self.configs[joint_id]

        print(f"\nCalibrating joint {joint_id} ({config.joint_name})")
        print("Move joint to 0° position and keep it still...")
        time.sleep(2)  # Give user time to position

        # Calibrate accelerometer
        sensor.calibrate(num_samples)

        # Read zero orientation
        orientation = sensor.calculate_orientation()
        config.zero_orientation = orientation.to_dict()

        print(f"✓ Zero orientation: Roll={orientation.roll:.1f}° Pitch={orientation.pitch:.1f}°")

        return True

    def calibrate_all(self, num_samples: int = 100):
        """Calibrate all sensors"""
        for joint_id in self.sensors.keys():
            self.calibrate_joint(joint_id, num_samples)
            time.sleep(1)  # Brief pause between joints

    def read_joint(self, joint_id: str) -> Optional[JointFeedback]:
        """
        Read current angle and state of a joint

        Args:
            joint_id: Joint to read

        Returns:
            JointFeedback with current state
        """
        if joint_id not in self.sensors:
            return None

        sensor = self.sensors[joint_id]
        config = self.configs[joint_id]

        # Read sensor
        accel = sensor.read()
        orientation = sensor.calculate_orientation(accel)

        # Calculate joint angle relative to zero position
        primary_axis = config.axis_mapping.get('primary', 'roll')

        if primary_axis == 'roll':
            measured_angle = orientation.roll - config.zero_orientation['roll']
        else:
            measured_angle = orientation.pitch - config.zero_orientation['pitch']

        # Create feedback
        feedback = JointFeedback(
            joint_id=joint_id,
            measured_angle=measured_angle,
            acceleration=accel,
            orientation=orientation,
            timestamp=time.time()
        )

        self.latest_feedback[joint_id] = feedback

        return feedback

    def read_all(self) -> Dict[str, JointFeedback]:
        """
        Read all joint sensors

        Returns:
            Dictionary of joint_id -> JointFeedback
        """
        feedback = {}

        for joint_id in self.sensors.keys():
            fb = self.read_joint(joint_id)
            if fb:
                feedback[joint_id] = fb

        return feedback

    def get_joint_angles(self) -> Dict[str, float]:
        """
        Get current measured angles for all joints

        Returns:
            Dictionary of joint_id -> angle (degrees)
        """
        feedback = self.read_all()
        return {jid: fb.measured_angle for jid, fb in feedback.items()}

    def compare_to_commanded(self, commanded_angles: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """
        Compare measured angles to commanded angles

        Args:
            commanded_angles: Expected joint angles

        Returns:
            Dictionary with comparison data for each joint
        """
        measured_angles = self.get_joint_angles()
        comparison = {}

        for joint_id in measured_angles.keys():
            if joint_id in commanded_angles:
                measured = measured_angles[joint_id]
                commanded = commanded_angles[joint_id]
                error = measured - commanded

                comparison[joint_id] = {
                    'measured': measured,
                    'commanded': commanded,
                    'error': error,
                    'percent_error': abs(error / commanded * 100) if commanded != 0 else 0
                }

        return comparison

    def save_config(self, filepath: Optional[str] = None):
        """Save sensor configuration to file"""
        if filepath is None:
            filepath = self.config_file

        config_data = {
            'sensors': {
                jid: config.to_dict()
                for jid, config in self.configs.items()
            }
        }

        with open(filepath, 'w') as f:
            json.dump(config_data, f, indent=2)

        print(f"✓ Configuration saved to {filepath}")

    def load_config(self, filepath: Optional[str] = None) -> bool:
        """Load sensor configuration from file"""
        if filepath is None:
            filepath = self.config_file

        try:
            with open(filepath, 'r') as f:
                config_data = json.load(f)

            for joint_id, sensor_config in config_data.get('sensors', {}).items():
                config = JointSensorConfig.from_dict(sensor_config)
                self.configs[joint_id] = config

            print(f"✓ Configuration loaded from {filepath}")
            return True

        except Exception as e:
            print(f"✗ Error loading configuration: {e}")
            return False

    def start_monitoring(self, callback=None, interval: float = 0.1):
        """
        Start continuous monitoring (blocking)

        Args:
            callback: Function to call with feedback data
            interval: Update interval in seconds
        """
        print("Starting sensor monitoring... (Ctrl+C to stop)")

        try:
            while True:
                feedback = self.read_all()

                if callback:
                    callback(feedback)
                else:
                    # Default: print to console
                    self._print_feedback(feedback)

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nMonitoring stopped")

    def _print_feedback(self, feedback: Dict[str, JointFeedback]):
        """Print feedback to console"""
        print("\r" + " " * 100, end='')  # Clear line

        feedback_str = "Joints: "
        for jid, fb in sorted(feedback.items()):
            feedback_str += f"{jid}={fb.measured_angle:6.1f}° "

        print(f"\r{feedback_str}", end='', flush=True)

    def disconnect_all(self):
        """Disconnect all sensors"""
        for sensor in self.sensors.values():
            sensor.disconnect()
        self.sensors.clear()
        print("✓ All sensors disconnected")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect_all()


def setup_thor_sensors(simulate: bool = False) -> SensorManager:
    """
    Setup sensors for Thor robot (example configuration)

    Args:
        simulate: Use simulators if True

    Returns:
        Configured SensorManager
    """
    manager = SensorManager()

    # Add sensors for each joint
    # Adjust addresses based on your hardware configuration
    manager.add_sensor('A', 'Base', i2c_address=0x53, simulate=simulate)
    manager.add_sensor('B', 'Shoulder', i2c_address=0x1D, simulate=simulate)
    manager.add_sensor('D', 'Elbow', i2c_address=0x53, i2c_bus=2, simulate=simulate)

    # Optionally add more sensors
    # manager.add_sensor('X', 'Wrist Pitch', i2c_address=0x1D, i2c_bus=2, simulate=simulate)
    # manager.add_sensor('Y', 'Wrist Roll', i2c_address=0x53, i2c_bus=3, simulate=simulate)

    return manager


def test_sensor_manager():
    """Test sensor manager"""
    print("=== Sensor Manager Test ===\n")

    # Create manager with simulated sensors
    manager = setup_thor_sensors(simulate=True)

    # Calibrate sensors
    print("\nCalibrating sensors...")
    manager.calibrate_all()

    # Read all sensors
    print("\nReading sensors:")
    feedback = manager.read_all()

    for joint_id, fb in feedback.items():
        config = manager.configs[joint_id]
        print(f"\n{config.joint_name} (Joint {joint_id}):")
        print(f"  Measured angle: {fb.measured_angle:6.1f}°")
        print(f"  Orientation: Roll={fb.orientation.roll:6.1f}° Pitch={fb.orientation.pitch:6.1f}°")
        print(f"  Acceleration: ({fb.acceleration.x:.3f}, {fb.acceleration.y:.3f}, {fb.acceleration.z:.3f}) g")

    # Compare to commanded angles
    print("\nComparing to commanded position:")
    commanded = {'A': 45.0, 'B': 30.0, 'D': -20.0}
    comparison = manager.compare_to_commanded(commanded)

    for joint_id, comp in comparison.items():
        print(f"  Joint {joint_id}: Commanded={comp['commanded']:6.1f}° "
              f"Measured={comp['measured']:6.1f}° "
              f"Error={comp['error']:6.1f}°")

    # Save configuration
    manager.save_config('test_sensor_config.json')

    # Cleanup
    manager.disconnect_all()


if __name__ == '__main__':
    test_sensor_manager()

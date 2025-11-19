"""
Sensor Integration with Robot Controller

Integrates ADXL345 sensor feedback with robot control and kinematics
Provides closed-loop position control and error monitoring
"""

import time
import threading
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass

from sensor_manager import SensorManager, JointFeedback
from robot_controller import RobotController, MovementType
from kinematics import ThorKinematics, Point3D


@dataclass
class ClosedLoopConfig:
    """Configuration for closed-loop control"""
    enabled: bool = False
    max_error: float = 5.0  # degrees
    correction_gain: float = 0.5  # Proportional gain
    min_correction: float = 0.5  # Minimum correction to apply
    update_rate: float = 10.0  # Hz


class SensorIntegration:
    """
    Integrates sensor feedback with robot control

    Provides:
    - Real-time position feedback
    - Closed-loop position correction
    - Error monitoring and alerts
    - Sensor-based kinematics updates
    """

    def __init__(self,
                 robot_controller: RobotController,
                 sensor_manager: SensorManager,
                 kinematics: Optional[ThorKinematics] = None):
        """
        Initialize sensor integration

        Args:
            robot_controller: Robot controller instance
            sensor_manager: Sensor manager instance
            kinematics: Kinematics instance (creates new if None)
        """
        self.robot = robot_controller
        self.sensors = sensor_manager
        self.kinematics = kinematics if kinematics else ThorKinematics()

        # Closed-loop control
        self.closed_loop_config = ClosedLoopConfig()
        self.closed_loop_thread: Optional[threading.Thread] = None
        self.closed_loop_running = False

        # State tracking
        self.commanded_angles: Dict[str, float] = {}
        self.measured_angles: Dict[str, float] = {}
        self.position_errors: Dict[str, float] = {}

        # Callbacks
        self.on_error_detected: Optional[Callable[[str, float], None]] = None
        self.on_position_updated: Optional[Callable[[Dict[str, float]], None]] = None

    def update_measured_position(self) -> Dict[str, float]:
        """
        Update measured position from sensors

        Returns:
            Dictionary of measured joint angles
        """
        self.measured_angles = self.sensors.get_joint_angles()

        # Update kinematics with measured position
        for joint_id, angle in self.measured_angles.items():
            if joint_id in self.kinematics.joint_angles:
                self.kinematics.joint_angles[joint_id] = angle

        # Trigger callback
        if self.on_position_updated:
            self.on_position_updated(self.measured_angles)

        return self.measured_angles

    def update_commanded_position(self, angles: Dict[str, float]):
        """
        Update commanded position

        Args:
            angles: Commanded joint angles
        """
        self.commanded_angles.update(angles)

    def calculate_errors(self) -> Dict[str, float]:
        """
        Calculate position errors between commanded and measured

        Returns:
            Dictionary of position errors
        """
        self.position_errors.clear()

        for joint_id in self.measured_angles.keys():
            if joint_id in self.commanded_angles:
                error = self.measured_angles[joint_id] - self.commanded_angles[joint_id]
                self.position_errors[joint_id] = error

                # Check for excessive error
                if abs(error) > self.closed_loop_config.max_error:
                    if self.on_error_detected:
                        self.on_error_detected(joint_id, error)

        return self.position_errors

    def apply_correction(self, errors: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate correction commands based on errors

        Args:
            errors: Position errors

        Returns:
            Dictionary of correction angles
        """
        corrections = {}

        for joint_id, error in errors.items():
            # Proportional control
            correction = error * self.closed_loop_config.correction_gain

            # Apply minimum threshold
            if abs(correction) < self.closed_loop_config.min_correction:
                correction = 0

            corrections[joint_id] = correction

        return corrections

    def move_with_feedback(self,
                          target_angles: Dict[str, float],
                          movement_type: MovementType = MovementType.G1_LINEAR,
                          feedrate: Optional[float] = None,
                          timeout: float = 5.0) -> bool:
        """
        Move to target position and verify with sensor feedback

        Args:
            target_angles: Target joint angles
            movement_type: Movement type
            feedrate: Optional feedrate
            timeout: Maximum time to wait for completion

        Returns:
            True if position reached within tolerance
        """
        if not self.robot.is_connected():
            print("Error: Robot not connected")
            return False

        # Send movement command
        self.commanded_angles.update(target_angles)
        self.robot.move_all_joints(target_angles, movement_type, feedrate)

        # Wait for movement and verify
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Read sensors
            self.update_measured_position()

            # Check if position reached
            errors = self.calculate_errors()

            all_within_tolerance = all(
                abs(error) < self.closed_loop_config.max_error
                for error in errors.values()
            )

            if all_within_tolerance:
                print(f"✓ Position reached (errors: {errors})")
                return True

            time.sleep(0.1)

        print(f"✗ Position not reached within {timeout}s (errors: {errors})")
        return False

    def start_closed_loop(self):
        """Start closed-loop position control"""
        if self.closed_loop_running:
            print("Closed-loop control already running")
            return

        self.closed_loop_config.enabled = True
        self.closed_loop_running = True

        # Start control thread
        self.closed_loop_thread = threading.Thread(target=self._closed_loop_worker, daemon=True)
        self.closed_loop_thread.start()

        print("✓ Closed-loop control started")

    def stop_closed_loop(self):
        """Stop closed-loop position control"""
        self.closed_loop_running = False

        if self.closed_loop_thread:
            self.closed_loop_thread.join(timeout=2.0)
            self.closed_loop_thread = None

        print("✓ Closed-loop control stopped")

    def _closed_loop_worker(self):
        """Closed-loop control worker thread"""
        interval = 1.0 / self.closed_loop_config.update_rate

        while self.closed_loop_running:
            start = time.time()

            # Update measured position
            self.update_measured_position()

            # Calculate errors
            errors = self.calculate_errors()

            # Apply corrections if enabled
            if self.closed_loop_config.enabled and errors:
                corrections = self.apply_correction(errors)

                # Send correction commands
                if any(abs(c) > 0 for c in corrections.values()):
                    corrected_angles = {
                        jid: self.commanded_angles[jid] + corrections[jid]
                        for jid in corrections.keys()
                        if jid in self.commanded_angles
                    }

                    if self.robot.is_connected():
                        self.robot.move_all_joints(
                            corrected_angles,
                            MovementType.G1_LINEAR,
                            feedrate=100  # Slow corrections
                        )

            # Maintain update rate
            elapsed = time.time() - start
            if elapsed < interval:
                time.sleep(interval - elapsed)

    def get_actual_end_effector_position(self) -> Optional[Point3D]:
        """
        Get actual end effector position based on sensor feedback

        Returns:
            Actual end effector position or None if sensors not available
        """
        if not self.measured_angles:
            return None

        # Calculate forward kinematics with measured angles
        end_pos, _ = self.kinematics.forward_kinematics(self.measured_angles)
        return end_pos

    def monitor_position(self, duration: float = 10.0):
        """
        Monitor position and print feedback

        Args:
            duration: Monitoring duration in seconds
        """
        print(f"Monitoring position for {duration}s...")
        print("Joint | Commanded | Measured | Error")
        print("-" * 45)

        start_time = time.time()

        while time.time() - start_time < duration:
            self.update_measured_position()
            errors = self.calculate_errors()

            for joint_id in sorted(self.measured_angles.keys()):
                commanded = self.commanded_angles.get(joint_id, 0.0)
                measured = self.measured_angles[joint_id]
                error = errors.get(joint_id, 0.0)

                print(f"\r{joint_id:5} | {commanded:9.1f}° | {measured:8.1f}° | {error:6.1f}°", end='')

            print()
            time.sleep(0.5)

        print("\nMonitoring complete")

    def calibrate_sensors_at_home(self):
        """Calibrate sensors at robot home position"""
        print("Calibrating sensors at home position...")

        # Home robot
        if self.robot.is_connected():
            self.robot.send_homing_command()
            time.sleep(3)  # Wait for homing

        # Calibrate all sensors
        self.sensors.calibrate_all()

        print("✓ Sensor calibration complete")

    def get_status_report(self) -> Dict:
        """
        Get comprehensive status report

        Returns:
            Dictionary with status information
        """
        # Update measurements
        self.update_measured_position()
        errors = self.calculate_errors()

        # Calculate end effector positions
        commanded_pos = None
        measured_pos = None

        if self.commanded_angles:
            commanded_pos, _ = self.kinematics.forward_kinematics(self.commanded_angles)

        if self.measured_angles:
            measured_pos, _ = self.kinematics.forward_kinematics(self.measured_angles)

        return {
            'commanded_angles': self.commanded_angles.copy(),
            'measured_angles': self.measured_angles.copy(),
            'position_errors': errors.copy(),
            'commanded_position': {
                'x': commanded_pos.x if commanded_pos else 0,
                'y': commanded_pos.y if commanded_pos else 0,
                'z': commanded_pos.z if commanded_pos else 0
            } if commanded_pos else None,
            'measured_position': {
                'x': measured_pos.x if measured_pos else 0,
                'y': measured_pos.y if measured_pos else 0,
                'z': measured_pos.z if measured_pos else 0
            } if measured_pos else None,
            'closed_loop_enabled': self.closed_loop_config.enabled,
            'max_error': max(abs(e) for e in errors.values()) if errors else 0
        }


def create_integrated_system(simulate_sensors: bool = False) -> SensorIntegration:
    """
    Create integrated robot system with sensors

    Args:
        simulate_sensors: Use simulated sensors if True

    Returns:
        Configured SensorIntegration instance
    """
    from sensor_manager import setup_thor_sensors

    # Create components
    robot = RobotController()
    sensors = setup_thor_sensors(simulate=simulate_sensors)
    kinematics = ThorKinematics()

    # Create integration
    integration = SensorIntegration(robot, sensors, kinematics)

    return integration


def demo_sensor_integration():
    """Demonstrate sensor integration"""
    print("=== Sensor Integration Demo ===\n")

    # Create integrated system (simulated)
    system = create_integrated_system(simulate_sensors=True)

    # Calibrate sensors
    system.calibrate_sensors_at_home()

    # Define target position
    target = {'A': 45.0, 'B': 30.0, 'D': -20.0}
    print(f"\nMoving to target: {target}")

    # Move with feedback (simulated)
    system.update_commanded_position(target)

    # Monitor position
    system.monitor_position(duration=5.0)

    # Get status report
    print("\nStatus Report:")
    status = system.get_status_report()

    print(f"  Position Errors:")
    for joint_id, error in status['position_errors'].items():
        print(f"    Joint {joint_id}: {error:6.1f}°")

    if status['measured_position']:
        print(f"  End Effector Position (measured):")
        print(f"    X: {status['measured_position']['x']:.1f} mm")
        print(f"    Y: {status['measured_position']['y']:.1f} mm")
        print(f"    Z: {status['measured_position']['z']:.1f} mm")

    # Cleanup
    system.sensors.disconnect_all()


if __name__ == '__main__':
    demo_sensor_integration()

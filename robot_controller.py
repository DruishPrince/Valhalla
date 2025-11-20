"""
Robot Controller Module
Handles all robot commands, state management, and communication logic

Supports multiple firmware backends:
- GRBL (default)
- Klipper (high-speed via KlipperController)
- Reprap
- Marlin
"""
import serial
from typing import Optional, Dict, List, Tuple
from enum import Enum


class RobotState(Enum):
    """Robot operational states"""
    IDLE = "Idle"
    RUN = "Run"
    HOME = "Home"
    ALARM = "Alarm"
    HOLD = "Hold"
    DISCONNECTED = "Disconnected"


class MovementType(Enum):
    """Movement command types"""
    G0_RAPID = "G0"  # Rapid positioning
    G1_LINEAR = "G1"  # Linear movement with feedrate


class RobotController:
    """
    Manages robot state, command generation, and serial communication
    for the Thor 6-axis robotic arm.

    Supports multiple firmware backends via dependency injection.
    """

    # Joint angle limits (degrees)
    JOINT_LIMITS = {
        'A': (-180, 180),  # Art1: Base rotation
        'B': (-90, 90),    # Art2: Shoulder
        'C': (-90, 90),    # Art3: Linked to Art2
        'D': (-90, 90),    # Art4: Elbow
        'X': (-90, 90),    # Art5: Wrist pitch
        'Y': (-90, 90),    # Art6: Wrist roll
        'Z': (-180, 180),  # Gripper rotation
    }

    def __init__(self, firmware_backend=None):
        """
        Initialize robot controller

        Args:
            firmware_backend: Optional backend controller (e.g., KlipperController)
                             If None, uses direct serial GRBL control
        """
        self.serial_port: Optional[serial.Serial] = None
        self.firmware_backend = firmware_backend  # Optional Klipper/other backend
        self.current_state = RobotState.DISCONNECTED
        self.current_position = {
            'A': 0.0, 'B': 0.0, 'C': 0.0,
            'D': 0.0, 'X': 0.0, 'Y': 0.0, 'Z': 0.0
        }
        self.gripper_position = 0  # 0-100%
        self.default_feedrate = 500  # degrees/min

    def connect(self, port: str, baudrate: int = 115200, timeout: float = 1.0,
                use_network: bool = False, network_host: str = "127.0.0.1") -> bool:
        """
        Connect to the robot via serial port or network

        Args:
            port: Serial port name (e.g., '/dev/ttyUSB0', 'COM3')
            baudrate: Communication speed (default 115200, up to 1500000 for FLY board)
            timeout: Read timeout in seconds
            use_network: Use network connection (Klipper/Moonraker)
            network_host: Network host for Klipper (default localhost)

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # If using firmware backend (e.g., Klipper)
            if self.firmware_backend:
                if use_network:
                    # Network connection for Klipper
                    success = self.firmware_backend.connect_network(network_host)
                else:
                    # High-speed serial for Klipper
                    success = self.firmware_backend.connect_serial(port, baudrate)

                if success:
                    self.current_state = RobotState.READY
                return success

            # Standard GRBL serial connection
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

            self.serial_port = serial.Serial(port, baudrate, timeout=timeout)
            self.current_state = RobotState.READY
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Close serial connection"""
        if self.firmware_backend:
            self.firmware_backend.disconnect()
        elif self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.current_state = RobotState.DISCONNECTED

    def is_connected(self) -> bool:
        """Check if robot is connected"""
        if self.firmware_backend:
            return self.firmware_backend.is_connected()
        return self.serial_port is not None and self.serial_port.is_open

    def validate_angle(self, joint: str, angle: float) -> Tuple[bool, float]:
        """
        Validate and clamp joint angle to safe limits

        Args:
            joint: Joint identifier ('A', 'B', 'C', 'D', 'X', 'Y', 'Z')
            angle: Desired angle in degrees

        Returns:
            Tuple of (is_valid, clamped_angle)
        """
        if joint not in self.JOINT_LIMITS:
            return False, angle

        min_angle, max_angle = self.JOINT_LIMITS[joint]
        clamped = max(min_angle, min(max_angle, angle))
        is_valid = (clamped == angle)

        return is_valid, clamped

    def build_move_command(self,
                          movement_type: MovementType,
                          joints: Dict[str, float],
                          feedrate: Optional[float] = None) -> str:
        """
        Build a movement command string

        Args:
            movement_type: G0 (rapid) or G1 (linear)
            joints: Dictionary of joint positions {joint_id: angle}
            feedrate: Optional feedrate for G1 moves (degrees/min)

        Returns:
            G-code command string
        """
        cmd_parts = [movement_type.value]

        # Handle coupled joints (Art2 controls both B and C)
        if 'B' in joints:
            joints['C'] = joints['B']  # Art3 is coupled to Art2

        # Add joint angles to command
        for joint, angle in joints.items():
            is_valid, clamped_angle = self.validate_angle(joint, angle)
            if not is_valid:
                print(f"Warning: Joint {joint} angle {angle}° clamped to {clamped_angle}°")
            cmd_parts.append(f"{joint}{clamped_angle}")

        # Add feedrate for G1 moves
        if movement_type == MovementType.G1_LINEAR:
            feed = feedrate if feedrate is not None else self.default_feedrate
            cmd_parts.append(f"F{feed}")

        return " ".join(cmd_parts)

    def move_joint(self, joint: str, angle: float,
                   movement_type: MovementType = MovementType.G0_RAPID,
                   feedrate: Optional[float] = None) -> bool:
        """
        Move a single joint to specified angle

        Args:
            joint: Joint identifier ('A', 'B', 'C', 'D', 'X', 'Y', 'Z')
            angle: Target angle in degrees
            movement_type: G0 or G1 movement
            feedrate: Optional feedrate for G1 moves

        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            print("Error: Robot not connected")
            return False

        command = self.build_move_command(movement_type, {joint: angle}, feedrate)
        return self.send_command(command)

    def move_all_joints(self, positions: Dict[str, float],
                       movement_type: MovementType = MovementType.G0_RAPID,
                       feedrate: Optional[float] = None) -> bool:
        """
        Move multiple joints simultaneously

        Args:
            positions: Dictionary of joint positions {joint_id: angle}
            movement_type: G0 or G1 movement
            feedrate: Optional feedrate for G1 moves

        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            print("Error: Robot not connected")
            return False

        command = self.build_move_command(movement_type, positions, feedrate)
        return self.send_command(command)

    def move_gripper(self, percentage: float) -> bool:
        """
        Control gripper position

        Args:
            percentage: Gripper opening (0-100%)

        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            print("Error: Robot not connected")
            return False

        # Clamp to 0-100%
        percentage = max(0, min(100, percentage))

        # Convert to PWM value (0-255)
        pwm_value = int((255 / 100) * percentage)

        command = f"M3 S{pwm_value}"
        self.gripper_position = percentage
        return self.send_command(command)

    def send_homing_command(self) -> bool:
        """Send homing cycle command"""
        return self.send_command("$H")

    def send_zero_position(self) -> bool:
        """Move all joints to zero position"""
        return self.send_command("G0 A0 B0 C0 D0 X0 Y0 Z0")

    def send_kill_alarm(self) -> bool:
        """Clear alarm state"""
        return self.send_command("$X")

    def send_status_query(self) -> bool:
        """Request current robot status"""
        return self.send_command("?")

    def send_command(self, command: str) -> bool:
        """
        Send a raw command to the robot

        Args:
            command: G-code command string

        Returns:
            True if sent successfully
        """
        if not self.is_connected():
            return False

        try:
            # Use firmware backend if available (Klipper, etc.)
            if self.firmware_backend:
                return self.firmware_backend.send_gcode(command)

            # Standard GRBL serial
            # Add newline if not present
            if not command.endswith('\n'):
                command += '\n'

            self.serial_port.write(command.encode('UTF-8'))
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False

    def parse_status_response(self, response: str) -> Dict:
        """
        Parse status response from robot

        Format: <state,MPos:a1,a2,a3,a4,a5,a6,WPos:...>

        Args:
            response: Status response string

        Returns:
            Dictionary with parsed status information
        """
        try:
            # Remove angle brackets and split by comma
            data = response.strip('<>').split(',')

            status = {
                'state': data[0],
                'positions': {}
            }

            # Parse MPos (Machine Position)
            if len(data) > 1 and 'MPos:' in data[1]:
                positions = data[1].split(':')[1:]
                joint_names = ['A', 'B', 'C', 'D', 'X', 'Y', 'Z']

                for i, pos_str in enumerate(positions):
                    if i < len(joint_names):
                        try:
                            angle = float(pos_str.strip())
                            status['positions'][joint_names[i]] = angle
                            self.current_position[joint_names[i]] = angle
                        except ValueError:
                            pass

            # Update state
            try:
                self.current_state = RobotState(data[0])
            except ValueError:
                pass

            return status

        except Exception as e:
            print(f"Error parsing status: {e}")
            return {'state': 'Unknown', 'positions': {}}

    def get_current_position(self) -> Dict[str, float]:
        """Get last known robot position"""
        return self.current_position.copy()

    def get_state(self) -> RobotState:
        """Get current robot state"""
        return self.current_state

    def get_gripper_position(self) -> float:
        """Get current gripper position (0-100%)"""
        return self.gripper_position


# Convenience functions for quick command generation
def create_controller() -> RobotController:
    """Create a new robot controller instance"""
    return RobotController()


def generate_move_command(joints: Dict[str, float],
                         rapid: bool = True,
                         feedrate: Optional[float] = None) -> str:
    """
    Generate a movement command without a controller instance

    Args:
        joints: Dictionary of joint positions
        rapid: Use G0 (rapid) if True, G1 (linear) if False
        feedrate: Optional feedrate for G1 moves

    Returns:
        G-code command string
    """
    controller = RobotController()
    movement_type = MovementType.G0_RAPID if rapid else MovementType.G1_LINEAR
    return controller.build_move_command(movement_type, joints, feedrate)

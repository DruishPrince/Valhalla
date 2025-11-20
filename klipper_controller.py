"""
Klipper Controller for FLY Super 8 Pro Board

Provides high-speed communication and advanced features for Klipper firmware:
- Network/wireless control via Moonraker API
- High-speed serial communication (up to 1.5M baud)
- Advanced motion control
- TMC driver support
"""

import serial
import socket
import json
import time
from typing import Optional, Dict, List, Tuple
from enum import Enum
import requests


class KlipperState(Enum):
    """Klipper printer states"""
    READY = "ready"
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class KlipperController:
    """
    Controller for Klipper firmware on FLY Super 8 Pro board

    Supports both:
    1. Direct serial communication (high-speed up to 1.5M baud)
    2. Network control via Moonraker API (wireless)
    """

    def __init__(self, use_network: bool = False):
        self.use_network = use_network
        self.serial_port: Optional[serial.Serial] = None
        self.moonraker_host = "127.0.0.1"
        self.moonraker_port = 7125
        self.state = KlipperState.DISCONNECTED

        self.current_position = {
            'A': 0.0, 'B': 0.0, 'C': 0.0,
            'D': 0.0, 'X': 0.0, 'Y': 0.0, 'Z': 0.0
        }

    def connect_serial(self, port: str, baudrate: int = 500000) -> bool:
        """
        Connect via high-speed serial

        Args:
            port: Serial port (e.g., '/dev/ttyACM0')
            baudrate: Up to 1500000 for FLY Super 8 Pro

        Returns:
            True if successful
        """
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

            # FLY Super 8 Pro supports very high baud rates
            self.serial_port = serial.Serial(
                port,
                baudrate,
                timeout=1.0,
                write_timeout=1.0
            )

            # Give Klipper time to initialize
            time.sleep(2)

            self.state = KlipperState.READY
            print(f"✓ Connected to Klipper at {baudrate} baud")
            return True

        except Exception as e:
            print(f"✗ Serial connection error: {e}")
            self.state = KlipperState.ERROR
            return False

    def connect_network(self, host: str = "127.0.0.1", port: int = 7125) -> bool:
        """
        Connect via Moonraker API (wireless/network control)

        Args:
            host: Moonraker host IP
            port: Moonraker port (default 7125)

        Returns:
            True if successful
        """
        self.moonraker_host = host
        self.moonraker_port = port
        self.use_network = True

        try:
            # Test connection
            response = self._api_request("GET", "/printer/info")
            if response:
                self.state = KlipperState.READY
                print(f"✓ Connected to Moonraker at {host}:{port}")
                return True
        except Exception as e:
            print(f"✗ Network connection error: {e}")
            self.state = KlipperState.ERROR

        return False

    def disconnect(self):
        """Disconnect from Klipper"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

        self.state = KlipperState.DISCONNECTED

    def is_connected(self) -> bool:
        """Check if connected"""
        if self.use_network:
            try:
                response = self._api_request("GET", "/server/info", timeout=1)
                return response is not None
            except:
                return False
        else:
            return self.serial_port is not None and self.serial_port.is_open

    def _api_request(self, method: str, endpoint: str, data: Dict = None, timeout: int = 5) -> Optional[Dict]:
        """Make Moonraker API request"""
        url = f"http://{self.moonraker_host}:{self.moonraker_port}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=timeout)
            else:
                return None

            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"API request error: {e}")

        return None

    def send_gcode(self, gcode: str) -> bool:
        """
        Send G-code command to Klipper

        Args:
            gcode: G-code command string

        Returns:
            True if sent successfully
        """
        if not self.is_connected():
            return False

        try:
            if self.use_network:
                # Send via Moonraker API
                response = self._api_request("POST", "/printer/gcode/script", {
                    "script": gcode
                })
                return response is not None

            else:
                # Send via serial
                command = gcode.strip() + "\n"
                self.serial_port.write(command.encode('utf-8'))
                self.serial_port.flush()
                return True

        except Exception as e:
            print(f"Error sending G-code: {e}")
            return False

    def move_joint(self, joint: str, angle: float, feedrate: int = 500) -> bool:
        """
        Move a single joint

        Args:
            joint: Joint ID ('A', 'B', 'D', 'X', 'Y', 'Z')
            angle: Target angle in degrees
            feedrate: Movement speed (degrees/min)

        Returns:
            True if command sent successfully
        """
        # Convert to G-code
        gcode = f"G1 {joint}{angle:.2f} F{feedrate}"
        success = self.send_gcode(gcode)

        if success:
            self.current_position[joint] = angle

        return success

    def move_all_joints(self, angles: Dict[str, float], feedrate: int = 500) -> bool:
        """
        Move multiple joints simultaneously

        Args:
            angles: Dictionary of joint angles {'A': 10, 'B': 20, ...}
            feedrate: Movement speed

        Returns:
            True if successful
        """
        # Build multi-axis G-code command
        gcode_parts = ["G1"]
        for joint, angle in angles.items():
            gcode_parts.append(f"{joint}{angle:.2f}")
        gcode_parts.append(f"F{feedrate}")

        gcode = " ".join(gcode_parts)
        success = self.send_gcode(gcode)

        if success:
            self.current_position.update(angles)

        return success

    def home_all(self) -> bool:
        """Home all axes"""
        return self.send_gcode("G28")

    def home_joint(self, joint: str) -> bool:
        """Home a specific joint"""
        return self.send_gcode(f"G28 {joint}")

    def emergency_stop(self) -> bool:
        """Emergency stop - immediately halt all motion"""
        if self.use_network:
            response = self._api_request("POST", "/printer/emergency_stop")
            return response is not None
        else:
            # Send M112 emergency stop
            return self.send_gcode("M112")

    def get_status(self) -> Dict:
        """
        Get Klipper status

        Returns:
            Dictionary with current status
        """
        if not self.is_connected():
            return {"state": "disconnected"}

        if self.use_network:
            response = self._api_request("GET", "/printer/objects/query?toolhead")
            if response and 'result' in response:
                status = response['result'].get('status', {})
                return {
                    "state": status.get('print_stats', {}).get('state', 'unknown'),
                    "position": status.get('toolhead', {}).get('position', []),
                    "velocities": status.get('toolhead', {}).get('max_velocity', 0),
                }

        return {
            "state": self.state.value,
            "position": self.current_position,
        }

    def configure_tmc_driver(self, joint: str, run_current: float = 0.8,
                            hold_current: float = 0.4, stealthchop: bool = True) -> bool:
        """
        Configure TMC driver settings for a joint

        Args:
            joint: Joint ID
            run_current: Running current in amps
            hold_current: Holding current in amps
            stealthchop: Enable StealthChop (quiet mode)

        Returns:
            True if successful
        """
        # Send TMC configuration commands
        commands = [
            f"SET_TMC_FIELD STEPPER=stepper_{joint} FIELD=RUN_CURRENT VALUE={run_current}",
            f"SET_TMC_FIELD STEPPER=stepper_{joint} FIELD=HOLD_CURRENT VALUE={hold_current}",
        ]

        if stealthchop:
            commands.append(f"SET_TMC_FIELD STEPPER=stepper_{joint} FIELD=en_spreadCycle VALUE=0")
        else:
            commands.append(f"SET_TMC_FIELD STEPPER=stepper_{joint} FIELD=en_spreadCycle VALUE=1")

        for cmd in commands:
            if not self.send_gcode(cmd):
                return False

        return True

    def set_velocity(self, velocity: float) -> bool:
        """
        Set maximum velocity (takes advantage of high-speed processor)

        Args:
            velocity: Max velocity in mm/s (FLY board can handle high speeds)

        Returns:
            True if successful
        """
        return self.send_gcode(f"SET_VELOCITY_LIMIT VELOCITY={velocity}")

    def set_acceleration(self, accel: float) -> bool:
        """
        Set acceleration (550MHz processor can handle high accelerations)

        Args:
            accel: Acceleration in mm/s^2

        Returns:
            True if successful
        """
        return self.send_gcode(f"SET_VELOCITY_LIMIT ACCEL={accel}")

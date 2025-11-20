"""
FLY Super 8 Pro Board Configuration and Utilities

Optimized for the Mellow FLY Super 8 Pro board with:
- 32-bit ARM Cortex-M7 @ 550MHz
- Klipper/Reprap firmware support
- High-speed communication (up to 1600K baud)
- TMC stepper driver support (UART/SPI)
- Network/wireless control
"""

from enum import Enum
from typing import Dict, List, Optional
import json


class FirmwareType(Enum):
    """Supported firmware types"""
    GRBL = "grbl"
    KLIPPER = "klipper"
    REPRAP = "reprap"
    MARLIN = "marlin"


class DriverType(Enum):
    """Stepper driver types supported by FLY Super 8 Pro"""
    A4988 = "A4988"
    LV8729 = "LV8729"
    DRV8225 = "DRV8225"
    TMC2208_UART = "TMC2208_UART"
    TMC2209_UART = "TMC2209_UART"
    TMC2130_SPI = "TMC2130_SPI"
    TMC5160_SPI = "TMC5160_SPI"


class FLYSuper8ProConfig:
    """
    Configuration for FLY Super 8 Pro board

    Takes advantage of the board's advanced features:
    - High-speed ARM Cortex-M7 processor
    - Multiple communication modes
    - Advanced stepper driver support
    - High-voltage capability
    """

    # Optimized baud rates for FLY Super 8 Pro
    # The board supports up to 1600K+ transfer speeds
    BAUDRATES = {
        'standard': 115200,
        'fast': 250000,
        'high_speed': 500000,
        'ultra_high_speed': 1000000,
        'maximum': 1500000  # Close to the 1600K+ spec
    }

    # Motor voltage options
    MOTOR_VOLTAGES = [12, 24, 48]  # DC12V-DC24V-DC48V support

    # Limit switch voltages
    LIMIT_SWITCH_VOLTAGES = [5, 12, 24]

    def __init__(self):
        self.firmware = FirmwareType.KLIPPER  # Default to Klipper for FLY boards
        self.baudrate = self.BAUDRATES['high_speed']  # 500K default
        self.motor_voltage = 24  # Most common
        self.limit_switch_voltage = 5

        # Stepper driver configuration for 6 axes
        self.drivers = {
            'A': DriverType.TMC2209_UART,  # Base
            'B': DriverType.TMC2209_UART,  # Shoulder
            'C': DriverType.TMC2209_UART,  # Linked
            'D': DriverType.TMC2209_UART,  # Elbow
            'X': DriverType.TMC2209_UART,  # Wrist pitch
            'Y': DriverType.TMC2209_UART,  # Wrist roll
            'Z': DriverType.TMC2209_UART,  # End effector
        }

        # TMC driver settings (for UART/SPI modes)
        self.tmc_settings = {
            'run_current': 0.8,  # Amps
            'hold_current': 0.4,  # Amps
            'microsteps': 16,
            'interpolate': True,
            'stealthchop': True,  # Quiet operation
            'spreadcycle': False,
        }

        # Klipper-specific settings
        self.klipper_config = {
            'host': '127.0.0.1',  # Moonraker API host
            'port': 7125,  # Default Moonraker port
            'use_network': False,  # Enable for wireless control
        }

    def get_klipper_driver_config(self, joint: str) -> Dict:
        """Generate Klipper config section for a TMC driver"""
        driver = self.drivers.get(joint)
        if not driver:
            return {}

        if driver in [DriverType.TMC2208_UART, DriverType.TMC2209_UART]:
            return {
                'uart_pin': f'P{joint}_UART',
                'run_current': self.tmc_settings['run_current'],
                'hold_current': self.tmc_settings['hold_current'],
                'microsteps': self.tmc_settings['microsteps'],
                'interpolate': self.tmc_settings['interpolate'],
                'stealthchop_threshold': 999999 if self.tmc_settings['stealthchop'] else 0,
            }
        elif driver in [DriverType.TMC2130_SPI, DriverType.TMC5160_SPI]:
            return {
                'spi_bus': 'spi1',
                'run_current': self.tmc_settings['run_current'],
                'hold_current': self.tmc_settings['hold_current'],
                'microsteps': self.tmc_settings['microsteps'],
                'interpolate': self.tmc_settings['interpolate'],
            }

        return {}

    def generate_klipper_config(self) -> str:
        """
        Generate a Klipper configuration file for the FLY Super 8 Pro
        optimized for the Thor robotic arm
        """
        config_lines = [
            "# Klipper Configuration for Thor Robotic Arm",
            "# FLY Super 8 Pro Board",
            "# 32-bit ARM Cortex-M7 @ 550MHz",
            "",
            "[mcu]",
            f"serial: /dev/serial/by-id/YOUR_BOARD_ID",
            f"baud: {self.baudrate}",
            "",
            "[printer]",
            "kinematics: none",  # For robotic arm
            f"max_velocity: 300",
            f"max_accel: 3000",
            "",
        ]

        # Add stepper configurations
        joints = ['A', 'B', 'C', 'D', 'X', 'Y', 'Z']
        for i, joint in enumerate(joints):
            config_lines.extend([
                f"[stepper_{joint}]",
                f"step_pin: STEP{i}",
                f"dir_pin: DIR{i}",
                f"enable_pin: !EN{i}",
                f"microsteps: {self.tmc_settings['microsteps']}",
                f"rotation_distance: 1.8",  # degrees per step (adjust as needed)
                f"endstop_pin: ^STOP{i}",
                f"position_min: -180",
                f"position_max: 180",
                f"homing_speed: 50",
                "",
            ])

            # Add TMC driver config if applicable
            driver = self.drivers.get(joint)
            if driver and 'TMC' in driver.value:
                driver_config = self.get_klipper_driver_config(joint)
                config_lines.append(f"[tmc2209 stepper_{joint}]")
                for key, value in driver_config.items():
                    if isinstance(value, bool):
                        value = str(value).lower()
                    config_lines.append(f"{key}: {value}")
                config_lines.append("")

        return "\n".join(config_lines)

    def to_dict(self) -> Dict:
        """Export configuration as dictionary"""
        return {
            'firmware': self.firmware.value,
            'baudrate': self.baudrate,
            'motor_voltage': self.motor_voltage,
            'limit_switch_voltage': self.limit_switch_voltage,
            'drivers': {k: v.value for k, v in self.drivers.items()},
            'tmc_settings': self.tmc_settings,
            'klipper_config': self.klipper_config,
        }

    def save_to_file(self, filename: str):
        """Save configuration to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filename: str) -> 'FLYSuper8ProConfig':
        """Load configuration from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)

        config = cls()
        config.firmware = FirmwareType(data['firmware'])
        config.baudrate = data['baudrate']
        config.motor_voltage = data['motor_voltage']
        config.limit_switch_voltage = data['limit_switch_voltage']
        config.drivers = {k: DriverType(v) for k, v in data['drivers'].items()}
        config.tmc_settings = data['tmc_settings']
        config.klipper_config = data['klipper_config']

        return config


# Default configuration optimized for FLY Super 8 Pro
DEFAULT_FLY_CONFIG = FLYSuper8ProConfig()

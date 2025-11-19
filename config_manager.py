"""
Configuration Manager
Handles loading, saving, and managing system configuration
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """
    Manages configuration settings for the robot control system
    """

    DEFAULT_CONFIG = {
        "serial": {
            "port": "/dev/ttyUSB0",
            "baudrate": 115200,
            "timeout": 1.0,
            "auto_connect": False
        },
        "robot": {
            "default_feedrate": 500,
            "homing_on_connect": True,
            "safety_limits_enabled": True,
            "max_feedrate": 2000,
            "min_feedrate": 50
        },
        "vision": {
            "camera_index": 0,
            "resolution": [640, 480],
            "fps": 30,
            "default_detection_method": "contour_detection",
            "calibration_file": "camera_calibration.npz",
            "auto_start_camera": False
        },
        "color_detection": {
            "lower_hsv": [0, 100, 100],
            "upper_hsv": [10, 255, 255],
            "min_area": 100
        },
        "contour_detection": {
            "min_area": 500,
            "max_area": 50000,
            "blur_kernel": 5,
            "canny_low": 50,
            "canny_high": 150
        },
        "sequencer": {
            "default_sequence_dir": "sequences",
            "auto_save_recording": True,
            "playback_speed": 1.0
        },
        "gui": {
            "theme": "default",
            "console_max_lines": 1000,
            "auto_scroll": True,
            "show_verbose": False
        },
        "paths": {
            "sequences_dir": "sequences",
            "calibrations_dir": "calibrations",
            "logs_dir": "logs"
        },
        "sensors": {
            "enabled": False,
            "mode": "direct",  # 'direct' or 'gateway'
            "gateway_type": "pi_zero",  # 'pi_zero' or 'pico'
            "config_file": "sensor_config.json",
            "calibration_samples": 200,
            "closed_loop_enabled": False,
            "max_position_error": 5.0,
            "correction_gain": 0.5,
            "update_rate": 10.0
        },
        "sensor_gateway": {
            "connection_mode": "serial",  # 'serial' or 'network'
            "serial_port": "/dev/ttyUSB1",
            "serial_baudrate": 115200,
            "network_host": "192.168.1.100",
            "network_port": 5555,
            "network_protocol": "tcp",  # 'tcp' or 'udp'
            "timeout": 1.0,
            "data_freshness_threshold": 1.0
        },
        "boards": {
            "current_board": "fly_super_8_pro",  # 'generic', 'fly_super_8_pro'
            "fly_super_8_pro": {
                "description": "Mellow FLY Super ♾️ Pro Board",
                "serial_port": "/dev/ttyUSB0",
                "baudrate": 115200,
                "requires_sensor_gateway": True,
                "i2c_exposed": False,
                "max_axes": 8,
                "supports_grbl": True
            },
            "generic": {
                "description": "Generic GRBL controller",
                "serial_port": "/dev/ttyUSB0",
                "baudrate": 115200,
                "requires_sensor_gateway": False,
                "i2c_exposed": True,
                "max_axes": 6,
                "supports_grbl": True
            }
        },
        "kinect": {
            "enabled": False,
            "version": "auto",  # 'auto', 'v1', 'v2', 'azure'
            "use_depth": True,
            "min_depth_mm": 500,
            "max_depth_mm": 4000,
            "depth_smoothing_window": 5,
            "min_object_area": 500,
            "max_object_area": 50000,
            "point_cloud_enabled": True,
            "save_point_clouds": False,
            "detection_mode": "color",  # 'color', 'contour', 'depth_clustering'
            "visualization": {
                "show_depth": True,
                "show_point_cloud": False,
                "depth_colormap": "JET",  # OpenCV colormap
                "overlay_detections": True
            }
        }
    }

    def __init__(self, config_file: str = "asgard_config.json"):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> bool:
        """
        Load configuration from file, create default if not exists

        Returns:
            True if loaded successfully
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)

                # Merge with defaults (in case new settings were added)
                self.config = self._merge_configs(self.DEFAULT_CONFIG, loaded_config)
                return True

            except Exception as e:
                print(f"Error loading config: {e}, using defaults")
                self.config = self.DEFAULT_CONFIG.copy()
                return False
        else:
            # Create default config
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()
            print(f"Created default config at {self.config_file}")
            return True

    def save(self) -> bool:
        """
        Save current configuration to file

        Returns:
            True if saved successfully
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation

        Args:
            key_path: Path to value (e.g., "serial.port" or "robot.default_feedrate")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any, auto_save: bool = True) -> bool:
        """
        Set a configuration value using dot notation

        Args:
            key_path: Path to value (e.g., "serial.port")
            value: Value to set
            auto_save: Automatically save config after setting

        Returns:
            True if set successfully
        """
        keys = key_path.split('.')
        config = self.config

        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value
        config[keys[-1]] = value

        if auto_save:
            return self.save()

        return True

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section

        Args:
            section: Section name (e.g., "serial", "robot")

        Returns:
            Dictionary of section settings
        """
        return self.config.get(section, {})

    def reset_to_defaults(self) -> bool:
        """
        Reset configuration to default values

        Returns:
            True if reset successful
        """
        self.config = self.DEFAULT_CONFIG.copy()
        return self.save()

    def ensure_directories(self):
        """
        Create necessary directories if they don't exist
        """
        paths = self.get_section('paths')
        for path_name, path_value in paths.items():
            Path(path_value).mkdir(parents=True, exist_ok=True)

    def _merge_configs(self, default: Dict, loaded: Dict) -> Dict:
        """
        Recursively merge loaded config with defaults

        Args:
            default: Default configuration
            loaded: Loaded configuration

        Returns:
            Merged configuration
        """
        result = default.copy()

        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def export_config(self, filepath: str) -> bool:
        """
        Export current config to a different file

        Args:
            filepath: Path to export file

        Returns:
            True if exported successfully
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting config: {e}")
            return False

    def import_config(self, filepath: str) -> bool:
        """
        Import config from file

        Args:
            filepath: Path to import file

        Returns:
            True if imported successfully
        """
        try:
            with open(filepath, 'r') as f:
                imported = json.load(f)

            self.config = self._merge_configs(self.DEFAULT_CONFIG, imported)
            return self.save()
        except Exception as e:
            print(f"Error importing config: {e}")
            return False

    def print_config(self, section: Optional[str] = None):
        """
        Print configuration (or specific section) in readable format

        Args:
            section: Optional section name to print
        """
        import pprint

        if section:
            print(f"\n=== {section.upper()} Configuration ===")
            pprint.pprint(self.get_section(section))
        else:
            print("\n=== Full Configuration ===")
            pprint.pprint(self.config)
        print()


# Global configuration instance
_global_config: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Get or create global configuration instance

    Returns:
        Global ConfigManager instance
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config


def init_config(config_file: str = "asgard_config.json") -> ConfigManager:
    """
    Initialize global configuration with custom file

    Args:
        config_file: Path to config file

    Returns:
        Configured ConfigManager instance
    """
    global _global_config
    _global_config = ConfigManager(config_file)
    return _global_config


# Convenience functions
def get_serial_config() -> Dict[str, Any]:
    """Get serial port configuration"""
    return get_config().get_section('serial')


def get_robot_config() -> Dict[str, Any]:
    """Get robot configuration"""
    return get_config().get_section('robot')


def get_vision_config() -> Dict[str, Any]:
    """Get vision configuration"""
    return get_config().get_section('vision')


def get_sequencer_config() -> Dict[str, Any]:
    """Get sequencer configuration"""
    return get_config().get_section('sequencer')


def get_sensor_config() -> Dict[str, Any]:
    """Get sensor configuration"""
    return get_config().get_section('sensors')


def get_sensor_gateway_config() -> Dict[str, Any]:
    """Get sensor gateway configuration"""
    return get_config().get_section('sensor_gateway')


def get_board_config(board_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get board configuration

    Args:
        board_name: Specific board name, or None for current board

    Returns:
        Board configuration dictionary
    """
    config = get_config()
    boards = config.get_section('boards')

    if board_name is None:
        board_name = boards.get('current_board', 'fly_super_8_pro')

    return boards.get(board_name, {})


def set_current_board(board_name: str) -> bool:
    """
    Set the current board configuration

    Args:
        board_name: Name of board profile ('fly_super_8_pro', 'generic')

    Returns:
        True if set successfully
    """
    return get_config().set('boards.current_board', board_name)


def is_sensor_gateway_required() -> bool:
    """
    Check if current board requires sensor gateway

    Returns:
        True if sensor gateway is required
    """
    board_config = get_board_config()
    return board_config.get('requires_sensor_gateway', False)


def get_kinect_config() -> Dict[str, Any]:
    """Get Kinect camera configuration"""
    return get_config().get_section('kinect')


def is_kinect_enabled() -> bool:
    """Check if Kinect depth camera is enabled"""
    kinect_config = get_kinect_config()
    return kinect_config.get('enabled', False)


if __name__ == '__main__':
    # Demo/test configuration system
    print("Configuration Manager Demo")
    print("=" * 50)

    config = ConfigManager("test_config.json")

    # Show current config
    config.print_config()

    # Get specific values
    print(f"Serial port: {config.get('serial.port')}")
    print(f"Default feedrate: {config.get('robot.default_feedrate')}")
    print(f"Camera index: {config.get('vision.camera_index')}")

    # Set values
    config.set('serial.port', '/dev/ttyACM0')
    config.set('robot.default_feedrate', 600)

    print("\nAfter modifications:")
    print(f"Serial port: {config.get('serial.port')}")
    print(f"Default feedrate: {config.get('robot.default_feedrate')}")

    # Ensure directories exist
    config.ensure_directories()
    print("\n✓ Directories created/verified")

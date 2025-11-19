#!/usr/bin/env python3
"""
Plugin Base Classes for Thor Robotic Arm

This module defines the base classes and interfaces for creating plugins
for the Asgard Enhanced GUI. All plugins must inherit from the Plugin class.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import QWidget


class PluginMetadata:
    """Metadata for a plugin"""
    def __init__(self, name: str, version: str, author: str, description: str):
        self.name = name
        self.version = version
        self.author = author
        self.description = description


class Plugin(ABC):
    """
    Base class for all Asgard Enhanced plugins.

    Plugins can:
    - Add custom UI tabs
    - Hook into robot events (movement, sensor updates)
    - Access the robot controller and kinematics
    - Add custom menu items
    - Process vision data

    Example:
        class MyPlugin(Plugin):
            def __init__(self):
                super().__init__()
                self.metadata = PluginMetadata(
                    name="My Plugin",
                    version="1.0.0",
                    author="Your Name",
                    description="Does cool stuff"
                )

            def initialize(self, gui_app):
                self.gui = gui_app
                self.robot = gui_app.robot
                print(f"{self.metadata.name} initialized!")

            def create_widget(self):
                # Return a QWidget for your plugin's UI
                return MyCustomWidget()
    """

    def __init__(self):
        self.metadata: Optional[PluginMetadata] = None
        self.gui = None  # Will be set by plugin manager
        self.robot = None  # Will be set by plugin manager
        self.enabled = True

    @abstractmethod
    def initialize(self, gui_app) -> bool:
        """
        Initialize the plugin with access to the main GUI application.

        Args:
            gui_app: The main AsgardEnhanced GUI application instance

        Returns:
            True if initialization succeeded, False otherwise

        This is called when the plugin is loaded. Store references to the
        GUI, robot controller, kinematics, etc. here.
        """
        pass

    def create_widget(self) -> Optional[QWidget]:
        """
        Create and return a QWidget for the plugin's UI.

        Returns:
            A QWidget that will be added as a tab, or None if no UI is needed

        This is optional. If your plugin has a GUI, return a QWidget here.
        The widget will be added as a tab in the main interface.
        """
        return None

    def on_robot_connected(self):
        """Called when the robot connects"""
        pass

    def on_robot_disconnected(self):
        """Called when the robot disconnects"""
        pass

    def on_joint_moved(self, joint_id: str, angle: float):
        """
        Called when a joint moves.

        Args:
            joint_id: Joint identifier ('A', 'B', 'D', 'X', 'Y', 'Z')
            angle: New angle in degrees
        """
        pass

    def on_kinect_frame(self, rgb_frame, depth_frame):
        """
        Called when a new Kinect frame is available.

        Args:
            rgb_frame: RGB image (numpy array)
            depth_frame: Depth image (numpy array)
        """
        pass

    def on_sensor_update(self, joint_id: str, sensor_data: Dict[str, Any]):
        """
        Called when sensor data is updated.

        Args:
            joint_id: Joint identifier
            sensor_data: Dictionary with sensor readings
        """
        pass

    def shutdown(self):
        """
        Called when the plugin is being unloaded or the application is closing.

        Use this to clean up resources, close connections, save state, etc.
        """
        pass

    def get_settings_widget(self) -> Optional[QWidget]:
        """
        Return a widget for plugin settings/configuration.

        Returns:
            A QWidget for settings, or None if no settings are needed
        """
        return None

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        return self.metadata if self.metadata else PluginMetadata(
            name=self.__class__.__name__,
            version="0.0.0",
            author="Unknown",
            description="No description provided"
        )


class VisionPlugin(Plugin):
    """
    Specialized plugin for computer vision tasks.

    Vision plugins have additional methods for processing camera frames
    and can draw overlays on the video feed.
    """

    def process_frame(self, frame):
        """
        Process a camera frame and return the result.

        Args:
            frame: Input frame (numpy array)

        Returns:
            Processed frame with any overlays/annotations
        """
        return frame

    def detect_objects(self, frame) -> List[Dict[str, Any]]:
        """
        Detect objects in the frame.

        Args:
            frame: Input frame (numpy array)

        Returns:
            List of detected objects with bounding boxes and labels
        """
        return []


class SequencePlugin(Plugin):
    """
    Specialized plugin for action sequences and automation.

    Sequence plugins can define custom movement patterns and automated tasks.
    """

    def get_sequences(self) -> Dict[str, callable]:
        """
        Return a dictionary of sequence names to functions.

        Returns:
            Dict mapping sequence names to callable functions
        """
        return {}

    def execute_sequence(self, sequence_name: str, **kwargs):
        """
        Execute a named sequence.

        Args:
            sequence_name: Name of the sequence to execute
            **kwargs: Additional parameters for the sequence
        """
        sequences = self.get_sequences()
        if sequence_name in sequences:
            sequences[sequence_name](**kwargs)

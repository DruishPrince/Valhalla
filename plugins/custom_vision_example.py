#!/usr/bin/env python3
"""
Custom Vision Example Plugin

This plugin demonstrates how to create a vision processing plugin
that processes camera frames and displays results.
"""

from plugin_base import VisionPlugin, PluginMetadata
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QCheckBox, QSpinBox, QGroupBox)
import cv2
import numpy as np


class CustomVisionPlugin(VisionPlugin):
    """
    Example vision plugin that performs edge detection on Kinect frames.
    """

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="Custom Vision Example",
            version="1.0.0",
            author="Thor Robotics",
            description="Example plugin showing custom vision processing with edge detection"
        )
        self.edge_detection_enabled = False
        self.canny_threshold1 = 100
        self.canny_threshold2 = 200

    def initialize(self, gui_app) -> bool:
        """Initialize the plugin"""
        self.gui = gui_app
        self.robot = gui_app.robot
        print("[CustomVision] Plugin initialized")
        return True

    def create_widget(self):
        """Create the plugin's UI widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Title
        title = QLabel("<h2>Custom Vision Processing</h2>")
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "This plugin demonstrates custom vision processing. "
            "It applies Canny edge detection to the Kinect RGB feed."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Controls group
        controls_group = QGroupBox("Edge Detection Controls")
        controls_layout = QVBoxLayout(controls_group)

        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable Edge Detection")
        self.enable_checkbox.setChecked(self.edge_detection_enabled)
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)
        controls_layout.addWidget(self.enable_checkbox)

        # Threshold 1
        threshold1_layout = QHBoxLayout()
        threshold1_layout.addWidget(QLabel("Threshold 1:"))
        self.threshold1_spin = QSpinBox()
        self.threshold1_spin.setRange(0, 500)
        self.threshold1_spin.setValue(self.canny_threshold1)
        self.threshold1_spin.valueChanged.connect(self.on_threshold1_changed)
        threshold1_layout.addWidget(self.threshold1_spin)
        threshold1_layout.addStretch()
        controls_layout.addLayout(threshold1_layout)

        # Threshold 2
        threshold2_layout = QHBoxLayout()
        threshold2_layout.addWidget(QLabel("Threshold 2:"))
        self.threshold2_spin = QSpinBox()
        self.threshold2_spin.setRange(0, 500)
        self.threshold2_spin.setValue(self.canny_threshold2)
        self.threshold2_spin.valueChanged.connect(self.on_threshold2_changed)
        threshold2_layout.addWidget(self.threshold2_spin)
        threshold2_layout.addStretch()
        controls_layout.addLayout(threshold2_layout)

        layout.addWidget(controls_group)

        # Info label
        info = QLabel(
            "<b>Note:</b> This plugin processes Kinect frames when enabled. "
            "Connect a Kinect to see the edge detection in action."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info)

        layout.addStretch()

        return widget

    def on_enable_changed(self, state):
        """Handle enable checkbox change"""
        self.edge_detection_enabled = (state == 2)  # Qt.Checked == 2
        print(f"[CustomVision] Edge detection {'enabled' if self.edge_detection_enabled else 'disabled'}")

    def on_threshold1_changed(self, value):
        """Handle threshold 1 change"""
        self.canny_threshold1 = value

    def on_threshold2_changed(self, value):
        """Handle threshold 2 change"""
        self.canny_threshold2 = value

    def on_kinect_frame(self, rgb_frame, depth_frame):
        """
        Process Kinect frames.

        This is called whenever a new Kinect frame is available.
        You can process the frame and do something with the results.
        """
        if not self.edge_detection_enabled or rgb_frame is None:
            return

        # Apply edge detection
        processed_frame = self.process_frame(rgb_frame)

        # Here you could:
        # - Display the processed frame in a custom window
        # - Send commands to the robot based on what you detect
        # - Store the results for later analysis
        # - etc.

    def process_frame(self, frame):
        """
        Apply edge detection to the frame.

        Args:
            frame: Input RGB frame

        Returns:
            Processed frame with edge detection overlay
        """
        if frame is None:
            return frame

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Canny edge detection
        edges = cv2.Canny(blurred, self.canny_threshold1, self.canny_threshold2)

        # Convert edges back to color for overlay
        edges_color = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        # Create overlay (blend original with edges)
        overlay = cv2.addWeighted(frame, 0.7, edges_color, 0.3, 0)

        return overlay

    def detect_objects(self, frame):
        """
        Example object detection method.

        In a real plugin, you might use this to detect specific objects,
        colors, shapes, etc. and return their positions.
        """
        # This is just a placeholder
        # In a real implementation, you might:
        # - Use color segmentation to find objects
        # - Use contour detection to find shapes
        # - Use a trained model for object recognition
        # - etc.

        objects = []
        # ... your detection logic here ...
        return objects

    def shutdown(self):
        """Called when plugin is being unloaded"""
        print("[CustomVision] Plugin shutting down")

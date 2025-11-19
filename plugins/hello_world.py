#!/usr/bin/env python3
"""
Hello World Example Plugin

This is a simple example plugin that demonstrates the basic plugin structure.
It adds a custom UI tab and responds to robot events.
"""

from plugin_base import Plugin, PluginMetadata
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit


class HelloWorldPlugin(Plugin):
    """
    A simple example plugin that shows how to create a plugin with UI.
    """

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="Hello World",
            version="1.0.0",
            author="Thor Robotics",
            description="A simple example plugin demonstrating the plugin API"
        )
        self.log_widget = None

    def initialize(self, gui_app) -> bool:
        """Initialize the plugin"""
        self.gui = gui_app
        self.robot = gui_app.robot
        self.log("Hello World plugin initialized!")
        return True

    def create_widget(self):
        """Create the plugin's UI widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Title
        title = QLabel("<h2>Hello World Plugin</h2>")
        layout.addWidget(title)

        # Description
        desc = QLabel("This is an example plugin. It logs robot events and has some buttons.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Button
        test_btn = QPushButton("Click Me!")
        test_btn.clicked.connect(self.on_button_clicked)
        layout.addWidget(test_btn)

        # Log output
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumHeight(200)
        layout.addWidget(QLabel("Event Log:"))
        layout.addWidget(self.log_widget)

        layout.addStretch()

        return widget

    def on_button_clicked(self):
        """Handle button click"""
        self.log("Button clicked!")

    def on_robot_connected(self):
        """Called when robot connects"""
        self.log("🤖 Robot connected!")

    def on_robot_disconnected(self):
        """Called when robot disconnects"""
        self.log("🔌 Robot disconnected")

    def on_joint_moved(self, joint_id: str, angle: float):
        """Called when a joint moves"""
        self.log(f"Joint {joint_id} moved to {angle:.1f}°")

    def log(self, message: str):
        """Add a message to the log"""
        if self.log_widget:
            self.log_widget.append(message)
        print(f"[HelloWorld] {message}")

    def shutdown(self):
        """Called when plugin is being unloaded"""
        self.log("Plugin shutting down...")

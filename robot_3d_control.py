#!/usr/bin/env python3
"""
3D Robot Control Application

Standalone application for controlling Thor robot arm with 3D visualization
"""

import sys
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QGroupBox, QSlider,
                             QDoubleSpinBox, QCheckBox, QTextEdit, QSplitter)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

from kinematics import ThorKinematics, Point3D
from robot_controller import RobotController, MovementType
import serial_port_finder as spf


class MplCanvas3D(FigureCanvasQTAgg):
    """Matplotlib 3D canvas for PyQt5"""

    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111, projection='3d')
        super().__init__(self.fig)

        self.setParent(parent)

        # Drawing elements
        self.arm_line = None
        self.joint_scatter = None
        self.target_scatter = None

    def setup_plot(self, bounds):
        """Setup 3D plot appearance"""
        max_range = max(bounds['x'][1], bounds['y'][1], bounds['z'][1])

        self.axes.set_xlim([-max_range, max_range])
        self.axes.set_ylim([-max_range, max_range])
        self.axes.set_zlim([0, max_range])

        self.axes.set_xlabel('X (mm)')
        self.axes.set_ylabel('Y (mm)')
        self.axes.set_zlabel('Z (mm)')
        self.axes.set_title('Robot Arm 3D View')
        self.axes.grid(True, alpha=0.3)

        # Draw workspace
        self._draw_workspace(max_range)

    def _draw_workspace(self, radius):
        """Draw workspace hemisphere"""
        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, np.pi / 2, 15)
        x = radius * np.outer(np.cos(u), np.sin(v))
        y = radius * np.outer(np.sin(u), np.sin(v))
        z = radius * np.outer(np.ones(np.size(u)), np.cos(v))

        self.axes.plot_surface(x, y, z, alpha=0.1, color='cyan')

    def update_arm(self, joint_positions, target_pos=None):
        """Update arm visualization"""
        xs = [p.x for p in joint_positions]
        ys = [p.y for p in joint_positions]
        zs = [p.z for p in joint_positions]

        # Clear previous
        if self.arm_line:
            self.arm_line.remove()
        if self.joint_scatter:
            self.joint_scatter.remove()

        # Draw arm
        self.arm_line = self.axes.plot(xs, ys, zs,
                                       'o-', linewidth=3, markersize=8,
                                       color='blue')[0]

        # End effector
        self.joint_scatter = self.axes.scatter([xs[-1]], [ys[-1]], [zs[-1]],
                                              c='green', s=200, marker='o',
                                              edgecolors='darkgreen', linewidth=2)

        # Target
        if target_pos:
            if self.target_scatter:
                self.target_scatter.remove()
            self.target_scatter = self.axes.scatter([target_pos.x], [target_pos.y], [target_pos.z],
                                                   c='red', s=300, marker='*',
                                                   edgecolors='darkred', linewidth=2)

        self.draw()


class Robot3DControl(QMainWindow):
    """Main 3D robot control application"""

    def __init__(self):
        super().__init__()

        self.kinematics = ThorKinematics()
        self.robot = RobotController()
        self.target_point = None

        self.init_ui()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_visualization)
        self.update_timer.start(100)  # 10 Hz update

    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle('Thor Robot 3D Control')
        self.setGeometry(100, 100, 1400, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left side: 3D view
        left_widget = self._create_3d_view()
        splitter.addWidget(left_widget)

        # Right side: Controls
        right_widget = self._create_controls()
        splitter.addWidget(right_widget)

        # Set splitter sizes
        splitter.setSizes([800, 600])

        main_layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage('Ready')

        # Initial visualization
        self.update_visualization()

    def _create_3d_view(self):
        """Create 3D visualization widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Canvas
        self.canvas = MplCanvas3D(widget, width=8, height=6)
        bounds = self.kinematics.get_workspace_bounds()
        self.canvas.setup_plot(bounds)

        # Toolbar
        toolbar = NavigationToolbar2QT(self.canvas, widget)

        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)

        return widget

    def _create_controls(self):
        """Create control panel widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Connection controls
        conn_group = self._create_connection_group()
        layout.addWidget(conn_group)

        # Joint controls
        joint_group = self._create_joint_controls()
        layout.addWidget(joint_group)

        # Target controls
        target_group = self._create_target_controls()
        layout.addWidget(target_group)

        # Action buttons
        action_group = self._create_action_buttons()
        layout.addWidget(action_group)

        # Console
        console_group = self._create_console()
        layout.addWidget(console_group)

        layout.addStretch()

        return widget

    def _create_connection_group(self):
        """Create connection controls"""
        group = QGroupBox("Robot Connection")
        layout = QVBoxLayout()

        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))

        self.port_combo = QtWidgets.QComboBox()
        self.refresh_ports()
        port_layout.addWidget(self.port_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_ports)
        port_layout.addWidget(refresh_btn)

        layout.addLayout(port_layout)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)

        # Status
        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("color: red")
        layout.addWidget(self.connection_status)

        group.setLayout(layout)
        return group

    def _create_joint_controls(self):
        """Create joint angle sliders"""
        group = QGroupBox("Joint Control (Degrees)")
        layout = QVBoxLayout()

        self.joint_sliders = {}
        self.joint_spinboxes = {}

        joints = [
            ('A', 'Base', -180, 180),
            ('B', 'Shoulder', -90, 90),
            ('D', 'Elbow', -90, 90),
            ('X', 'Wrist Pitch', -90, 90),
            ('Y', 'Wrist Roll', -90, 90),
        ]

        for key, label, min_val, max_val in joints:
            joint_layout = QHBoxLayout()

            # Label
            joint_layout.addWidget(QLabel(f"{label}:"))

            # Slider
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(min_val)
            slider.setMaximum(max_val)
            slider.setValue(0)
            slider.valueChanged.connect(lambda v, k=key: self.on_slider_changed(k, v))
            joint_layout.addWidget(slider)

            # Spinbox
            spinbox = QDoubleSpinBox()
            spinbox.setMinimum(min_val)
            spinbox.setMaximum(max_val)
            spinbox.setValue(0)
            spinbox.setSingleStep(1.0)
            spinbox.valueChanged.connect(lambda v, k=key: self.on_spinbox_changed(k, v))
            joint_layout.addWidget(spinbox)

            self.joint_sliders[key] = slider
            self.joint_spinboxes[key] = spinbox

            layout.addLayout(joint_layout)

        group.setLayout(layout)
        return group

    def _create_target_controls(self):
        """Create target position controls"""
        group = QGroupBox("Target Position (mm)")
        layout = QVBoxLayout()

        self.target_spinboxes = {}

        for axis in ['X', 'Y', 'Z']:
            axis_layout = QHBoxLayout()
            axis_layout.addWidget(QLabel(f"{axis}:"))

            spinbox = QDoubleSpinBox()
            spinbox.setMinimum(-500)
            spinbox.setMaximum(500)
            spinbox.setValue(200 if axis == 'X' else 100 if axis == 'Y' else 200)
            spinbox.setSingleStep(10.0)
            axis_layout.addWidget(spinbox)

            self.target_spinboxes[axis] = spinbox
            layout.addLayout(axis_layout)

        # Set target button
        set_target_btn = QPushButton("Set Target (IK)")
        set_target_btn.clicked.connect(self.set_target_from_spinboxes)
        layout.addWidget(set_target_btn)

        # Reachable indicator
        self.reachable_label = QLabel("")
        layout.addWidget(self.reachable_label)

        group.setLayout(layout)
        return group

    def _create_action_buttons(self):
        """Create action buttons"""
        group = QGroupBox("Actions")
        layout = QVBoxLayout()

        # Send to robot
        send_btn = QPushButton("Send to Robot")
        send_btn.clicked.connect(self.send_to_robot)
        layout.addWidget(send_btn)

        # Home
        home_btn = QPushButton("Home Robot")
        home_btn.clicked.connect(self.home_robot)
        layout.addWidget(home_btn)

        # Zero position
        zero_btn = QPushButton("Zero Position")
        zero_btn.clicked.connect(self.zero_position)
        layout.addWidget(zero_btn)

        group.setLayout(layout)
        return group

    def _create_console(self):
        """Create console output"""
        group = QGroupBox("Console")
        layout = QVBoxLayout()

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        layout.addWidget(self.console)

        group.setLayout(layout)
        return group

    def refresh_ports(self):
        """Refresh serial port list"""
        self.port_combo.clear()
        ports = spf.serial_ports()
        self.port_combo.addItems(ports)

    def toggle_connection(self):
        """Connect/disconnect robot"""
        if self.robot.is_connected():
            self.robot.disconnect()
            self.connect_btn.setText("Connect")
            self.connection_status.setText("Disconnected")
            self.connection_status.setStyleSheet("color: red")
            self.log("Disconnected from robot")
        else:
            port = self.port_combo.currentText()
            if port and self.robot.connect(port, 115200):
                self.connect_btn.setText("Disconnect")
                self.connection_status.setText(f"Connected to {port}")
                self.connection_status.setStyleSheet("color: green")
                self.log(f"Connected to robot on {port}")
            else:
                self.log("Failed to connect to robot")

    def on_slider_changed(self, joint_key, value):
        """Handle slider value change"""
        self.joint_spinboxes[joint_key].setValue(value)
        self.kinematics.joint_angles[joint_key] = value

        # Handle coupled joints
        if joint_key == 'B':
            self.kinematics.joint_angles['C'] = value

        self.update_visualization()

    def on_spinbox_changed(self, joint_key, value):
        """Handle spinbox value change"""
        self.joint_sliders[joint_key].setValue(int(value))

    def set_target_from_spinboxes(self):
        """Set target position from spinboxes and solve IK"""
        target = Point3D(
            self.target_spinboxes['X'].value(),
            self.target_spinboxes['Y'].value(),
            self.target_spinboxes['Z'].value()
        )

        if self.kinematics.is_reachable(target):
            self.log(f"Solving IK for target: ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})")

            solution = self.kinematics.inverse_kinematics(target)

            if solution:
                self.target_point = target

                # Update sliders
                for key, value in solution.items():
                    if key in self.joint_spinboxes:
                        self.joint_spinboxes[key].setValue(value)

                self.log(f"IK solution found: {solution}")
                self.reachable_label.setText("✓ Target reachable")
                self.reachable_label.setStyleSheet("color: green")
            else:
                self.log("IK solver failed to converge")
                self.reachable_label.setText("✗ IK failed")
                self.reachable_label.setStyleSheet("color: orange")
        else:
            self.log(f"Target out of reach: ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})")
            self.reachable_label.setText("✗ Out of reach")
            self.reachable_label.setStyleSheet("color: red")

    def update_visualization(self):
        """Update 3D visualization"""
        # Calculate current pose
        end_pos, joint_positions = self.kinematics.forward_kinematics()

        # Update canvas
        self.canvas.update_arm(joint_positions, self.target_point)

        # Update status bar
        self.statusBar().showMessage(
            f"End Effector: ({end_pos.x:.1f}, {end_pos.y:.1f}, {end_pos.z:.1f}) mm"
        )

    def send_to_robot(self):
        """Send current angles to robot"""
        if not self.robot.is_connected():
            self.log("Robot not connected")
            return

        angles = self.kinematics.joint_angles
        self.log(f"Sending to robot: {angles}")

        self.robot.move_all_joints(angles, MovementType.G1_LINEAR, feedrate=300)
        self.log("Command sent")

    def home_robot(self):
        """Home the robot"""
        if not self.robot.is_connected():
            self.log("Robot not connected")
            return

        self.log("Homing robot...")
        self.robot.send_homing_command()

    def zero_position(self):
        """Move to zero position"""
        # Update sliders
        for key in self.joint_spinboxes.keys():
            self.joint_spinboxes[key].setValue(0)

    def log(self, message):
        """Add message to console"""
        self.console.append(message)


def main():
    """Main entry point"""
    app = QtWidgets.QApplication(sys.argv)
    window = Robot3DControl()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

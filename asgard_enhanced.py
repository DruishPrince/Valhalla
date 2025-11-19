#!/usr/bin/env python3
"""
Asgard Enhanced - Modern GUI for Thor Robotic Arm Control

Enhanced version with integrated support for:
- Kinect RGB-D depth sensing
- ADXL345 sensor feedback
- Sensor gateway (Pi Zero 2W / Pico)
- 3D visualization and manipulation
- Advanced computer vision
- Action sequencing and playback

This is a complete rewrite of the original Asgard GUI with a modern,
tabbed interface and integration of all advanced features.
"""

import sys
import time
import cv2
import numpy as np
from typing import Optional, Dict, List

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QSlider, QSpinBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QGroupBox, QGridLayout, QCheckBox, QLineEdit,
    QSplitter, QFileDialog, QMessageBox, QProgressBar, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QFont

# Import our enhanced modules
from robot_controller import RobotController, MovementType
from kinect_interface import KinectInterface, visualize_depth
from vision_controller_3d import VisionController3D
from sensor_gateway_client import SensorGatewayClient, GatewayConfig
from sensor_integration import SensorIntegration
from action_sequencer import ActionSequencer
from kinematics import ThorKinematics
from config_manager import (
    get_config, get_serial_config, get_kinect_config,
    get_sensor_gateway_config, get_board_config
)


class ImageDisplayWidget(QLabel):
    """Widget for displaying camera images"""

    def __init__(self, width=640, height=480):
        super().__init__()
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self.setScaledContents(True)
        self.setStyleSheet("border: 1px solid #888; background-color: #000;")
        self.setText("No Image")
        self.setAlignment(Qt.AlignCenter)

    def update_image(self, image: np.ndarray):
        """Update displayed image from numpy array"""
        if image is None:
            return

        # Convert BGR to RGB
        if len(image.shape) == 3:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            # Grayscale
            h, w = image.shape
            bytes_per_line = w
            qt_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_Grayscale8)

        self.setPixmap(QPixmap.fromImage(qt_image))


class KinectWorker(QThread):
    """Background thread for Kinect camera processing"""

    frame_ready = pyqtSignal(object)  # RGB-D frame
    error_occurred = pyqtSignal(str)

    def __init__(self, kinect: KinectInterface):
        super().__init__()
        self.kinect = kinect
        self.running = False

    def run(self):
        """Capture frames continuously"""
        self.running = True
        while self.running:
            try:
                frame = self.kinect.get_rgbd_frame()
                if frame:
                    self.frame_ready.emit(frame)
                time.sleep(0.033)  # ~30 FPS
            except Exception as e:
                self.error_occurred.emit(str(e))
                break

    def stop(self):
        """Stop capture thread"""
        self.running = False


class AsgardEnhanced(QMainWindow):
    """
    Enhanced Asgard GUI with full feature integration
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Asgard Enhanced - Thor Robotic Arm Control")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize components
        self.robot = RobotController()
        self.kinect: Optional[KinectInterface] = None
        self.kinect_worker: Optional[KinectWorker] = None
        self.vision_3d: Optional[VisionController3D] = None
        self.sensor_gateway: Optional[SensorGatewayClient] = None
        self.sensor_integration: Optional[SensorIntegration] = None
        self.sequencer = ActionSequencer(self.robot)
        self.kinematics = ThorKinematics()

        # Current state
        self.current_kinect_frame = None
        self.detected_objects_3d = []
        self.ik_solution: Optional[Dict[str, float]] = None

        # Load configuration
        self.config = get_config()

        # Build UI
        self.init_ui()

        # Setup update timers
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(100)  # 10 Hz

        # Apply initial config
        self.apply_configuration()

    def init_ui(self):
        """Initialize user interface"""
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Add tabs
        self.tabs.addTab(self.create_control_tab(), "Robot Control")
        self.tabs.addTab(self.create_kinect_tab(), "Kinect Vision")
        self.tabs.addTab(self.create_sensors_tab(), "Sensors")
        self.tabs.addTab(self.create_sequencer_tab(), "Action Sequencer")
        self.tabs.addTab(self.create_config_tab(), "Configuration")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.robot_status_label = QLabel("Robot: Disconnected")
        self.kinect_status_label = QLabel("Kinect: Not Active")
        self.sensors_status_label = QLabel("Sensors: Not Active")

        self.status_bar.addPermanentWidget(self.robot_status_label)
        self.status_bar.addPermanentWidget(QLabel("|"))
        self.status_bar.addPermanentWidget(self.kinect_status_label)
        self.status_bar.addPermanentWidget(QLabel("|"))
        self.status_bar.addPermanentWidget(self.sensors_status_label)

    def create_control_tab(self) -> QWidget:
        """Create robot control tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Connection group
        conn_group = QGroupBox("Connection")
        conn_layout = QHBoxLayout(conn_group)

        self.port_combo = QComboBox()
        self.port_combo.addItems(self.find_serial_ports())
        self.refresh_ports_btn = QPushButton("Refresh")
        self.refresh_ports_btn.clicked.connect(self.refresh_serial_ports)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_robot_connection)

        conn_layout.addWidget(QLabel("Port:"))
        conn_layout.addWidget(self.port_combo)
        conn_layout.addWidget(self.refresh_ports_btn)
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addStretch()

        layout.addWidget(conn_group)

        # Joint control
        joint_group = QGroupBox("Joint Control")
        joint_layout = QGridLayout(joint_group)

        self.joint_controls = {}
        joints = [('A', 'Base'), ('B', 'Shoulder'), ('D', 'Elbow'),
                  ('X', 'Wrist Pitch'), ('Y', 'Wrist Roll'), ('Z', 'Wrist Rotate')]

        for i, (joint_id, joint_name) in enumerate(joints):
            # Label
            joint_layout.addWidget(QLabel(f"{joint_name} ({joint_id}):"), i, 0)

            # Slider
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(-180)
            slider.setMaximum(180)
            slider.setValue(0)
            joint_layout.addWidget(slider, i, 1)

            # Spinbox
            spinbox = QDoubleSpinBox()
            spinbox.setMinimum(-180)
            spinbox.setMaximum(180)
            spinbox.setValue(0)
            spinbox.setSuffix("°")
            joint_layout.addWidget(spinbox, i, 2)

            # Go button
            go_btn = QPushButton("Go")
            go_btn.clicked.connect(lambda checked, j=joint_id: self.move_joint(j))
            joint_layout.addWidget(go_btn, i, 3)

            # Store controls
            self.joint_controls[joint_id] = {
                'slider': slider,
                'spinbox': spinbox,
                'button': go_btn
            }

            # Connect slider and spinbox
            slider.valueChanged.connect(spinbox.setValue)
            spinbox.valueChanged.connect(lambda v: slider.setValue(int(v)))

        layout.addWidget(joint_group)

        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)

        self.home_btn = QPushButton("Home All")
        self.home_btn.clicked.connect(self.home_robot)
        self.zero_btn = QPushButton("Zero Position")
        self.zero_btn.clicked.connect(self.zero_robot)
        self.move_all_btn = QPushButton("Move All Joints")
        self.move_all_btn.clicked.connect(self.move_all_joints)

        actions_layout.addWidget(self.home_btn)
        actions_layout.addWidget(self.zero_btn)
        actions_layout.addWidget(self.move_all_btn)
        actions_layout.addStretch()

        layout.addWidget(actions_group)

        # IK Positioning
        ik_group = QGroupBox("Inverse Kinematics Positioning")
        ik_layout = QGridLayout(ik_group)

        # Target position inputs
        ik_layout.addWidget(QLabel("Target Position (mm):"), 0, 0)

        ik_layout.addWidget(QLabel("X:"), 1, 0)
        self.ik_x_spin = QDoubleSpinBox()
        self.ik_x_spin.setMinimum(-1000)
        self.ik_x_spin.setMaximum(1000)
        self.ik_x_spin.setValue(200)
        self.ik_x_spin.setSuffix(" mm")
        ik_layout.addWidget(self.ik_x_spin, 1, 1)

        ik_layout.addWidget(QLabel("Y:"), 1, 2)
        self.ik_y_spin = QDoubleSpinBox()
        self.ik_y_spin.setMinimum(-1000)
        self.ik_y_spin.setMaximum(1000)
        self.ik_y_spin.setValue(0)
        self.ik_y_spin.setSuffix(" mm")
        ik_layout.addWidget(self.ik_y_spin, 1, 3)

        ik_layout.addWidget(QLabel("Z:"), 1, 4)
        self.ik_z_spin = QDoubleSpinBox()
        self.ik_z_spin.setMinimum(0)
        self.ik_z_spin.setMaximum(1000)
        self.ik_z_spin.setValue(200)
        self.ik_z_spin.setSuffix(" mm")
        ik_layout.addWidget(self.ik_z_spin, 1, 5)

        # Buttons
        self.ik_check_btn = QPushButton("Check Reachability")
        self.ik_check_btn.clicked.connect(self.check_ik_reachability)
        ik_layout.addWidget(self.ik_check_btn, 2, 0, 1, 2)

        self.ik_calculate_btn = QPushButton("Calculate IK")
        self.ik_calculate_btn.clicked.connect(self.calculate_ik_solution)
        ik_layout.addWidget(self.ik_calculate_btn, 2, 2, 1, 2)

        self.ik_move_btn = QPushButton("Move to Position")
        self.ik_move_btn.clicked.connect(self.move_to_ik_position)
        self.ik_move_btn.setEnabled(False)
        ik_layout.addWidget(self.ik_move_btn, 2, 4, 1, 2)

        # Status and solution display
        self.ik_status_label = QLabel("Status: Ready")
        ik_layout.addWidget(self.ik_status_label, 3, 0, 1, 6)

        self.ik_solution_text = QTextEdit()
        self.ik_solution_text.setReadOnly(True)
        self.ik_solution_text.setMaximumHeight(80)
        self.ik_solution_text.setPlaceholderText("IK solution will appear here...")
        ik_layout.addWidget(self.ik_solution_text, 4, 0, 1, 6)

        layout.addWidget(ik_group)

        # Console
        console_group = QGroupBox("Console")
        console_layout = QVBoxLayout(console_group)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setMaximumHeight(200)
        console_layout.addWidget(self.console_output)

        input_layout = QHBoxLayout()
        self.console_input = QLineEdit()
        self.console_input.setPlaceholderText("Enter G-code command...")
        self.console_input.returnPressed.connect(self.send_console_command)
        self.console_send_btn = QPushButton("Send")
        self.console_send_btn.clicked.connect(self.send_console_command)

        input_layout.addWidget(self.console_input)
        input_layout.addWidget(self.console_send_btn)
        console_layout.addLayout(input_layout)

        layout.addWidget(console_group)
        layout.addStretch()

        return tab

    def create_kinect_tab(self) -> QWidget:
        """Create Kinect vision tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Kinect control
        kinect_control_group = QGroupBox("Kinect Control")
        kinect_control_layout = QHBoxLayout(kinect_control_group)

        self.kinect_connect_btn = QPushButton("Connect Kinect")
        self.kinect_connect_btn.clicked.connect(self.toggle_kinect_connection)

        self.kinect_version_label = QLabel("Version: Not Connected")

        kinect_control_layout.addWidget(self.kinect_connect_btn)
        kinect_control_layout.addWidget(self.kinect_version_label)
        kinect_control_layout.addStretch()

        layout.addWidget(kinect_control_group)

        # Image display
        images_layout = QHBoxLayout()

        # RGB view
        rgb_group = QGroupBox("RGB Camera")
        rgb_layout = QVBoxLayout(rgb_group)
        self.kinect_rgb_display = ImageDisplayWidget(640, 480)
        rgb_layout.addWidget(self.kinect_rgb_display)
        images_layout.addWidget(rgb_group)

        # Depth view
        depth_group = QGroupBox("Depth Map")
        depth_layout = QVBoxLayout(depth_group)
        self.kinect_depth_display = ImageDisplayWidget(640, 480)
        depth_layout.addWidget(self.kinect_depth_display)
        images_layout.addWidget(depth_group)

        layout.addLayout(images_layout)

        # Detection controls
        detection_group = QGroupBox("3D Object Detection")
        detection_layout = QGridLayout(detection_group)

        detection_layout.addWidget(QLabel("Detection Mode:"), 0, 0)
        self.detection_mode_combo = QComboBox()
        self.detection_mode_combo.addItems(["Color", "Contour", "Depth Clustering"])
        detection_layout.addWidget(self.detection_mode_combo, 0, 1)

        self.detect_btn = QPushButton("Detect Objects")
        self.detect_btn.clicked.connect(self.detect_objects_3d)
        detection_layout.addWidget(self.detect_btn, 0, 2)

        self.clear_detect_btn = QPushButton("Clear")
        self.clear_detect_btn.clicked.connect(self.clear_detections)
        detection_layout.addWidget(self.clear_detect_btn, 0, 3)

        # Detection results
        self.detection_results = QTextEdit()
        self.detection_results.setReadOnly(True)
        self.detection_results.setMaximumHeight(150)
        detection_layout.addWidget(self.detection_results, 1, 0, 1, 4)

        layout.addWidget(detection_group)

        layout.addStretch()

        return tab

    def create_sensors_tab(self) -> QWidget:
        """Create sensors tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Gateway control
        gateway_group = QGroupBox("Sensor Gateway")
        gateway_layout = QGridLayout(gateway_group)

        gateway_layout.addWidget(QLabel("Gateway Type:"), 0, 0)
        self.gateway_type_combo = QComboBox()
        self.gateway_type_combo.addItems(["Pi Zero 2W", "Pico"])
        gateway_layout.addWidget(self.gateway_type_combo, 0, 1)

        gateway_layout.addWidget(QLabel("Connection:"), 1, 0)
        self.gateway_mode_combo = QComboBox()
        self.gateway_mode_combo.addItems(["Serial", "Network"])
        gateway_layout.addWidget(self.gateway_mode_combo, 1, 1)

        gateway_layout.addWidget(QLabel("Port/Host:"), 2, 0)
        self.gateway_port_input = QLineEdit()
        self.gateway_port_input.setPlaceholderText("COM4 or 192.168.1.100")
        gateway_layout.addWidget(self.gateway_port_input, 2, 1)

        self.gateway_connect_btn = QPushButton("Connect Gateway")
        self.gateway_connect_btn.clicked.connect(self.toggle_gateway_connection)
        gateway_layout.addWidget(self.gateway_connect_btn, 3, 0, 1, 2)

        layout.addWidget(gateway_group)

        # Sensor readings
        readings_group = QGroupBox("Sensor Readings")
        readings_layout = QVBoxLayout(readings_group)

        self.sensor_readings_text = QTextEdit()
        self.sensor_readings_text.setReadOnly(True)
        readings_layout.addWidget(self.sensor_readings_text)

        # Calibration
        calibrate_layout = QHBoxLayout()
        self.calibrate_all_btn = QPushButton("Calibrate All Sensors")
        self.calibrate_all_btn.clicked.connect(self.calibrate_sensors)
        calibrate_layout.addWidget(self.calibrate_all_btn)
        calibrate_layout.addStretch()
        readings_layout.addLayout(calibrate_layout)

        layout.addWidget(readings_group)

        # Closed-loop control
        closed_loop_group = QGroupBox("Closed-Loop Control")
        closed_loop_layout = QGridLayout(closed_loop_group)

        self.closed_loop_enable = QCheckBox("Enable Closed-Loop")
        closed_loop_layout.addWidget(self.closed_loop_enable, 0, 0, 1, 2)

        closed_loop_layout.addWidget(QLabel("Max Error:"), 1, 0)
        self.max_error_spin = QDoubleSpinBox()
        self.max_error_spin.setValue(5.0)
        self.max_error_spin.setSuffix("°")
        closed_loop_layout.addWidget(self.max_error_spin, 1, 1)

        closed_loop_layout.addWidget(QLabel("Correction Gain:"), 2, 0)
        self.correction_gain_spin = QDoubleSpinBox()
        self.correction_gain_spin.setMinimum(0.1)
        self.correction_gain_spin.setMaximum(1.0)
        self.correction_gain_spin.setSingleStep(0.1)
        self.correction_gain_spin.setValue(0.5)
        closed_loop_layout.addWidget(self.correction_gain_spin, 2, 1)

        layout.addWidget(closed_loop_group)
        layout.addStretch()

        return tab

    def create_sequencer_tab(self) -> QWidget:
        """Create action sequencer tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Recording controls
        record_group = QGroupBox("Recording")
        record_layout = QHBoxLayout(record_group)

        self.record_name_input = QLineEdit()
        self.record_name_input.setPlaceholderText("Sequence name...")

        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)

        self.save_sequence_btn = QPushButton("Save Sequence")
        self.save_sequence_btn.clicked.connect(self.save_sequence)
        self.save_sequence_btn.setEnabled(False)

        record_layout.addWidget(QLabel("Name:"))
        record_layout.addWidget(self.record_name_input)
        record_layout.addWidget(self.record_btn)
        record_layout.addWidget(self.save_sequence_btn)

        layout.addWidget(record_group)

        # Playback controls
        playback_group = QGroupBox("Playback")
        playback_layout = QVBoxLayout(playback_group)

        load_layout = QHBoxLayout()
        self.load_sequence_btn = QPushButton("Load Sequence")
        self.load_sequence_btn.clicked.connect(self.load_sequence)
        self.play_sequence_btn = QPushButton("Play Sequence")
        self.play_sequence_btn.clicked.connect(self.play_sequence)
        self.play_sequence_btn.setEnabled(False)

        load_layout.addWidget(self.load_sequence_btn)
        load_layout.addWidget(self.play_sequence_btn)
        load_layout.addStretch()
        playback_layout.addLayout(load_layout)

        # Sequence info
        self.sequence_info = QTextEdit()
        self.sequence_info.setReadOnly(True)
        playback_layout.addWidget(self.sequence_info)

        layout.addWidget(playback_group)
        layout.addStretch()

        return tab

    def create_config_tab(self) -> QWidget:
        """Create configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Board selection
        board_group = QGroupBox("Controller Board")
        board_layout = QHBoxLayout(board_group)

        board_layout.addWidget(QLabel("Board Type:"))
        self.board_combo = QComboBox()
        self.board_combo.addItems(["Generic GRBL", "FLY Super ♾️ Pro"])
        board_layout.addWidget(self.board_combo)
        board_layout.addStretch()

        layout.addWidget(board_group)

        # Robot Dimensions Configuration
        dimensions_group = QGroupBox("Robot Physical Dimensions (for IK)")
        dimensions_layout = QGridLayout(dimensions_group)

        dimensions_layout.addWidget(QLabel("Measure your robot and input dimensions in millimeters:"), 0, 0, 1, 4)

        # Dimension inputs
        dim_row = 1
        self.dim_base_height = QDoubleSpinBox()
        self.dim_base_height.setRange(0, 500)
        self.dim_base_height.setSuffix(" mm")
        self.dim_base_height.setValue(self.kinematics.params['base_height'])
        dimensions_layout.addWidget(QLabel("Base Height:"), dim_row, 0)
        dimensions_layout.addWidget(self.dim_base_height, dim_row, 1)

        self.dim_shoulder_offset = QDoubleSpinBox()
        self.dim_shoulder_offset.setRange(0, 500)
        self.dim_shoulder_offset.setSuffix(" mm")
        self.dim_shoulder_offset.setValue(self.kinematics.params['shoulder_offset'])
        dimensions_layout.addWidget(QLabel("Shoulder Offset:"), dim_row, 2)
        dimensions_layout.addWidget(self.dim_shoulder_offset, dim_row, 3)

        dim_row += 1
        self.dim_upper_arm = QDoubleSpinBox()
        self.dim_upper_arm.setRange(0, 1000)
        self.dim_upper_arm.setSuffix(" mm")
        self.dim_upper_arm.setValue(self.kinematics.params['upper_arm'])
        dimensions_layout.addWidget(QLabel("Upper Arm Length:"), dim_row, 0)
        dimensions_layout.addWidget(self.dim_upper_arm, dim_row, 1)

        self.dim_forearm = QDoubleSpinBox()
        self.dim_forearm.setRange(0, 1000)
        self.dim_forearm.setSuffix(" mm")
        self.dim_forearm.setValue(self.kinematics.params['forearm'])
        dimensions_layout.addWidget(QLabel("Forearm Length:"), dim_row, 2)
        dimensions_layout.addWidget(self.dim_forearm, dim_row, 3)

        dim_row += 1
        self.dim_wrist_length = QDoubleSpinBox()
        self.dim_wrist_length.setRange(0, 500)
        self.dim_wrist_length.setSuffix(" mm")
        self.dim_wrist_length.setValue(self.kinematics.params['wrist_length'])
        dimensions_layout.addWidget(QLabel("Wrist to End Effector:"), dim_row, 0)
        dimensions_layout.addWidget(self.dim_wrist_length, dim_row, 1)

        apply_dims_btn = QPushButton("Apply Dimensions")
        apply_dims_btn.clicked.connect(self.apply_robot_dimensions)
        dimensions_layout.addWidget(apply_dims_btn, dim_row, 2, 1, 2)

        layout.addWidget(dimensions_group)

        # Joint Limits Configuration
        limits_group = QGroupBox("Joint Rotation Limits")
        limits_layout = QGridLayout(limits_group)

        limits_layout.addWidget(QLabel("Joint"), 0, 0)
        limits_layout.addWidget(QLabel("Min Angle (°)"), 0, 1)
        limits_layout.addWidget(QLabel("Max Angle (°)"), 0, 2)
        limits_layout.addWidget(QLabel("Can Rotate 360°?"), 0, 3)

        self.joint_limit_controls = {}
        joints_for_limits = [
            ('A', 'Base Rotation', -180, 180, True),
            ('B', 'Shoulder', -90, 90, False),
            ('C', 'Linked (auto)', -90, 90, False),
            ('D', 'Elbow', -90, 90, False),
            ('X', 'Wrist Pitch', -90, 90, False),
            ('Y', 'Wrist Roll', -180, 180, True),
            ('Z', 'End Effector', -180, 180, True),
        ]

        for i, (joint_id, joint_name, default_min, default_max, can_full_rotate) in enumerate(joints_for_limits, 1):
            limits_layout.addWidget(QLabel(f"{joint_id} ({joint_name}):"), i, 0)

            min_spin = QDoubleSpinBox()
            min_spin.setRange(-360, 360)
            min_spin.setSuffix("°")
            min_spin.setValue(default_min)
            limits_layout.addWidget(min_spin, i, 1)

            max_spin = QDoubleSpinBox()
            max_spin.setRange(-360, 360)
            max_spin.setSuffix("°")
            max_spin.setValue(default_max)
            limits_layout.addWidget(max_spin, i, 2)

            full_rotate_check = QCheckBox()
            full_rotate_check.setChecked(can_full_rotate)
            if can_full_rotate:
                # If can rotate fully, disable min/max
                full_rotate_check.toggled.connect(lambda checked, mn=min_spin, mx=max_spin: (mn.setEnabled(not checked), mx.setEnabled(not checked)))
            limits_layout.addWidget(full_rotate_check, i, 3)

            self.joint_limit_controls[joint_id] = {
                'min': min_spin,
                'max': max_spin,
                'full_rotate': full_rotate_check
            }

        apply_limits_btn = QPushButton("Apply Joint Limits")
        apply_limits_btn.clicked.connect(self.apply_joint_limits)
        limits_layout.addWidget(apply_limits_btn, len(joints_for_limits) + 1, 0, 1, 4)

        layout.addWidget(limits_group)

        # Configuration display
        config_text = QTextEdit()
        config_text.setReadOnly(True)
        config_text.setPlainText(self.get_config_summary())
        layout.addWidget(config_text)

        # Reload button
        reload_layout = QHBoxLayout()
        reload_btn = QPushButton("Reload Configuration")
        reload_btn.clicked.connect(self.reload_configuration)
        reload_layout.addWidget(reload_btn)
        reload_layout.addStretch()
        layout.addLayout(reload_layout)

        return tab

    # Connection methods

    def toggle_robot_connection(self):
        """Connect/disconnect robot"""
        if self.robot.is_connected():
            self.robot.disconnect()
            self.connect_btn.setText("Connect")
            self.log_console("Robot disconnected")
        else:
            port = self.port_combo.currentText()
            if self.robot.connect(port, 115200):
                self.connect_btn.setText("Disconnect")
                self.log_console(f"Robot connected on {port}")
            else:
                QMessageBox.warning(self, "Connection Error", "Failed to connect to robot")

    def toggle_kinect_connection(self):
        """Connect/disconnect Kinect"""
        if self.kinect is None:
            self.kinect = KinectInterface()
            if self.kinect.open():
                version_text = self.kinect.version.value if self.kinect.version else "Unknown"
                self.kinect_version_label.setText(f"Version: {version_text}")
                self.vision_3d = VisionController3D(self.kinect)

                # Start worker thread
                self.kinect_worker = KinectWorker(self.kinect)
                self.kinect_worker.frame_ready.connect(self.update_kinect_display)
                self.kinect_worker.start()

                self.kinect_connect_btn.setText("Disconnect Kinect")
                self.log_console("Kinect connected")
            else:
                QMessageBox.warning(self, "Kinect Error", "Failed to open Kinect camera")
                self.kinect = None
        else:
            if self.kinect_worker:
                self.kinect_worker.stop()
                self.kinect_worker.wait()

            self.kinect.close()
            self.kinect = None
            self.vision_3d = None
            self.kinect_connect_btn.setText("Connect Kinect")
            self.kinect_version_label.setText("Version: Not Connected")
            self.log_console("Kinect disconnected")

    def toggle_gateway_connection(self):
        """Connect/disconnect sensor gateway"""
        if self.sensor_gateway is None:
            mode = 'serial' if self.gateway_mode_combo.currentText() == 'Serial' else 'network'
            port_or_host = self.gateway_port_input.text()

            config = GatewayConfig(
                mode=mode,
                serial_port=port_or_host if mode == 'serial' else '/dev/ttyUSB1',
                network_host=port_or_host if mode == 'network' else '192.168.1.100'
            )

            self.sensor_gateway = SensorGatewayClient(config)
            if self.sensor_gateway.connect():
                self.gateway_connect_btn.setText("Disconnect Gateway")
                self.log_console("Sensor gateway connected")

                # Create integration if robot is connected
                if self.robot.is_connected():
                    self.sensor_integration = SensorIntegration(
                        self.robot, self.sensor_gateway, self.kinematics
                    )
            else:
                QMessageBox.warning(self, "Gateway Error", "Failed to connect to sensor gateway")
                self.sensor_gateway = None
        else:
            if self.sensor_integration:
                if self.sensor_integration.closed_loop_running:
                    self.sensor_integration.stop_closed_loop()

            self.sensor_gateway.disconnect()
            self.sensor_gateway = None
            self.sensor_integration = None
            self.gateway_connect_btn.setText("Connect Gateway")
            self.log_console("Sensor gateway disconnected")

    # Robot control methods

    def move_joint(self, joint_id: str):
        """Move single joint"""
        if not self.robot.is_connected():
            QMessageBox.warning(self, "Robot Error", "Robot not connected")
            return

        angle = self.joint_controls[joint_id]['spinbox'].value()
        self.robot.move_joint(joint_id, angle, MovementType.G1_LINEAR, feedrate=500)
        self.log_console(f"Moving joint {joint_id} to {angle}°")

    def move_all_joints(self):
        """Move all joints to current positions"""
        if not self.robot.is_connected():
            QMessageBox.warning(self, "Robot Error", "Robot not connected")
            return

        angles = {
            joint_id: controls['spinbox'].value()
            for joint_id, controls in self.joint_controls.items()
        }

        self.robot.move_all_joints(angles, MovementType.G1_LINEAR, feedrate=500)
        self.log_console(f"Moving all joints: {angles}")

    def home_robot(self):
        """Home all joints"""
        if not self.robot.is_connected():
            return

        self.robot.send_homing_command()
        self.log_console("Homing robot...")

    def zero_robot(self):
        """Move to zero position"""
        if not self.robot.is_connected():
            return

        for controls in self.joint_controls.values():
            controls['slider'].setValue(0)
            controls['spinbox'].setValue(0)

        self.move_all_joints()

    def send_console_command(self):
        """Send command from console"""
        if not self.robot.is_connected():
            return

        command = self.console_input.text().strip()
        if command:
            self.robot.send_command(command)
            self.log_console(f">>> {command}")
            self.console_input.clear()

    def check_ik_reachability(self):
        """Check if target position is reachable"""
        from kinematics import Point3D

        target = Point3D(
            x=self.ik_x_spin.value(),
            y=self.ik_y_spin.value(),
            z=self.ik_z_spin.value()
        )

        if self.kinematics.is_reachable(target):
            self.ik_status_label.setText(f"✓ Position ({target.x:.1f}, {target.y:.1f}, {target.z:.1f}) is REACHABLE")
            self.ik_status_label.setStyleSheet("color: green;")
            self.log_console(f"IK Check: Position is reachable")
        else:
            self.ik_status_label.setText(f"✗ Position ({target.x:.1f}, {target.y:.1f}, {target.z:.1f}) is OUT OF REACH")
            self.ik_status_label.setStyleSheet("color: red;")
            self.log_console(f"IK Check: Position is out of reach")

        # Show workspace bounds
        bounds = self.kinematics.get_workspace_bounds()
        bounds_text = f"Workspace: X[{bounds['x'][0]:.0f}, {bounds['x'][1]:.0f}] "
        bounds_text += f"Y[{bounds['y'][0]:.0f}, {bounds['y'][1]:.0f}] "
        bounds_text += f"Z[{bounds['z'][0]:.0f}, {bounds['z'][1]:.0f}] mm"
        self.ik_solution_text.setPlainText(bounds_text)

    def calculate_ik_solution(self):
        """Calculate IK solution for target position"""
        from kinematics import Point3D

        target = Point3D(
            x=self.ik_x_spin.value(),
            y=self.ik_y_spin.value(),
            z=self.ik_z_spin.value()
        )

        # Check reachability first
        if not self.kinematics.is_reachable(target):
            self.ik_status_label.setText("✗ Cannot calculate: Position is out of reach")
            self.ik_status_label.setStyleSheet("color: red;")
            self.ik_move_btn.setEnabled(False)
            return

        # Get current joint angles as starting point
        current_angles = {joint_id: ctrl['spinbox'].value()
                         for joint_id, ctrl in self.joint_controls.items()}

        # Calculate IK
        self.ik_status_label.setText("Calculating IK solution...")
        self.ik_status_label.setStyleSheet("color: blue;")

        self.ik_solution = self.kinematics.inverse_kinematics(target, current_angles)

        if self.ik_solution:
            # Verify solution with forward kinematics
            end_pos, _ = self.kinematics.forward_kinematics(self.ik_solution)
            error_x = abs(end_pos.x - target.x)
            error_y = abs(end_pos.y - target.y)
            error_z = abs(end_pos.z - target.z)
            total_error = (error_x**2 + error_y**2 + error_z**2)**0.5

            # Display solution
            solution_text = f"IK Solution Found (error: {total_error:.2f} mm):\n\n"
            for joint_id in ['A', 'B', 'C', 'D', 'X', 'Y', 'Z']:
                if joint_id in self.ik_solution:
                    solution_text += f"{joint_id}: {self.ik_solution[joint_id]:6.1f}°\n"

            solution_text += f"\nVerification:\n"
            solution_text += f"Target:  ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})\n"
            solution_text += f"Reached: ({end_pos.x:.1f}, {end_pos.y:.1f}, {end_pos.z:.1f})"

            self.ik_solution_text.setPlainText(solution_text)
            self.ik_status_label.setText(f"✓ Solution found with {total_error:.2f} mm error")
            self.ik_status_label.setStyleSheet("color: green;")
            self.ik_move_btn.setEnabled(True)
            self.log_console(f"IK Solution calculated for ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})")
        else:
            self.ik_solution_text.setPlainText("No solution found. Try adjusting the target position.")
            self.ik_status_label.setText("✗ IK solver failed to converge")
            self.ik_status_label.setStyleSheet("color: red;")
            self.ik_move_btn.setEnabled(False)
            self.log_console("IK calculation failed")

    def move_to_ik_position(self):
        """Move robot to calculated IK position"""
        from kinematics import Point3D

        if not self.robot.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to robot first")
            return

        if not self.ik_solution:
            QMessageBox.warning(self, "No Solution", "Please calculate IK solution first")
            return

        # Move each joint to calculated angle
        for joint_id, angle in self.ik_solution.items():
            if joint_id in self.joint_controls:
                self.robot.move_joint(joint_id, angle)
                # Update UI
                self.joint_controls[joint_id]['slider'].setValue(int(angle))
                self.joint_controls[joint_id]['spinbox'].setValue(angle)

        target = Point3D(
            x=self.ik_x_spin.value(),
            y=self.ik_y_spin.value(),
            z=self.ik_z_spin.value()
        )
        self.log_console(f"Moving to position ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})")
        self.ik_status_label.setText("✓ Movement commands sent")
        self.ik_status_label.setStyleSheet("color: green;")

    # Kinect methods

    def update_kinect_display(self, frame):
        """Update Kinect image displays"""
        self.current_kinect_frame = frame

        # Update RGB
        self.kinect_rgb_display.update_image(frame.rgb)

        # Update depth
        depth_viz = visualize_depth(frame.depth)
        self.kinect_depth_display.update_image(depth_viz)

    def detect_objects_3d(self):
        """Detect 3D objects using current detection mode"""
        if not self.vision_3d or not self.current_kinect_frame:
            QMessageBox.warning(self, "Detection Error", "Kinect not connected")
            return

        mode = self.detection_mode_combo.currentText()

        if mode == "Color":
            self.detected_objects_3d = self.vision_3d.detect_objects_color(
                lower_hsv=(0, 100, 100),
                upper_hsv=(10, 255, 255),
                frame=self.current_kinect_frame
            )
        elif mode == "Contour":
            self.detected_objects_3d = self.vision_3d.detect_objects_contour(
                frame=self.current_kinect_frame
            )
        else:  # Depth Clustering
            self.detected_objects_3d = self.vision_3d.detect_objects_depth_clustering(
                frame=self.current_kinect_frame
            )

        # Display results
        self.display_detection_results()

        # Update RGB view with detections
        vis = self.vision_3d.visualize_detections(self.detected_objects_3d, self.current_kinect_frame)
        self.kinect_rgb_display.update_image(vis)

    def clear_detections(self):
        """Clear detected objects"""
        self.detected_objects_3d = []
        self.detection_results.clear()
        if self.current_kinect_frame:
            self.kinect_rgb_display.update_image(self.current_kinect_frame.rgb)

    def display_detection_results(self):
        """Display detection results in text box"""
        text = f"Detected {len(self.detected_objects_3d)} objects:\n\n"

        for i, obj in enumerate(self.detected_objects_3d, 1):
            text += f"{i}. {obj.label}\n"
            text += f"   2D Position: {obj.position_2d}\n"
            text += f"   3D Position: ({obj.position_3d[0]:.1f}, {obj.position_3d[1]:.1f}, {obj.position_3d[2]:.1f}) mm\n"
            text += f"   Depth: {obj.depth:.1f} mm ({obj.depth/1000:.3f} m)\n"
            if obj.volume:
                text += f"   Volume: {obj.volume/1000:.1f} cm³\n"
            text += "\n"

        self.detection_results.setPlainText(text)

    # Sensor methods

    def calibrate_sensors(self):
        """Calibrate all sensors"""
        if not self.sensor_gateway:
            QMessageBox.warning(self, "Sensor Error", "Sensor gateway not connected")
            return

        reply = QMessageBox.question(
            self, 'Calibrate Sensors',
            'Make sure robot is at home position and stationary.\n\nContinue with calibration?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.sensor_gateway.calibrate_all()
            self.log_console("Sensors calibrated")

    # Sequencer methods

    def toggle_recording(self):
        """Start/stop recording sequence"""
        if not self.robot.is_connected():
            QMessageBox.warning(self, "Robot Error", "Robot not connected")
            return

        if not self.sequencer.is_recording:
            name = self.record_name_input.text() or "New Sequence"
            self.sequencer.start_recording(name)
            self.record_btn.setText("Stop Recording")
            self.save_sequence_btn.setEnabled(False)
            self.log_console(f"Started recording: {name}")
        else:
            self.sequencer.stop_recording()
            self.record_btn.setText("Start Recording")
            self.save_sequence_btn.setEnabled(True)
            self.log_console("Stopped recording")

    def save_sequence(self):
        """Save recorded sequence"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Sequence", "", "JSON Files (*.json)"
        )
        if filename:
            if self.sequencer.current_sequence:
                self.sequencer.save_sequence(self.sequencer.current_sequence, filename)
                self.log_console(f"Sequence saved: {filename}")

    def load_sequence(self):
        """Load sequence from file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Sequence", "", "JSON Files (*.json)"
        )
        if filename:
            sequence = self.sequencer.load_sequence(filename)
            if sequence:
                self.sequencer.current_sequence = sequence
                self.play_sequence_btn.setEnabled(True)
                self.sequence_info.setPlainText(
                    f"Sequence: {sequence.name}\n"
                    f"Actions: {len(sequence.actions)}\n"
                    f"Duration: {sequence.actions[-1].timestamp - sequence.actions[0].timestamp:.2f}s"
                )
                self.log_console(f"Sequence loaded: {filename}")

    def play_sequence(self):
        """Play loaded sequence"""
        if self.sequencer.current_sequence:
            self.sequencer.play_sequence(self.sequencer.current_sequence)
            self.log_console("Playing sequence...")

    # Utility methods

    def find_serial_ports(self) -> List[str]:
        """Find available serial ports"""
        import serial.tools.list_ports
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports if ports else ["No ports found"]

    def refresh_serial_ports(self):
        """Refresh serial port list"""
        self.port_combo.clear()
        self.port_combo.addItems(self.find_serial_ports())

    def log_console(self, message: str):
        """Log message to console"""
        self.console_output.append(message)
        # Auto-scroll to bottom
        scrollbar = self.console_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_status(self):
        """Update status bar"""
        # Robot status
        if self.robot.is_connected():
            self.robot_status_label.setText("Robot: Connected ✓")
            self.robot_status_label.setStyleSheet("color: green;")
        else:
            self.robot_status_label.setText("Robot: Disconnected")
            self.robot_status_label.setStyleSheet("color: red;")

        # Kinect status
        if self.kinect and self.kinect.version:
            self.kinect_status_label.setText(f"Kinect: {self.kinect.version.value} ✓")
            self.kinect_status_label.setStyleSheet("color: green;")
        else:
            self.kinect_status_label.setText("Kinect: Not Active")
            self.kinect_status_label.setStyleSheet("color: gray;")

        # Sensor status
        if self.sensor_gateway and self.sensor_gateway.is_connected():
            status = self.sensor_gateway.get_status()
            num_joints = status.get('num_joints', 0)
            self.sensors_status_label.setText(f"Sensors: {num_joints} active ✓")
            self.sensors_status_label.setStyleSheet("color: green;")

            # Update sensor readings
            feedback = self.sensor_gateway.read_all()
            text = "Joint Angles:\n\n"
            for joint_id, fb in sorted(feedback.items()):
                text += f"{joint_id}: {fb.measured_angle:6.1f}°\n"
            self.sensor_readings_text.setPlainText(text)
        else:
            self.sensors_status_label.setText("Sensors: Not Active")
            self.sensors_status_label.setStyleSheet("color: gray;")

    def apply_configuration(self):
        """Apply loaded configuration"""
        serial_config = get_serial_config()
        if 'port' in serial_config:
            idx = self.port_combo.findText(serial_config['port'])
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)

        # Load robot dimensions from config
        if 'robot_dimensions' in self.config.config:
            dims = self.config.config['robot_dimensions']
            if 'base_height' in dims:
                self.kinematics.params['base_height'] = dims['base_height']
            if 'shoulder_offset' in dims:
                self.kinematics.params['shoulder_offset'] = dims['shoulder_offset']
            if 'upper_arm' in dims:
                self.kinematics.params['upper_arm'] = dims['upper_arm']
            if 'forearm' in dims:
                self.kinematics.params['forearm'] = dims['forearm']
            if 'wrist_length' in dims:
                self.kinematics.params['wrist_length'] = dims['wrist_length']

            self.log_console(f"Loaded robot dimensions from config")

        # Load joint limits from config
        if 'joint_limits' in self.config.config:
            for joint_id, limits in self.config.config['joint_limits'].items():
                if joint_id in self.joint_controls:
                    min_angle = limits.get('min', -180)
                    max_angle = limits.get('max', 180)

                    slider = self.joint_controls[joint_id]['slider']
                    spinbox = self.joint_controls[joint_id]['spinbox']

                    slider.setMinimum(int(min_angle))
                    slider.setMaximum(int(max_angle))
                    spinbox.setMinimum(min_angle)
                    spinbox.setMaximum(max_angle)

            self.log_console(f"Loaded joint limits from config")

    def apply_robot_dimensions(self):
        """Apply robot dimension settings to kinematics"""
        # Update kinematics parameters
        self.kinematics.params['base_height'] = self.dim_base_height.value()
        self.kinematics.params['shoulder_offset'] = self.dim_shoulder_offset.value()
        self.kinematics.params['upper_arm'] = self.dim_upper_arm.value()
        self.kinematics.params['forearm'] = self.dim_forearm.value()
        self.kinematics.params['wrist_length'] = self.dim_wrist_length.value()

        # Save to config
        if 'robot_dimensions' not in self.config.config:
            self.config.config['robot_dimensions'] = {}

        self.config.config['robot_dimensions'].update({
            'base_height': self.dim_base_height.value(),
            'shoulder_offset': self.dim_shoulder_offset.value(),
            'upper_arm': self.dim_upper_arm.value(),
            'forearm': self.dim_forearm.value(),
            'wrist_length': self.dim_wrist_length.value()
        })
        self.config.save()

        # Show workspace update
        bounds = self.kinematics.get_workspace_bounds()
        max_reach = bounds['x'][1]

        QMessageBox.information(
            self,
            "Dimensions Applied",
            f"Robot dimensions updated!\n\n"
            f"Upper Arm: {self.dim_upper_arm.value():.0f} mm\n"
            f"Forearm: {self.dim_forearm.value():.0f} mm\n"
            f"Wrist: {self.dim_wrist_length.value():.0f} mm\n\n"
            f"Maximum Reach: {max_reach:.0f} mm"
        )

        self.log_console(f"Robot dimensions updated - Max reach: {max_reach:.0f} mm")

    def apply_joint_limits(self):
        """Apply joint limit settings"""
        # Store joint limits
        if 'joint_limits' not in self.config.config:
            self.config.config['joint_limits'] = {}

        for joint_id, controls in self.joint_limit_controls.items():
            min_angle = controls['min'].value()
            max_angle = controls['max'].value()
            can_full_rotate = controls['full_rotate'].isChecked()

            self.config.config['joint_limits'][joint_id] = {
                'min': min_angle if not can_full_rotate else -360,
                'max': max_angle if not can_full_rotate else 360,
                'full_rotate': can_full_rotate
            }

            # Update joint control slider ranges
            if joint_id in self.joint_controls:
                slider = self.joint_controls[joint_id]['slider']
                spinbox = self.joint_controls[joint_id]['spinbox']

                actual_min = -360 if can_full_rotate else min_angle
                actual_max = 360 if can_full_rotate else max_angle

                slider.setMinimum(int(actual_min))
                slider.setMaximum(int(actual_max))
                spinbox.setMinimum(actual_min)
                spinbox.setMaximum(actual_max)

        self.config.save()

        QMessageBox.information(
            self,
            "Joint Limits Applied",
            "Joint rotation limits have been updated!\n\n"
            "The joint control sliders have been adjusted\n"
            "to match the new limits."
        )

        self.log_console("Joint limits updated")

    def reload_configuration(self):
        """Reload configuration from file"""
        self.config.load()
        self.apply_configuration()
        QMessageBox.information(self, "Configuration", "Configuration reloaded")

    def get_config_summary(self) -> str:
        """Get configuration summary"""
        serial_cfg = get_serial_config()
        kinect_cfg = get_kinect_config()
        board_cfg = get_board_config()

        summary = "Current Configuration:\n\n"
        summary += "=" * 50 + "\n"
        summary += "COMMUNICATION\n"
        summary += "=" * 50 + "\n"
        summary += f"Serial Port: {serial_cfg.get('port', 'Not set')}\n"
        summary += f"Baud Rate: {serial_cfg.get('baudrate', 115200)}\n"
        summary += f"Board: {board_cfg.get('description', 'Generic')}\n\n"

        summary += "=" * 50 + "\n"
        summary += "ROBOT DIMENSIONS (mm)\n"
        summary += "=" * 50 + "\n"
        if 'robot_dimensions' in self.config.config:
            dims = self.config.config['robot_dimensions']
            summary += f"Base Height: {dims.get('base_height', 0):.0f}\n"
            summary += f"Shoulder Offset: {dims.get('shoulder_offset', 0):.0f}\n"
            summary += f"Upper Arm: {dims.get('upper_arm', 200):.0f}\n"
            summary += f"Forearm: {dims.get('forearm', 200):.0f}\n"
            summary += f"Wrist Length: {dims.get('wrist_length', 100):.0f}\n"

            # Calculate and show max reach
            total = dims.get('upper_arm', 200) + dims.get('forearm', 200) + dims.get('wrist_length', 100)
            summary += f"\nMaximum Reach: {total:.0f} mm\n"
        else:
            summary += "Using default dimensions\n"

        summary += "\n" + "=" * 50 + "\n"
        summary += "JOINT LIMITS (degrees)\n"
        summary += "=" * 50 + "\n"
        if 'joint_limits' in self.config.config:
            for joint_id in ['A', 'B', 'C', 'D', 'X', 'Y', 'Z']:
                if joint_id in self.config.config['joint_limits']:
                    limits = self.config.config['joint_limits'][joint_id]
                    if limits.get('full_rotate', False):
                        summary += f"Joint {joint_id}: Full 360° rotation\n"
                    else:
                        summary += f"Joint {joint_id}: {limits.get('min', -180):.0f}° to {limits.get('max', 180):.0f}°\n"
        else:
            summary += "Using default limits\n"

        summary += "\n" + "=" * 50 + "\n"
        summary += "SENSORS\n"
        summary += "=" * 50 + "\n"
        summary += f"Kinect Enabled: {kinect_cfg.get('enabled', False)}\n"
        summary += f"Kinect Version: {kinect_cfg.get('version', 'auto')}\n\n"

        summary += f"Config File: {self.config.config_file}\n"

        return summary

    def closeEvent(self, event):
        """Handle window close"""
        # Stop Kinect worker
        if self.kinect_worker:
            self.kinect_worker.stop()
            self.kinect_worker.wait()

        # Disconnect devices
        if self.robot.is_connected():
            self.robot.disconnect()

        if self.kinect:
            self.kinect.close()

        if self.sensor_gateway:
            self.sensor_gateway.disconnect()

        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    # Create and show window
    window = AsgardEnhanced()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

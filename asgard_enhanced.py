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
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QEvent, QObject
from PyQt5.QtGui import QImage, QPixmap, QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

# Import our enhanced modules
from robot_controller import RobotController, MovementType
from kinect_interface import KinectInterface, visualize_depth
from vision_controller_3d import VisionController3D
from sensor_gateway_client import SensorGatewayClient, GatewayConfig
from sensor_integration import SensorIntegration
from action_sequencer import ActionSequencer
from kinematics import ThorKinematics, IKResult
from plugin_manager import PluginManager
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


class VisualizerEventFilter(QObject):
    """
    Qt event filter to intercept mouse events before matplotlib sees them.
    This allows us to implement middle-mouse dragging without matplotlib
    interfering with its own pan/zoom functionality.
    """
    def __init__(self, parent_gui):
        super().__init__()
        self.gui = parent_gui
        self.dragging = False
        self.last_x = 0
        self.last_y = 0
        self.drag_viewport = None
        self.dragging_joint = None  # Which joint index is being dragged (None = end effector)
        self.frame_skip_counter = 0  # For performance - update every N frames

        # Axis lock system (tangent locks)
        self.axis_lock = None  # None, 'X', 'Y', or 'Z'
        self.drag_start_pos = None  # Starting position for locked axis dragging

    def find_nearest_joint(self, mouse_x, mouse_y, viewport):
        """
        Find which joint marker is nearest to the mouse click.
        Returns joint index (0=base, 1-5=joints, None=none close enough)
        """
        # Get current joint positions
        current_angles = {joint_id: ctrl['spinbox'].value()
                         for joint_id, ctrl in self.gui.joint_controls.items()}
        end_pos, joint_positions = self.gui.kinematics.forward_kinematics(current_angles)

        # Convert mouse position to normalized canvas coordinates (0-1)
        canvas_width = self.gui.viz_canvas.width()
        canvas_height = self.gui.viz_canvas.height()

        # Get which quadrant we're in
        if mouse_y < canvas_height / 2:  # Top half
            quadrant_y = 0
            quadrant_x = 0 if mouse_x < canvas_width / 2 else 1
        else:  # Bottom half
            quadrant_y = 1
            quadrant_x = 0 if mouse_x < canvas_width / 2 else 1

        # Calculate relative position within the quadrant
        quadrant_mouse_x = (mouse_x % (canvas_width / 2)) / (canvas_width / 2)
        quadrant_mouse_y = (mouse_y % (canvas_height / 2)) / (canvas_height / 2)

        # Project joint positions to 2D based on viewport
        # This is a simplified projection - a full solution would use the actual matplotlib transform
        min_dist = float('inf')
        nearest_joint = None
        click_threshold = 0.25  # VERY forgiving threshold (25% of viewport)

        for i, joint_pos in enumerate(joint_positions):
            # Project to 2D based on viewport
            if viewport == 'top':
                # XY plane
                proj_x = (joint_pos.x + 600) / 1200  # Normalize to 0-1
                proj_y = 1.0 - (joint_pos.y + 600) / 1200  # Flip Y
            elif viewport == 'front':
                # XZ plane
                proj_x = (joint_pos.x + 600) / 1200
                proj_y = 1.0 - joint_pos.z / 600
            elif viewport == 'side':
                # YZ plane
                proj_x = (joint_pos.y + 600) / 1200
                proj_y = 1.0 - joint_pos.z / 600
            else:  # perspective - use approximate XY
                proj_x = (joint_pos.x + 600) / 1200
                proj_y = 1.0 - (joint_pos.y + 600) / 1200

            # Calculate distance
            dist = ((proj_x - quadrant_mouse_x)**2 + (proj_y - quadrant_mouse_y)**2)**0.5

            if dist < min_dist:
                min_dist = dist
                nearest_joint = i

        # Only return if within threshold
        if min_dist < click_threshold:
            self.gui.log_console(f"  Found nearest joint: {nearest_joint} (distance: {min_dist:.3f})")
            return nearest_joint
        else:
            self.gui.log_console(f"  No joint near click (min distance: {min_dist:.3f}, threshold: {click_threshold})")
            return None

    def eventFilter(self, obj, event):
        """Filter Qt mouse events on the canvas"""
        # Only handle events on the matplotlib canvas
        if obj != self.gui.viz_canvas:
            return False

        event_type = event.type()

        # Middle mouse button press - start dragging
        if event_type == QEvent.MouseButtonPress:
            if event.button() == Qt.MiddleButton:
                self.gui.log_console(f"🖱️  Middle-click at ({event.x()}, {event.y()})")

                if not self.gui.viz_interactive_mode.isChecked():
                    self.gui.log_console("⚠ Interactive mode is OFF - enable it to drag")
                    return False

                self.dragging = True
                self.last_x = event.x()
                self.last_y = event.y()
                self.frame_skip_counter = 0  # Reset frame counter

                # Get current end effector position
                current_angles = {joint_id: ctrl['spinbox'].value()
                                 for joint_id, ctrl in self.gui.joint_controls.items()}
                end_pos, _ = self.gui.kinematics.forward_kinematics(current_angles)
                self.gui.viz_target_pos = [end_pos.x, end_pos.y, end_pos.z]
                self.drag_start_pos = [end_pos.x, end_pos.y, end_pos.z]  # Store start position for axis locks

                # Determine which viewport we're in by checking mouse position
                # Convert to figure coordinates
                canvas_width = self.gui.viz_canvas.width()
                canvas_height = self.gui.viz_canvas.height()

                # Simple quadrant detection (2x2 grid)
                if event.y() < canvas_height / 2:  # Top half
                    if event.x() < canvas_width / 2:  # Left
                        self.drag_viewport = 'top'
                    else:  # Right
                        self.drag_viewport = 'front'
                else:  # Bottom half
                    if event.x() < canvas_width / 2:  # Left
                        self.drag_viewport = 'side'
                    else:  # Right
                        self.drag_viewport = 'persp'

                self.gui.log_console(f"  Viewport: {self.drag_viewport.upper()}")

                # Detect which joint (if any) is being clicked
                self.dragging_joint = self.find_nearest_joint(event.x(), event.y(), self.drag_viewport)

                # Disable auto-update temporarily
                self.gui.viz_auto_update.setChecked(False)

                view_label = self.drag_viewport.upper() if self.drag_viewport else "UNKNOWN"
                if self.dragging_joint is not None:
                    joint_names = ['Base', 'Joint 1', 'Joint 2', 'Joint 3', 'Joint 4', 'Joint 5', 'End Effector']
                    joint_name = joint_names[self.dragging_joint] if self.dragging_joint < len(joint_names) else f'Joint {self.dragging_joint}'
                    self.gui.log_console(f"✓ DRAGGING {joint_name} in {view_label} view - move mouse to adjust")
                else:
                    self.gui.log_console(f"✓ DRAG STARTED (end effector) in {view_label} view at ({end_pos.x:.0f}, {end_pos.y:.0f}, {end_pos.z:.0f})")

                return True  # Consume event to prevent matplotlib from seeing it

        # Middle mouse button release - stop dragging
        elif event_type == QEvent.MouseButtonRelease:
            if event.button() == Qt.MiddleButton and self.dragging:
                self.dragging = False
                self.frame_skip_counter = 0  # Reset frame counter

                # Only calculate IK if we were dragging end effector (not a specific joint)
                if self.dragging_joint is None and self.gui.viz_target_pos:
                    from kinematics import Point3D
                    target = Point3D(
                        x=self.gui.viz_target_pos[0],
                        y=self.gui.viz_target_pos[1],
                        z=self.gui.viz_target_pos[2]
                    )

                    current_angles = {joint_id: ctrl['spinbox'].value()
                                     for joint_id, ctrl in self.gui.joint_controls.items()}
                    ik_result = self.gui.kinematics.inverse_kinematics(target, current_angles)

                    if ik_result.success:
                        # Update joint controls
                        for joint_id, angle in ik_result.angles.items():
                            if joint_id in self.gui.joint_controls:
                                self.gui.joint_controls[joint_id]['slider'].setValue(int(angle))
                                self.gui.joint_controls[joint_id]['spinbox'].setValue(angle)

                        self.gui.log_console(f"✓ Moved to ({target.x:.1f}, {target.y:.1f}, {target.z:.1f}) - {ik_result.reason}")
                    else:
                        self.gui.log_console(f"✗ Drag failed: {ik_result.reason}")

                # Re-enable auto-update
                self.gui.viz_auto_update.setChecked(True)
                self.gui.update_3d_visualization()

                self.drag_viewport = None
                self.dragging_joint = None
                return True  # Consume event

        # Mouse motion - update drag position
        elif event_type == QEvent.MouseMove:
            if self.dragging:
                # Calculate pixel delta
                dx = event.x() - self.last_x
                dy = event.y() - self.last_y

                self.last_x = event.x()
                self.last_y = event.y()

                # Handle dragging a specific joint vs. end effector differently
                if self.dragging_joint is not None:
                    # Dragging a specific joint - directly control that joint's angle
                    # Map joint index to joint ID
                    joint_ids = ['A', 'B', 'D', 'X', 'Y', 'Z']

                    # For base joint (index 0), we can control the base rotation (A)
                    # For other joints, map appropriately
                    if self.dragging_joint == 0:
                        # Base - control A joint (rotation around Z)
                        joint_to_control = 'A'
                        angle_delta = dx * 0.5  # Horizontal movement controls rotation
                    elif self.dragging_joint < len(joint_ids):
                        # Other joints - map to B, D, X, Y, Z
                        joint_to_control = joint_ids[min(self.dragging_joint, len(joint_ids) - 1)]
                        # Use combined dx and dy for more intuitive control
                        angle_delta = (dx - dy) * 0.5  # 0.5 degrees per pixel
                    else:
                        joint_to_control = None
                        angle_delta = 0

                    if joint_to_control and joint_to_control in self.gui.joint_controls:
                        # Get current angle
                        current_angle = self.gui.joint_controls[joint_to_control]['spinbox'].value()
                        new_angle = current_angle + angle_delta

                        # Clamp to limits
                        new_angle = max(-180, min(180, new_angle))

                        # Update the joint control
                        self.gui.joint_controls[joint_to_control]['spinbox'].blockSignals(True)
                        self.gui.joint_controls[joint_to_control]['slider'].blockSignals(True)
                        self.gui.joint_controls[joint_to_control]['slider'].setValue(int(new_angle))
                        self.gui.joint_controls[joint_to_control]['spinbox'].setValue(new_angle)
                        self.gui.joint_controls[joint_to_control]['spinbox'].blockSignals(False)
                        self.gui.joint_controls[joint_to_control]['slider'].blockSignals(False)

                        # Update info label every frame (lightweight)
                        self.gui.viz_info_label.setText(
                            f"Dragging Joint {joint_to_control}: {new_angle:.1f}°"
                        )

                        # Update visualization every 2nd frame to reduce lag
                        self.frame_skip_counter += 1
                        if self.frame_skip_counter % 2 == 0:
                            self.gui.update_3d_visualization()

                else:
                    # Dragging end effector - use IK
                    # Convert pixel delta to world space delta
                    scale = 0.8
                    world_dx = dx * scale
                    world_dy = -dy * scale  # Invert Y (Qt Y goes down, world Y goes up)

                    # AXIS LOCK SYSTEM: If an axis is locked, only move along that axis
                    if self.axis_lock:
                        # Reset to starting position
                        if self.drag_start_pos:
                            self.gui.viz_target_pos = self.drag_start_pos.copy()

                        # Combined mouse movement (diagonal movement magnitude)
                        combined_delta = ((world_dx ** 2) + (world_dy ** 2)) ** 0.5
                        # Use sign of dominant axis for direction
                        if abs(world_dx) > abs(world_dy):
                            direction = 1 if world_dx > 0 else -1
                        else:
                            direction = 1 if world_dy > 0 else -1

                        combined_delta *= direction

                        # Apply to locked axis only
                        if self.axis_lock == 'X':
                            self.gui.viz_target_pos[0] = self.drag_start_pos[0] + combined_delta
                        elif self.axis_lock == 'Y':
                            self.gui.viz_target_pos[1] = self.drag_start_pos[1] + combined_delta
                        elif self.axis_lock == 'Z':
                            self.gui.viz_target_pos[2] = self.drag_start_pos[2] + combined_delta

                    else:
                        # No axis lock - normal viewport-based dragging
                        # Update target position based on viewport
                        if self.drag_viewport == 'top':
                            # Top view: drag in XY plane
                            self.gui.viz_target_pos[0] += world_dx  # X
                            self.gui.viz_target_pos[1] += world_dy  # Y
                        elif self.drag_viewport == 'front':
                            # Front view: drag in XZ plane
                            self.gui.viz_target_pos[0] += world_dx  # X
                            self.gui.viz_target_pos[2] += world_dy  # Z
                        elif self.drag_viewport == 'side':
                            # Side view: drag in YZ plane
                            self.gui.viz_target_pos[1] += world_dx  # Y
                            self.gui.viz_target_pos[2] += world_dy  # Z
                        else:  # perspective
                            # Perspective: drag in XY plane
                            self.gui.viz_target_pos[0] += world_dx  # X
                            self.gui.viz_target_pos[1] += world_dy  # Y

                    # Clamp to workspace
                    self.gui.viz_target_pos[0] = max(-600, min(600, self.gui.viz_target_pos[0]))
                    self.gui.viz_target_pos[1] = max(-600, min(600, self.gui.viz_target_pos[1]))
                    self.gui.viz_target_pos[2] = max(0, min(600, self.gui.viz_target_pos[2]))

                    # Calculate IK for preview
                    from kinematics import Point3D
                    target = Point3D(
                        x=self.gui.viz_target_pos[0],
                        y=self.gui.viz_target_pos[1],
                        z=self.gui.viz_target_pos[2]
                    )

                    # Only calculate IK every 3rd frame to reduce lag
                    self.frame_skip_counter += 1
                    if self.frame_skip_counter % 3 == 0:
                        current_angles = {joint_id: ctrl['spinbox'].value()
                                         for joint_id, ctrl in self.gui.joint_controls.items()}
                        ik_result = self.gui.kinematics.inverse_kinematics(target, current_angles)

                        if ik_result.success:
                            # Update joint controls without triggering moves
                            for joint_id, angle in ik_result.angles.items():
                                if joint_id in self.gui.joint_controls:
                                    self.gui.joint_controls[joint_id]['spinbox'].blockSignals(True)
                                    self.gui.joint_controls[joint_id]['slider'].blockSignals(True)
                                    self.gui.joint_controls[joint_id]['slider'].setValue(int(angle))
                                    self.gui.joint_controls[joint_id]['spinbox'].setValue(angle)
                                    self.gui.joint_controls[joint_id]['spinbox'].blockSignals(False)
                                    self.gui.joint_controls[joint_id]['slider'].blockSignals(False)

                            # Update info label
                            status_prefix = "~" if ik_result.is_approximate else ""
                            axis_lock_text = f" [🔒{self.axis_lock}]" if self.axis_lock else ""
                            self.gui.viz_info_label.setText(
                                f"{status_prefix}Dragging{axis_lock_text}: ({target.x:.1f}, {target.y:.1f}, {target.z:.1f}) mm, error: {ik_result.error:.1f}mm"
                            )

                            # Update visualization
                            self.gui.update_3d_visualization()

                return True  # Consume event

        # Keyboard events for axis locking (tangent locks)
        elif event_type == QEvent.KeyPress:
            key = event.key()

            # X key - lock to X axis
            if key == Qt.Key_X:
                if self.axis_lock == 'X':
                    self.axis_lock = None
                    self.gui.log_console("🔓 Axis lock removed")
                else:
                    self.axis_lock = 'X'
                    self.gui.log_console("🔒 Locked to X axis")
                self.gui.update_viz_axis_lock_indicator()
                return True

            # Y key - lock to Y axis
            elif key == Qt.Key_Y:
                if self.axis_lock == 'Y':
                    self.axis_lock = None
                    self.gui.log_console("🔓 Axis lock removed")
                else:
                    self.axis_lock = 'Y'
                    self.gui.log_console("🔒 Locked to Y axis")
                self.gui.update_viz_axis_lock_indicator()
                return True

            # Z key - lock to Z axis
            elif key == Qt.Key_Z:
                if self.axis_lock == 'Z':
                    self.axis_lock = None
                    self.gui.log_console("🔓 Axis lock removed")
                else:
                    self.axis_lock = 'Z'
                    self.gui.log_console("🔒 Locked to Z axis")
                self.gui.update_viz_axis_lock_indicator()
                return True

            # Escape key - clear any axis lock
            elif key == Qt.Key_Escape:
                if self.axis_lock:
                    self.axis_lock = None
                    self.gui.log_console("🔓 Axis lock removed")
                    self.gui.update_viz_axis_lock_indicator()
                    return True

        # Let other events pass through
        return False


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
        self.plugin_manager = PluginManager()

        # Current state
        self.current_kinect_frame = None
        self.detected_objects_3d = []
        self.ik_solution: Optional[Dict[str, float]] = None

        # 3D visualizer interaction state
        self.viz_dragging = False
        self.viz_drag_start = None
        self.viz_target_pos = None
        self.viz_drag_viewport = None  # Which viewport we're dragging in
        self.viz_drag_counter = 0  # Counter for debug output

        # Load configuration
        self.config = get_config()

        # Build UI
        self.init_ui()

        # Load plugins (after UI is built so plugins can add tabs/widgets)
        self.plugin_manager.load_all_plugins(self)
        self.load_plugin_tabs()  # Add tabs from plugins with UI

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
        self.tabs.addTab(self.create_visualizer_tab(), "3D Visualizer")
        self.tabs.addTab(self.create_kinect_tab(), "Kinect Vision")
        self.tabs.addTab(self.create_sensors_tab(), "Sensors")
        self.tabs.addTab(self.create_sequencer_tab(), "Action Sequencer")
        self.tabs.addTab(self.create_config_tab(), "Configuration")
        self.tabs.addTab(self.create_plugins_tab(), "Plugins")

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

        # Jog increment selector
        joint_layout.addWidget(QLabel("Jog Increment:"), 0, 0)
        self.jog_increment_combo = QComboBox()
        self.jog_increment_combo.addItems(["0.1°", "1°", "5°", "10°", "45°", "90°"])
        self.jog_increment_combo.setCurrentText("1°")
        joint_layout.addWidget(self.jog_increment_combo, 0, 1, 1, 2)

        self.joint_controls = {}
        joints = [('A', 'Base'), ('B', 'Shoulder'), ('D', 'Elbow'),
                  ('X', 'Wrist Pitch'), ('Y', 'Wrist Roll'), ('Z', 'Wrist Rotate')]

        for i, (joint_id, joint_name) in enumerate(joints):
            row = i + 1  # Offset by 1 for increment selector row

            # Label
            joint_layout.addWidget(QLabel(f"{joint_name} ({joint_id}):"), row, 0)

            # Slider
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(-180)
            slider.setMaximum(180)
            slider.setValue(0)
            joint_layout.addWidget(slider, row, 1)

            # Spinbox
            spinbox = QDoubleSpinBox()
            spinbox.setMinimum(-180)
            spinbox.setMaximum(180)
            spinbox.setValue(0)
            spinbox.setSuffix("°")
            joint_layout.addWidget(spinbox, row, 2)

            # Jog - button
            jog_minus_btn = QPushButton("-")
            jog_minus_btn.setMaximumWidth(40)
            jog_minus_btn.setToolTip(f"Jog {joint_name} negative")
            jog_minus_btn.clicked.connect(lambda checked, j=joint_id: self.jog_joint(j, -1))
            joint_layout.addWidget(jog_minus_btn, row, 3)

            # Jog + button
            jog_plus_btn = QPushButton("+")
            jog_plus_btn.setMaximumWidth(40)
            jog_plus_btn.setToolTip(f"Jog {joint_name} positive")
            jog_plus_btn.clicked.connect(lambda checked, j=joint_id: self.jog_joint(j, 1))
            joint_layout.addWidget(jog_plus_btn, row, 4)

            # Go button
            go_btn = QPushButton("Go")
            go_btn.clicked.connect(lambda checked, j=joint_id: self.move_joint(j))
            joint_layout.addWidget(go_btn, row, 5)

            # Store controls
            self.joint_controls[joint_id] = {
                'slider': slider,
                'spinbox': spinbox,
                'button': go_btn,
                'jog_minus': jog_minus_btn,
                'jog_plus': jog_plus_btn
            }

            # Connect slider and spinbox
            slider.valueChanged.connect(spinbox.setValue)
            spinbox.valueChanged.connect(lambda v: slider.setValue(int(v)))

            # Connect to 3D visualization update
            spinbox.valueChanged.connect(self.on_joint_changed)

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

    def create_visualizer_tab(self) -> QWidget:
        """Create 3D arm visualizer tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Controls
        controls_group = QGroupBox("Visualization Controls")
        controls_layout = QHBoxLayout(controls_group)

        self.viz_interactive_mode = QCheckBox("Interactive Mode (drag end effector)")
        self.viz_interactive_mode.setChecked(True)
        controls_layout.addWidget(self.viz_interactive_mode)

        # Alternative keyboard controls
        keyboard_controls_label = QLabel("OR use keyboard: ← → ↑ ↓ for XY, PgUp/PgDn for Z")
        keyboard_controls_label.setStyleSheet("color: gray; font-style: italic;")
        controls_layout.addWidget(keyboard_controls_label)

        self.viz_auto_update = QCheckBox("Auto-update from joint controls")
        self.viz_auto_update.setChecked(True)
        controls_layout.addWidget(self.viz_auto_update)

        self.viz_show_workspace = QCheckBox("Show workspace bounds")
        self.viz_show_workspace.setChecked(False)
        self.viz_show_workspace.toggled.connect(self.update_3d_visualization)
        controls_layout.addWidget(self.viz_show_workspace)

        self.viz_show_target = QCheckBox("Show target marker")
        self.viz_show_target.setChecked(False)
        self.viz_show_target.toggled.connect(self.update_3d_visualization)
        controls_layout.addWidget(self.viz_show_target)

        refresh_btn = QPushButton("Refresh View")
        refresh_btn.clicked.connect(self.update_3d_visualization)
        controls_layout.addWidget(refresh_btn)

        reset_view_btn = QPushButton("Reset Camera")
        reset_view_btn.clicked.connect(self.reset_3d_view)
        controls_layout.addWidget(reset_view_btn)

        controls_layout.addStretch()

        layout.addWidget(controls_group)

        # Info panel
        info_group = QGroupBox("Arm Information")
        info_layout = QHBoxLayout(info_group)

        self.viz_info_label = QLabel("End Effector Position: (0.0, 0.0, 0.0) mm")
        info_layout.addWidget(self.viz_info_label)

        layout.addWidget(info_group)

        # Axis Lock Controls (Tangent Locks)
        axis_lock_group = QGroupBox("Axis Locks (Tangent Constraints)")
        axis_lock_layout = QHBoxLayout(axis_lock_group)

        axis_lock_label = QLabel("Lock movement to axis:")
        axis_lock_layout.addWidget(axis_lock_label)

        self.axis_lock_x_btn = QPushButton("X")
        self.axis_lock_x_btn.setCheckable(True)
        self.axis_lock_x_btn.setMaximumWidth(40)
        self.axis_lock_x_btn.clicked.connect(lambda: self.toggle_axis_lock('X'))
        self.axis_lock_x_btn.setToolTip("Lock to X axis (or press X key while dragging)")
        axis_lock_layout.addWidget(self.axis_lock_x_btn)

        self.axis_lock_y_btn = QPushButton("Y")
        self.axis_lock_y_btn.setCheckable(True)
        self.axis_lock_y_btn.setMaximumWidth(40)
        self.axis_lock_y_btn.clicked.connect(lambda: self.toggle_axis_lock('Y'))
        self.axis_lock_y_btn.setToolTip("Lock to Y axis (or press Y key while dragging)")
        axis_lock_layout.addWidget(self.axis_lock_y_btn)

        self.axis_lock_z_btn = QPushButton("Z")
        self.axis_lock_z_btn.setCheckable(True)
        self.axis_lock_z_btn.setMaximumWidth(40)
        self.axis_lock_z_btn.clicked.connect(lambda: self.toggle_axis_lock('Z'))
        self.axis_lock_z_btn.setToolTip("Lock to Z axis (or press Z key while dragging)")
        axis_lock_layout.addWidget(self.axis_lock_z_btn)

        self.axis_lock_status_label = QLabel("None")
        self.axis_lock_status_label.setStyleSheet("font-weight: bold; color: gray;")
        axis_lock_layout.addWidget(self.axis_lock_status_label)

        axis_lock_help = QLabel("(Keyboard: Press X/Y/Z to toggle locks, ESC to clear)")
        axis_lock_help.setStyleSheet("color: gray; font-style: italic; font-size: 10px;")
        axis_lock_layout.addWidget(axis_lock_help)

        axis_lock_layout.addStretch()
        layout.addWidget(axis_lock_group)

        # Matplotlib quad view canvas (like 3D Studio Max)
        # Use larger figure size to prevent cramping
        self.viz_figure = Figure(figsize=(14, 12), dpi=80)
        self.viz_canvas = FigureCanvas(self.viz_figure)

        # Set better spacing between subplots to prevent overlap
        self.viz_figure.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05,
                                        hspace=0.25, wspace=0.25)

        # Create 2x2 grid of subplots
        # Top-left: Top view (XY plane)
        self.viz_ax_top = self.viz_figure.add_subplot(221, projection='3d')
        self.viz_ax_top.set_title('TOP VIEW (XY)', fontweight='bold', fontsize=10)

        # Top-right: Front view (XZ plane)
        self.viz_ax_front = self.viz_figure.add_subplot(222, projection='3d')
        self.viz_ax_front.set_title('FRONT VIEW (XZ)', fontweight='bold', fontsize=10)

        # Bottom-left: Side view (YZ plane)
        self.viz_ax_side = self.viz_figure.add_subplot(223, projection='3d')
        self.viz_ax_side.set_title('SIDE VIEW (YZ)', fontweight='bold', fontsize=10)

        # Bottom-right: Perspective view
        self.viz_ax_persp = self.viz_figure.add_subplot(224, projection='3d')
        self.viz_ax_persp.set_title('PERSPECTIVE', fontweight='bold', fontsize=10)

        # CRITICAL: Disable matplotlib's toolbar and navigation completely
        self.viz_canvas.setFocusPolicy(Qt.StrongFocus)
        self.viz_canvas.setFocus()

        # Disable all matplotlib default mouse/key bindings
        for ax in [self.viz_ax_top, self.viz_ax_front, self.viz_ax_side, self.viz_ax_persp]:
            ax.set_navigate(False)  # Disable toolbar navigation

        # Override matplotlib's toolbar mode
        try:
            self.viz_canvas.toolbar = None
        except:
            pass

        # Store all axes for easy iteration
        self.viz_axes = {
            'top': self.viz_ax_top,
            'front': self.viz_ax_front,
            'side': self.viz_ax_side,
            'persp': self.viz_ax_persp
        }

        # Adjust spacing
        self.viz_figure.tight_layout(pad=2.0)

        # Connect mouse events for interactive manipulation
        # Note: Keep matplotlib connections for scroll and keyboard events
        self.viz_canvas.mpl_connect('scroll_event', self.on_viz_scroll)
        self.viz_canvas.mpl_connect('key_press_event', self.on_viz_key_press)

        # Install Qt event filter to intercept mouse drag events BEFORE matplotlib sees them
        # This is more reliable than matplotlib's event system for middle-mouse dragging
        self.viz_event_filter = VisualizerEventFilter(self)
        self.viz_canvas.installEventFilter(self.viz_event_filter)

        layout.addWidget(self.viz_canvas)

        # Make sure canvas can receive keyboard events
        self.viz_canvas.setFocusPolicy(Qt.StrongFocus)

        # Initialize the plot
        self.update_3d_visualization()

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
        self.board_combo.addItems(["FLY Super ♾️ Pro", "Generic GRBL"])
        self.board_combo.setCurrentIndex(0)  # FLY Super ♾️ Pro as default
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

    def create_plugins_tab(self) -> QWidget:
        """Create plugins management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Header
        header = QLabel("<h2>Plugin Manager</h2>")
        layout.addWidget(header)

        desc = QLabel(
            "Plugins extend the functionality of Asgard Enhanced. "
            "Enable/disable plugins below, or create your own plugins in the 'plugins/' directory."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Plugin list group
        plugins_group = QGroupBox("Loaded Plugins")
        plugins_layout = QVBoxLayout(plugins_group)

        # This will be populated with plugin controls
        self.plugin_controls_layout = QVBoxLayout()
        plugins_layout.addLayout(self.plugin_controls_layout)

        # Refresh plugins list
        self.refresh_plugin_list()

        plugins_layout.addStretch()
        layout.addWidget(plugins_group)

        # Reload button
        reload_layout = QHBoxLayout()
        reload_plugins_btn = QPushButton("Reload All Plugins")
        reload_plugins_btn.clicked.connect(self.reload_all_plugins)
        reload_layout.addWidget(reload_plugins_btn)

        open_plugins_dir_btn = QPushButton("Open Plugins Folder")
        open_plugins_dir_btn.clicked.connect(self.open_plugins_directory)
        reload_layout.addWidget(open_plugins_dir_btn)

        reload_layout.addStretch()
        layout.addLayout(reload_layout)

        # Info section
        info_group = QGroupBox("Plugin Development")
        info_layout = QVBoxLayout(info_group)

        info_text = QLabel(
            "<b>Want to create your own plugins?</b><br>"
            "See <tt>PLUGIN_DEVELOPMENT.md</tt> for a complete guide.<br><br>"
            "<b>Quick start:</b><br>"
            "1. Create a Python file in the <tt>plugins/</tt> directory<br>"
            "2. Inherit from <tt>Plugin</tt> or <tt>VisionPlugin</tt> base class<br>"
            "3. Implement the <tt>initialize()</tt> method<br>"
            "4. Optional: implement <tt>create_widget()</tt> for custom UI<br>"
            "5. Restart Asgard Enhanced or click 'Reload All Plugins'"
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        return tab

    def refresh_plugin_list(self):
        """Refresh the list of plugins in the UI"""
        # Clear existing controls
        while self.plugin_controls_layout.count():
            child = self.plugin_controls_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add controls for each loaded plugin
        plugins = self.plugin_manager.get_all_plugins()

        if not plugins:
            no_plugins_label = QLabel("<i>No plugins loaded. Add plugins to the 'plugins/' directory.</i>")
            no_plugins_label.setStyleSheet("color: gray;")
            self.plugin_controls_layout.addWidget(no_plugins_label)
            return

        for plugin_name, plugin in plugins.items():
            # Create a widget for each plugin
            plugin_widget = QWidget()
            plugin_layout = QHBoxLayout(plugin_widget)
            plugin_layout.setContentsMargins(5, 5, 5, 5)

            # Plugin info
            metadata = plugin.get_metadata()
            name_label = QLabel(f"<b>{metadata.name}</b> v{metadata.version}")
            plugin_layout.addWidget(name_label)

            desc_label = QLabel(f"- {metadata.description}")
            desc_label.setStyleSheet("color: gray;")
            plugin_layout.addWidget(desc_label, 1)  # Stretch factor 1

            # Enable/Disable checkbox
            enable_check = QCheckBox("Enabled")
            enable_check.setChecked(plugin.enabled)
            enable_check.toggled.connect(
                lambda checked, p=plugin_name: self.toggle_plugin(p, checked)
            )
            plugin_layout.addWidget(enable_check)

            # Add to layout
            self.plugin_controls_layout.addWidget(plugin_widget)

    def toggle_plugin(self, plugin_name: str, enabled: bool):
        """Enable/disable a plugin"""
        if enabled:
            self.plugin_manager.enable_plugin(plugin_name)
            self.log_console(f"✓ Enabled plugin: {plugin_name}")
        else:
            self.plugin_manager.disable_plugin(plugin_name)
            self.log_console(f"⊗ Disabled plugin: {plugin_name}")

    def reload_all_plugins(self):
        """Reload all plugins"""
        self.log_console("Reloading all plugins...")

        # Shutdown existing plugins
        self.plugin_manager.shutdown_all()

        # Reload
        self.plugin_manager.load_all_plugins(self)

        # Refresh UI
        self.refresh_plugin_list()

        # Add plugin tabs
        self.load_plugin_tabs()

        self.log_console("✓ Plugins reloaded")

    def load_plugin_tabs(self):
        """Load tabs from plugins that have UI"""
        plugins_with_ui = self.plugin_manager.get_plugins_with_ui()

        for plugin_name, plugin in plugins_with_ui.items():
            widget = plugin.create_widget()
            if widget:
                # Check if tab already exists
                tab_title = f"🔌 {plugin.get_metadata().name}"
                tab_exists = False
                for i in range(self.tabs.count()):
                    if self.tabs.tabText(i) == tab_title:
                        tab_exists = True
                        break

                if not tab_exists:
                    self.tabs.addTab(widget, tab_title)

    def open_plugins_directory(self):
        """Open the plugins directory in file explorer"""
        import os
        import subprocess
        import platform

        plugins_path = os.path.abspath("plugins")

        # Create directory if it doesn't exist
        os.makedirs(plugins_path, exist_ok=True)

        # Open in file explorer based on OS
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(plugins_path)
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", plugins_path])
            else:  # Linux
                subprocess.Popen(["xdg-open", plugins_path])

            self.log_console(f"Opened plugins directory: {plugins_path}")
        except Exception as e:
            self.log_console(f"Could not open plugins directory: {e}")

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

    def jog_joint(self, joint_id: str, direction: int):
        """
        Jog a joint by the selected increment

        Args:
            joint_id: Joint identifier ('A', 'B', 'D', 'X', 'Y', 'Z')
            direction: 1 for positive, -1 for negative
        """
        # Get current jog increment from combo box
        increment_text = self.jog_increment_combo.currentText()
        increment = float(increment_text.replace('°', ''))

        # Calculate new angle
        current_angle = self.joint_controls[joint_id]['spinbox'].value()
        new_angle = current_angle + (increment * direction)

        # Clamp to joint limits
        new_angle = max(-180, min(180, new_angle))

        # Update the spinbox (this will also update the slider and trigger visualization)
        self.joint_controls[joint_id]['spinbox'].setValue(new_angle)

        # If robot is connected, send the move command immediately
        if self.robot.is_connected():
            self.robot.move_joint(joint_id, new_angle, MovementType.G1_LINEAR, feedrate=500)
            direction_str = "+" if direction > 0 else ""
            self.log_console(f"Jogged joint {joint_id} {direction_str}{increment * direction}° → {new_angle:.1f}°")
        else:
            # Just update the UI
            direction_str = "+" if direction > 0 else ""
            self.log_console(f"Joint {joint_id} jogged {direction_str}{increment * direction}° → {new_angle:.1f}° (not connected)")

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

        ik_result = self.kinematics.inverse_kinematics(target, current_angles)

        if ik_result.success:
            # Store solution
            self.ik_solution = ik_result.angles

            # Verify solution with forward kinematics
            end_pos, _ = self.kinematics.forward_kinematics(ik_result.angles)

            # Display solution
            solution_text = ""
            if ik_result.is_approximate:
                solution_text += "⚠ APPROXIMATE SOLUTION ⚠\n"
            else:
                solution_text += "✓ EXACT SOLUTION\n"

            solution_text += f"\n{ik_result.reason}\n\n"
            solution_text += "Joint Angles:\n"
            for joint_id in ['A', 'B', 'C', 'D', 'X', 'Y', 'Z']:
                if joint_id in ik_result.angles:
                    solution_text += f"{joint_id}: {ik_result.angles[joint_id]:6.1f}°\n"

            solution_text += f"\nVerification:\n"
            solution_text += f"Target:  ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})\n"
            solution_text += f"Reached: ({end_pos.x:.1f}, {end_pos.y:.1f}, {end_pos.z:.1f})\n"
            solution_text += f"Error:   {ik_result.error:.2f} mm"

            self.ik_solution_text.setPlainText(solution_text)

            if ik_result.is_approximate:
                self.ik_status_label.setText(f"⚠ Approximate solution: {ik_result.error:.2f} mm error")
                self.ik_status_label.setStyleSheet("color: orange;")
            else:
                self.ik_status_label.setText(f"✓ Exact solution: {ik_result.error:.2f} mm error")
                self.ik_status_label.setStyleSheet("color: green;")

            self.ik_move_btn.setEnabled(True)
            self.log_console(f"IK: {ik_result.reason}")
        else:
            # Failed - show why
            self.ik_solution = None
            self.ik_solution_text.setPlainText(f"❌ IK FAILED\n\n{ik_result.reason}\n\nError: {ik_result.error:.1f} mm")
            self.ik_status_label.setText(f"✗ {ik_result.reason}")
            self.ik_status_label.setStyleSheet("color: red;")
            self.ik_move_btn.setEnabled(False)
            self.log_console(f"IK Failed: {ik_result.reason}")

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

        # Update 3D visualization if auto-update is enabled
        if hasattr(self, 'viz_auto_update') and self.viz_auto_update.isChecked():
            self.update_3d_visualization()

    # 3D Visualization methods

    def on_joint_changed(self):
        """Called when a joint value changes"""
        # Only update if auto-update is enabled and visualization tab exists
        if hasattr(self, 'viz_auto_update') and self.viz_auto_update.isChecked():
            self.update_3d_visualization()

    def update_3d_visualization(self):
        """Update quad view visualization (Top, Front, Side, Perspective)"""
        # Get current joint angles from UI
        current_angles = {joint_id: ctrl['spinbox'].value()
                         for joint_id, ctrl in self.joint_controls.items()}

        # Calculate forward kinematics to get joint positions
        end_pos, joint_positions = self.kinematics.forward_kinematics(current_angles)

        # Extract coordinates for plotting
        x_coords = [p.x for p in joint_positions]
        y_coords = [p.y for p in joint_positions]
        z_coords = [p.z for p in joint_positions]

        max_range = 600  # mm

        # Draw each view
        for view_name, ax in self.viz_axes.items():
            ax.clear()

            # Plot the arm links (just lines, no markers on the line itself)
            ax.plot(x_coords, y_coords, z_coords,
                   'b-', linewidth=3, alpha=0.7)

            # Draw large, clickable joint markers
            # Skip first (base) and last (end effector) as they get special markers
            if len(joint_positions) > 2:
                mid_joints_x = x_coords[1:-1]
                mid_joints_y = y_coords[1:-1]
                mid_joints_z = z_coords[1:-1]
                ax.scatter(mid_joints_x, mid_joints_y, mid_joints_z,
                          c='red', s=250, marker='o', alpha=0.9,
                          edgecolors='darkred', linewidths=2.5,
                          label='Joints', picker=True, pickradius=10)

            # Highlight base (larger and distinct)
            ax.scatter([0], [0], [0],
                      c='green', s=300, marker='s', alpha=0.9,
                      edgecolors='darkgreen', linewidths=2.5,
                      label='Base')

            # Highlight end effector (larger and distinct)
            ax.scatter([end_pos.x], [end_pos.y], [end_pos.z],
                      c='orange', s=300, marker='^', alpha=0.9,
                      edgecolors='darkorange', linewidths=2.5,
                      label='End Effector', picker=True, pickradius=10)

            # Show drag target if enabled OR currently dragging
            if self.viz_target_pos and (self.viz_show_target.isChecked() or self.viz_dragging):
                ax.scatter([self.viz_target_pos[0]], [self.viz_target_pos[1]], [self.viz_target_pos[2]],
                          c='cyan', s=120, marker='*',
                          edgecolors='yellow', linewidths=2,
                          label='Target' if not self.viz_dragging else 'Dragging...')

            # Set axis limits (FIXED - never change during dragging)
            ax.set_xlim([-max_range, max_range])
            ax.set_ylim([-max_range, max_range])
            ax.set_zlim([0, max_range])

            # CRITICAL: Set equal aspect ratio to prevent scrunching
            # This ensures 1mm in X = 1mm in Y = 1mm in Z visually
            try:
                # For newer matplotlib versions
                ax.set_box_aspect([2, 2, 1])  # X:Y:Z aspect ratio (Z is half range)
            except AttributeError:
                # For older matplotlib versions
                pass

            # Disable autoscaling to prevent view changes during updates
            ax.set_autoscale_on(False)

            # Set axis labels
            ax.set_xlabel('X (mm)', fontsize=8)
            ax.set_ylabel('Y (mm)', fontsize=8)
            ax.set_zlabel('Z (mm)', fontsize=8)

            # Add grid
            ax.grid(True, alpha=0.3)

            # Set camera angle for each view (LOCKED)
            if view_name == 'top':
                # Top view: Looking down Z-axis
                ax.view_init(elev=90, azim=-90)
                ax.set_title('TOP VIEW (XY)', fontweight='bold', fontsize=9)
            elif view_name == 'front':
                # Front view: Looking from Y-axis
                ax.view_init(elev=0, azim=-90)
                ax.set_title('FRONT VIEW (XZ)', fontweight='bold', fontsize=9)
            elif view_name == 'side':
                # Side view: Looking from X-axis
                ax.view_init(elev=0, azim=0)
                ax.set_title('SIDE VIEW (YZ)', fontweight='bold', fontsize=9)
            else:  # perspective
                # Perspective view
                ax.view_init(elev=20, azim=45)
                ax.set_title('PERSPECTIVE', fontweight='bold', fontsize=9)

            # Disable mouse rotation for orthographic views
            if view_name in ['top', 'front', 'side']:
                ax.disable_mouse_rotation()

        # Update info label
        self.viz_info_label.setText(
            f"End Effector: ({end_pos.x:.1f}, {end_pos.y:.1f}, {end_pos.z:.1f}) mm  |  "
            f"Reach: {(end_pos.x**2 + end_pos.y**2 + end_pos.z**2)**0.5:.1f} mm"
        )

        # Redraw canvas
        # Don't use tight_layout during updates - it causes dynamic resizing/scrunching
        # We use fixed subplots_adjust() set during initialization instead
        self.viz_canvas.draw()

    def reset_3d_view(self):
        """Reset all views to default angles"""
        # Reset each view to its locked orientation
        self.viz_ax_top.view_init(elev=90, azim=-90)
        self.viz_ax_front.view_init(elev=0, azim=-90)
        self.viz_ax_side.view_init(elev=0, azim=0)
        self.viz_ax_persp.view_init(elev=20, azim=45)
        self.viz_canvas.draw()

    def toggle_axis_lock(self, axis: str):
        """Toggle axis lock for the visualizer"""
        current_lock = self.viz_event_filter.axis_lock

        if current_lock == axis:
            # Disable the lock
            self.viz_event_filter.axis_lock = None
            self.log_console(f"🔓 Removed {axis} axis lock")
        else:
            # Enable the lock
            self.viz_event_filter.axis_lock = axis
            self.log_console(f"🔒 Locked to {axis} axis")

        self.update_viz_axis_lock_indicator()

    def update_viz_axis_lock_indicator(self):
        """Update the axis lock UI indicators"""
        current_lock = self.viz_event_filter.axis_lock

        # Update button states
        self.axis_lock_x_btn.setChecked(current_lock == 'X')
        self.axis_lock_y_btn.setChecked(current_lock == 'Y')
        self.axis_lock_z_btn.setChecked(current_lock == 'Z')

        # Update status label
        if current_lock:
            self.axis_lock_status_label.setText(f"🔒 {current_lock} Axis")
            self.axis_lock_status_label.setStyleSheet("font-weight: bold; color: #ff6600;")
        else:
            self.axis_lock_status_label.setText("None")
            self.axis_lock_status_label.setStyleSheet("font-weight: bold; color: gray;")

    def on_viz_mouse_press(self, event):
        """Handle mouse press in 3D visualization"""
        # Debug: Log ALL mouse presses
        if event.button:
            button_name = {1: 'LEFT', 2: 'MIDDLE', 3: 'RIGHT'}.get(event.button, f'BUTTON{event.button}')
            self.log_console(f"Mouse press detected: {button_name} button, inaxes={event.inaxes is not None}")

        if not self.viz_interactive_mode.isChecked():
            self.log_console("Interactive mode is OFF - enable it to drag")
            return

        # Middle mouse button to start dragging
        if event.button == 2:
            if event.inaxes not in self.viz_axes.values():
                self.log_console("Middle-click detected but not in a viewport - click inside a view")
                return

            # Get current end effector position
            current_angles = {joint_id: ctrl['spinbox'].value()
                             for joint_id, ctrl in self.joint_controls.items()}
            end_pos, _ = self.kinematics.forward_kinematics(current_angles)

            self.viz_dragging = True
            self.viz_drag_start = (event.xdata, event.ydata)
            self.viz_target_pos = [end_pos.x, end_pos.y, end_pos.z]

            # Determine which viewport we're dragging in
            for view_name, ax in self.viz_axes.items():
                if event.inaxes == ax:
                    self.viz_drag_viewport = view_name
                    break

            # Temporarily disable auto-update to avoid conflicts
            self.viz_auto_update.setChecked(False)

            view_label = self.viz_drag_viewport.upper() if self.viz_drag_viewport else "UNKNOWN"
            self.log_console(f"✓ DRAG STARTED in {view_label} view at ({end_pos.x:.0f}, {end_pos.y:.0f}, {end_pos.z:.0f})")
            self.log_console(f"  Now move your mouse while holding middle button...")

    def on_viz_mouse_release(self, event):
        """Handle mouse release in 3D visualization"""
        if event.button == 2 and self.viz_dragging:
            self.viz_dragging = False
            self.viz_drag_start = None
            self.viz_drag_viewport = None
            self.viz_drag_counter = 0  # Reset counter

            # Calculate IK for final position if we have a target
            if self.viz_target_pos:
                from kinematics import Point3D
                target = Point3D(
                    x=self.viz_target_pos[0],
                    y=self.viz_target_pos[1],
                    z=self.viz_target_pos[2]
                )

                # Calculate IK
                current_angles = {joint_id: ctrl['spinbox'].value()
                                 for joint_id, ctrl in self.joint_controls.items()}
                ik_result = self.kinematics.inverse_kinematics(target, current_angles)

                if ik_result.success:
                    # Update joint controls
                    for joint_id, angle in ik_result.angles.items():
                        if joint_id in self.joint_controls:
                            self.joint_controls[joint_id]['slider'].setValue(int(angle))
                            self.joint_controls[joint_id]['spinbox'].setValue(angle)

                    if ik_result.is_approximate:
                        self.log_console(f"✓ Drag: {ik_result.reason}")
                    else:
                        self.log_console(f"✓ Moved to ({target.x:.1f}, {target.y:.1f}, {target.z:.1f}) - {ik_result.reason}")
                else:
                    self.log_console(f"✗ Drag failed: {ik_result.reason}")

            # Re-enable auto-update
            self.viz_auto_update.setChecked(True)
            self.update_3d_visualization()

    def on_viz_mouse_motion(self, event):
        """Handle mouse motion in 3D visualization"""
        # CRITICAL DEBUG: Log ALL motion events briefly
        if not hasattr(self, '_motion_event_count'):
            self._motion_event_count = 0
        self._motion_event_count += 1

        # Log every 100th motion to show we're getting events
        if self._motion_event_count % 100 == 1:
            self.log_console(f"💡 INFO: Received {self._motion_event_count} motion events total")

        if not self.viz_dragging:
            # Motion while NOT dragging - this is normal
            return

        self.log_console(f"✓✓✓ DRAG MOTION EVENT #{self.viz_drag_counter} ✓✓✓")

        if event.inaxes not in self.viz_axes.values():
            self.log_console(f"⚠ Motion event but cursor left viewport")
            return

        if event.xdata is None or event.ydata is None:
            self.log_console(f"⚠ Motion event but xdata/ydata is None")
            return

        # Calculate movement deltas (increase sensitivity)
        dx = (event.xdata - self.viz_drag_start[0])
        dy = (event.ydata - self.viz_drag_start[1])

        # Debug output every 10 motion events
        self.viz_drag_counter += 1
        if self.viz_drag_counter == 1:
            self.log_console(f"✓✓✓ FIRST DRAG MOTION! dx={dx:.2f}, dy={dy:.2f} ✓✓✓")

        # Increased sensitivity for better responsiveness
        sensitivity = 2.0

        # Update target position based on which viewport we're dragging in
        # Each viewport has different axes mappings
        if self.viz_drag_viewport == 'top':
            # Top view: drag in XY plane (looking down Z)
            self.viz_target_pos[0] += dx * sensitivity  # X
            self.viz_target_pos[1] += dy * sensitivity  # Y
            # Z stays constant
        elif self.viz_drag_viewport == 'front':
            # Front view: drag in XZ plane (looking from Y)
            self.viz_target_pos[0] += dx * sensitivity  # X
            self.viz_target_pos[2] += dy * sensitivity  # Z
            # Y stays constant
        elif self.viz_drag_viewport == 'side':
            # Side view: drag in YZ plane (looking from X)
            self.viz_target_pos[1] += dx * sensitivity  # Y
            self.viz_target_pos[2] += dy * sensitivity  # Z
            # X stays constant
        else:  # perspective or default
            # Perspective: drag in XY plane
            self.viz_target_pos[0] += dx * sensitivity  # X
            self.viz_target_pos[1] += dy * sensitivity  # Y

        # Clamp positions to reasonable workspace
        self.viz_target_pos[0] = max(-600, min(600, self.viz_target_pos[0]))
        self.viz_target_pos[1] = max(-600, min(600, self.viz_target_pos[1]))
        self.viz_target_pos[2] = max(0, min(600, self.viz_target_pos[2]))

        # Update drag start for next delta
        self.viz_drag_start = (event.xdata, event.ydata)

        # Calculate IK for preview
        from kinematics import Point3D
        target = Point3D(
            x=self.viz_target_pos[0],
            y=self.viz_target_pos[1],
            z=self.viz_target_pos[2]
        )

        # Get current angles for IK starting point
        current_angles = {joint_id: ctrl['spinbox'].value()
                         for joint_id, ctrl in self.joint_controls.items()}

        ik_result = self.kinematics.inverse_kinematics(target, current_angles)

        if ik_result.success:
            # Update joint controls temporarily (without triggering moves)
            for joint_id, angle in ik_result.angles.items():
                if joint_id in self.joint_controls:
                    self.joint_controls[joint_id]['spinbox'].blockSignals(True)
                    self.joint_controls[joint_id]['slider'].blockSignals(True)
                    self.joint_controls[joint_id]['slider'].setValue(int(angle))
                    self.joint_controls[joint_id]['spinbox'].setValue(angle)
                    self.joint_controls[joint_id]['spinbox'].blockSignals(False)
                    self.joint_controls[joint_id]['slider'].blockSignals(False)

            # Log position periodically (every 10th drag event)
            self.viz_drag_counter += 1
            if self.viz_drag_counter % 10 == 0:
                status_prefix = "~" if ik_result.is_approximate else ""
                self.viz_info_label.setText(
                    f"{status_prefix}Dragging: ({target.x:.1f}, {target.y:.1f}, {target.z:.1f}) mm, error: {ik_result.error:.1f}mm"
                )

            # Update visualization
            self.update_3d_visualization()
        else:
            # IK failed - log it occasionally
            self.viz_drag_counter += 1
            if self.viz_drag_counter % 20 == 0:
                self.log_console(f"✗ Drag IK failed: {ik_result.reason}")

    def on_viz_scroll(self, event):
        """Handle mouse scroll in 3D visualization"""
        if not self.viz_interactive_mode.isChecked():
            return

        # Scroll to move Z-axis (up/down)
        if event.inaxes in self.viz_axes.values():
            # Get current end effector position if not dragging
            if not self.viz_dragging:
                current_angles = {joint_id: ctrl['spinbox'].value()
                                 for joint_id, ctrl in self.joint_controls.items()}
                end_pos, _ = self.kinematics.forward_kinematics(current_angles)
                self.viz_target_pos = [end_pos.x, end_pos.y, end_pos.z]

            # Scroll up = increase Z, scroll down = decrease Z
            dz = 10 if event.step > 0 else -10
            self.viz_target_pos[2] += dz

            # Clamp Z to reasonable range
            self.viz_target_pos[2] = max(0, min(600, self.viz_target_pos[2]))

            # Calculate IK
            from kinematics import Point3D
            target = Point3D(
                x=self.viz_target_pos[0],
                y=self.viz_target_pos[1],
                z=self.viz_target_pos[2]
            )

            current_angles = {joint_id: ctrl['spinbox'].value()
                             for joint_id, ctrl in self.joint_controls.items()}
            ik_result = self.kinematics.inverse_kinematics(target, current_angles)

            if ik_result.success:
                # Update joint controls
                for joint_id, angle in ik_result.angles.items():
                    if joint_id in self.joint_controls:
                        self.joint_controls[joint_id]['slider'].setValue(int(angle))
                        self.joint_controls[joint_id]['spinbox'].setValue(angle)

                status = "~" if ik_result.is_approximate else "✓"
                self.log_console(f"{status} Scroll: Z={self.viz_target_pos[2]:.1f} mm (error: {ik_result.error:.1f}mm)")
                self.update_3d_visualization()
            else:
                self.log_console(f"✗ Scroll failed: {ik_result.reason}")

    def on_viz_key_press(self, event):
        """Handle keyboard control of end effector"""
        if not self.viz_interactive_mode.isChecked():
            return

        # Get current end effector position
        current_angles = {joint_id: ctrl['spinbox'].value()
                         for joint_id, ctrl in self.joint_controls.items()}
        end_pos, _ = self.kinematics.forward_kinematics(current_angles)

        # Set target position to current
        target_pos = [end_pos.x, end_pos.y, end_pos.z]

        # Movement step size
        step = 10  # mm

        # Update target based on key
        moved = False
        if event.key == 'left':
            target_pos[0] -= step
            moved = True
            self.log_console(f"← Keyboard: X-{step}mm")
        elif event.key == 'right':
            target_pos[0] += step
            moved = True
            self.log_console(f"→ Keyboard: X+{step}mm")
        elif event.key == 'up':
            target_pos[1] += step
            moved = True
            self.log_console(f"↑ Keyboard: Y+{step}mm")
        elif event.key == 'down':
            target_pos[1] -= step
            moved = True
            self.log_console(f"↓ Keyboard: Y-{step}mm")
        elif event.key == 'pageup':
            target_pos[2] += step
            moved = True
            self.log_console(f"⤴ Keyboard: Z+{step}mm")
        elif event.key == 'pagedown':
            target_pos[2] -= step
            moved = True
            self.log_console(f"⤵ Keyboard: Z-{step}mm")

        if moved:
            # Clamp to workspace
            target_pos[0] = max(-600, min(600, target_pos[0]))
            target_pos[1] = max(-600, min(600, target_pos[1]))
            target_pos[2] = max(0, min(600, target_pos[2]))

            # Calculate IK
            from kinematics import Point3D
            target = Point3D(x=target_pos[0], y=target_pos[1], z=target_pos[2])

            ik_result = self.kinematics.inverse_kinematics(target, current_angles)

            if ik_result.success:
                # Update joint controls
                for joint_id, angle in ik_result.angles.items():
                    if joint_id in self.joint_controls:
                        self.joint_controls[joint_id]['slider'].setValue(int(angle))
                        self.joint_controls[joint_id]['spinbox'].setValue(angle)

                self.viz_target_pos = target_pos
                self.update_3d_visualization()
            else:
                self.log_console(f"✗ Keyboard move failed: {ik_result.reason}")

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
            summary += f"Base Height: {dims.get('base_height', 137):.0f}\n"
            summary += f"Shoulder Offset: {dims.get('shoulder_offset', 0):.0f}\n"
            summary += f"Upper Arm: {dims.get('upper_arm', 240):.0f}\n"
            summary += f"Forearm: {dims.get('forearm', 133):.0f}\n"
            summary += f"Wrist Length: {dims.get('wrist_length', 100):.0f}\n"

            # Calculate and show max reach
            total = dims.get('upper_arm', 240) + dims.get('forearm', 133) + dims.get('wrist_length', 100)
            summary += f"\nMaximum Reach: {total:.0f} mm\n"
        else:
            summary += "Using default Thor dimensions (Base: 137mm, Upper: 240mm, Forearm: 133mm, Wrist: 100mm)\n"

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

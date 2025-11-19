#!/usr/bin/env python3
"""
Interactive 3D Robot Arm Viewer

Provides real-time 3D visualization and interactive manipulation
of the Thor robotic arm.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3D
from typing import Optional, Callable, List, Tuple, Dict
import matplotlib
matplotlib.use('Qt5Agg')

from kinematics import ThorKinematics, Point3D
from robot_controller import RobotController, MovementType


class Interactive3DViewer:
    """
    Interactive 3D visualization of robot arm with drag-to-position control
    """

    def __init__(self, kinematics: Optional[ThorKinematics] = None,
                 robot_controller: Optional[RobotController] = None):
        """
        Initialize 3D viewer

        Args:
            kinematics: Kinematics instance (creates new if None)
            robot_controller: Robot controller for sending commands
        """
        self.kin = kinematics if kinematics else ThorKinematics()
        self.robot = robot_controller

        # Matplotlib setup
        self.fig = plt.figure(figsize=(12, 9))
        self.ax = self.fig.add_subplot(111, projection='3d')

        # Visualization elements
        self.arm_lines = None
        self.joint_scatter = None
        self.target_scatter = None
        self.workspace_surface = None

        # Interactive state
        self.target_point = None
        self.dragging = False
        self.selected_point = None

        # Callbacks
        self.on_target_changed: Optional[Callable[[Point3D], None]] = None
        self.on_angles_changed: Optional[Callable[[Dict[str, float]], None]] = None

        # Setup
        self._setup_plot()
        self._connect_events()

    def _setup_plot(self):
        """Setup 3D plot appearance"""
        # Get workspace bounds
        bounds = self.kin.get_workspace_bounds()

        # Set axis limits
        max_range = max(bounds['x'][1], bounds['y'][1], bounds['z'][1])
        self.ax.set_xlim([-max_range, max_range])
        self.ax.set_ylim([-max_range, max_range])
        self.ax.set_zlim([0, max_range])

        # Labels
        self.ax.set_xlabel('X (mm)', fontsize=10)
        self.ax.set_ylabel('Y (mm)', fontsize=10)
        self.ax.set_zlabel('Z (mm)', fontsize=10)
        self.ax.set_title('Thor Robot Arm - Interactive 3D View\n(Drag red target to move)',
                         fontsize=12, fontweight='bold')

        # Grid
        self.ax.grid(True, alpha=0.3)

        # Equal aspect ratio
        self.ax.set_box_aspect([1, 1, 1])

        # Draw workspace
        self._draw_workspace()

    def _draw_workspace(self):
        """Draw workspace boundary"""
        # Draw workspace as a hemisphere
        max_reach = (self.kin.params['upper_arm'] +
                    self.kin.params['forearm'] +
                    self.kin.params['wrist_length'])

        # Create hemisphere
        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, np.pi / 2, 15)
        x = max_reach * np.outer(np.cos(u), np.sin(v))
        y = max_reach * np.outer(np.sin(u), np.sin(v))
        z = max_reach * np.outer(np.ones(np.size(u)), np.cos(v))

        self.workspace_surface = self.ax.plot_surface(
            x, y, z, alpha=0.1, color='cyan', edgecolor='none'
        )

    def _connect_events(self):
        """Connect matplotlib events for interactivity"""
        self.fig.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.fig.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)

    def update_arm(self, joint_angles: Optional[Dict[str, float]] = None):
        """
        Update arm visualization

        Args:
            joint_angles: Joint angles to display (uses current if None)
        """
        # Calculate forward kinematics
        end_pos, joint_positions = self.kin.forward_kinematics(joint_angles)

        # Extract coordinates
        xs = [p.x for p in joint_positions]
        ys = [p.y for p in joint_positions]
        zs = [p.z for p in joint_positions]

        # Remove old arm visualization
        if self.arm_lines:
            self.arm_lines.remove()
        if self.joint_scatter:
            self.joint_scatter.remove()

        # Draw arm as connected lines
        self.arm_lines = self.ax.plot(xs, ys, zs,
                                      'o-', linewidth=3, markersize=8,
                                      color='blue', markerfacecolor='darkblue',
                                      label='Robot Arm')[0]

        # Highlight end effector
        self.joint_scatter = self.ax.scatter([end_pos.x], [end_pos.y], [end_pos.z],
                                            c='green', s=200, marker='o',
                                            edgecolors='darkgreen', linewidth=2,
                                            label='End Effector', zorder=10)

        # Add joint labels
        for i, (x, y, z) in enumerate(zip(xs, ys, zs)):
            self.ax.text(x, y, z, f'  J{i}', fontsize=8)

        # Trigger callback
        if self.on_angles_changed and joint_angles:
            self.on_angles_changed(joint_angles)

        self.fig.canvas.draw_idle()

    def set_target(self, target: Point3D, update_arm: bool = True):
        """
        Set target position for end effector

        Args:
            target: Target 3D position
            update_arm: If True, solve IK and update arm position
        """
        self.target_point = target

        # Remove old target marker
        if self.target_scatter:
            self.target_scatter.remove()

        # Draw target
        self.target_scatter = self.ax.scatter(
            [target.x], [target.y], [target.z],
            c='red', s=300, marker='*',
            edgecolors='darkred', linewidth=2,
            label='Target', zorder=15
        )

        if update_arm:
            # Solve inverse kinematics
            if self.kin.is_reachable(target):
                solution = self.kin.inverse_kinematics(target)
                if solution:
                    self.update_arm(solution)
                    print(f"Target reached: ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})")

                    # Trigger callback
                    if self.on_target_changed:
                        self.on_target_changed(target)
                else:
                    print("IK solution not found")
            else:
                print(f"Target out of reach: ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})")

        self.fig.canvas.draw_idle()

    def _on_mouse_press(self, event):
        """Handle mouse button press"""
        if event.inaxes != self.ax:
            return

        if event.button == 1:  # Left click
            # Check if clicking near target
            if self.target_point:
                # Get 2D projection of target
                proj_x, proj_y = self._project_3d_to_2d(self.target_point)

                # Check distance
                if event.xdata and event.ydata:
                    dist = np.sqrt((event.xdata - proj_x)**2 + (event.ydata - proj_y)**2)

                    if dist < 0.1:  # Close enough to drag
                        self.dragging = True
                        self.selected_point = self.target_point

    def _on_mouse_release(self, event):
        """Handle mouse button release"""
        self.dragging = False
        self.selected_point = None

    def _on_mouse_move(self, event):
        """Handle mouse movement for dragging"""
        if not self.dragging or not self.selected_point:
            return

        if event.inaxes != self.ax and event.xdata and event.ydata:
            return

        # Update target position based on mouse
        # Keep current Z, update X and Y based on mouse position
        if event.xdata is not None and event.ydata is not None:
            new_target = Point3D(
                event.xdata,
                event.ydata,
                self.selected_point.z
            )
            self.set_target(new_target, update_arm=True)

    def _project_3d_to_2d(self, point: Point3D) -> Tuple[float, float]:
        """
        Project 3D point to 2D screen coordinates

        Args:
            point: 3D point

        Returns:
            Tuple of (x, y) in 2D
        """
        # This is a simplified projection
        # Matplotlib handles the actual 3D->2D transformation
        return point.x, point.y

    def add_waypoint_marker(self, point: Point3D, label: str = "", color: str = 'orange'):
        """
        Add a waypoint marker to the visualization

        Args:
            point: Waypoint position
            label: Optional label
            color: Marker color
        """
        self.ax.scatter([point.x], [point.y], [point.z],
                       c=color, s=150, marker='^',
                       edgecolors='black', linewidth=1.5,
                       label=label if label else 'Waypoint')

        if label:
            self.ax.text(point.x, point.y, point.z, f'  {label}', fontsize=9)

        self.fig.canvas.draw_idle()

    def draw_path(self, points: List[Point3D], color: str = 'purple', alpha: float = 0.5):
        """
        Draw a path through multiple points

        Args:
            points: List of 3D points
            color: Path color
            alpha: Transparency
        """
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        zs = [p.z for p in points]

        self.ax.plot(xs, ys, zs,
                    '--', linewidth=2, color=color, alpha=alpha,
                    label='Planned Path')

        self.fig.canvas.draw_idle()

    def clear_markers(self):
        """Clear all markers and paths (keeps arm and workspace)"""
        # This would require tracking all added elements
        # For now, redraw everything
        self.ax.clear()
        self._setup_plot()
        self.update_arm()

    def send_to_robot(self):
        """Send current target to physical robot"""
        if not self.robot or not self.robot.is_connected():
            print("Robot not connected")
            return

        if not self.target_point:
            print("No target set")
            return

        # Get current joint angles from kinematics
        angles = self.kin.joint_angles

        # Send to robot
        self.robot.move_all_joints(angles, MovementType.G1_LINEAR, feedrate=300)
        print(f"Sent position to robot: {angles}")

    def show(self):
        """Display the viewer"""
        # Initial pose
        self.update_arm()

        # Add legend
        self.ax.legend(loc='upper right', fontsize=9)

        plt.tight_layout()
        plt.show()


class SliderControl3D:
    """
    3D viewer with joint angle sliders for manual control
    """

    def __init__(self, viewer: Interactive3DViewer):
        """
        Initialize slider controls

        Args:
            viewer: Interactive3DViewer instance
        """
        self.viewer = viewer
        self.sliders = {}
        self.slider_axes = []

        self._create_sliders()

    def _create_sliders(self):
        """Create slider widgets for each joint"""
        from matplotlib.widgets import Slider

        # Adjust figure to make room for sliders
        self.viewer.fig.subplots_adjust(left=0.15, bottom=0.25)

        # Joint definitions
        joints = [
            ('A', 'Base', -180, 180),
            ('B', 'Shoulder', -90, 90),
            ('D', 'Elbow', -90, 90),
            ('X', 'Wrist Pitch', -90, 90),
            ('Y', 'Wrist Roll', -90, 90),
        ]

        # Create sliders
        for i, (key, label, min_val, max_val) in enumerate(joints):
            # Position for this slider
            ax_slider = self.viewer.fig.add_axes([0.15, 0.18 - i * 0.03, 0.7, 0.02])
            self.slider_axes.append(ax_slider)

            # Create slider
            slider = Slider(
                ax_slider, label, min_val, max_val,
                valinit=self.viewer.kin.joint_angles.get(key, 0),
                valstep=1.0
            )

            # Connect callback
            slider.on_changed(lambda val, k=key: self._on_slider_change(k, val))

            self.sliders[key] = slider

    def _on_slider_change(self, joint_key: str, value: float):
        """Handle slider value change"""
        # Update kinematics
        self.viewer.kin.joint_angles[joint_key] = value

        # Handle coupled joints
        if joint_key == 'B':
            self.viewer.kin.joint_angles['C'] = value

        # Update visualization
        self.viewer.update_arm(self.viewer.kin.joint_angles)


def create_interactive_viewer(robot: Optional[RobotController] = None,
                              use_sliders: bool = True) -> Interactive3DViewer:
    """
    Create and configure interactive 3D viewer

    Args:
        robot: Optional robot controller for sending commands
        use_sliders: Add joint angle sliders

    Returns:
        Configured viewer instance
    """
    viewer = Interactive3DViewer(robot_controller=robot)

    if use_sliders:
        SliderControl3D(viewer)

    return viewer


def demo_interactive_viewer():
    """Demo the interactive 3D viewer"""
    print("=== Interactive 3D Viewer Demo ===\n")
    print("Controls:")
    print("  - Use sliders to adjust joint angles")
    print("  - Click and drag red target star to move end effector")
    print("  - Rotate view by dragging")
    print("  - Close window to exit\n")

    # Create viewer
    viewer = create_interactive_viewer(use_sliders=True)

    # Set initial target
    initial_target = Point3D(200, 100, 200)
    viewer.set_target(initial_target)

    # Add some waypoints for demonstration
    viewer.add_waypoint_marker(Point3D(150, 150, 100), "WP1", 'yellow')
    viewer.add_waypoint_marker(Point3D(250, 50, 150), "WP2", 'yellow')

    # Show viewer
    viewer.show()


if __name__ == '__main__':
    demo_interactive_viewer()

#!/usr/bin/env python3
"""
Examples for 3D Robot Control and Visualization

Demonstrates various ways to use the 3D visualization and kinematics features
"""

from kinematics import ThorKinematics, Point3D
from viewer_3d import Interactive3DViewer, create_interactive_viewer
from robot_controller import RobotController, MovementType
from path_planner import PathPlanner, Waypoint, InterpolationMethod
import time


def example_1_basic_kinematics():
    """Example 1: Basic Forward and Inverse Kinematics"""
    print("="*60)
    print("Example 1: Basic Kinematics")
    print("="*60 + "\n")

    kin = ThorKinematics()

    # Forward kinematics
    print("1. Forward Kinematics:")
    print("   Set joint angles and calculate end effector position\n")

    angles = {'A': 0, 'B': 45, 'D': -30, 'X': 0, 'Y': 0}
    print(f"   Input joint angles: {angles}")

    end_pos, joints = kin.forward_kinematics(angles)
    print(f"   End effector position: ({end_pos.x:.1f}, {end_pos.y:.1f}, {end_pos.z:.1f}) mm\n")

    # Inverse kinematics
    print("2. Inverse Kinematics:")
    print("   Set target position and calculate joint angles\n")

    target = Point3D(200, 100, 200)
    print(f"   Target position: ({target.x:.1f}, {target.y:.1f}, {target.z:.1f}) mm")

    if kin.is_reachable(target):
        solution = kin.inverse_kinematics(target)
        if solution:
            print(f"   Solution: {solution}")

            # Verify
            verify_pos, _ = kin.forward_kinematics(solution)
            error = ((verify_pos.x - target.x)**2 +
                    (verify_pos.y - target.y)**2 +
                    (verify_pos.z - target.z)**2) ** 0.5
            print(f"   Verification error: {error:.2f} mm")
        else:
            print("   No solution found")
    else:
        print("   Target out of reach!")


def example_2_interactive_viewer():
    """Example 2: Interactive 3D Viewer"""
    print("\n" + "="*60)
    print("Example 2: Interactive 3D Viewer")
    print("="*60 + "\n")

    print("Starting interactive 3D viewer...")
    print("\nControls:")
    print("  - Use sliders to adjust joint angles")
    print("  - Rotate view by clicking and dragging")
    print("  - Zoom with scroll wheel")
    print("  - Close window when done\n")

    # Create viewer with sliders
    viewer = create_interactive_viewer(use_sliders=True)

    # Set initial target
    target = Point3D(250, 50, 200)
    viewer.set_target(target)

    # Add waypoints for visualization
    viewer.add_waypoint_marker(Point3D(200, 0, 100), "Start", 'green')
    viewer.add_waypoint_marker(Point3D(200, 100, 200), "Mid", 'yellow')
    viewer.add_waypoint_marker(Point3D(200, 0, 300), "End", 'red')

    # Show viewer
    viewer.show()


def example_3_path_visualization():
    """Example 3: Visualize Planned Path in 3D"""
    print("\n" + "="*60)
    print("Example 3: Path Visualization")
    print("="*60 + "\n")

    print("Creating smooth path and visualizing in 3D...\n")

    # Create kinematics and viewer
    kin = ThorKinematics()
    viewer = Interactive3DViewer()

    # Create path planner
    planner = PathPlanner()

    # Define waypoints (in joint space)
    waypoints = [
        Waypoint({'A': 0, 'B': 0, 'D': 0}),
        Waypoint({'A': 45, 'B': 30, 'D': -20}),
        Waypoint({'A': 90, 'B': 45, 'D': -30}),
        Waypoint({'A': 45, 'B': 30, 'D': -20}),
        Waypoint({'A': 0, 'B': 0, 'D': 0}),
    ]

    # Generate smooth path
    path = planner.generate_multi_waypoint_path(
        waypoints,
        points_per_segment=10,
        method=InterpolationMethod.QUINTIC
    )

    print(f"Generated path with {len(path)} points")

    # Convert to 3D positions
    path_3d = []
    for joint_angles in path:
        end_pos, _ = kin.forward_kinematics(joint_angles)
        path_3d.append(end_pos)

    # Visualize
    viewer.draw_path(path_3d, color='purple', alpha=0.7)

    # Mark waypoints
    for i, wp in enumerate(waypoints):
        end_pos, _ = kin.forward_kinematics(wp.positions)
        viewer.add_waypoint_marker(end_pos, f"WP{i}", 'orange')

    # Show current position (last point)
    viewer.update_arm(path[-1])

    print("\nShowing 3D visualization...")
    viewer.show()


def example_4_vision_to_3d():
    """Example 4: Vision-Guided 3D Control"""
    print("\n" + "="*60)
    print("Example 4: Vision-Guided 3D Control")
    print("="*60 + "\n")

    print("This example shows how to use vision detection with 3D control")
    print("(Requires camera and calibration)\n")

    # Simulated vision detection (replace with actual vision controller)
    detected_objects = [
        Point3D(200, 100, 50),   # Object 1
        Point3D(150, 150, 50),   # Object 2
        Point3D(250, 50, 50),    # Object 3
    ]

    kin = ThorKinematics()
    viewer = Interactive3DViewer()

    # Visualize detected objects
    for i, obj in enumerate(detected_objects):
        viewer.add_waypoint_marker(obj, f"Obj{i+1}", 'cyan')
        print(f"Object {i+1} at ({obj.x:.1f}, {obj.y:.1f}, {obj.z:.1f})")

    # Pick first object
    print(f"\nPlanning to pick Object 1...")
    target = detected_objects[0]

    # Add approach offset (hover above object)
    approach = Point3D(target.x, target.y, target.z + 100)

    if kin.is_reachable(approach):
        solution = kin.inverse_kinematics(approach)
        if solution:
            print(f"Solution found: {solution}")
            viewer.set_target(approach)
            viewer.update_arm(solution)
        else:
            print("IK failed")
    else:
        print("Target out of reach")

    viewer.show()


def example_5_robot_with_3d():
    """Example 5: Control Real Robot with 3D Viewer"""
    print("\n" + "="*60)
    print("Example 5: Real Robot Control with 3D")
    print("="*60 + "\n")

    print("This example connects to real robot and uses 3D visualization")
    print("(Requires robot connection)\n")

    # Create robot controller
    robot = RobotController()

    # Try to connect
    proceed = input("Connect to robot? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Skipping robot connection")
        return

    port = input("Enter serial port (e.g., /dev/ttyUSB0): ").strip()

    if robot.connect(port, 115200):
        print(f"✓ Connected to robot on {port}\n")

        # Create viewer with robot
        viewer = create_interactive_viewer(robot=robot, use_sliders=True)

        # Callback when target changes
        def on_target_changed(target: Point3D):
            print(f"Target changed to: ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})")

            send = input("Send to robot? (y/n): ").strip().lower()
            if send == 'y':
                viewer.send_to_robot()

        viewer.on_target_changed = on_target_changed

        print("3D viewer with robot control active")
        print("Adjust sliders or drag target to control robot")
        print("Close window when done\n")

        viewer.show()

        robot.disconnect()
        print("\n✓ Disconnected from robot")
    else:
        print("✗ Failed to connect to robot")


def example_6_workspace_analysis():
    """Example 6: Analyze Robot Workspace"""
    print("\n" + "="*60)
    print("Example 6: Workspace Analysis")
    print("="*60 + "\n")

    kin = ThorKinematics()

    # Get workspace bounds
    bounds = kin.get_workspace_bounds()

    print("Workspace Bounds:")
    for axis, (min_val, max_val) in bounds.items():
        print(f"  {axis}: [{min_val:.1f}, {max_val:.1f}] mm")

    # Test reachability of various points
    print("\nReachability Test:")

    test_points = [
        Point3D(100, 100, 100),
        Point3D(300, 0, 200),
        Point3D(500, 500, 500),  # Probably out of reach
        Point3D(0, 0, 50),
    ]

    for point in test_points:
        reachable = kin.is_reachable(point)
        status = "✓ Reachable" if reachable else "✗ Out of reach"
        print(f"  ({point.x:.0f}, {point.y:.0f}, {point.z:.0f}): {status}")

    # Visualize reachable and unreachable points
    viewer = Interactive3DViewer()

    for point in test_points:
        color = 'green' if kin.is_reachable(point) else 'red'
        label = "R" if kin.is_reachable(point) else "U"
        viewer.add_waypoint_marker(point, label, color)

    viewer.update_arm()
    print("\nShowing workspace visualization...")
    viewer.show()


def main():
    """Main menu for 3D control examples"""
    print("\n" + "="*60)
    print("3D Robot Control Examples")
    print("="*60 + "\n")

    examples = {
        '1': ('Basic Kinematics', example_1_basic_kinematics),
        '2': ('Interactive 3D Viewer', example_2_interactive_viewer),
        '3': ('Path Visualization', example_3_path_visualization),
        '4': ('Vision-Guided 3D', example_4_vision_to_3d),
        '5': ('Real Robot Control', example_5_robot_with_3d),
        '6': ('Workspace Analysis', example_6_workspace_analysis),
    }

    print("Available Examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  a. Run all (non-interactive)")
    print("  q. Quit\n")

    while True:
        choice = input("Select example (1-6, a, q): ").strip().lower()

        if choice == 'q':
            print("\nGoodbye!\n")
            break

        if choice == 'a':
            # Run non-interactive examples
            example_1_basic_kinematics()
            input("\nPress Enter to continue...")
            example_6_workspace_analysis()
            break

        if choice in examples:
            name, func = examples[choice]
            try:
                func()
            except KeyboardInterrupt:
                print("\n\nExample interrupted\n")
            except Exception as e:
                print(f"\n✗ Error: {e}\n")

            input("\nPress Enter to return to menu...")
            print("\n")
        else:
            print("Invalid choice\n")


if __name__ == '__main__':
    main()

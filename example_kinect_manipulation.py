#!/usr/bin/env python3
"""
Kinect-Based Robot Manipulation Examples

Demonstrates using Kinect RGB-D camera for improved robotic manipulation:
1. Pick and place with accurate 3D localization
2. Obstacle avoidance using depth sensing
3. Volumetric measurements
4. Multi-object sorting by depth
5. Collision-free path planning
6. Workspace mapping

The Kinect provides depth information which dramatically improves
manipulation accuracy compared to monocular vision.
"""

import time
import numpy as np
import cv2
from typing import List, Tuple, Optional

from kinect_interface import KinectInterface, visualize_depth
from vision_controller_3d import VisionController3D, Object3D
from robot_controller import RobotController, MovementType
from vision_controller import CoordinateTransformer


class KinectManipulation:
    """
    Robot manipulation using Kinect RGB-D camera

    Provides high-level manipulation primitives with depth sensing
    """

    def __init__(self, robot: RobotController, kinect: KinectInterface,
                 transformer: Optional[CoordinateTransformer] = None):
        """
        Initialize Kinect manipulation system

        Args:
            robot: Robot controller
            kinect: Kinect camera interface
            transformer: Camera-to-robot coordinate transformer
        """
        self.robot = robot
        self.kinect = kinect
        self.vision = VisionController3D(kinect, transformer)

        # Safety parameters
        self.min_safe_depth = 200  # mm - minimum approach distance
        self.max_reach = 500       # mm - maximum reach from robot base

    def example_1_accurate_pick_and_place(self):
        """
        Example 1: Accurate Pick and Place

        Uses depth information for precise object localization and grasping
        """
        print("\n" + "=" * 60)
        print("Example 1: Accurate Pick and Place with Depth")
        print("=" * 60 + "\n")

        print("Place a red object in the workspace...")
        input("Press Enter when ready...")

        # Capture frame
        self.vision.capture_frame()

        # Detect red objects
        objects = self.vision.detect_objects_color(
            lower_hsv=(0, 100, 100),
            upper_hsv=(10, 255, 255)
        )

        if not objects:
            print("No objects detected")
            return

        # Sort by confidence
        objects.sort(key=lambda x: x.confidence, reverse=True)
        target = objects[0]

        print(f"\nDetected: {target.label}")
        print(f"  2D position: {target.position_2d}")
        print(f"  3D position: ({target.position_3d[0]:.1f}, {target.position_3d[1]:.1f}, {target.position_3d[2]:.1f}) mm")
        print(f"  Depth: {target.depth/1000:.3f} m")

        if target.position_robot:
            print(f"  Robot coordinates: ({target.position_robot[0]:.1f}, {target.position_robot[1]:.1f}, {target.position_robot[2]:.1f}) mm")

            # Calculate approach height (above object)
            approach_height = target.position_robot[2] + 50  # 50mm above

            print(f"\nExecuting pick sequence...")

            # 1. Move to approach position
            print("  1. Moving to approach position...")
            self.robot.move_to_position(
                target.position_robot[0],
                target.position_robot[1],
                approach_height,
                feedrate=300
            )
            time.sleep(1)

            # 2. Descend to grasp
            print("  2. Descending to grasp...")
            self.robot.move_to_position(
                target.position_robot[0],
                target.position_robot[1],
                target.position_robot[2] + 10,  # 10mm above object
                feedrate=100
            )
            time.sleep(0.5)

            # 3. Close gripper (simulated)
            print("  3. Closing gripper...")
            time.sleep(0.5)

            # 4. Lift object
            print("  4. Lifting object...")
            self.robot.move_to_position(
                target.position_robot[0],
                target.position_robot[1],
                approach_height,
                feedrate=200
            )
            time.sleep(1)

            # 5. Move to place position
            place_x = target.position_robot[0] + 100
            place_y = target.position_robot[1]

            print(f"  5. Moving to place position...")
            self.robot.move_to_position(place_x, place_y, approach_height, feedrate=300)
            time.sleep(1)

            # 6. Place object
            print("  6. Placing object...")
            self.robot.move_to_position(place_x, place_y, target.position_robot[2] + 10, feedrate=100)
            time.sleep(0.5)

            # 7. Open gripper
            print("  7. Opening gripper...")
            time.sleep(0.5)

            # 8. Retract
            print("  8. Retracting...")
            self.robot.move_to_position(place_x, place_y, approach_height, feedrate=200)

            print("\n✓ Pick and place complete!\n")

        # Show visualization
        vis = self.vision.visualize_detections(objects)
        cv2.imshow('Detected Objects', vis)
        cv2.waitKey(3000)
        cv2.destroyAllWindows()

    def example_2_obstacle_avoidance(self):
        """
        Example 2: Obstacle Avoidance

        Uses depth map to detect obstacles and plan collision-free paths
        """
        print("\n" + "=" * 60)
        print("Example 2: Obstacle Avoidance with Depth Sensing")
        print("=" * 60 + "\n")

        print("Place obstacles in the workspace...")
        input("Press Enter to scan...")

        # Capture depth map
        self.vision.capture_frame()
        frame = self.vision.current_frame

        # Create obstacle map
        print("\nAnalyzing workspace...")

        # Find regions closer than safe distance
        obstacle_mask = (frame.depth > 0) & (frame.depth < self.min_safe_depth)

        # Visualize
        depth_viz = visualize_depth(frame.depth)
        obstacle_viz = cv2.cvtColor(obstacle_mask.astype(np.uint8) * 255, cv2.COLOR_GRAY2BGR)
        obstacle_viz[:, :, 2] = 255  # Red obstacles

        combined = cv2.addWeighted(depth_viz, 0.7, obstacle_viz, 0.3, 0)

        cv2.putText(combined, "Red = Too Close (Obstacles)", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow('Obstacle Map', combined)
        cv2.waitKey(3000)
        cv2.destroyAllWindows()

        # Count obstacle pixels
        obstacle_count = np.sum(obstacle_mask)
        workspace_size = frame.depth.size

        obstacle_percent = (obstacle_count / workspace_size) * 100

        print(f"\nWorkspace analysis:")
        print(f"  Obstacle coverage: {obstacle_percent:.1f}%")
        print(f"  Safe for operation: {'Yes' if obstacle_percent < 30 else 'No'}")

    def example_3_volume_measurement(self):
        """
        Example 3: Volumetric Measurements

        Estimates object volumes using point cloud data
        """
        print("\n" + "=" * 60)
        print("Example 3: Object Volume Measurement")
        print("=" * 60 + "\n")

        print("Place objects to measure in workspace...")
        input("Press Enter to measure...")

        # Capture and detect
        self.vision.capture_frame()
        objects = self.vision.detect_objects_depth_clustering()

        if not objects:
            print("No objects detected")
            return

        print(f"\nDetected {len(objects)} objects:\n")

        for i, obj in enumerate(objects, 1):
            print(f"Object {i}:")
            print(f"  Position: ({obj.position_3d[0]:.1f}, {obj.position_3d[1]:.1f}, {obj.position_3d[2]:.1f}) mm")

            if obj.bbox_3d:
                size = obj.bbox_3d['size']
                print(f"  Dimensions: {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm")

            if obj.volume:
                volume_cm3 = obj.volume / 1000  # mm³ to cm³
                volume_ml = volume_cm3  # 1 cm³ = 1 ml
                print(f"  Bounding volume: {volume_cm3:.1f} cm³ ({volume_ml:.1f} ml)")

            if obj.point_cloud is not None:
                print(f"  Point cloud: {len(obj.point_cloud)} points")

            print()

        # Visualize
        vis = self.vision.visualize_detections(objects)
        cv2.imshow('Volume Measurements', vis)
        cv2.waitKey(3000)
        cv2.destroyAllWindows()

    def example_4_depth_based_sorting(self):
        """
        Example 4: Multi-Object Sorting by Depth

        Sorts objects by their distance from camera/robot
        """
        print("\n" + "=" * 60)
        print("Example 4: Depth-Based Object Sorting")
        print("=" * 60 + "\n")

        print("Place multiple objects at different depths...")
        input("Press Enter to detect...")

        # Capture and detect
        self.vision.capture_frame()
        objects = self.vision.detect_objects_depth_clustering()

        if len(objects) < 2:
            print("Need at least 2 objects for sorting")
            return

        # Sort by depth (closest first)
        objects.sort(key=lambda x: x.depth)

        print(f"\nDetected {len(objects)} objects, sorted by depth:\n")

        for i, obj in enumerate(objects, 1):
            print(f"{i}. {obj.label}")
            print(f"   Depth: {obj.depth/1000:.3f} m")
            print(f"   Position: ({obj.position_3d[0]:.1f}, {obj.position_3d[1]:.1f}, {obj.position_3d[2]:.1f}) mm")

        print("\nPick order (closest to farthest):")
        for i, obj in enumerate(objects, 1):
            print(f"  {i}. Pick object at depth {obj.depth/1000:.3f}m")

        # Visualize with numbering
        vis = self.vision.visualize_detections(objects)

        for i, obj in enumerate(objects, 1):
            cv2.putText(vis, str(i), (obj.position_2d[0]-10, obj.position_2d[1]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)

        cv2.imshow('Sorted by Depth', vis)
        cv2.waitKey(5000)
        cv2.destroyAllWindows()

    def example_5_workspace_mapping(self):
        """
        Example 5: 3D Workspace Mapping

        Creates a 3D map of the entire workspace
        """
        print("\n" + "=" * 60)
        print("Example 5: 3D Workspace Mapping")
        print("=" * 60 + "\n")

        print("Mapping workspace...")

        # Capture frame
        self.vision.capture_frame()
        frame = self.vision.current_frame

        # Generate full point cloud
        point_cloud = frame.get_point_cloud(self.kinect.camera_matrix)

        print(f"\nWorkspace point cloud:")
        print(f"  Total points: {len(point_cloud):,}")

        # Analyze workspace bounds
        points_3d = point_cloud[:, :3]

        min_bounds = np.min(points_3d, axis=0)
        max_bounds = np.max(points_3d, axis=0)

        workspace_size = max_bounds - min_bounds

        print(f"\nWorkspace bounds (mm):")
        print(f"  X: {min_bounds[0]:.1f} to {max_bounds[0]:.1f} (range: {workspace_size[0]:.1f})")
        print(f"  Y: {min_bounds[1]:.1f} to {max_bounds[1]:.1f} (range: {workspace_size[1]:.1f})")
        print(f"  Z: {min_bounds[2]:.1f} to {max_bounds[2]:.1f} (range: {workspace_size[2]:.1f})")

        # Find flat surfaces (potential work surfaces)
        # Group points by depth and find largest horizontal clusters
        depth_hist, bins = np.histogram(points_3d[:, 2], bins=50)

        # Find peaks in depth histogram (likely surfaces)
        from scipy.signal import find_peaks
        peaks, properties = find_peaks(depth_hist, height=len(point_cloud)*0.01)

        if len(peaks) > 0:
            print(f"\nDetected {len(peaks)} potential work surfaces:")
            for i, peak in enumerate(peaks[:5], 1):  # Top 5
                depth = bins[peak]
                print(f"  {i}. Surface at depth {depth:.1f}mm")

        # Save point cloud
        np.save('workspace_pointcloud.npy', point_cloud)
        print("\n✓ Point cloud saved to workspace_pointcloud.npy")

        # Visualize depth map
        depth_viz = visualize_depth(frame.depth)
        cv2.imshow('Workspace Depth Map', depth_viz)
        cv2.waitKey(3000)
        cv2.destroyAllWindows()

    def example_6_collision_free_planning(self):
        """
        Example 6: Collision-Free Path Planning

        Plans paths that avoid obstacles detected via depth sensing
        """
        print("\n" + "=" * 60)
        print("Example 6: Collision-Free Path Planning")
        print("=" * 60 + "\n")

        print("This example demonstrates planning a path around obstacles")
        print("detected using the Kinect depth camera.\n")

        # Capture workspace
        self.vision.capture_frame()
        frame = self.vision.current_frame

        # Detect objects as obstacles
        obstacles = self.vision.detect_objects_depth_clustering()

        print(f"Detected {len(obstacles)} obstacles in workspace")

        if obstacles:
            print("\nObstacle positions:")
            for i, obs in enumerate(obstacles, 1):
                print(f"  {i}. ({obs.position_3d[0]:.1f}, {obs.position_3d[1]:.1f}, {obs.position_3d[2]:.1f}) mm")

        # Define start and goal
        start = (100, 100, 200)  # mm
        goal = (300, 300, 200)   # mm

        print(f"\nPlanning path from {start} to {goal}")
        print("Avoiding detected obstacles...")

        # Simple obstacle avoidance: go over obstacles
        if obstacles:
            max_obstacle_height = max(obs.position_3d[2] for obs in obstacles)
            safe_height = max_obstacle_height + 100  # 100mm clearance

            waypoints = [
                start,
                (start[0], start[1], safe_height),
                (goal[0], goal[1], safe_height),
                goal
            ]

            print(f"\nPlanned waypoints (with {safe_height:.1f}mm clearance):")
            for i, wp in enumerate(waypoints, 1):
                print(f"  {i}. ({wp[0]:.1f}, {wp[1]:.1f}, {wp[2]:.1f})")

        else:
            print("No obstacles detected, using direct path")
            waypoints = [start, goal]

        # Visualize
        vis = self.vision.visualize_detections(obstacles)
        cv2.putText(vis, "Obstacles detected - planning safe path", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imshow('Path Planning', vis)
        cv2.waitKey(3000)
        cv2.destroyAllWindows()


def main():
    """Main menu for Kinect manipulation examples"""
    print("\n" + "=" * 60)
    print("Kinect-Based Robot Manipulation Examples")
    print("=" * 60 + "\n")

    # Initialize Kinect
    print("Initializing Kinect...")
    kinect = KinectInterface()

    if not kinect.open():
        print("✗ Failed to open Kinect camera")
        print("\nPlease install required library:")
        print("  Kinect v1: pip install freenect")
        print("  Kinect v2: pip install pylibfreenect2")
        print("  Azure Kinect: pip install pyk4a")
        return

    print(f"✓ {kinect.version.value} ready\n")

    # Initialize robot (simulated for demo)
    print("Note: Robot commands are shown but not executed (no robot connected)")
    print("Connect a robot via serial to enable actual movement\n")

    robot = RobotController()
    # robot.connect('/dev/ttyUSB0', 115200)  # Uncomment to use real robot

    # Create manipulation system
    # For full functionality, calibrate camera-to-robot transformation
    # transformer = CoordinateTransformer()
    # transformer.calibrate(...)

    manipulation = KinectManipulation(robot, kinect, transformer=None)

    # Main menu
    while True:
        print("\n" + "=" * 60)
        print("Examples Menu")
        print("=" * 60)
        print("1. Accurate Pick and Place (with depth)")
        print("2. Obstacle Avoidance (depth sensing)")
        print("3. Volume Measurement (point clouds)")
        print("4. Depth-Based Sorting (multi-object)")
        print("5. Workspace Mapping (3D reconstruction)")
        print("6. Collision-Free Planning (path planning)")
        print("7. Exit")

        choice = input("\nSelect example (1-7): ").strip()

        if choice == '1':
            manipulation.example_1_accurate_pick_and_place()
        elif choice == '2':
            manipulation.example_2_obstacle_avoidance()
        elif choice == '3':
            manipulation.example_3_volume_measurement()
        elif choice == '4':
            manipulation.example_4_depth_based_sorting()
        elif choice == '5':
            manipulation.example_5_workspace_mapping()
        elif choice == '6':
            manipulation.example_6_collision_free_planning()
        elif choice == '7':
            break
        else:
            print("Invalid choice")

    # Cleanup
    kinect.close()
    if robot.is_connected():
        robot.disconnect()

    print("\n✓ Examples complete\n")


if __name__ == '__main__':
    # Check for scipy (needed for surface detection)
    try:
        import scipy.signal
    except ImportError:
        print("Note: Install scipy for advanced features: pip install scipy\n")

    main()

"""
Path Planning and Interpolation Module
Provides smooth path generation for robot movements
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import math


class InterpolationMethod(Enum):
    """Path interpolation methods"""
    LINEAR = "linear"
    CUBIC = "cubic"
    QUINTIC = "quintic"
    SMOOTH_STEP = "smooth_step"


@dataclass
class Waypoint:
    """Represents a waypoint in robot space"""
    positions: Dict[str, float]  # Joint positions
    velocity: Optional[float] = None  # Optional velocity at this point
    timestamp: float = 0.0  # Time to reach this point


class PathPlanner:
    """
    Generates smooth paths between robot positions
    """

    def __init__(self):
        self.interpolation_method = InterpolationMethod.CUBIC

    def interpolate_linear(self, start: float, end: float, t: float) -> float:
        """
        Linear interpolation between two values

        Args:
            start: Start value
            end: End value
            t: Interpolation parameter (0 to 1)

        Returns:
            Interpolated value
        """
        return start + (end - start) * t

    def interpolate_cubic(self, start: float, end: float, t: float) -> float:
        """
        Cubic (smooth) interpolation between two values

        Args:
            start: Start value
            end: End value
            t: Interpolation parameter (0 to 1)

        Returns:
            Interpolated value with smooth acceleration/deceleration
        """
        # Cubic ease-in-out
        if t < 0.5:
            return start + (end - start) * (4 * t * t * t)
        else:
            return start + (end - start) * (1 - math.pow(-2 * t + 2, 3) / 2)

    def interpolate_smooth_step(self, start: float, end: float, t: float) -> float:
        """
        Smooth step interpolation (Perlin's smoothstep function)

        Args:
            start: Start value
            end: End value
            t: Interpolation parameter (0 to 1)

        Returns:
            Interpolated value
        """
        # Clamp t to [0, 1]
        t = max(0, min(1, t))

        # Smoothstep formula: 3t^2 - 2t^3
        smooth_t = t * t * (3 - 2 * t)

        return start + (end - start) * smooth_t

    def interpolate_quintic(self, start: float, end: float, t: float) -> float:
        """
        Quintic (very smooth) interpolation

        Args:
            start: Start value
            end: End value
            t: Interpolation parameter (0 to 1)

        Returns:
            Interpolated value with very smooth acceleration
        """
        # Clamp t to [0, 1]
        t = max(0, min(1, t))

        # Quintic formula: 6t^5 - 15t^4 + 10t^3
        smooth_t = t * t * t * (t * (t * 6 - 15) + 10)

        return start + (end - start) * smooth_t

    def interpolate_point(self,
                         start_pos: Dict[str, float],
                         end_pos: Dict[str, float],
                         t: float,
                         method: Optional[InterpolationMethod] = None) -> Dict[str, float]:
        """
        Interpolate between two joint positions

        Args:
            start_pos: Starting joint positions
            end_pos: Ending joint positions
            t: Interpolation parameter (0 to 1)
            method: Interpolation method to use

        Returns:
            Interpolated joint positions
        """
        if method is None:
            method = self.interpolation_method

        result = {}

        # Get all joint names
        all_joints = set(start_pos.keys()) | set(end_pos.keys())

        for joint in all_joints:
            start_val = start_pos.get(joint, 0.0)
            end_val = end_pos.get(joint, 0.0)

            if method == InterpolationMethod.LINEAR:
                result[joint] = self.interpolate_linear(start_val, end_val, t)
            elif method == InterpolationMethod.CUBIC:
                result[joint] = self.interpolate_cubic(start_val, end_val, t)
            elif method == InterpolationMethod.SMOOTH_STEP:
                result[joint] = self.interpolate_smooth_step(start_val, end_val, t)
            elif method == InterpolationMethod.QUINTIC:
                result[joint] = self.interpolate_quintic(start_val, end_val, t)

        return result

    def generate_path(self,
                     start_pos: Dict[str, float],
                     end_pos: Dict[str, float],
                     num_points: int = 10,
                     method: Optional[InterpolationMethod] = None) -> List[Dict[str, float]]:
        """
        Generate a smooth path between two positions

        Args:
            start_pos: Starting joint positions
            end_pos: Ending joint positions
            num_points: Number of intermediate points
            method: Interpolation method

        Returns:
            List of intermediate positions
        """
        if num_points < 2:
            return [start_pos, end_pos]

        path = []

        for i in range(num_points):
            t = i / (num_points - 1)
            point = self.interpolate_point(start_pos, end_pos, t, method)
            path.append(point)

        return path

    def generate_multi_waypoint_path(self,
                                    waypoints: List[Waypoint],
                                    points_per_segment: int = 10,
                                    method: Optional[InterpolationMethod] = None) -> List[Dict[str, float]]:
        """
        Generate path through multiple waypoints

        Args:
            waypoints: List of waypoints to pass through
            points_per_segment: Number of points between each waypoint
            method: Interpolation method

        Returns:
            Complete path through all waypoints
        """
        if len(waypoints) < 2:
            return [waypoints[0].positions] if waypoints else []

        complete_path = []

        for i in range(len(waypoints) - 1):
            start = waypoints[i].positions
            end = waypoints[i + 1].positions

            segment = self.generate_path(start, end, points_per_segment, method)

            # Add segment (skip last point except for final segment)
            if i < len(waypoints) - 2:
                complete_path.extend(segment[:-1])
            else:
                complete_path.extend(segment)

        return complete_path

    def calculate_path_length(self, path: List[Dict[str, float]]) -> float:
        """
        Calculate total path length in joint space

        Args:
            path: List of positions

        Returns:
            Total distance traveled (sum of joint angle changes)
        """
        if len(path) < 2:
            return 0.0

        total_distance = 0.0

        for i in range(len(path) - 1):
            current = path[i]
            next_point = path[i + 1]

            # Calculate Euclidean distance in joint space
            segment_dist = 0.0
            all_joints = set(current.keys()) | set(next_point.keys())

            for joint in all_joints:
                curr_val = current.get(joint, 0.0)
                next_val = next_point.get(joint, 0.0)
                segment_dist += (next_val - curr_val) ** 2

            total_distance += math.sqrt(segment_dist)

        return total_distance

    def smooth_path(self,
                   path: List[Dict[str, float]],
                   window_size: int = 3) -> List[Dict[str, float]]:
        """
        Apply moving average smoothing to a path

        Args:
            path: Original path
            window_size: Smoothing window size (must be odd)

        Returns:
            Smoothed path
        """
        if len(path) < 3 or window_size < 3:
            return path

        # Ensure window size is odd
        if window_size % 2 == 0:
            window_size += 1

        half_window = window_size // 2
        smoothed = []

        for i in range(len(path)):
            # Determine window bounds
            start_idx = max(0, i - half_window)
            end_idx = min(len(path), i + half_window + 1)

            # Calculate average position
            avg_pos = {}
            all_joints = set()

            for pos in path[start_idx:end_idx]:
                all_joints.update(pos.keys())

            for joint in all_joints:
                values = [path[j].get(joint, 0.0) for j in range(start_idx, end_idx)]
                avg_pos[joint] = sum(values) / len(values)

            smoothed.append(avg_pos)

        return smoothed


class TrajectoryPlanner:
    """
    Plans trajectories with velocity and acceleration constraints
    """

    def __init__(self, max_velocity: float = 1000.0, max_acceleration: float = 500.0):
        self.max_velocity = max_velocity  # degrees/second
        self.max_acceleration = max_acceleration  # degrees/second^2

    def calculate_trajectory_time(self,
                                 start_pos: Dict[str, float],
                                 end_pos: Dict[str, float]) -> float:
        """
        Calculate time needed to move between positions

        Args:
            start_pos: Starting position
            end_pos: Ending position

        Returns:
            Time in seconds
        """
        # Find maximum joint movement
        max_movement = 0.0
        all_joints = set(start_pos.keys()) | set(end_pos.keys())

        for joint in all_joints:
            start = start_pos.get(joint, 0.0)
            end = end_pos.get(joint, 0.0)
            movement = abs(end - start)
            max_movement = max(max_movement, movement)

        # Calculate time based on max velocity
        # Using trapezoidal velocity profile
        accel_time = self.max_velocity / self.max_acceleration
        accel_distance = 0.5 * self.max_acceleration * accel_time ** 2

        if max_movement <= 2 * accel_distance:
            # Triangular profile (doesn't reach max velocity)
            return 2 * math.sqrt(max_movement / self.max_acceleration)
        else:
            # Trapezoidal profile
            constant_distance = max_movement - 2 * accel_distance
            constant_time = constant_distance / self.max_velocity
            return 2 * accel_time + constant_time

    def generate_timed_trajectory(self,
                                 start_pos: Dict[str, float],
                                 end_pos: Dict[str, float],
                                 duration: Optional[float] = None,
                                 dt: float = 0.1) -> List[Tuple[float, Dict[str, float]]]:
        """
        Generate trajectory with timestamps

        Args:
            start_pos: Starting position
            end_pos: Ending position
            duration: Total duration (calculated if None)
            dt: Time step in seconds

        Returns:
            List of (time, position) tuples
        """
        if duration is None:
            duration = self.calculate_trajectory_time(start_pos, end_pos)

        num_points = int(duration / dt) + 1
        trajectory = []
        planner = PathPlanner()

        for i in range(num_points):
            t = min(i * dt / duration, 1.0)
            time = i * dt

            # Use quintic interpolation for smooth velocity profile
            pos = planner.interpolate_point(
                start_pos, end_pos, t,
                method=InterpolationMethod.QUINTIC
            )

            trajectory.append((time, pos))

        return trajectory


# Helper functions
def create_circular_path(center_joint: str,
                        center_angle: float,
                        radius: float,
                        num_points: int = 36) -> List[Dict[str, float]]:
    """
    Create a circular path for a single joint

    Args:
        center_joint: Joint to move in circle
        center_angle: Center angle
        radius: Radius in degrees
        num_points: Number of points in circle

    Returns:
        Circular path
    """
    path = []

    for i in range(num_points + 1):
        angle = 2 * math.pi * i / num_points
        offset = radius * math.cos(angle)
        path.append({center_joint: center_angle + offset})

    return path


def create_home_sequence(joints: List[str]) -> List[Dict[str, float]]:
    """
    Create a safe homing sequence (move to zero incrementally)

    Args:
        joints: List of joint names

    Returns:
        Homing path
    """
    planner = PathPlanner()

    # Current assumed position (all non-zero)
    current = {joint: 45.0 for joint in joints}

    # Target: all zeros
    target = {joint: 0.0 for joint in joints}

    # Generate smooth path
    return planner.generate_path(current, target, num_points=20,
                                 method=InterpolationMethod.QUINTIC)


if __name__ == '__main__':
    # Demo path planning
    print("=== Path Planning Demo ===\n")

    planner = PathPlanner()

    # Example positions
    start = {'A': 0, 'B': 0, 'D': 0}
    end = {'A': 45, 'B': 30, 'D': -20}

    # Generate different types of paths
    print("1. Linear interpolation:")
    linear_path = planner.generate_path(start, end, 5, InterpolationMethod.LINEAR)
    for i, pos in enumerate(linear_path):
        print(f"   Point {i}: {pos}")

    print("\n2. Smooth (cubic) interpolation:")
    smooth_path = planner.generate_path(start, end, 5, InterpolationMethod.CUBIC)
    for i, pos in enumerate(smooth_path):
        print(f"   Point {i}: {pos}")

    # Multi-waypoint path
    print("\n3. Multi-waypoint path:")
    waypoints = [
        Waypoint({'A': 0, 'B': 0}),
        Waypoint({'A': 45, 'B': 30}),
        Waypoint({'A': 90, 'B': 0}),
        Waypoint({'A': 0, 'B': 0})
    ]

    multi_path = planner.generate_multi_waypoint_path(waypoints, points_per_segment=3)
    for i, pos in enumerate(multi_path):
        print(f"   Point {i}: {pos}")

    # Calculate path length
    length = planner.calculate_path_length(smooth_path)
    print(f"\nPath length: {length:.2f} degrees (joint space distance)")

    # Trajectory planning
    print("\n4. Time-optimized trajectory:")
    traj_planner = TrajectoryPlanner(max_velocity=500, max_acceleration=200)

    duration = traj_planner.calculate_trajectory_time(start, end)
    print(f"   Estimated duration: {duration:.2f} seconds")

    trajectory = traj_planner.generate_timed_trajectory(start, end, dt=0.5)
    for time, pos in trajectory[:5]:  # Show first 5 points
        print(f"   t={time:.1f}s: {pos}")

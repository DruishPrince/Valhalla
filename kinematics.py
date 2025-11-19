"""
Kinematics Module
Forward and Inverse Kinematics for Thor 6-axis robotic arm
"""

import numpy as np
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import math


@dataclass
class DHParameter:
    """Denavit-Hartenberg parameters for a joint"""
    theta: float  # Joint angle (degrees)
    d: float      # Link offset (mm)
    a: float      # Link length (mm)
    alpha: float  # Link twist (degrees)


@dataclass
class Point3D:
    """3D point representation"""
    x: float
    y: float
    z: float

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    @classmethod
    def from_array(cls, arr: np.ndarray) -> 'Point3D':
        return cls(float(arr[0]), float(arr[1]), float(arr[2]))


class ThorKinematics:
    """
    Forward and Inverse Kinematics for Thor 6-axis arm

    Based on typical 6-axis robot arm configuration.
    Adjust DH parameters to match your specific Thor arm.
    """

    # Default DH parameters for Thor arm (adjust to your robot)
    # These are approximate values - measure your actual robot!
    DEFAULT_DH_PARAMS = {
        'base_height': 0,      # Height of base (mm)
        'shoulder_offset': 0,   # Shoulder offset (mm)
        'upper_arm': 200,      # Upper arm length (mm)
        'forearm': 200,        # Forearm length (mm)
        'wrist_length': 100,   # Wrist to end effector (mm)
    }

    def __init__(self, dh_params: Optional[Dict] = None):
        """
        Initialize kinematics

        Args:
            dh_params: Dictionary of DH parameters (uses defaults if None)
        """
        self.params = self.DEFAULT_DH_PARAMS.copy()
        if dh_params:
            self.params.update(dh_params)

        # Current joint angles (degrees)
        self.joint_angles = {
            'A': 0.0,  # Base rotation
            'B': 0.0,  # Shoulder
            'C': 0.0,  # Linked to B
            'D': 0.0,  # Elbow
            'X': 0.0,  # Wrist pitch
            'Y': 0.0,  # Wrist roll
            'Z': 0.0   # End effector rotation
        }

    def deg_to_rad(self, degrees: float) -> float:
        """Convert degrees to radians"""
        return degrees * np.pi / 180.0

    def rad_to_deg(self, radians: float) -> float:
        """Convert radians to degrees"""
        return radians * 180.0 / np.pi

    def dh_transform(self, theta: float, d: float, a: float, alpha: float) -> np.ndarray:
        """
        Calculate transformation matrix from DH parameters

        Args:
            theta: Joint angle (radians)
            d: Link offset
            a: Link length
            alpha: Link twist (radians)

        Returns:
            4x4 transformation matrix
        """
        ct = np.cos(theta)
        st = np.sin(theta)
        ca = np.cos(alpha)
        sa = np.sin(alpha)

        return np.array([
            [ct, -st * ca,  st * sa, a * ct],
            [st,  ct * ca, -ct * sa, a * st],
            [0,   sa,       ca,      d],
            [0,   0,        0,       1]
        ])

    def forward_kinematics(self,
                          joint_angles: Optional[Dict[str, float]] = None) -> Tuple[Point3D, List[Point3D]]:
        """
        Calculate end effector position from joint angles

        Args:
            joint_angles: Dictionary of joint angles in degrees

        Returns:
            Tuple of (end_effector_position, joint_positions)
        """
        if joint_angles is None:
            joint_angles = self.joint_angles
        else:
            self.joint_angles = joint_angles.copy()

        # Convert to radians
        theta1 = self.deg_to_rad(joint_angles.get('A', 0))  # Base
        theta2 = self.deg_to_rad(joint_angles.get('B', 0))  # Shoulder
        theta3 = self.deg_to_rad(joint_angles.get('D', 0))  # Elbow
        theta4 = self.deg_to_rad(joint_angles.get('X', 0))  # Wrist pitch
        theta5 = self.deg_to_rad(joint_angles.get('Y', 0))  # Wrist roll

        # Get link lengths
        d1 = self.params['base_height']
        a2 = self.params['upper_arm']
        a3 = self.params['forearm']
        d6 = self.params['wrist_length']

        # Build transformation matrices
        # Base rotation (around Z)
        T01 = self.dh_transform(theta1, d1, 0, np.pi/2)

        # Shoulder (around Y in rotated frame)
        T12 = self.dh_transform(theta2, 0, a2, 0)

        # Elbow (around Y)
        T23 = self.dh_transform(theta3, 0, a3, 0)

        # Wrist pitch (around Y)
        T34 = self.dh_transform(theta4, 0, 0, np.pi/2)

        # Wrist roll (around Z)
        T45 = self.dh_transform(theta5, 0, 0, 0)

        # End effector
        T56 = self.dh_transform(0, d6, 0, 0)

        # Calculate cumulative transformations
        T02 = T01 @ T12
        T03 = T02 @ T23
        T04 = T03 @ T34
        T05 = T04 @ T45
        T06 = T05 @ T56

        # Extract joint positions
        joint_positions = [
            Point3D(0, 0, 0),  # Base
            Point3D(T01[0, 3], T01[1, 3], T01[2, 3]),  # Joint 1
            Point3D(T02[0, 3], T02[1, 3], T02[2, 3]),  # Joint 2 (shoulder)
            Point3D(T03[0, 3], T03[1, 3], T03[2, 3]),  # Joint 3 (elbow)
            Point3D(T04[0, 3], T04[1, 3], T04[2, 3]),  # Joint 4
            Point3D(T05[0, 3], T05[1, 3], T05[2, 3]),  # Joint 5
            Point3D(T06[0, 3], T06[1, 3], T06[2, 3]),  # End effector
        ]

        # End effector position
        end_effector = joint_positions[-1]

        return end_effector, joint_positions

    def inverse_kinematics(self,
                          target: Point3D,
                          current_angles: Optional[Dict[str, float]] = None) -> Optional[Dict[str, float]]:
        """
        Calculate joint angles to reach target position (numerical solver)

        Args:
            target: Target 3D position
            current_angles: Starting joint angles (uses current if None)

        Returns:
            Dictionary of joint angles or None if unreachable
        """
        if current_angles is None:
            current_angles = self.joint_angles.copy()

        # Use numerical IK solver (Jacobian-based)
        return self._numerical_ik(target, current_angles)

    def _numerical_ik(self,
                     target: Point3D,
                     initial_angles: Dict[str, float],
                     max_iterations: int = 100,
                     tolerance: float = 1.0) -> Optional[Dict[str, float]]:
        """
        Numerical inverse kinematics using Jacobian method

        Args:
            target: Target position
            initial_angles: Starting joint angles
            max_iterations: Maximum solver iterations
            tolerance: Position error tolerance (mm)

        Returns:
            Joint angles or None if failed
        """
        # Start with initial guess
        angles = initial_angles.copy()

        # Only solve for first 3 joints (base, shoulder, elbow) for simplicity
        # Wrist orientation is kept neutral
        joint_keys = ['A', 'B', 'D']

        for iteration in range(max_iterations):
            # Calculate current position
            current_pos, _ = self.forward_kinematics(angles)

            # Calculate error
            error = np.array([
                target.x - current_pos.x,
                target.y - current_pos.y,
                target.z - current_pos.z
            ])

            error_magnitude = np.linalg.norm(error)

            # Check if we're close enough
            if error_magnitude < tolerance:
                return angles

            # Calculate Jacobian (numerical approximation)
            J = self._calculate_jacobian(angles, joint_keys)

            # Pseudo-inverse for damped least squares
            lambda_damping = 0.01
            JT = J.T
            J_damped = JT @ J + lambda_damping * np.eye(len(joint_keys))
            J_inv = np.linalg.inv(J_damped) @ JT

            # Calculate joint angle changes
            delta_theta = J_inv @ error

            # Update angles with step limiting
            max_step = 5.0  # degrees
            for i, key in enumerate(joint_keys):
                step = np.clip(delta_theta[i], -max_step, max_step)
                angles[key] += step

                # Apply joint limits
                if key == 'A':
                    angles[key] = np.clip(angles[key], -180, 180)
                elif key in ['B', 'D']:
                    angles[key] = np.clip(angles[key], -90, 90)

        # Failed to converge
        print(f"IK failed to converge. Final error: {error_magnitude:.2f} mm")
        return None

    def _calculate_jacobian(self, angles: Dict[str, float], joint_keys: List[str]) -> np.ndarray:
        """
        Calculate Jacobian matrix numerically

        Args:
            angles: Current joint angles
            joint_keys: Keys of joints to vary

        Returns:
            3xN Jacobian matrix
        """
        epsilon = 0.01  # Small angle change for numerical derivative
        J = np.zeros((3, len(joint_keys)))

        # Get current position
        current_pos, _ = self.forward_kinematics(angles)

        # Numerical derivative for each joint
        for i, key in enumerate(joint_keys):
            # Perturb joint angle
            angles_perturbed = angles.copy()
            angles_perturbed[key] += epsilon

            # Calculate new position
            new_pos, _ = self.forward_kinematics(angles_perturbed)

            # Numerical derivative
            J[0, i] = (new_pos.x - current_pos.x) / epsilon
            J[1, i] = (new_pos.y - current_pos.y) / epsilon
            J[2, i] = (new_pos.z - current_pos.z) / epsilon

        return J

    def is_reachable(self, target: Point3D) -> bool:
        """
        Check if target position is within robot's workspace

        Args:
            target: Target position

        Returns:
            True if reachable
        """
        # Calculate distance from base
        distance = np.sqrt(target.x**2 + target.y**2 + target.z**2)

        # Maximum reach
        max_reach = (self.params['upper_arm'] +
                    self.params['forearm'] +
                    self.params['wrist_length'])

        # Minimum reach (arm can't fold completely)
        min_reach = abs(self.params['upper_arm'] -
                       self.params['forearm'] -
                       self.params['wrist_length'])

        return min_reach <= distance <= max_reach

    def get_workspace_bounds(self) -> Dict[str, Tuple[float, float]]:
        """
        Get approximate workspace boundaries

        Returns:
            Dictionary with min/max for x, y, z
        """
        max_reach = (self.params['upper_arm'] +
                    self.params['forearm'] +
                    self.params['wrist_length'])

        return {
            'x': (-max_reach, max_reach),
            'y': (-max_reach, max_reach),
            'z': (0, max_reach)  # Assuming robot sits on ground
        }


# Helper functions
def create_kinematics(custom_params: Optional[Dict] = None) -> ThorKinematics:
    """Create kinematics instance with optional custom parameters"""
    return ThorKinematics(custom_params)


def test_kinematics():
    """Test forward and inverse kinematics"""
    print("=== Testing Kinematics ===\n")

    kin = ThorKinematics()

    # Test forward kinematics
    print("1. Forward Kinematics Test:")
    angles = {'A': 0, 'B': 45, 'D': -30, 'X': 0, 'Y': 0}
    end_pos, joints = kin.forward_kinematics(angles)

    print(f"   Joint angles: {angles}")
    print(f"   End effector position: ({end_pos.x:.1f}, {end_pos.y:.1f}, {end_pos.z:.1f})")

    # Test inverse kinematics
    print("\n2. Inverse Kinematics Test:")
    target = Point3D(200, 100, 150)
    print(f"   Target position: ({target.x:.1f}, {target.y:.1f}, {target.z:.1f})")

    if kin.is_reachable(target):
        print("   Target is reachable")
        result_angles = kin.inverse_kinematics(target)

        if result_angles:
            print(f"   Solution found: {result_angles}")

            # Verify solution
            verify_pos, _ = kin.forward_kinematics(result_angles)
            error = np.sqrt((verify_pos.x - target.x)**2 +
                          (verify_pos.y - target.y)**2 +
                          (verify_pos.z - target.z)**2)
            print(f"   Verification error: {error:.2f} mm")
        else:
            print("   No solution found")
    else:
        print("   Target is out of reach")

    # Workspace bounds
    print("\n3. Workspace Bounds:")
    bounds = kin.get_workspace_bounds()
    for axis, (min_val, max_val) in bounds.items():
        print(f"   {axis}: [{min_val:.1f}, {max_val:.1f}] mm")


if __name__ == '__main__':
    test_kinematics()

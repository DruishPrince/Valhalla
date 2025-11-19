#!/usr/bin/env python3
"""
Interactive Camera Calibration Utility

This tool helps you calibrate your camera for vision-guided robot control.
It provides an interactive way to map camera pixels to robot coordinates.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from vision_controller import CoordinateTransformer
from robot_controller import RobotController
import sys


class CalibrationTool:
    """
    Interactive tool for camera-robot calibration
    """

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.capture: Optional[cv2.VideoCapture] = None
        self.transformer = CoordinateTransformer()

        # Calibration points
        self.camera_points: List[Tuple[float, float]] = []
        self.robot_points: List[Tuple[float, float, float]] = []

        # Current frame
        self.current_frame: Optional[np.ndarray] = None

        # UI state
        self.point_mode = "camera"  # "camera" or "robot"
        self.temp_robot_point = [0.0, 0.0, 0.0]  # Temporary storage for robot point

    def start(self) -> bool:
        """Start camera"""
        self.capture = cv2.VideoCapture(self.camera_index)
        if not self.capture.isOpened():
            print(f"Error: Could not open camera {self.camera_index}")
            return False

        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return True

    def stop(self):
        """Stop camera"""
        if self.capture:
            self.capture.release()
        cv2.destroyAllWindows()

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to select calibration points"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.point_mode == "camera":
                self.camera_points.append((float(x), float(y)))
                print(f"\n✓ Camera point {len(self.camera_points)}: ({x}, {y})")
                print("Now enter the corresponding robot coordinates:")
                self.point_mode = "robot"
            else:
                print("First enter robot coordinates, then click again")

    def add_robot_point(self, x: float, y: float, z: float):
        """Add robot coordinate point"""
        self.robot_points.append((x, y, z))
        print(f"✓ Robot point {len(self.robot_points)}: ({x:.1f}, {y:.1f}, {z:.1f})")
        self.point_mode = "camera"

        if len(self.camera_points) >= 4:
            print("\n✓ Minimum calibration points collected!")
            print("You can add more points (recommended) or press 'c' to calibrate")

    def draw_points(self, frame: np.ndarray) -> np.ndarray:
        """Draw calibration points on frame"""
        output = frame.copy()

        # Draw existing points
        for i, (x, y) in enumerate(self.camera_points):
            cv2.circle(output, (int(x), int(y)), 8, (0, 255, 0), -1)
            cv2.putText(output, str(i + 1), (int(x) + 10, int(y) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Draw crosshair at mouse position
        cv2.line(output, (0, frame.shape[0] // 2),
                (frame.shape[1], frame.shape[0] // 2), (255, 255, 255), 1)
        cv2.line(output, (frame.shape[1] // 2, 0),
                (frame.shape[1] // 2, frame.shape[0]), (255, 255, 255), 1)

        # Draw instructions
        if self.point_mode == "camera":
            text = f"Click on calibration point #{len(self.camera_points) + 1}"
            color = (0, 255, 255)
        else:
            text = "Enter robot coordinates in console"
            color = (0, 165, 255)

        cv2.putText(output, text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Draw point count
        count_text = f"Points: {len(self.camera_points)}/4 minimum"
        cv2.putText(output, count_text, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return output

    def calibrate(self) -> bool:
        """Perform calibration"""
        if len(self.camera_points) < 4 or len(self.robot_points) < 4:
            print("Error: Need at least 4 point pairs for calibration")
            return False

        if len(self.camera_points) != len(self.robot_points):
            print("Error: Mismatch between camera and robot points")
            return False

        try:
            self.transformer.calibrate_from_points(
                self.camera_points,
                self.robot_points
            )
            print("\n✓ Calibration successful!")
            return True
        except Exception as e:
            print(f"✗ Calibration failed: {e}")
            return False

    def test_calibration(self, test_pixel_x: int, test_pixel_y: int):
        """Test calibration by converting a pixel point"""
        try:
            robot_coords = self.transformer.pixel_to_robot(test_pixel_x, test_pixel_y)
            print(f"\nTest conversion:")
            print(f"  Pixel: ({test_pixel_x}, {test_pixel_y})")
            print(f"  Robot: ({robot_coords[0]:.1f}, {robot_coords[1]:.1f}, {robot_coords[2]:.1f})")
        except Exception as e:
            print(f"✗ Test failed: {e}")

    def save_calibration(self, filepath: str) -> bool:
        """Save calibration to file"""
        if self.transformer.save_calibration(filepath):
            print(f"\n✓ Calibration saved to {filepath}")
            return True
        else:
            print(f"\n✗ Failed to save calibration")
            return False

    def run_interactive(self):
        """Run interactive calibration session"""
        print("\n" + "=" * 60)
        print("Interactive Camera Calibration Tool")
        print("=" * 60)
        print("\nInstructions:")
        print("1. Place calibration markers (e.g., checkerboard, colored dots)")
        print("2. Move robot to each marker and note the position")
        print("3. Click on marker in camera view")
        print("4. Enter robot coordinates when prompted")
        print("5. Repeat for at least 4 points (more is better)")
        print("6. Press 'c' to calculate calibration")
        print("7. Press 's' to save calibration")
        print("8. Press 'q' to quit")
        print("\nTIP: Spread points across entire workspace for best results")
        print("=" * 60 + "\n")

        if not self.start():
            return

        cv2.namedWindow('Calibration')
        cv2.setMouseCallback('Calibration', self.mouse_callback)

        while True:
            ret, frame = self.capture.read()
            if not ret:
                print("Error: Failed to capture frame")
                break

            self.current_frame = frame

            # Draw visualization
            display_frame = self.draw_points(frame)
            cv2.imshow('Calibration', display_frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\nCalibration cancelled")
                break

            elif key == ord('c'):
                if self.calibrate():
                    print("\nCalibration complete! Press 's' to save or 't' to test")

            elif key == ord('s'):
                filepath = input("\nEnter filename to save (default: camera_calibration.npz): ").strip()
                if not filepath:
                    filepath = "camera_calibration.npz"
                self.save_calibration(filepath)

            elif key == ord('t'):
                print("\nClick on a point to test the calibration...")

            elif key == ord('r'):
                # Reset calibration
                self.camera_points.clear()
                self.robot_points.clear()
                print("\n✓ Calibration points cleared")

            # Check if we need robot input
            if self.point_mode == "robot" and len(self.camera_points) > len(self.robot_points):
                # Non-blocking input handling would require threading
                # For now, we'll use a simple approach
                pass

        self.stop()


class SimpleCalibration:
    """
    Simple calibration using a grid pattern
    """

    @staticmethod
    def calibrate_with_grid(camera_index: int = 0,
                           grid_size: Tuple[int, int] = (9, 6),
                           square_size: float = 25.0):
        """
        Calibrate camera using checkerboard pattern

        Args:
            camera_index: Camera index
            grid_size: Internal corners of checkerboard (width, height)
            square_size: Size of checkerboard square in mm

        Returns:
            CoordinateTransformer with calibration
        """
        print("\n=== Automatic Checkerboard Calibration ===")
        print(f"Looking for {grid_size[0]}x{grid_size[1]} checkerboard...")
        print("Press SPACE to capture, ESC to finish\n")

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("Error: Could not open camera")
            return None

        # Prepare object points
        objp = np.zeros((grid_size[0] * grid_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:grid_size[0], 0:grid_size[1]].T.reshape(-1, 2)
        objp *= square_size

        # Arrays to store points
        obj_points = []  # 3D points in real world
        img_points = []  # 2D points in image

        captured_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Find checkerboard corners
            ret, corners = cv2.findChessboardCorners(gray, grid_size, None)

            display = frame.copy()
            if ret:
                # Refine corner positions
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

                # Draw corners
                cv2.drawChessboardCorners(display, grid_size, corners2, ret)
                cv2.putText(display, "Pattern found! Press SPACE to capture",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(display, "No pattern detected",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.putText(display, f"Captured: {captured_count} images",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            cv2.imshow('Checkerboard Calibration', display)

            key = cv2.waitKey(1) & 0xFF

            if key == 27:  # ESC
                break
            elif key == 32 and ret:  # SPACE
                obj_points.append(objp)
                img_points.append(corners2)
                captured_count += 1
                print(f"✓ Captured image {captured_count}")

                if captured_count >= 10:
                    print("Sufficient images captured! Press ESC to finish")

        cap.release()
        cv2.destroyAllWindows()

        if captured_count < 3:
            print("Error: Need at least 3 calibration images")
            return None

        # Perform calibration
        print("\nCalculating calibration...")
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            obj_points, img_points, gray.shape[::-1], None, None
        )

        if ret:
            print("✓ Calibration successful!")
            print(f"  Reprojection error: {ret:.4f}")

            # Save camera matrix and distortion coefficients
            np.savez('camera_intrinsics.npz',
                    camera_matrix=camera_matrix,
                    dist_coeffs=dist_coeffs)
            print("✓ Saved intrinsic calibration to camera_intrinsics.npz")

        return camera_matrix, dist_coeffs


def main():
    """Main entry point"""
    print("\nCalibration Mode Selection:")
    print("1. Interactive point-based calibration (recommended for robot)")
    print("2. Automatic checkerboard calibration (for camera intrinsics)")
    print("3. Quick 4-point calibration")

    choice = input("\nSelect mode (1-3): ").strip()

    if choice == '1':
        tool = CalibrationTool(camera_index=0)
        tool.run_interactive()

        # Prompt for robot coordinates after each camera point
        while len(tool.robot_points) < len(tool.camera_points):
            print(f"\nEnter robot coordinates for point #{len(tool.robot_points) + 1}:")
            try:
                x = float(input("  X (mm): "))
                y = float(input("  Y (mm): "))
                z = float(input("  Z (mm): "))
                tool.add_robot_point(x, y, z)
            except ValueError:
                print("Invalid input, please enter numbers")

    elif choice == '2':
        camera_matrix, dist_coeffs = SimpleCalibration.calibrate_with_grid()

    elif choice == '3':
        # Quick calibration
        print("\n=== Quick 4-Point Calibration ===")
        print("You will need to provide 4 point correspondences")
        print("Format: pixel_x pixel_y robot_x robot_y robot_z")
        print("\nExample: 100 100 -200 -200 0")
        print("(means pixel 100,100 corresponds to robot position -200,-200,0)")

        camera_points = []
        robot_points = []

        for i in range(4):
            while True:
                try:
                    data = input(f"\nPoint {i + 1}: ").strip().split()
                    if len(data) != 5:
                        print("Error: Need 5 values (px py rx ry rz)")
                        continue

                    px, py, rx, ry, rz = map(float, data)
                    camera_points.append((px, py))
                    robot_points.append((rx, ry, rz))
                    break
                except ValueError:
                    print("Error: Invalid numbers")

        # Calibrate
        transformer = CoordinateTransformer()
        transformer.calibrate_from_points(camera_points, robot_points)

        filepath = input("\nSave calibration to (default: camera_calibration.npz): ").strip()
        if not filepath:
            filepath = "camera_calibration.npz"

        transformer.save_calibration(filepath)
        print(f"✓ Calibration saved to {filepath}")

    else:
        print("Invalid choice")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCalibration interrupted by user")
        sys.exit(0)

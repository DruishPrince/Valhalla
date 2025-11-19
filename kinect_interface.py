#!/usr/bin/env python3
"""
Kinect Camera Interface

Provides unified interface for Microsoft Kinect cameras (v1, v2, Azure)
for RGB-D (color + depth) imaging to improve robot vision capabilities.

Supported Kinect Versions:
- Kinect v1 (Xbox 360) - via libfreenect/freenect
- Kinect v2 (Xbox One) - via pylibfreenect2
- Azure Kinect - via pyk4a

The Kinect provides depth data which enables:
- Accurate 3D object localization
- Obstacle detection and avoidance
- Precise pick-and-place operations
- Volume and shape estimation
- Better occlusion handling
"""

import numpy as np
import cv2
import time
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum


class KinectVersion(Enum):
    """Supported Kinect versions"""
    V1 = "kinect_v1"          # Xbox 360 Kinect
    V2 = "kinect_v2"          # Xbox One Kinect
    AZURE = "azure_kinect"    # Azure Kinect DK


@dataclass
class DepthFrame:
    """Depth frame data"""
    depth: np.ndarray         # Depth map in millimeters (H x W)
    timestamp: float          # Capture timestamp
    min_depth: float          # Minimum reliable depth (mm)
    max_depth: float          # Maximum reliable depth (mm)


@dataclass
class RGBDFrame:
    """RGB-D frame with aligned color and depth"""
    rgb: np.ndarray           # RGB image (H x W x 3)
    depth: np.ndarray         # Depth map in mm (H x W)
    timestamp: float          # Capture timestamp

    def get_point_cloud(self, camera_matrix: np.ndarray) -> np.ndarray:
        """
        Generate 3D point cloud from RGB-D data

        Args:
            camera_matrix: 3x3 camera intrinsic matrix

        Returns:
            Point cloud as Nx6 array (X, Y, Z, R, G, B)
        """
        h, w = self.depth.shape

        # Create pixel coordinate grids
        u, v = np.meshgrid(np.arange(w), np.arange(h))

        # Get camera intrinsics
        fx, fy = camera_matrix[0, 0], camera_matrix[1, 1]
        cx, cy = camera_matrix[0, 2], camera_matrix[1, 2]

        # Convert depth to meters
        z = self.depth / 1000.0

        # Back-project to 3D
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy

        # Filter invalid points (depth = 0)
        valid = z > 0

        # Create point cloud
        points_3d = np.stack([x[valid], y[valid], z[valid]], axis=1)
        colors = self.rgb[valid] / 255.0

        # Combine geometry and color
        point_cloud = np.hstack([points_3d, colors])

        return point_cloud


class KinectInterface:
    """
    Unified interface for Kinect cameras

    Automatically detects and connects to available Kinect device
    """

    def __init__(self, version: Optional[KinectVersion] = None):
        """
        Initialize Kinect interface

        Args:
            version: Specific Kinect version to use (auto-detect if None)
        """
        self.version = version
        self.device = None
        self.is_open = False

        # Device-specific objects
        self.freenect_ctx = None      # For Kinect v1
        self.freenect2_device = None  # For Kinect v2
        self.k4a_device = None        # For Azure Kinect

        # Camera parameters (updated when device opens)
        self.rgb_resolution = (640, 480)
        self.depth_resolution = (640, 480)
        self.camera_matrix = np.eye(3)
        self.depth_range = (500, 4000)  # mm

    def open(self) -> bool:
        """
        Open Kinect device

        Returns:
            True if successfully opened
        """
        if self.is_open:
            return True

        # Try to detect and open Kinect
        if self.version is None:
            # Auto-detect
            for version in [KinectVersion.V1, KinectVersion.V2, KinectVersion.AZURE]:
                if self._try_open(version):
                    self.version = version
                    return True
            return False
        else:
            return self._try_open(self.version)

    def _try_open(self, version: KinectVersion) -> bool:
        """Try to open specific Kinect version"""
        try:
            if version == KinectVersion.V1:
                return self._open_kinect_v1()
            elif version == KinectVersion.V2:
                return self._open_kinect_v2()
            elif version == KinectVersion.AZURE:
                return self._open_azure_kinect()
        except Exception as e:
            print(f"Failed to open {version.value}: {e}")
            return False

    def _open_kinect_v1(self) -> bool:
        """Open Kinect v1 (Xbox 360)"""
        try:
            import freenect

            # Initialize context
            self.freenect_ctx = freenect.init()

            # Check if device available
            num_devices = freenect.num_devices(self.freenect_ctx)
            if num_devices == 0:
                return False

            # Open first device
            self.device = freenect.open_device(self.freenect_ctx, 0)

            # Set video and depth modes
            freenect.set_video_mode(
                self.device,
                freenect.RESOLUTION_MEDIUM,
                freenect.VIDEO_RGB
            )
            freenect.set_depth_mode(
                self.device,
                freenect.RESOLUTION_MEDIUM,
                freenect.DEPTH_MM
            )

            # Start streams
            freenect.start_video(self.device)
            freenect.start_depth(self.device)

            # Set parameters
            self.rgb_resolution = (640, 480)
            self.depth_resolution = (640, 480)
            self.depth_range = (500, 4000)

            # Kinect v1 intrinsics (approximate)
            fx, fy = 525.0, 525.0
            cx, cy = 319.5, 239.5
            self.camera_matrix = np.array([
                [fx, 0, cx],
                [0, fy, cy],
                [0, 0, 1]
            ])

            self.is_open = True
            print("✓ Kinect v1 opened successfully")
            return True

        except ImportError:
            print("freenect library not installed. Install with: pip install freenect")
            return False
        except Exception as e:
            print(f"Kinect v1 error: {e}")
            return False

    def _open_kinect_v2(self) -> bool:
        """Open Kinect v2 (Xbox One)"""
        try:
            from pylibfreenect2 import Freenect2, SyncMultiFrameListener
            from pylibfreenect2 import FrameType, Registration, Frame

            # Initialize Freenect2
            fn = Freenect2()

            # Check for devices
            num_devices = fn.enumerateDevices()
            if num_devices == 0:
                return False

            # Open first device
            serial = fn.getDeviceSerialNumber(0)
            self.freenect2_device = fn.openDevice(serial)

            # Setup listeners
            self.listener = SyncMultiFrameListener(
                FrameType.Color | FrameType.Depth
            )

            self.freenect2_device.setColorFrameListener(self.listener)
            self.freenect2_device.setIrAndDepthFrameListener(self.listener)

            # Start device
            self.freenect2_device.start()

            # Setup registration for alignment
            self.registration = Registration(
                self.freenect2_device.getIrCameraParams(),
                self.freenect2_device.getColorCameraParams()
            )

            # Set parameters
            self.rgb_resolution = (1920, 1080)
            self.depth_resolution = (512, 424)
            self.depth_range = (500, 4500)

            # Get intrinsics
            color_params = self.freenect2_device.getColorCameraParams()
            self.camera_matrix = np.array([
                [color_params.fx, 0, color_params.cx],
                [0, color_params.fy, color_params.cy],
                [0, 0, 1]
            ])

            self.is_open = True
            print("✓ Kinect v2 opened successfully")
            return True

        except ImportError:
            print("pylibfreenect2 not installed. See: https://github.com/r9y9/pylibfreenect2")
            return False
        except Exception as e:
            print(f"Kinect v2 error: {e}")
            return False

    def _open_azure_kinect(self) -> bool:
        """Open Azure Kinect DK"""
        try:
            import pyk4a
            from pyk4a import Config, PyK4A

            # Configure device
            config = Config(
                color_resolution=pyk4a.ColorResolution.RES_720P,
                depth_mode=pyk4a.DepthMode.NFOV_UNBINNED,
                synchronized_images_only=True,
            )

            # Open device
            self.k4a_device = PyK4A(config=config)
            self.k4a_device.start()

            # Set parameters
            self.rgb_resolution = (1280, 720)
            self.depth_resolution = (640, 576)
            self.depth_range = (500, 3860)

            # Get calibration
            calibration = self.k4a_device.calibration

            # Get color camera intrinsics
            intrinsics = calibration.get_camera_matrix(pyk4a.calibration.CalibrationType.COLOR)
            self.camera_matrix = intrinsics

            self.is_open = True
            print("✓ Azure Kinect opened successfully")
            return True

        except ImportError:
            print("pyk4a not installed. Install with: pip install pyk4a")
            return False
        except Exception as e:
            print(f"Azure Kinect error: {e}")
            return False

    def get_rgbd_frame(self) -> Optional[RGBDFrame]:
        """
        Capture aligned RGB-D frame

        Returns:
            RGBDFrame or None if capture failed
        """
        if not self.is_open:
            return None

        if self.version == KinectVersion.V1:
            return self._get_frame_v1()
        elif self.version == KinectVersion.V2:
            return self._get_frame_v2()
        elif self.version == KinectVersion.AZURE:
            return self._get_frame_azure()

        return None

    def _get_frame_v1(self) -> Optional[RGBDFrame]:
        """Get frame from Kinect v1"""
        try:
            import freenect

            # Get RGB frame
            rgb, _ = freenect.sync_get_video()
            rgb = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            # Get depth frame
            depth, _ = freenect.sync_get_depth(format=freenect.DEPTH_MM)

            return RGBDFrame(
                rgb=rgb,
                depth=depth.astype(np.float32),
                timestamp=time.time()
            )

        except Exception as e:
            print(f"Error capturing Kinect v1 frame: {e}")
            return None

    def _get_frame_v2(self) -> Optional[RGBDFrame]:
        """Get frame from Kinect v2"""
        try:
            from pylibfreenect2 import FrameType

            # Wait for frames
            frames = self.listener.waitForNewFrame()

            # Get color and depth
            color = frames[FrameType.Color]
            depth = frames[FrameType.Depth]

            # Convert to numpy
            rgb = color.asarray()[:, :, :3]  # Remove alpha channel
            rgb = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            depth_map = depth.asarray()

            # Create registered (aligned) depth
            undistorted = np.zeros((424, 512), dtype=np.float32)
            registered = np.zeros((1080, 1920), dtype=np.float32)

            self.registration.apply(
                color, depth, undistorted, registered
            )

            # Release frames
            self.listener.release(frames)

            return RGBDFrame(
                rgb=rgb,
                depth=registered,
                timestamp=time.time()
            )

        except Exception as e:
            print(f"Error capturing Kinect v2 frame: {e}")
            return None

    def _get_frame_azure(self) -> Optional[RGBDFrame]:
        """Get frame from Azure Kinect"""
        try:
            # Capture frame
            capture = self.k4a_device.get_capture()

            if capture.color is None or capture.depth is None:
                return None

            # Get RGB (convert BGRA to BGR)
            rgb = capture.color[:, :, :3]

            # Get depth
            depth = capture.depth.astype(np.float32)

            # Transform depth to color camera space
            depth_in_color = capture.transformed_depth

            return RGBDFrame(
                rgb=rgb,
                depth=depth_in_color.astype(np.float32),
                timestamp=time.time()
            )

        except Exception as e:
            print(f"Error capturing Azure Kinect frame: {e}")
            return None

    def get_depth_at_point(self, frame: RGBDFrame, x: int, y: int,
                          window_size: int = 5) -> Optional[float]:
        """
        Get depth at specific pixel with averaging

        Args:
            frame: RGB-D frame
            x, y: Pixel coordinates
            window_size: Average over window (reduces noise)

        Returns:
            Depth in millimeters or None if invalid
        """
        h, w = frame.depth.shape

        # Check bounds
        half_window = window_size // 2
        if (x < half_window or x >= w - half_window or
            y < half_window or y >= h - half_window):
            return None

        # Extract window
        window = frame.depth[
            y - half_window : y + half_window + 1,
            x - half_window : x + half_window + 1
        ]

        # Filter invalid depths
        valid_depths = window[window > 0]

        if len(valid_depths) == 0:
            return None

        # Return median (robust to outliers)
        return float(np.median(valid_depths))

    def pixel_to_3d(self, x: int, y: int, depth: float) -> Tuple[float, float, float]:
        """
        Convert pixel + depth to 3D point

        Args:
            x, y: Pixel coordinates
            depth: Depth in millimeters

        Returns:
            3D point (X, Y, Z) in millimeters
        """
        # Get intrinsics
        fx, fy = self.camera_matrix[0, 0], self.camera_matrix[1, 1]
        cx, cy = self.camera_matrix[0, 2], self.camera_matrix[1, 2]

        # Back-project
        X = (x - cx) * depth / fx
        Y = (y - cy) * depth / fy
        Z = depth

        return (X, Y, Z)

    def close(self):
        """Close Kinect device"""
        if not self.is_open:
            return

        try:
            if self.version == KinectVersion.V1:
                import freenect
                freenect.sync_stop()
                if self.device:
                    freenect.close_device(self.device)
                if self.freenect_ctx:
                    freenect.shutdown(self.freenect_ctx)

            elif self.version == KinectVersion.V2:
                if self.freenect2_device:
                    self.freenect2_device.stop()
                    self.freenect2_device.close()

            elif self.version == KinectVersion.AZURE:
                if self.k4a_device:
                    self.k4a_device.stop()

            self.is_open = False
            print("✓ Kinect closed")

        except Exception as e:
            print(f"Error closing Kinect: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def visualize_depth(depth: np.ndarray, min_depth: float = 500,
                   max_depth: float = 4000) -> np.ndarray:
    """
    Convert depth map to colorized visualization

    Args:
        depth: Depth map in millimeters
        min_depth: Minimum depth for visualization
        max_depth: Maximum depth for visualization

    Returns:
        RGB visualization image
    """
    # Normalize depth to 0-255
    depth_normalized = np.clip(depth, min_depth, max_depth)
    depth_normalized = ((depth_normalized - min_depth) / (max_depth - min_depth) * 255).astype(np.uint8)

    # Apply colormap
    depth_colorized = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)

    # Set invalid depths to black
    depth_colorized[depth == 0] = 0

    return depth_colorized


def demo_kinect():
    """Demonstrate Kinect interface"""
    print("=== Kinect Camera Demo ===\n")

    # Open Kinect
    kinect = KinectInterface()

    if not kinect.open():
        print("✗ Failed to open Kinect camera")
        print("\nMake sure:")
        print("  1. Kinect is connected via USB")
        print("  2. Required library is installed:")
        print("     - Kinect v1: pip install freenect")
        print("     - Kinect v2: pip install pylibfreenect2")
        print("     - Azure: pip install pyk4a")
        return

    print(f"Opened: {kinect.version.value}")
    print(f"RGB resolution: {kinect.rgb_resolution}")
    print(f"Depth resolution: {kinect.depth_resolution}")
    print(f"Depth range: {kinect.depth_range[0]}-{kinect.depth_range[1]} mm\n")

    print("Press 'q' to quit, 's' to save frame, 'p' for point cloud\n")

    try:
        while True:
            # Capture frame
            frame = kinect.get_rgbd_frame()

            if frame is None:
                print("Failed to capture frame")
                time.sleep(0.1)
                continue

            # Visualize
            depth_viz = visualize_depth(frame.depth)

            # Combine RGB and depth
            combined = np.hstack([frame.rgb, depth_viz])

            # Add text overlay
            cv2.putText(combined, f"{kinect.version.value}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow('Kinect - RGB | Depth', combined)

            # Handle keys
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save frame
                cv2.imwrite('kinect_rgb.png', frame.rgb)
                cv2.imwrite('kinect_depth.png', depth_viz)
                np.save('kinect_depth.npy', frame.depth)
                print("✓ Saved frame")
            elif key == ord('p'):
                # Generate point cloud
                pc = frame.get_point_cloud(kinect.camera_matrix)
                np.save('kinect_pointcloud.npy', pc)
                print(f"✓ Saved point cloud ({pc.shape[0]} points)")

    finally:
        kinect.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    demo_kinect()

#!/usr/bin/env python3
"""
3D Vision Controller with Kinect Support

Enhanced vision controller that integrates RGB-D data from Kinect cameras
for improved 3D object detection, localization, and manipulation.

Key improvements over regular vision:
- Accurate 3D object positions (not just X, Y but also Z depth)
- Better occlusion handling
- Object volume and shape estimation
- Point cloud processing
- Collision avoidance with depth sensing
"""

import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from kinect_interface import KinectInterface, RGBDFrame, visualize_depth
from vision_controller import DetectedObject, CoordinateTransformer


@dataclass
class Object3D:
    """3D object detection result"""
    label: str
    position_2d: Tuple[int, int]      # Pixel coordinates (x, y)
    position_3d: Tuple[float, float, float]  # 3D position (X, Y, Z) in mm
    position_robot: Optional[Tuple[float, float, float]]  # Robot coordinates
    depth: float                      # Depth in mm
    bbox_2d: Tuple[int, int, int, int]  # 2D bounding box (x, y, w, h)
    bbox_3d: Optional[Dict]           # 3D bounding box
    point_cloud: Optional[np.ndarray] # Object point cloud
    volume: Optional[float]           # Estimated volume in mm³
    confidence: float                 # Detection confidence


class VisionController3D:
    """
    Enhanced vision controller with depth sensing

    Combines RGB detection with depth data for accurate 3D localization
    """

    def __init__(self, kinect: KinectInterface,
                 coordinate_transformer: Optional[CoordinateTransformer] = None):
        """
        Initialize 3D vision controller

        Args:
            kinect: Kinect interface
            coordinate_transformer: Camera to robot coordinate transformer
        """
        self.kinect = kinect
        self.transformer = coordinate_transformer

        # Latest frame
        self.current_frame: Optional[RGBDFrame] = None

        # Detection parameters
        self.min_object_area = 500
        self.max_object_area = 50000
        self.depth_smoothing_window = 5

    def capture_frame(self) -> bool:
        """
        Capture RGB-D frame from Kinect

        Returns:
            True if frame captured successfully
        """
        self.current_frame = self.kinect.get_rgbd_frame()
        return self.current_frame is not None

    def detect_objects_color(self, lower_hsv: Tuple[int, int, int],
                            upper_hsv: Tuple[int, int, int],
                            frame: Optional[RGBDFrame] = None) -> List[Object3D]:
        """
        Detect objects by color with depth information

        Args:
            lower_hsv: Lower HSV threshold
            upper_hsv: Upper HSV threshold
            frame: RGB-D frame (uses current if None)

        Returns:
            List of detected 3D objects
        """
        if frame is None:
            frame = self.current_frame

        if frame is None:
            return []

        # Convert to HSV
        hsv = cv2.cvtColor(frame.rgb, cv2.COLOR_BGR2HSV)

        # Create mask
        mask = cv2.inRange(hsv, np.array(lower_hsv), np.array(upper_hsv))

        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Process each contour
        objects = []

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            if area < self.min_object_area or area > self.max_object_area:
                continue

            # Get 2D properties
            moments = cv2.moments(contour)
            if moments['m00'] == 0:
                continue

            cx = int(moments['m10'] / moments['m00'])
            cy = int(moments['m01'] / moments['m00'])

            x, y, w, h = cv2.boundingRect(contour)

            # Get depth at object center
            depth = self.kinect.get_depth_at_point(
                frame, cx, cy,
                window_size=self.depth_smoothing_window
            )

            if depth is None or depth == 0:
                continue

            # Convert to 3D
            X, Y, Z = self.kinect.pixel_to_3d(cx, cy, depth)

            # Transform to robot coordinates if transformer available
            robot_coords = None
            if self.transformer:
                robot_coords = self.transformer.pixel_to_robot(cx, cy)
                # Add depth as Z coordinate
                robot_coords = (robot_coords[0], robot_coords[1], Z)

            # Extract object point cloud
            point_cloud = self._extract_object_cloud(frame, mask, contour)

            # Estimate volume
            volume = self._estimate_volume(point_cloud) if point_cloud is not None else None

            # Create 3D object
            obj = Object3D(
                label=f"object_{i}",
                position_2d=(cx, cy),
                position_3d=(X, Y, Z),
                position_robot=robot_coords,
                depth=depth,
                bbox_2d=(x, y, w, h),
                bbox_3d=self._compute_3d_bbox(point_cloud) if point_cloud is not None else None,
                point_cloud=point_cloud,
                volume=volume,
                confidence=min(area / self.max_object_area, 1.0)
            )

            objects.append(obj)

        return objects

    def detect_objects_contour(self, frame: Optional[RGBDFrame] = None,
                              canny_low: int = 50,
                              canny_high: int = 150) -> List[Object3D]:
        """
        Detect objects using edge detection with depth

        Args:
            frame: RGB-D frame (uses current if None)
            canny_low: Lower Canny threshold
            canny_high: Upper Canny threshold

        Returns:
            List of detected 3D objects
        """
        if frame is None:
            frame = self.current_frame

        if frame is None:
            return []

        # Convert to grayscale
        gray = cv2.cvtColor(frame.rgb, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        edges = cv2.Canny(blurred, canny_low, canny_high)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Process similar to color detection
        objects = []

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            if area < self.min_object_area or area > self.max_object_area:
                continue

            moments = cv2.moments(contour)
            if moments['m00'] == 0:
                continue

            cx = int(moments['m10'] / moments['m00'])
            cy = int(moments['m01'] / moments['m00'])

            x, y, w, h = cv2.boundingRect(contour)

            depth = self.kinect.get_depth_at_point(frame, cx, cy, self.depth_smoothing_window)

            if depth is None or depth == 0:
                continue

            X, Y, Z = self.kinect.pixel_to_3d(cx, cy, depth)

            robot_coords = None
            if self.transformer:
                robot_coords = self.transformer.pixel_to_robot(cx, cy)
                robot_coords = (robot_coords[0], robot_coords[1], Z)

            # Create mask for this contour
            mask = np.zeros(frame.rgb.shape[:2], dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)

            point_cloud = self._extract_object_cloud(frame, mask, contour)
            volume = self._estimate_volume(point_cloud) if point_cloud is not None else None

            obj = Object3D(
                label=f"edge_object_{i}",
                position_2d=(cx, cy),
                position_3d=(X, Y, Z),
                position_robot=robot_coords,
                depth=depth,
                bbox_2d=(x, y, w, h),
                bbox_3d=self._compute_3d_bbox(point_cloud) if point_cloud is not None else None,
                point_cloud=point_cloud,
                volume=volume,
                confidence=min(area / self.max_object_area, 1.0)
            )

            objects.append(obj)

        return objects

    def detect_objects_depth_clustering(self, frame: Optional[RGBDFrame] = None,
                                       depth_threshold: float = 50.0) -> List[Object3D]:
        """
        Detect objects using depth-based clustering

        Groups pixels with similar depths into object clusters

        Args:
            frame: RGB-D frame
            depth_threshold: Maximum depth difference within object (mm)

        Returns:
            List of detected 3D objects
        """
        if frame is None:
            frame = self.current_frame

        if frame is None:
            return []

        # Get valid depth mask
        valid_mask = (frame.depth > 0).astype(np.uint8) * 255

        # Find connected components in depth image
        # (pixels with similar depths)
        depth_normalized = cv2.normalize(frame.depth, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        depth_normalized[frame.depth == 0] = 0

        # Apply threshold to group similar depths
        _, thresh = cv2.threshold(depth_normalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Find contours in thresholded depth
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        objects = []

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            if area < self.min_object_area or area > self.max_object_area:
                continue

            # Get centroid
            moments = cv2.moments(contour)
            if moments['m00'] == 0:
                continue

            cx = int(moments['m10'] / moments['m00'])
            cy = int(moments['m01'] / moments['m00'])

            x, y, w, h = cv2.boundingRect(contour)

            depth = self.kinect.get_depth_at_point(frame, cx, cy, self.depth_smoothing_window)

            if depth is None or depth == 0:
                continue

            X, Y, Z = self.kinect.pixel_to_3d(cx, cy, depth)

            robot_coords = None
            if self.transformer:
                robot_coords = self.transformer.pixel_to_robot(cx, cy)
                robot_coords = (robot_coords[0], robot_coords[1], Z)

            # Create mask
            mask = np.zeros(frame.rgb.shape[:2], dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)

            point_cloud = self._extract_object_cloud(frame, mask, contour)
            volume = self._estimate_volume(point_cloud) if point_cloud is not None else None

            obj = Object3D(
                label=f"depth_cluster_{i}",
                position_2d=(cx, cy),
                position_3d=(X, Y, Z),
                position_robot=robot_coords,
                depth=depth,
                bbox_2d=(x, y, w, h),
                bbox_3d=self._compute_3d_bbox(point_cloud) if point_cloud is not None else None,
                point_cloud=point_cloud,
                volume=volume,
                confidence=min(area / self.max_object_area, 1.0)
            )

            objects.append(obj)

        return objects

    def _extract_object_cloud(self, frame: RGBDFrame, mask: np.ndarray,
                             contour: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract point cloud for specific object

        Args:
            frame: RGB-D frame
            mask: Binary mask of object
            contour: Object contour

        Returns:
            Nx6 point cloud (X, Y, Z, R, G, B) or None
        """
        try:
            # Get bounding box to reduce computation
            x, y, w, h = cv2.boundingRect(contour)

            # Extract region
            depth_roi = frame.depth[y:y+h, x:x+w]
            rgb_roi = frame.rgb[y:y+h, x:x+w]
            mask_roi = mask[y:y+h, x:x+w]

            # Get camera intrinsics
            fx, fy = self.kinect.camera_matrix[0, 0], self.kinect.camera_matrix[1, 1]
            cx, cy = self.kinect.camera_matrix[0, 2], self.kinect.camera_matrix[1, 2]

            # Create coordinate grids
            u, v = np.meshgrid(np.arange(w), np.arange(h))
            u = u + x
            v = v + y

            # Get valid points (masked and with valid depth)
            valid = (mask_roi > 0) & (depth_roi > 0)

            if np.sum(valid) == 0:
                return None

            # Convert to 3D
            z = depth_roi[valid]
            x_pts = (u[valid] - cx) * z / fx
            y_pts = (v[valid] - cy) * z / fy

            # Get colors
            colors = rgb_roi[valid] / 255.0

            # Combine
            points = np.stack([x_pts, y_pts, z], axis=1)
            point_cloud = np.hstack([points, colors])

            return point_cloud

        except Exception as e:
            print(f"Error extracting point cloud: {e}")
            return None

    def _compute_3d_bbox(self, point_cloud: np.ndarray) -> Dict:
        """
        Compute 3D bounding box from point cloud

        Args:
            point_cloud: Nx6 point cloud

        Returns:
            Dictionary with bbox parameters
        """
        if point_cloud is None or len(point_cloud) == 0:
            return None

        # Get 3D coordinates
        points_3d = point_cloud[:, :3]

        # Compute min/max along each axis
        min_pt = np.min(points_3d, axis=0)
        max_pt = np.max(points_3d, axis=0)

        # Compute center and size
        center = (min_pt + max_pt) / 2
        size = max_pt - min_pt

        return {
            'center': tuple(center),
            'size': tuple(size),
            'min': tuple(min_pt),
            'max': tuple(max_pt)
        }

    def _estimate_volume(self, point_cloud: np.ndarray) -> Optional[float]:
        """
        Estimate object volume from point cloud

        Args:
            point_cloud: Nx6 point cloud

        Returns:
            Volume in mm³ or None
        """
        if point_cloud is None or len(point_cloud) == 0:
            return None

        # Simple bounding box volume
        bbox = self._compute_3d_bbox(point_cloud)
        if bbox is None:
            return None

        volume = np.prod(bbox['size'])
        return float(volume)

    def visualize_detections(self, objects: List[Object3D],
                            frame: Optional[RGBDFrame] = None) -> np.ndarray:
        """
        Visualize detected 3D objects

        Args:
            objects: List of detected objects
            frame: RGB-D frame (uses current if None)

        Returns:
            Visualization image
        """
        if frame is None:
            frame = self.current_frame

        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)

        # Create visualization
        vis = frame.rgb.copy()

        for obj in objects:
            # Draw 2D bounding box
            x, y, w, h = obj.bbox_2d
            cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Draw center point
            cv2.circle(vis, obj.position_2d, 5, (0, 0, 255), -1)

            # Add text label with depth
            label = f"{obj.label}"
            depth_text = f"Z={obj.depth/1000:.2f}m"

            cv2.putText(vis, label, (x, y-25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(vis, depth_text, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            # Add 3D position if available
            if obj.position_robot:
                robot_text = f"({obj.position_robot[0]:.0f}, {obj.position_robot[1]:.0f}, {obj.position_robot[2]:.0f})"
                cv2.putText(vis, robot_text, (x, y+h+15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)

        return vis


def demo_3d_vision():
    """Demonstrate 3D vision controller"""
    print("=== 3D Vision Controller Demo ===\n")

    # Open Kinect
    kinect = KinectInterface()
    if not kinect.open():
        print("Failed to open Kinect")
        return

    # Create 3D vision controller
    vision = VisionController3D(kinect)

    print("Press keys:")
    print("  'c' - Color detection (red objects)")
    print("  'e' - Edge detection")
    print("  'd' - Depth clustering")
    print("  'q' - Quit\n")

    detection_mode = 'c'

    try:
        while True:
            # Capture frame
            if not vision.capture_frame():
                continue

            # Detect based on mode
            if detection_mode == 'c':
                # Detect red objects
                objects = vision.detect_objects_color(
                    lower_hsv=(0, 100, 100),
                    upper_hsv=(10, 255, 255)
                )
            elif detection_mode == 'e':
                objects = vision.detect_objects_contour()
            elif detection_mode == 'd':
                objects = vision.detect_objects_depth_clustering()
            else:
                objects = []

            # Visualize
            vis_rgb = vision.visualize_detections(objects)
            vis_depth = visualize_depth(vision.current_frame.depth)

            combined = np.hstack([vis_rgb, vis_depth])

            # Add mode indicator
            mode_text = {'c': 'Color', 'e': 'Edge', 'd': 'Depth'}[detection_mode]
            cv2.putText(combined, f"Mode: {mode_text}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            cv2.imshow('3D Vision - RGB | Depth', combined)

            # Print detections
            if objects:
                print(f"\n{len(objects)} objects detected:")
                for obj in objects:
                    print(f"  {obj.label}: depth={obj.depth/1000:.2f}m, "
                          f"pos=({obj.position_3d[0]:.0f}, {obj.position_3d[1]:.0f}, {obj.position_3d[2]:.0f})")
                    if obj.volume:
                        print(f"    volume={obj.volume/1000:.1f} cm³")

            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key in [ord('c'), ord('e'), ord('d')]:
                detection_mode = chr(key)

    finally:
        kinect.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    demo_3d_vision()

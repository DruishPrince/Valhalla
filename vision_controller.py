"""
Vision Controller Module
Provides computer vision capabilities for robotic arm control including
object detection, tracking, and coordinate transformation
"""
import cv2
import numpy as np
from typing import Optional, List, Tuple, Dict, Callable
from dataclasses import dataclass
from enum import Enum


class DetectionMethod(Enum):
    """Object detection methods"""
    COLOR_THRESHOLD = "color_threshold"
    CONTOUR_DETECTION = "contour_detection"
    ARUCO_MARKER = "aruco_marker"
    TEMPLATE_MATCHING = "template_matching"
    FEATURE_MATCHING = "feature_matching"


@dataclass
class DetectedObject:
    """Represents a detected object in the image"""
    center_x: int
    center_y: int
    width: int
    height: int
    confidence: float
    label: str = ""
    contour: Optional[np.ndarray] = None
    bounding_box: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h

    def get_center(self) -> Tuple[int, int]:
        """Get center point as tuple"""
        return (self.center_x, self.center_y)


class CoordinateTransformer:
    """
    Transforms coordinates between camera space and robot workspace
    """

    def __init__(self):
        # Camera calibration parameters
        self.camera_matrix: Optional[np.ndarray] = None
        self.dist_coeffs: Optional[np.ndarray] = None

        # Transformation matrix from camera to robot base
        self.camera_to_robot_transform: Optional[np.ndarray] = None

        # Calibration points (camera pixels -> robot coordinates)
        self.calibration_points_camera: List[Tuple[float, float]] = []
        self.calibration_points_robot: List[Tuple[float, float, float]] = []

        # Working plane parameters (for 2D->3D projection)
        self.plane_height: float = 0.0  # Z height of working surface

    def calibrate_from_points(self,
                             camera_points: List[Tuple[float, float]],
                             robot_points: List[Tuple[float, float, float]]):
        """
        Calibrate transformation using known point correspondences

        Args:
            camera_points: List of (x, y) pixel coordinates
            robot_points: List of (x, y, z) robot coordinates in mm/degrees
        """
        if len(camera_points) < 4 or len(camera_points) != len(robot_points):
            raise ValueError("Need at least 4 matching point pairs for calibration")

        self.calibration_points_camera = camera_points
        self.calibration_points_robot = robot_points

        # Create homography matrix for 2D transformation
        src_points = np.array(camera_points, dtype=np.float32)
        # Use only X,Y from robot points for 2D homography
        dst_points = np.array([(p[0], p[1]) for p in robot_points], dtype=np.float32)

        # Calculate homography
        self.camera_to_robot_transform, _ = cv2.findHomography(src_points, dst_points)

        # Set plane height as average Z of calibration points
        self.plane_height = np.mean([p[2] for p in robot_points])

    def pixel_to_robot(self, pixel_x: float, pixel_y: float) -> Tuple[float, float, float]:
        """
        Convert pixel coordinates to robot workspace coordinates

        Args:
            pixel_x: X pixel coordinate
            pixel_y: Y pixel coordinate

        Returns:
            Tuple of (x, y, z) in robot coordinates
        """
        if self.camera_to_robot_transform is None:
            raise ValueError("Coordinate transformer not calibrated")

        # Apply homography transformation
        pixel_point = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)
        robot_point = cv2.perspectiveTransform(pixel_point, self.camera_to_robot_transform)

        x, y = robot_point[0][0]
        z = self.plane_height

        return (float(x), float(y), float(z))

    def robot_to_pixel(self, robot_x: float, robot_y: float) -> Tuple[int, int]:
        """
        Convert robot coordinates to pixel coordinates

        Args:
            robot_x: X robot coordinate
            robot_y: Y robot coordinate

        Returns:
            Tuple of (pixel_x, pixel_y)
        """
        if self.camera_to_robot_transform is None:
            raise ValueError("Coordinate transformer not calibrated")

        # Invert homography
        inv_transform = np.linalg.inv(self.camera_to_robot_transform)

        robot_point = np.array([[[robot_x, robot_y]]], dtype=np.float32)
        pixel_point = cv2.perspectiveTransform(robot_point, inv_transform)

        x, y = pixel_point[0][0]
        return (int(x), int(y))

    def load_calibration(self, filepath: str) -> bool:
        """Load calibration data from file"""
        try:
            data = np.load(filepath, allow_pickle=True)
            self.camera_to_robot_transform = data['transform']
            self.plane_height = float(data['plane_height'])
            self.calibration_points_camera = data['camera_points'].tolist()
            self.calibration_points_robot = data['robot_points'].tolist()
            return True
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return False

    def save_calibration(self, filepath: str) -> bool:
        """Save calibration data to file"""
        try:
            np.savez(filepath,
                    transform=self.camera_to_robot_transform,
                    plane_height=self.plane_height,
                    camera_points=np.array(self.calibration_points_camera),
                    robot_points=np.array(self.calibration_points_robot))
            return True
        except Exception as e:
            print(f"Error saving calibration: {e}")
            return False


class VisionController:
    """
    Main computer vision controller for robotic arm
    """

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.capture: Optional[cv2.VideoCapture] = None
        self.current_frame: Optional[np.ndarray] = None
        self.is_running = False

        # Coordinate transformer
        self.transformer = CoordinateTransformer()

        # Detection parameters
        self.detection_method = DetectionMethod.CONTOUR_DETECTION

        # Color detection parameters (HSV)
        self.color_lower = np.array([0, 100, 100])
        self.color_upper = np.array([10, 255, 255])

        # Callbacks
        self.on_frame_processed: Optional[Callable[[np.ndarray], None]] = None
        self.on_object_detected: Optional[Callable[[List[DetectedObject]], None]] = None

    def start_camera(self) -> bool:
        """Start camera capture"""
        try:
            self.capture = cv2.VideoCapture(self.camera_index)
            if not self.capture.isOpened():
                return False

            # Set camera properties for better performance
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.capture.set(cv2.CAP_PROP_FPS, 30)

            self.is_running = True
            return True
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False

    def stop_camera(self):
        """Stop camera capture"""
        self.is_running = False
        if self.capture:
            self.capture.release()
            self.capture = None

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from camera

        Returns:
            Frame as numpy array or None if failed
        """
        if not self.capture or not self.capture.isOpened():
            return None

        ret, frame = self.capture.read()
        if ret:
            self.current_frame = frame
            return frame
        return None

    def detect_objects_by_color(self,
                                frame: np.ndarray,
                                lower_hsv: np.ndarray,
                                upper_hsv: np.ndarray,
                                min_area: int = 100) -> List[DetectedObject]:
        """
        Detect objects by color thresholding

        Args:
            frame: Input image
            lower_hsv: Lower HSV threshold
            upper_hsv: Upper HSV threshold
            min_area: Minimum contour area to consider

        Returns:
            List of detected objects
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Create mask
        mask = cv2.inRange(hsv, lower_hsv, upper_hsv)

        # Morphological operations to clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detected_objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)

            # Calculate center
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2

            obj = DetectedObject(
                center_x=cx,
                center_y=cy,
                width=w,
                height=h,
                confidence=min(1.0, area / 10000),  # Normalize confidence
                label="color_object",
                contour=contour,
                bounding_box=(x, y, w, h)
            )

            detected_objects.append(obj)

        return detected_objects

    def detect_objects_by_contour(self,
                                  frame: np.ndarray,
                                  min_area: int = 500,
                                  max_area: int = 50000) -> List[DetectedObject]:
        """
        Detect objects by finding contours in edge-detected image

        Args:
            frame: Input image
            min_area: Minimum contour area
            max_area: Maximum contour area

        Returns:
            List of detected objects
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)

        # Dilate edges to close gaps
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detected_objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area > max_area:
                continue

            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)

            # Calculate center
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2

            # Calculate confidence based on contour properties
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0

            obj = DetectedObject(
                center_x=cx,
                center_y=cy,
                width=w,
                height=h,
                confidence=float(circularity),
                label="contour_object",
                contour=contour,
                bounding_box=(x, y, w, h)
            )

            detected_objects.append(obj)

        return detected_objects

    def detect_aruco_markers(self,
                            frame: np.ndarray,
                            dictionary_type=cv2.aruco.DICT_4X4_50) -> List[DetectedObject]:
        """
        Detect ArUco markers in frame

        Args:
            frame: Input image
            dictionary_type: ArUco dictionary to use

        Returns:
            List of detected markers
        """
        try:
            # Create ArUco dictionary and parameters
            aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_type)
            aruco_params = cv2.aruco.DetectorParameters()

            # Detect markers
            corners, ids, rejected = cv2.aruco.detectMarkers(
                frame, aruco_dict, parameters=aruco_params
            )

            detected_objects = []
            if ids is not None:
                for i, corner in enumerate(corners):
                    # Calculate center
                    cx = int(np.mean(corner[0][:, 0]))
                    cy = int(np.mean(corner[0][:, 1]))

                    # Calculate bounding box
                    x_min = int(np.min(corner[0][:, 0]))
                    y_min = int(np.min(corner[0][:, 1]))
                    x_max = int(np.max(corner[0][:, 0]))
                    y_max = int(np.max(corner[0][:, 1]))
                    w = x_max - x_min
                    h = y_max - y_min

                    obj = DetectedObject(
                        center_x=cx,
                        center_y=cy,
                        width=w,
                        height=h,
                        confidence=1.0,
                        label=f"ArUco_{ids[i][0]}",
                        bounding_box=(x_min, y_min, w, h)
                    )

                    detected_objects.append(obj)

            return detected_objects
        except Exception as e:
            print(f"Error detecting ArUco markers: {e}")
            return []

    def draw_detections(self,
                       frame: np.ndarray,
                       objects: List[DetectedObject],
                       show_labels: bool = True,
                       show_centers: bool = True) -> np.ndarray:
        """
        Draw detected objects on frame

        Args:
            frame: Input image
            objects: List of detected objects
            show_labels: Draw object labels
            show_centers: Draw center points

        Returns:
            Frame with drawings
        """
        output = frame.copy()

        for obj in objects:
            # Draw bounding box
            if obj.bounding_box:
                x, y, w, h = obj.bounding_box
                color = (0, 255, 0)  # Green
                cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)

            # Draw center
            if show_centers:
                cv2.circle(output, (obj.center_x, obj.center_y), 5, (0, 0, 255), -1)

            # Draw label
            if show_labels and obj.label:
                label_text = f"{obj.label} ({obj.confidence:.2f})"
                cv2.putText(output, label_text,
                           (obj.center_x - 50, obj.center_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            # Draw contour
            if obj.contour is not None:
                cv2.drawContours(output, [obj.contour], -1, (255, 0, 0), 2)

        return output

    def process_frame(self, frame: Optional[np.ndarray] = None) -> Tuple[np.ndarray, List[DetectedObject]]:
        """
        Process a frame and detect objects

        Args:
            frame: Frame to process (uses current_frame if None)

        Returns:
            Tuple of (processed_frame, detected_objects)
        """
        if frame is None:
            frame = self.get_frame()

        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8), []

        # Detect objects based on selected method
        if self.detection_method == DetectionMethod.COLOR_THRESHOLD:
            objects = self.detect_objects_by_color(frame, self.color_lower, self.color_upper)
        elif self.detection_method == DetectionMethod.CONTOUR_DETECTION:
            objects = self.detect_objects_by_contour(frame)
        elif self.detection_method == DetectionMethod.ARUCO_MARKER:
            objects = self.detect_aruco_markers(frame)
        else:
            objects = []

        # Draw detections on frame
        processed_frame = self.draw_detections(frame, objects)

        # Trigger callbacks
        if self.on_frame_processed:
            self.on_frame_processed(processed_frame)

        if objects and self.on_object_detected:
            self.on_object_detected(objects)

        return processed_frame, objects

    def get_robot_coordinates(self, detected_object: DetectedObject) -> Optional[Tuple[float, float, float]]:
        """
        Convert detected object position to robot coordinates

        Args:
            detected_object: Detected object

        Returns:
            Robot coordinates (x, y, z) or None if transformation not calibrated
        """
        try:
            return self.transformer.pixel_to_robot(
                detected_object.center_x,
                detected_object.center_y
            )
        except ValueError:
            return None


# Helper functions
def create_vision_controller(camera_index: int = 0) -> VisionController:
    """Create and initialize a vision controller"""
    return VisionController(camera_index)


def create_coordinate_transformer() -> CoordinateTransformer:
    """Create a coordinate transformer"""
    return CoordinateTransformer()

"""
Example Scripts for Using the Enhanced Robot Control System

This file contains practical examples demonstrating:
1. Basic robot control
2. Recording and playing action sequences
3. Computer vision integration
4. Vision-guided manipulation
"""

from robot_controller import RobotController, MovementType
from action_sequencer import ActionSequencer, ActionSequence, create_pick_and_place_sequence
from vision_controller import VisionController, DetectionMethod
import time


# ============================================================================
# EXAMPLE 1: Basic Robot Control
# ============================================================================
def example_basic_control():
    """
    Demonstrates basic robot control operations
    """
    print("=== Example 1: Basic Robot Control ===\n")

    # Create robot controller
    robot = RobotController()

    # Connect to robot (adjust port for your system)
    # Linux: typically '/dev/ttyUSB0' or '/dev/ttyACM0'
    # Windows: typically 'COM3', 'COM4', etc.
    if robot.connect('/dev/ttyUSB0', baudrate=115200):
        print("✓ Connected to robot\n")
    else:
        print("✗ Failed to connect to robot")
        return

    # Home the robot
    print("Homing robot...")
    robot.send_homing_command()
    time.sleep(3)

    # Move individual joints
    print("Moving base (joint A) to 45°...")
    robot.move_joint('A', 45.0, MovementType.G1_LINEAR, feedrate=300)
    time.sleep(2)

    print("Moving shoulder (joint B) to 30°...")
    robot.move_joint('B', 30.0, MovementType.G1_LINEAR, feedrate=300)
    time.sleep(2)

    # Move multiple joints simultaneously
    print("Moving multiple joints...")
    robot.move_all_joints(
        {'A': 0.0, 'B': 45.0, 'D': -30.0},
        MovementType.G1_LINEAR,
        feedrate=400
    )
    time.sleep(3)

    # Control gripper
    print("Opening gripper...")
    robot.move_gripper(100)  # 100% open
    time.sleep(1)

    print("Closing gripper...")
    robot.move_gripper(0)  # 0% closed
    time.sleep(1)

    # Return to zero position
    print("Returning to zero position...")
    robot.send_zero_position()
    time.sleep(3)

    robot.disconnect()
    print("\n✓ Example 1 complete\n")


# ============================================================================
# EXAMPLE 2: Recording and Playing Action Sequences
# ============================================================================
def example_sequence_recording():
    """
    Demonstrates recording and playing back action sequences
    """
    print("=== Example 2: Recording and Playing Sequences ===\n")

    # Create robot controller and sequencer
    robot = RobotController()
    sequencer = ActionSequencer(robot)

    if not robot.connect('/dev/ttyUSB0'):
        print("✗ Failed to connect to robot")
        return

    print("✓ Connected to robot\n")

    # Start recording a sequence
    print("Starting sequence recording...")
    sequencer.start_recording("Demo Sequence")

    # Record some movements
    print("Recording movements...")

    sequencer.record_move_joint('A', 45.0, MovementType.G1_LINEAR, feedrate=300,
                                description="Move base to 45°")
    time.sleep(1)

    sequencer.record_move_joint('B', 30.0, MovementType.G1_LINEAR, feedrate=300,
                                description="Move shoulder to 30°")
    time.sleep(1)

    sequencer.record_gripper(100, description="Open gripper")
    time.sleep(0.5)

    sequencer.record_wait(1.0, description="Wait 1 second")

    sequencer.record_gripper(0, description="Close gripper")
    time.sleep(0.5)

    sequencer.record_move_all(
        {'A': 0.0, 'B': 0.0},
        MovementType.G1_LINEAR,
        feedrate=300,
        description="Return to zero"
    )

    # Stop recording
    sequencer.stop_recording()
    print("✓ Recording complete\n")

    # Save sequence to file
    print("Saving sequence to file...")
    if sequencer.save_sequence('demo_sequence.json'):
        print("✓ Sequence saved\n")
    else:
        print("✗ Failed to save sequence\n")

    # Play back the sequence
    input("Press Enter to play back the sequence...")
    print("Playing sequence...")
    sequencer.play_sequence(respect_timing=True)
    print("✓ Playback complete\n")

    robot.disconnect()
    print("✓ Example 2 complete\n")


# ============================================================================
# EXAMPLE 3: Loading and Using Pre-defined Sequences
# ============================================================================
def example_predefined_sequence():
    """
    Demonstrates using pre-defined sequences (like pick-and-place)
    """
    print("=== Example 3: Pre-defined Pick-and-Place Sequence ===\n")

    robot = RobotController()
    sequencer = ActionSequencer(robot)

    if not robot.connect('/dev/ttyUSB0'):
        print("✗ Failed to connect to robot")
        return

    print("✓ Connected to robot\n")

    # Define pick and place positions
    pick_position = {
        'A': 45.0,   # Base rotation
        'B': 30.0,   # Shoulder
        'D': -20.0,  # Elbow
        'X': 10.0    # Wrist
    }

    place_position = {
        'A': -45.0,  # Base rotation
        'B': 35.0,   # Shoulder
        'D': -25.0,  # Elbow
        'X': 15.0    # Wrist
    }

    # Create pick-and-place sequence
    print("Creating pick-and-place sequence...")
    sequence = create_pick_and_place_sequence(
        pick_position,
        place_position,
        approach_height=10.0,
        name="Example Pick and Place"
    )

    # Save it for later use
    sequence.save_to_file('pick_and_place.json')
    print(f"✓ Created sequence with {len(sequence.actions)} actions\n")

    # Execute the sequence
    input("Press Enter to execute pick-and-place...")
    print("Executing sequence...")
    sequencer.play_sequence(sequence, respect_timing=False)
    print("✓ Sequence complete\n")

    robot.disconnect()
    print("✓ Example 3 complete\n")


# ============================================================================
# EXAMPLE 4: Computer Vision - Object Detection
# ============================================================================
def example_vision_detection():
    """
    Demonstrates basic computer vision object detection
    """
    print("=== Example 4: Computer Vision Object Detection ===\n")

    # Create vision controller
    vision = VisionController(camera_index=0)

    if not vision.start_camera():
        print("✗ Failed to start camera")
        return

    print("✓ Camera started\n")

    # Set detection method
    vision.detection_method = DetectionMethod.CONTOUR_DETECTION

    print("Detecting objects (press 'q' to quit)...")
    print("Detection methods:")
    print("  1 - Color threshold")
    print("  2 - Contour detection")
    print("  3 - ArUco markers\n")

    try:
        while True:
            # Process frame and detect objects
            frame, objects = vision.process_frame()

            if frame is not None:
                # Display results
                import cv2
                cv2.imshow('Object Detection', frame)

                # Print detected objects
                if objects:
                    print(f"\rDetected {len(objects)} objects", end='', flush=True)
                    for obj in objects:
                        # Print object details
                        if obj.confidence > 0.5:  # Only high-confidence detections
                            pass  # Could print details here

                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('1'):
                    vision.detection_method = DetectionMethod.COLOR_THRESHOLD
                    print("\nSwitched to color threshold detection")
                elif key == ord('2'):
                    vision.detection_method = DetectionMethod.CONTOUR_DETECTION
                    print("\nSwitched to contour detection")
                elif key == ord('3'):
                    vision.detection_method = DetectionMethod.ARUCO_MARKER
                    print("\nSwitched to ArUco marker detection")

    finally:
        import cv2
        cv2.destroyAllWindows()
        vision.stop_camera()
        print("\n\n✓ Example 4 complete\n")


# ============================================================================
# EXAMPLE 5: Vision-Guided Robot Control
# ============================================================================
def example_vision_guided_control():
    """
    Demonstrates using computer vision to guide robot movements
    """
    print("=== Example 5: Vision-Guided Robot Control ===\n")

    # Create controllers
    robot = RobotController()
    vision = VisionController(camera_index=0)

    # Connect robot
    if not robot.connect('/dev/ttyUSB0'):
        print("✗ Failed to connect to robot")
        return

    # Start camera
    if not vision.start_camera():
        print("✗ Failed to start camera")
        robot.disconnect()
        return

    print("✓ Robot and camera ready\n")

    # Note: Calibration would need to be done first in a real application
    # For this example, we'll show the structure

    print("Camera calibration needed before vision-guided control")
    print("Calibration steps:")
    print("  1. Place calibration markers at known robot positions")
    print("  2. Record pixel coordinates and corresponding robot coordinates")
    print("  3. Use transformer.calibrate_from_points()")
    print("\nExample calibration:")

    # Example calibration (these would be measured in real use)
    camera_points = [
        (100, 100), (500, 100), (100, 400), (500, 400)
    ]
    robot_points = [
        (-200, -200, 0), (200, -200, 0), (-200, 200, 0), (200, 200, 0)
    ]

    vision.transformer.calibrate_from_points(camera_points, robot_points)
    print("✓ Calibration complete (example data)\n")

    # Detect objects and get robot coordinates
    vision.detection_method = DetectionMethod.CONTOUR_DETECTION

    print("Looking for objects...")
    for i in range(30):  # Try for a few frames
        frame, objects = vision.process_frame()

        if objects:
            obj = objects[0]  # Take first detected object
            print(f"\n✓ Object detected at pixel ({obj.center_x}, {obj.center_y})")

            # Convert to robot coordinates
            robot_coords = vision.get_robot_coordinates(obj)
            if robot_coords:
                x, y, z = robot_coords
                print(f"  Robot coordinates: X={x:.1f}, Y={y:.1f}, Z={z:.1f}")

                # Here you would calculate inverse kinematics to reach this position
                # For now, we'll just show the concept
                print("  → Would move robot to reach this position")

            break

        time.sleep(0.1)

    vision.stop_camera()
    robot.disconnect()
    print("\n✓ Example 5 complete\n")


# ============================================================================
# EXAMPLE 6: Advanced - Vision-Triggered Sequence
# ============================================================================
def example_vision_triggered_sequence():
    """
    Demonstrates triggering action sequences based on vision detection
    """
    print("=== Example 6: Vision-Triggered Sequence ===\n")

    robot = RobotController()
    vision = VisionController(camera_index=0)
    sequencer = ActionSequencer(robot)

    if not robot.connect('/dev/ttyUSB0'):
        print("✗ Failed to connect to robot")
        return

    if not vision.start_camera():
        print("✗ Failed to start camera")
        robot.disconnect()
        return

    print("✓ System ready\n")

    # Load a pre-defined sequence
    sequence = ActionSequence.load_from_file('pick_and_place.json')
    if not sequence:
        print("Creating new pick-and-place sequence...")
        pick_pos = {'A': 45.0, 'B': 30.0, 'D': -20.0}
        place_pos = {'A': -45.0, 'B': 30.0, 'D': -20.0}
        sequence = create_pick_and_place_sequence(pick_pos, place_pos)

    # Set up vision detection
    vision.detection_method = DetectionMethod.ARUCO_MARKER

    print("Waiting for ArUco marker to trigger sequence...")
    print("(Press 'q' to quit)\n")

    import cv2
    try:
        while True:
            frame, objects = vision.process_frame()

            if frame is not None:
                cv2.imshow('Vision Trigger', frame)

            # Check if object detected
            if objects and not sequencer.is_playing:
                print(f"✓ Detected {len(objects)} markers - triggering sequence!")
                sequencer.play_sequence(sequence, respect_timing=False)
                time.sleep(5)  # Cooldown period

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    finally:
        cv2.destroyAllWindows()
        vision.stop_camera()
        robot.disconnect()
        print("\n✓ Example 6 complete\n")


# ============================================================================
# Main Menu
# ============================================================================
def main():
    """
    Main menu for running examples
    """
    print("\n" + "="*60)
    print("Robot Control Examples - Enhanced Asgard System")
    print("="*60 + "\n")

    examples = {
        '1': ('Basic Robot Control', example_basic_control),
        '2': ('Recording and Playing Sequences', example_sequence_recording),
        '3': ('Pre-defined Pick-and-Place', example_predefined_sequence),
        '4': ('Computer Vision Detection', example_vision_detection),
        '5': ('Vision-Guided Control', example_vision_guided_control),
        '6': ('Vision-Triggered Sequence', example_vision_triggered_sequence),
    }

    print("Available Examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  q. Quit\n")

    while True:
        choice = input("Select example to run (1-6, q to quit): ").strip()

        if choice.lower() == 'q':
            print("\nGoodbye!\n")
            break

        if choice in examples:
            name, func = examples[choice]
            print(f"\n{'='*60}")
            print(f"Running: {name}")
            print(f"{'='*60}\n")

            try:
                func()
            except KeyboardInterrupt:
                print("\n\n⚠ Example interrupted by user\n")
            except Exception as e:
                print(f"\n✗ Error running example: {e}\n")

            input("\nPress Enter to return to menu...")
            print("\n")
        else:
            print("Invalid choice. Please try again.\n")


if __name__ == '__main__':
    main()

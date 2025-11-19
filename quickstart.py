#!/usr/bin/env python3
"""
Quick Start Utility for Asgard Robot Control

This interactive tool helps you:
1. Configure your robot connection
2. Test basic movements
3. Verify camera setup
4. Run example workflows
"""

import sys
import time
from typing import Optional
from robot_controller import RobotController, MovementType, RobotState
from vision_controller import VisionController, DetectionMethod
from action_sequencer import ActionSequencer
from config_manager import ConfigManager, get_config
import serial_port_finder as spf


class QuickStart:
    """Interactive quick-start wizard"""

    def __init__(self):
        self.config = ConfigManager()
        self.robot: Optional[RobotController] = None
        self.vision: Optional[VisionController] = None
        self.sequencer: Optional[ActionSequencer] = None

    def print_header(self, text: str):
        """Print formatted header"""
        print("\n" + "=" * 60)
        print(f"  {text}")
        print("=" * 60)

    def print_step(self, step: int, total: int, text: str):
        """Print step indicator"""
        print(f"\n[Step {step}/{total}] {text}")

    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        self.print_header("Checking Dependencies")

        required = {
            'PyQt5': False,
            'pyserial': False,
            'cv2 (OpenCV)': False,
            'numpy': False
        }

        # Check PyQt5
        try:
            import PyQt5
            required['PyQt5'] = True
            print("✓ PyQt5 installed")
        except ImportError:
            print("✗ PyQt5 not found")

        # Check pyserial
        try:
            import serial
            required['pyserial'] = True
            print("✓ pyserial installed")
        except ImportError:
            print("✗ pyserial not found")

        # Check OpenCV
        try:
            import cv2
            required['cv2 (OpenCV)'] = True
            print("✓ OpenCV installed")
        except ImportError:
            print("✗ OpenCV not found")

        # Check numpy
        try:
            import numpy
            required['numpy'] = True
            print("✓ numpy installed")
        except ImportError:
            print("✗ numpy not found")

        all_installed = all(required.values())

        if not all_installed:
            print("\n⚠ Missing dependencies detected!")
            print("Install with: pip install -r requirements.txt")
            return False

        print("\n✓ All dependencies installed")
        return True

    def setup_serial_connection(self) -> bool:
        """Interactive serial port setup"""
        self.print_header("Robot Connection Setup")

        # List available ports
        ports = spf.serial_ports()

        if not ports:
            print("✗ No serial ports detected")
            print("\nMake sure:")
            print("  - Robot is powered on")
            print("  - USB cable is connected")
            print("  - Drivers are installed")
            return False

        print("\nAvailable serial ports:")
        for i, port in enumerate(ports):
            default_marker = " (saved default)" if port == self.config.get('serial.port') else ""
            print(f"  {i + 1}. {port}{default_marker}")

        # Select port
        while True:
            choice = input(f"\nSelect port (1-{len(ports)}) or Enter for default: ").strip()

            if choice == "":
                port = self.config.get('serial.port', ports[0])
                break
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(ports):
                    port = ports[idx]
                    break
                else:
                    print("Invalid selection")
            except ValueError:
                print("Please enter a number")

        # Select baud rate
        baudrate = self.config.get('serial.baudrate', 115200)
        custom_baud = input(f"\nBaud rate (default: {baudrate}): ").strip()
        if custom_baud:
            try:
                baudrate = int(custom_baud)
            except ValueError:
                print(f"Invalid baud rate, using {baudrate}")

        # Save to config
        self.config.set('serial.port', port)
        self.config.set('serial.baudrate', baudrate)

        # Attempt connection
        print(f"\nConnecting to {port} at {baudrate} baud...")
        self.robot = RobotController()

        if self.robot.connect(port, baudrate):
            print("✓ Connected successfully!")
            return True
        else:
            print("✗ Connection failed")
            return False

    def test_robot_basics(self) -> bool:
        """Test basic robot operations"""
        self.print_header("Testing Robot Basic Functions")

        if not self.robot or not self.robot.is_connected():
            print("✗ Robot not connected")
            return False

        # Test 1: Status query
        print("\nTest 1: Status Query")
        if self.robot.send_status_query():
            time.sleep(0.2)
            state = self.robot.get_state()
            print(f"✓ Robot state: {state.value}")
        else:
            print("✗ Status query failed")
            return False

        # Test 2: Small movement
        print("\nTest 2: Small Movement (Joint A)")
        proceed = input("Move joint A by 5 degrees? (y/n): ").strip().lower()

        if proceed == 'y':
            current_pos = self.robot.get_current_position()
            target = current_pos.get('A', 0) + 5.0

            print(f"Moving A from {current_pos.get('A', 0):.1f}° to {target:.1f}°...")
            if self.robot.move_joint('A', target, MovementType.G1_LINEAR, feedrate=200):
                time.sleep(2)
                print("✓ Movement command sent")
            else:
                print("✗ Movement failed")
                return False

        # Test 3: Gripper
        print("\nTest 3: Gripper Control")
        proceed = input("Test gripper open/close? (y/n): ").strip().lower()

        if proceed == 'y':
            print("Opening gripper...")
            self.robot.move_gripper(100)
            time.sleep(1)

            print("Closing gripper...")
            self.robot.move_gripper(0)
            time.sleep(1)

            print("✓ Gripper test complete")

        print("\n✓ Basic robot tests passed")
        return True

    def setup_camera(self) -> bool:
        """Setup and test camera"""
        self.print_header("Camera Setup")

        # Select camera
        camera_index = self.config.get('vision.camera_index', 0)
        custom_index = input(f"\nCamera index (default: {camera_index}): ").strip()

        if custom_index:
            try:
                camera_index = int(custom_index)
            except ValueError:
                print(f"Invalid index, using {camera_index}")

        self.config.set('vision.camera_index', camera_index)

        # Test camera
        print(f"\nTesting camera {camera_index}...")
        self.vision = VisionController(camera_index)

        if not self.vision.start_camera():
            print("✗ Could not open camera")
            print("\nTroubleshooting:")
            print("  - Check camera is connected")
            print("  - Try different camera index (0, 1, 2, etc.)")
            print("  - Check camera permissions")
            return False

        print("✓ Camera opened successfully")

        # Show preview
        show_preview = input("\nShow camera preview? (y/n): ").strip().lower()

        if show_preview == 'y':
            import cv2
            print("\nShowing preview... Press 'q' to close")

            for _ in range(100):  # ~3 seconds at 30fps
                frame = self.vision.get_frame()
                if frame is not None:
                    cv2.imshow('Camera Preview', frame)
                    if cv2.waitKey(30) & 0xFF == ord('q'):
                        break

            cv2.destroyAllWindows()

        return True

    def test_vision(self) -> bool:
        """Test vision detection"""
        self.print_header("Testing Vision Detection")

        if not self.vision or not self.vision.is_running:
            print("✗ Camera not running")
            return False

        import cv2

        # Select detection method
        print("\nAvailable detection methods:")
        print("  1. Contour detection (general purpose)")
        print("  2. Color-based detection")
        print("  3. ArUco marker detection")

        choice = input("\nSelect method (1-3, default: 1): ").strip()

        if choice == '2':
            self.vision.detection_method = DetectionMethod.COLOR_THRESHOLD
            print("Using color detection (red objects)")
        elif choice == '3':
            self.vision.detection_method = DetectionMethod.ARUCO_MARKER
            print("Using ArUco marker detection")
        else:
            self.vision.detection_method = DetectionMethod.CONTOUR_DETECTION
            print("Using contour detection")

        print("\nRunning detection... Press 'q' to quit")
        print("(Detections will be highlighted in green)")

        detected_count = 0
        frames_processed = 0

        while frames_processed < 300:  # ~10 seconds
            frame, objects = self.vision.process_frame()

            if frame is not None:
                cv2.imshow('Vision Detection Test', frame)

                if objects:
                    detected_count += 1
                    if frames_processed % 30 == 0:  # Print every second
                        print(f"Detected {len(objects)} objects")

                frames_processed += 1

                if cv2.waitKey(30) & 0xFF == ord('q'):
                    break

        cv2.destroyAllWindows()

        print(f"\n✓ Detection test complete")
        print(f"  Objects detected in {detected_count}/{frames_processed} frames")

        return True

    def demo_sequence(self) -> bool:
        """Demo sequence recording and playback"""
        self.print_header("Action Sequence Demo")

        if not self.robot or not self.robot.is_connected():
            print("✗ Robot not connected")
            return False

        self.sequencer = ActionSequencer(self.robot)

        print("\nThis demo will:")
        print("  1. Record a simple movement sequence")
        print("  2. Save it to a file")
        print("  3. Play it back")

        proceed = input("\nProceed? (y/n): ").strip().lower()
        if proceed != 'y':
            return False

        # Record sequence
        print("\nRecording sequence...")
        self.sequencer.start_recording("QuickStart Demo")

        # Simple movements
        self.sequencer.record_move_joint('A', 10.0, MovementType.G1_LINEAR, 300)
        time.sleep(0.5)

        self.sequencer.record_move_joint('A', 0.0, MovementType.G1_LINEAR, 300)
        time.sleep(0.5)

        self.sequencer.record_gripper(50)
        time.sleep(0.5)

        self.sequencer.stop_recording()
        print("✓ Sequence recorded")

        # Save
        filename = "quickstart_demo.json"
        if self.sequencer.save_sequence(filename):
            print(f"✓ Saved to {filename}")

        # Playback
        replay = input("\nPlay back sequence? (y/n): ").strip().lower()
        if replay == 'y':
            print("Playing sequence...")
            self.sequencer.play_sequence()
            print("✓ Playback complete")

        return True

    def show_next_steps(self):
        """Show recommended next steps"""
        self.print_header("Next Steps")

        print("\nRecommended actions:")
        print("\n1. Run interactive examples:")
        print("   python examples.py")

        print("\n2. Calibrate camera for vision-guided control:")
        print("   python calibrate_camera.py")

        print("\n3. Explore the modules:")
        print("   - robot_controller.py - Programmatic robot control")
        print("   - action_sequencer.py - Record and playback actions")
        print("   - vision_controller.py - Computer vision integration")
        print("   - path_planner.py - Smooth path generation")

        print("\n4. Read the documentation:")
        print("   - README.md - Overview and quick start")
        print("   - USAGE_GUIDE.md - Detailed usage examples")

        print("\n5. Launch the GUI:")
        print("   python asgard.py")

    def run(self):
        """Run the complete quick-start wizard"""
        self.print_header("Asgard Robot Control - Quick Start Wizard")

        print("\nThis wizard will help you:")
        print("  • Check dependencies")
        print("  • Configure robot connection")
        print("  • Test basic operations")
        print("  • Setup camera and vision")
        print("  • Try a simple sequence")

        input("\nPress Enter to begin...")

        try:
            # Step 1: Check dependencies
            self.print_step(1, 5, "Checking Dependencies")
            if not self.check_dependencies():
                return

            # Step 2: Setup robot connection
            self.print_step(2, 5, "Robot Connection Setup")
            if not self.setup_serial_connection():
                print("\n⚠ Skipping robot tests (no connection)")
            else:
                # Step 3: Test robot
                self.print_step(3, 5, "Testing Robot Functions")
                self.test_robot_basics()

                # Step 4: Demo sequence
                demo_seq = input("\nTry action sequence demo? (y/n): ").strip().lower()
                if demo_seq == 'y':
                    self.demo_sequence()

            # Step 5: Setup camera
            setup_cam = input("\nSetup camera? (y/n): ").strip().lower()
            if setup_cam == 'y':
                self.print_step(4, 5, "Camera Setup")
                if self.setup_camera():
                    # Step 6: Test vision
                    test_vis = input("\nTest vision detection? (y/n): ").strip().lower()
                    if test_vis == 'y':
                        self.print_step(5, 5, "Testing Vision Detection")
                        self.test_vision()

            # Cleanup
            if self.vision:
                self.vision.stop_camera()
            if self.robot:
                self.robot.disconnect()

            # Show next steps
            self.show_next_steps()

            self.print_header("Quick Start Complete!")
            print("\n✓ Your Asgard system is ready to use!\n")

        except KeyboardInterrupt:
            print("\n\nQuick start interrupted by user")
            if self.vision:
                self.vision.stop_camera()
            if self.robot:
                self.robot.disconnect()


def main():
    """Main entry point"""
    wizard = QuickStart()
    wizard.run()


if __name__ == '__main__':
    main()

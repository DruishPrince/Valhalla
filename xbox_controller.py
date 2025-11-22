"""
Xbox Controller Plugin for Asgard Robotic Arm Control
Provides real-time control of the Thor robotic arm using an Xbox controller.

Controller Mapping:
- Left Stick X: Art1 (Joint A - Base Rotation)
- Left Stick Y: Art2 (Joints B/C - Shoulder)
- Right Stick X: Art5 (Joint Y - Wrist Rotation)
- Right Stick Y: Art4 (Joint X - Wrist Pitch)
- D-Pad Up/Down: Art3 (Joint D - Elbow)
- D-Pad Left/Right: Art6 (Joint Z - Wrist Roll)
- Right Trigger: Open Gripper
- Left Trigger: Close Gripper
- A Button: Execute movement (when using incremental mode)
- B Button: Stop all movement
- Start Button: Homing Cycle ($H)
- Back Button: Zero Position
- X Button: Kill Alarm ($X)
- Y Button: Toggle control mode (Continuous/Incremental)

Author: Asgard Team
License: CC-BY-SA 4.0
"""

from PyQt5 import QtCore
import time

# Try to import pygame, set flag if unavailable
PYGAME_AVAILABLE = False
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    print("WARNING: pygame not installed. Xbox controller support disabled.")
    print("Install pygame with: pip install pygame --only-binary :all:")
    print("Or run: install_pygame.bat")


class XboxControllerThread(QtCore.QThread):
    """Thread class for handling Xbox controller input"""

    # Signals for communicating with the main GUI
    controllerSignal = QtCore.pyqtSignal(str, float)  # (joint_name, value)
    statusSignal = QtCore.pyqtSignal(str)  # Status messages
    buttonSignal = QtCore.pyqtSignal(str)  # Button commands (home, zero, kill_alarm)
    gripperSignal = QtCore.pyqtSignal(float)  # Gripper value (0-100)

    def __init__(self):
        super().__init__()
        self.running = True
        self.controller = None
        self.connected = False

        # Control mode: 'continuous' or 'incremental'
        self.control_mode = 'continuous'

        # Deadzone for joysticks (prevent drift)
        self.deadzone = 0.15

        # Sensitivity multipliers
        self.rotation_speed = 2.0  # degrees per update for continuous mode
        self.increment_size = 1.0  # degrees per button press for incremental mode

        # Current joint values (initialized to None, will be set by GUI)
        self.current_values = {
            'Art1': 0.0,
            'Art2': 0.0,
            'Art3': 0.0,
            'Art4': 0.0,
            'Art5': 0.0,
            'Art6': 0.0,
            'Gripper': 0.0
        }

        # Button state tracking (for toggle detection)
        self.button_states = {}

        # Update rate (Hz)
        self.update_rate = 30  # 30 Hz update rate
        self.update_interval = 1.0 / self.update_rate

    def initialize_controller(self):
        """Initialize pygame and detect Xbox controller"""
        if not PYGAME_AVAILABLE:
            self.statusSignal.emit("pygame not installed - Xbox controller disabled")
            return False

        try:
            pygame.init()
            pygame.joystick.init()

            # Check for connected joysticks
            joystick_count = pygame.joystick.get_count()

            if joystick_count == 0:
                self.statusSignal.emit("No Xbox controller detected")
                return False

            # Initialize the first joystick
            self.controller = pygame.joystick.Joystick(0)
            self.controller.init()

            controller_name = self.controller.get_name()
            self.statusSignal.emit(f"Connected: {controller_name}")
            self.connected = True

            return True

        except Exception as e:
            self.statusSignal.emit(f"Controller initialization error: {str(e)}")
            return False

    def apply_deadzone(self, value):
        """Apply deadzone to joystick values to prevent drift"""
        if abs(value) < self.deadzone:
            return 0.0
        # Rescale the value to maintain smooth motion outside deadzone
        sign = 1 if value > 0 else -1
        return sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)

    def update_joint_value(self, joint_name, current_value):
        """Update the current value for a joint (called from GUI)"""
        self.current_values[joint_name] = current_value

    def process_input(self):
        """Process Xbox controller input and emit signals"""
        if not self.connected:
            return

        try:
            # Process pygame events
            pygame.event.pump()

            # Read joystick axes
            left_stick_x = self.apply_deadzone(self.controller.get_axis(0))  # Art1
            left_stick_y = self.apply_deadzone(self.controller.get_axis(1))  # Art2
            right_stick_x = self.apply_deadzone(self.controller.get_axis(3))  # Art5
            right_stick_y = self.apply_deadzone(self.controller.get_axis(4))  # Art4

            # Read triggers (usually axis 2 and 5, range -1 to 1)
            try:
                left_trigger = (self.controller.get_axis(2) + 1) / 2  # Normalize to 0-1
                right_trigger = (self.controller.get_axis(5) + 1) / 2  # Normalize to 0-1
            except:
                # Fallback if triggers are not available
                left_trigger = 0.0
                right_trigger = 0.0

            # Process continuous movement for joysticks
            if self.control_mode == 'continuous':
                if left_stick_x != 0:
                    new_value = self.current_values['Art1'] + (left_stick_x * self.rotation_speed)
                    self.controllerSignal.emit('Art1', new_value)

                if left_stick_y != 0:
                    new_value = self.current_values['Art2'] + (-left_stick_y * self.rotation_speed)
                    self.controllerSignal.emit('Art2', new_value)

                if right_stick_x != 0:
                    new_value = self.current_values['Art5'] + (right_stick_x * self.rotation_speed)
                    self.controllerSignal.emit('Art5', new_value)

                if right_stick_y != 0:
                    new_value = self.current_values['Art4'] + (-right_stick_y * self.rotation_speed)
                    self.controllerSignal.emit('Art4', new_value)

            # Process D-Pad (Hat)
            if self.controller.get_numhats() > 0:
                hat = self.controller.get_hat(0)

                # D-Pad Up/Down for Art3
                if hat[1] != 0:
                    new_value = self.current_values['Art3'] + (hat[1] * self.increment_size)
                    self.controllerSignal.emit('Art3', new_value)

                # D-Pad Left/Right for Art6
                if hat[0] != 0:
                    new_value = self.current_values['Art6'] + (hat[0] * self.increment_size)
                    self.controllerSignal.emit('Art6', new_value)

            # Process triggers for gripper control
            if left_trigger > 0.1 or right_trigger > 0.1:
                # Right trigger opens (increases), left trigger closes (decreases)
                gripper_delta = (right_trigger - left_trigger) * 5.0  # 5% per update
                new_gripper = max(0, min(100, self.current_values['Gripper'] + gripper_delta))
                self.gripperSignal.emit(new_gripper)

            # Process buttons
            self.process_buttons()

        except Exception as e:
            self.statusSignal.emit(f"Input processing error: {str(e)}")

    def process_buttons(self):
        """Process button presses"""
        try:
            # Button mapping for Xbox controller:
            # 0 = A, 1 = B, 2 = X, 3 = Y
            # 6 = Back, 7 = Start

            # Start button - Homing Cycle
            if self.controller.get_button(7):
                if not self.button_states.get('start', False):
                    self.buttonSignal.emit('home')
                    self.statusSignal.emit("Homing cycle initiated")
                    self.button_states['start'] = True
            else:
                self.button_states['start'] = False

            # Back button - Zero Position
            if self.controller.get_button(6):
                if not self.button_states.get('back', False):
                    self.buttonSignal.emit('zero')
                    self.statusSignal.emit("Zero position command sent")
                    self.button_states['back'] = True
            else:
                self.button_states['back'] = False

            # X button - Kill Alarm
            if self.controller.get_button(2):
                if not self.button_states.get('x', False):
                    self.buttonSignal.emit('kill_alarm')
                    self.statusSignal.emit("Alarm killed")
                    self.button_states['x'] = True
            else:
                self.button_states['x'] = False

            # Y button - Toggle control mode
            if self.controller.get_button(3):
                if not self.button_states.get('y', False):
                    if self.control_mode == 'continuous':
                        self.control_mode = 'incremental'
                        self.statusSignal.emit("Control mode: Incremental")
                    else:
                        self.control_mode = 'continuous'
                        self.statusSignal.emit("Control mode: Continuous")
                    self.button_states['y'] = True
            else:
                self.button_states['y'] = False

            # B button - Emergency stop (future feature)
            if self.controller.get_button(1):
                if not self.button_states.get('b', False):
                    self.statusSignal.emit("Stop button pressed")
                    self.button_states['b'] = True
            else:
                self.button_states['b'] = False

        except Exception as e:
            self.statusSignal.emit(f"Button processing error: {str(e)}")

    def run(self):
        """Main thread loop"""
        # Initialize controller
        if not self.initialize_controller():
            self.statusSignal.emit("Failed to initialize Xbox controller")
            return

        self.statusSignal.emit("Xbox controller thread started")

        # Main loop
        while self.running:
            self.process_input()
            time.sleep(self.update_interval)

        # Cleanup
        if PYGAME_AVAILABLE:
            if self.controller:
                self.controller.quit()
            pygame.quit()
        self.statusSignal.emit("Xbox controller disconnected")

    def stop(self):
        """Stop the thread"""
        self.running = False

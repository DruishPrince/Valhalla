"""
Action Sequencer Module
Enables recording, saving, loading, and playback of robot action sequences
"""
import json
import time
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from robot_controller import RobotController, MovementType


class ActionType(Enum):
    """Types of actions that can be sequenced"""
    MOVE_JOINT = "move_joint"
    MOVE_ALL = "move_all"
    MOVE_GRIPPER = "move_gripper"
    WAIT = "wait"
    HOME = "home"
    CUSTOM_COMMAND = "custom_command"


@dataclass
class Action:
    """Represents a single robot action"""
    action_type: ActionType
    parameters: Dict
    timestamp: float = 0.0  # Time since start of sequence
    description: str = ""

    def to_dict(self) -> Dict:
        """Convert action to dictionary for serialization"""
        return {
            'action_type': self.action_type.value,
            'parameters': self.parameters,
            'timestamp': self.timestamp,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Action':
        """Create action from dictionary"""
        return cls(
            action_type=ActionType(data['action_type']),
            parameters=data['parameters'],
            timestamp=data.get('timestamp', 0.0),
            description=data.get('description', '')
        )


class ActionSequence:
    """
    Container for a sequence of robot actions
    """

    def __init__(self, name: str = "Unnamed Sequence"):
        self.name = name
        self.actions: List[Action] = []
        self.description = ""
        self.created_at = time.time()

    def add_action(self, action: Action):
        """Add an action to the sequence"""
        self.actions.append(action)

    def remove_action(self, index: int) -> bool:
        """Remove action at specified index"""
        if 0 <= index < len(self.actions):
            self.actions.pop(index)
            return True
        return False

    def clear(self):
        """Remove all actions"""
        self.actions.clear()

    def get_duration(self) -> float:
        """Get total sequence duration in seconds"""
        if not self.actions:
            return 0.0
        return max(action.timestamp for action in self.actions)

    def save_to_file(self, filepath: str) -> bool:
        """
        Save sequence to JSON file

        Args:
            filepath: Path to save file

        Returns:
            True if successful
        """
        try:
            data = {
                'name': self.name,
                'description': self.description,
                'created_at': self.created_at,
                'actions': [action.to_dict() for action in self.actions]
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving sequence: {e}")
            return False

    @classmethod
    def load_from_file(cls, filepath: str) -> Optional['ActionSequence']:
        """
        Load sequence from JSON file

        Args:
            filepath: Path to sequence file

        Returns:
            ActionSequence object or None if failed
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            sequence = cls(data.get('name', 'Loaded Sequence'))
            sequence.description = data.get('description', '')
            sequence.created_at = data.get('created_at', time.time())

            for action_data in data.get('actions', []):
                action = Action.from_dict(action_data)
                sequence.add_action(action)

            return sequence
        except Exception as e:
            print(f"Error loading sequence: {e}")
            return None


class ActionSequencer:
    """
    Manages recording, editing, and playback of action sequences
    """

    def __init__(self, robot_controller: RobotController):
        self.robot = robot_controller
        self.current_sequence: Optional[ActionSequence] = None
        self.is_recording = False
        self.is_playing = False
        self.recording_start_time = 0.0

        # Callbacks for events
        self.on_action_recorded: Optional[Callable[[Action], None]] = None
        self.on_action_executed: Optional[Callable[[Action], None]] = None
        self.on_sequence_complete: Optional[Callable[[], None]] = None
        self.on_playback_error: Optional[Callable[[str], None]] = None

    def create_sequence(self, name: str = "New Sequence") -> ActionSequence:
        """Create a new empty sequence"""
        self.current_sequence = ActionSequence(name)
        return self.current_sequence

    def load_sequence(self, filepath: str) -> bool:
        """Load a sequence from file"""
        sequence = ActionSequence.load_from_file(filepath)
        if sequence:
            self.current_sequence = sequence
            return True
        return False

    def save_sequence(self, filepath: str) -> bool:
        """Save current sequence to file"""
        if self.current_sequence:
            return self.current_sequence.save_to_file(filepath)
        return False

    def start_recording(self, sequence_name: str = "Recorded Sequence"):
        """Start recording a new sequence"""
        self.current_sequence = ActionSequence(sequence_name)
        self.is_recording = True
        self.recording_start_time = time.time()
        print(f"Recording started: {sequence_name}")

    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False
        print(f"Recording stopped. {len(self.current_sequence.actions)} actions recorded.")

    def record_move_joint(self, joint: str, angle: float,
                         movement_type: MovementType = MovementType.G0_RAPID,
                         feedrate: Optional[float] = None,
                         description: str = ""):
        """Record a single joint movement"""
        if not self.is_recording or not self.current_sequence:
            return

        action = Action(
            action_type=ActionType.MOVE_JOINT,
            parameters={
                'joint': joint,
                'angle': angle,
                'movement_type': movement_type.value,
                'feedrate': feedrate
            },
            timestamp=time.time() - self.recording_start_time,
            description=description or f"Move {joint} to {angle}°"
        )

        self.current_sequence.add_action(action)

        if self.on_action_recorded:
            self.on_action_recorded(action)

    def record_move_all(self, positions: Dict[str, float],
                       movement_type: MovementType = MovementType.G0_RAPID,
                       feedrate: Optional[float] = None,
                       description: str = ""):
        """Record a multi-joint movement"""
        if not self.is_recording or not self.current_sequence:
            return

        action = Action(
            action_type=ActionType.MOVE_ALL,
            parameters={
                'positions': positions,
                'movement_type': movement_type.value,
                'feedrate': feedrate
            },
            timestamp=time.time() - self.recording_start_time,
            description=description or f"Move all joints"
        )

        self.current_sequence.add_action(action)

        if self.on_action_recorded:
            self.on_action_recorded(action)

    def record_gripper(self, percentage: float, description: str = ""):
        """Record a gripper movement"""
        if not self.is_recording or not self.current_sequence:
            return

        action = Action(
            action_type=ActionType.MOVE_GRIPPER,
            parameters={'percentage': percentage},
            timestamp=time.time() - self.recording_start_time,
            description=description or f"Gripper to {percentage}%"
        )

        self.current_sequence.add_action(action)

        if self.on_action_recorded:
            self.on_action_recorded(action)

    def record_wait(self, duration: float, description: str = ""):
        """Record a wait/delay"""
        if not self.is_recording or not self.current_sequence:
            return

        action = Action(
            action_type=ActionType.WAIT,
            parameters={'duration': duration},
            timestamp=time.time() - self.recording_start_time,
            description=description or f"Wait {duration}s"
        )

        self.current_sequence.add_action(action)

        if self.on_action_recorded:
            self.on_action_recorded(action)

    def record_custom_command(self, command: str, description: str = ""):
        """Record a custom G-code command"""
        if not self.is_recording or not self.current_sequence:
            return

        action = Action(
            action_type=ActionType.CUSTOM_COMMAND,
            parameters={'command': command},
            timestamp=time.time() - self.recording_start_time,
            description=description or f"Command: {command}"
        )

        self.current_sequence.add_action(action)

        if self.on_action_recorded:
            self.on_action_recorded(action)

    def play_sequence(self, sequence: Optional[ActionSequence] = None,
                     respect_timing: bool = True) -> bool:
        """
        Play back a sequence

        Args:
            sequence: Sequence to play (uses current_sequence if None)
            respect_timing: If True, respect original timing; if False, execute immediately

        Returns:
            True if playback started successfully
        """
        if sequence is None:
            sequence = self.current_sequence

        if not sequence or not sequence.actions:
            print("No sequence to play")
            return False

        if not self.robot.is_connected():
            print("Robot not connected")
            if self.on_playback_error:
                self.on_playback_error("Robot not connected")
            return False

        self.is_playing = True
        playback_start = time.time()

        try:
            for i, action in enumerate(sequence.actions):
                if not self.is_playing:  # Allow stopping playback
                    break

                # Wait for proper timing if respect_timing is True
                if respect_timing and i > 0:
                    target_time = playback_start + action.timestamp
                    current_time = time.time()
                    if current_time < target_time:
                        time.sleep(target_time - current_time)

                # Execute action
                self._execute_action(action)

                if self.on_action_executed:
                    self.on_action_executed(action)

            self.is_playing = False

            if self.on_sequence_complete:
                self.on_sequence_complete()

            return True

        except Exception as e:
            print(f"Playback error: {e}")
            self.is_playing = False
            if self.on_playback_error:
                self.on_playback_error(str(e))
            return False

    def stop_playback(self):
        """Stop playback immediately"""
        self.is_playing = False

    def _execute_action(self, action: Action):
        """Execute a single action"""
        try:
            if action.action_type == ActionType.MOVE_JOINT:
                params = action.parameters
                movement_type = MovementType(params['movement_type'])
                self.robot.move_joint(
                    params['joint'],
                    params['angle'],
                    movement_type,
                    params.get('feedrate')
                )

            elif action.action_type == ActionType.MOVE_ALL:
                params = action.parameters
                movement_type = MovementType(params['movement_type'])
                self.robot.move_all_joints(
                    params['positions'],
                    movement_type,
                    params.get('feedrate')
                )

            elif action.action_type == ActionType.MOVE_GRIPPER:
                self.robot.move_gripper(action.parameters['percentage'])

            elif action.action_type == ActionType.WAIT:
                time.sleep(action.parameters['duration'])

            elif action.action_type == ActionType.HOME:
                self.robot.send_homing_command()

            elif action.action_type == ActionType.CUSTOM_COMMAND:
                self.robot.send_command(action.parameters['command'])

        except Exception as e:
            print(f"Error executing action: {e}")
            raise


# Helper functions for creating common sequences
def create_pick_and_place_sequence(
    pick_position: Dict[str, float],
    place_position: Dict[str, float],
    approach_height: float = 10.0,
    name: str = "Pick and Place"
) -> ActionSequence:
    """
    Create a standard pick-and-place sequence

    Args:
        pick_position: Joint angles for pick location
        place_position: Joint angles for place location
        approach_height: Offset for approach movements
        name: Sequence name

    Returns:
        ActionSequence ready to execute
    """
    sequence = ActionSequence(name)

    # Open gripper
    sequence.add_action(Action(
        ActionType.MOVE_GRIPPER,
        {'percentage': 100},
        description="Open gripper"
    ))

    # Move to approach position
    approach_pick = pick_position.copy()
    approach_pick['B'] += approach_height  # Offset shoulder joint
    sequence.add_action(Action(
        ActionType.MOVE_ALL,
        {'positions': approach_pick, 'movement_type': MovementType.G0_RAPID.value},
        description="Approach pick position"
    ))

    # Move to pick position
    sequence.add_action(Action(
        ActionType.MOVE_ALL,
        {'positions': pick_position, 'movement_type': MovementType.G1_LINEAR.value, 'feedrate': 200},
        description="Move to pick position"
    ))

    # Close gripper
    sequence.add_action(Action(
        ActionType.MOVE_GRIPPER,
        {'percentage': 0},
        description="Close gripper"
    ))

    # Wait for gripper to close
    sequence.add_action(Action(
        ActionType.WAIT,
        {'duration': 0.5},
        description="Wait for grip"
    ))

    # Lift up
    sequence.add_action(Action(
        ActionType.MOVE_ALL,
        {'positions': approach_pick, 'movement_type': MovementType.G1_LINEAR.value, 'feedrate': 200},
        description="Lift object"
    ))

    # Move to place approach
    approach_place = place_position.copy()
    approach_place['B'] += approach_height
    sequence.add_action(Action(
        ActionType.MOVE_ALL,
        {'positions': approach_place, 'movement_type': MovementType.G0_RAPID.value},
        description="Approach place position"
    ))

    # Move to place position
    sequence.add_action(Action(
        ActionType.MOVE_ALL,
        {'positions': place_position, 'movement_type': MovementType.G1_LINEAR.value, 'feedrate': 200},
        description="Move to place position"
    ))

    # Open gripper
    sequence.add_action(Action(
        ActionType.MOVE_GRIPPER,
        {'percentage': 100},
        description="Release object"
    ))

    # Wait
    sequence.add_action(Action(
        ActionType.WAIT,
        {'duration': 0.5},
        description="Wait for release"
    ))

    # Lift up
    sequence.add_action(Action(
        ActionType.MOVE_ALL,
        {'positions': approach_place, 'movement_type': MovementType.G1_LINEAR.value, 'feedrate': 200},
        description="Lift after place"
    ))

    return sequence

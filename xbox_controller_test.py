"""
Simple Xbox Controller Test Script
Tests if your Xbox controller is properly detected and working
"""

import sys

try:
    import pygame
except ImportError:
    print("ERROR: pygame not installed!")
    print("Install it with: pip install pygame")
    sys.exit(1)

def test_controller():
    print("=" * 50)
    print("Xbox Controller Test")
    print("=" * 50)
    print()

    # Initialize pygame
    pygame.init()
    pygame.joystick.init()

    # Check for joysticks
    joystick_count = pygame.joystick.get_count()
    print(f"Number of joysticks detected: {joystick_count}")

    if joystick_count == 0:
        print()
        print("No controllers detected!")
        print()
        print("Troubleshooting:")
        print("  1. Make sure your Xbox controller is connected")
        print("  2. Try USB connection instead of Bluetooth")
        print("  3. Check Windows Device Manager")
        print("  4. Try unplugging and reconnecting")
        pygame.quit()
        return

    # Initialize the first joystick
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    print()
    print(f"Controller Name: {joystick.get_name()}")
    print(f"Number of Axes: {joystick.get_numaxes()}")
    print(f"Number of Buttons: {joystick.get_numbuttons()}")
    print(f"Number of Hats: {joystick.get_numhats()}")
    print()
    print("=" * 50)
    print("Testing controller input...")
    print("Move joysticks, press buttons, pull triggers")
    print("Press CTRL+C to exit")
    print("=" * 50)
    print()

    try:
        clock = pygame.time.Clock()
        while True:
            pygame.event.pump()

            # Check for any input
            output = []

            # Axes
            for i in range(joystick.get_numaxes()):
                value = joystick.get_axis(i)
                if abs(value) > 0.1:  # Deadzone
                    axis_names = {
                        0: "Left Stick X",
                        1: "Left Stick Y",
                        2: "Left Trigger",
                        3: "Right Stick X",
                        4: "Right Stick Y",
                        5: "Right Trigger"
                    }
                    name = axis_names.get(i, f"Axis {i}")
                    output.append(f"{name}: {value:+.2f}")

            # Buttons
            for i in range(joystick.get_numbuttons()):
                if joystick.get_button(i):
                    button_names = {
                        0: "A",
                        1: "B",
                        2: "X",
                        3: "Y",
                        4: "LB",
                        5: "RB",
                        6: "Back",
                        7: "Start",
                        8: "Left Stick",
                        9: "Right Stick"
                    }
                    name = button_names.get(i, f"Button {i}")
                    output.append(f"[{name}]")

            # Hat (D-Pad)
            if joystick.get_numhats() > 0:
                hat = joystick.get_hat(0)
                if hat != (0, 0):
                    hat_dir = []
                    if hat[1] == 1:
                        hat_dir.append("UP")
                    elif hat[1] == -1:
                        hat_dir.append("DOWN")
                    if hat[0] == 1:
                        hat_dir.append("RIGHT")
                    elif hat[0] == -1:
                        hat_dir.append("LEFT")
                    output.append(f"D-Pad: {'+'.join(hat_dir)}")

            # Display output
            if output:
                print("\r" + " | ".join(output) + " " * 20, end="", flush=True)

            clock.tick(30)  # 30 FPS

    except KeyboardInterrupt:
        print()
        print()
        print("=" * 50)
        print("Test completed!")
        print()
        print("If you saw input when moving the controller,")
        print("everything is working correctly!")
        print("=" * 50)

    finally:
        joystick.quit()
        pygame.quit()

if __name__ == "__main__":
    test_controller()

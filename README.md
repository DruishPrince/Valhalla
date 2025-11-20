# Asgard

Asgard is a Graphical User Interface (GUI) for [Thor](https://github.com/AngelLM/Thor) designed and programmed with [PyQt5](https://riverbankcomputing.com/software/pyqt/download5).

* Key features:
  *  User-friendly Graphical Interface
  *  Forward Kinematics implementation (1st version)
  *  Xbox Controller support for real-time robotic arm control
  *  Inverse Kinematics implementation (2nd version) - *Coming soon*
  *  Sequence Programmer (3rd version) - *Coming soon*
* Some things that I would want to add, but not in the short-term:
  * 3D display
  * 3D IK Controller/Sequence Programmer

<img src="doc/AsgardGUI.png" width="800">

## Xbox Controller Support

Asgard now includes Xbox controller support for intuitive, real-time control of the Thor robotic arm!

### Requirements
* Python pygame library: `pip install pygame`
* Xbox controller (Xbox 360, Xbox One, or compatible controller)

### Controller Mapping

**Joysticks:**
* **Left Stick X-axis**: Art1 (Joint A - Base Rotation)
* **Left Stick Y-axis**: Art2 (Joints B/C - Shoulder)
* **Right Stick X-axis**: Art5 (Joint Y - Wrist Rotation)
* **Right Stick Y-axis**: Art4 (Joint X - Wrist Pitch)

**D-Pad:**
* **D-Pad Up/Down**: Art3 (Joint D - Elbow)
* **D-Pad Left/Right**: Art6 (Joint Z - Wrist Roll)

**Triggers:**
* **Right Trigger**: Open Gripper
* **Left Trigger**: Close Gripper

**Buttons:**
* **Start Button**: Homing Cycle ($H)
* **Back/Select Button**: Zero Position
* **X Button**: Kill Alarm ($X)
* **Y Button**: Toggle control mode (Continuous/Incremental)
* **B Button**: Emergency stop (reserved for future use)

### Usage

1. Connect your Xbox controller to your computer via USB or Bluetooth
2. Launch Asgard - the Xbox controller will be automatically detected and enabled
3. Status messages will appear in the console showing controller connection status
4. Use the controller as mapped above to control the robotic arm

### Control Modes

* **Continuous Mode** (default): Joystick movements immediately control the arm in real-time
* **Incremental Mode**: Joystick movements update the target position but require pressing the 'A' button to execute
* Toggle between modes by pressing the **Y button** on the controller

### Features

* Automatic controller detection on startup
* Real-time position updates synchronized with GUI
* Adjustable deadzone to prevent joystick drift
* Configurable sensitivity and movement speed
* Visual feedback in the console for all controller actions

## Installation

### Requirements
* Python 3.4 or higher
* PyQt5
* pyserial
* pygame (for Xbox controller support)

### Quick Install
Install all dependencies using pip:
```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install PyQt5 pyserial pygame
```

### Running Asgard
```bash
python asgard.py
```

## Tools and useful links
* **QtDesigner** - Used to design the graphical part of gui
* **Python 3.4** - Used to program and execute Asgard
+ **[SKYLOGIC PROJECTS Tutorial](http://projects.skylogic.ca/blog/how-to-install-pyqt5-and-build-your-first-gui-in-python-3-4/)** - How to Install PyQt5 and Build Your First GUI in Python 3.4

## Thanks!

* **[Stack Overflow Community](https://stackoverflow.com/)**: And not only related to this project, but also for having all the answers to all questions I had since I started programming.
* **[Harrison Kinsley](https://twitter.com/Sentdex)** ([sentdex](https://www.youtube.com/user/sentdex) from [pythonprogramming.net](https://pythonprogramming.net)): I learned from you almost everything I know about python. Thanks for that detailed tutorials & examples!
* **[Matthew Dirks](https://github.com/skylogic004)** from [SkyLogic](http://projects.skylogic.ca): Thank you for [this detailed tutorial](http://projects.skylogic.ca/blog/how-to-install-pyqt5-and-build-your-first-gui-in-python-3-4/)! It was incredible easy to make my first GUI in less than an hour following your steps!
* **[Thor Community](https://groups.google.com/forum/#!forum/thor-opensource-3d-printable-robotic-arm)**: For all the support and feedback given! YOU ROCK GUYS!



Do not hesitate on contributing to this project!

## License <img src="doc/By-sa.png" width="100">

All files included in this repository are licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-sa/4.0/)

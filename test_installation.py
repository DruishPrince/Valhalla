#!/usr/bin/env python3
"""
Test script to verify installation
Run this to check if all required modules are available
"""

import sys

def test_import(module_name, package_name=None):
    """Test if a module can be imported"""
    try:
        __import__(module_name)
        print(f"✓ {module_name:20s} - OK")
        return True
    except ImportError as e:
        pkg = package_name or module_name
        print(f"✗ {module_name:20s} - MISSING (install with: pip install {pkg})")
        return False

def main():
    print("=" * 60)
    print("Asgard Enhanced - Installation Test")
    print("=" * 60)
    print()

    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print()

    print("Testing core dependencies:")
    print("-" * 60)

    results = {}

    # Core dependencies
    results['PyQt5'] = test_import('PyQt5')
    results['serial'] = test_import('serial', 'pyserial')
    results['cv2'] = test_import('cv2', 'opencv-python')
    results['numpy'] = test_import('numpy')
    results['matplotlib'] = test_import('matplotlib')
    results['scipy'] = test_import('scipy')

    print()
    print("Testing optional dependencies:")
    print("-" * 60)

    # Optional - Kinect support
    kinect_v1 = test_import('freenect')
    kinect_v2 = test_import('pylibfreenect2')
    kinect_azure = test_import('pyk4a')

    results['kinect'] = kinect_v1 or kinect_v2 or kinect_azure

    # Optional - Sensor support
    results['smbus2'] = test_import('smbus2')

    print()
    print("Testing project modules:")
    print("-" * 60)

    # Project modules
    project_modules = [
        'robot_controller',
        'kinect_interface',
        'vision_controller_3d',
        'sensor_gateway_client',
        'action_sequencer',
        'kinematics',
        'config_manager'
    ]

    for module in project_modules:
        try:
            __import__(module)
            print(f"✓ {module:20s} - OK")
            results[module] = True
        except Exception as e:
            print(f"✗ {module:20s} - ERROR: {str(e)[:40]}")
            results[module] = False

    print()
    print("=" * 60)
    print("Summary:")
    print("=" * 60)

    core_ok = all([results.get(k, False) for k in ['PyQt5', 'serial', 'cv2', 'numpy', 'matplotlib', 'scipy']])
    project_ok = all([results.get(k, False) for k in project_modules])

    if core_ok and project_ok:
        print("✓ All required dependencies are installed!")
        print("✓ All project modules loaded successfully!")
        print()
        print("You can now run: run_asgard_enhanced.bat")
        return 0
    else:
        print("✗ Some dependencies are missing")
        print()
        if not core_ok:
            print("To install missing core dependencies, run:")
            print("  setup_windows.bat")
            print()
            print("Or manually install:")
            missing = []
            if not results.get('PyQt5'): missing.append('PyQt5')
            if not results.get('serial'): missing.append('pyserial')
            if not results.get('cv2'): missing.append('opencv-python')
            if not results.get('numpy'): missing.append('numpy')
            if not results.get('matplotlib'): missing.append('matplotlib')
            if not results.get('scipy'): missing.append('scipy')

            if missing:
                print(f"  pip install {' '.join(missing)}")

        if not project_ok:
            print()
            print("Project module errors detected.")
            print("This usually means you're not in the correct directory")
            print("or files are missing from the repository.")

        return 1

if __name__ == '__main__':
    sys.exit(main())

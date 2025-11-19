#!/usr/bin/env python3
"""
Simple installation test - shows exactly what works
"""

import sys

print("=" * 60)
print("Simple Installation Test")
print("=" * 60)
print()
print(f"Python: {sys.version}")
print(f"Location: {sys.executable}")
print()

def test(module_name):
    """Test if module works"""
    try:
        mod = __import__(module_name)
        version = getattr(mod, '__version__', 'unknown')
        print(f"[OK] {module_name:20s} {version}")
        return True
    except Exception as e:
        print(f"[FAIL] {module_name:20s} - {str(e)[:40]}")
        return False

print("Testing modules:")
print("-" * 60)

results = {}
results['PyQt5'] = test('PyQt5')
results['serial'] = test('serial')
results['cv2'] = test('cv2')
results['numpy'] = test('numpy')
results['matplotlib'] = test('matplotlib')
results['scipy'] = test('scipy')

print()
print("=" * 60)

all_ok = all(results.values())

if all_ok:
    print("SUCCESS - All modules installed correctly!")
    print()
    print("You can now run:")
    print("  python asgard_enhanced.py")
else:
    print("PROBLEMS FOUND")
    print()
    missing = [k for k, v in results.items() if not v]
    print(f"Missing: {', '.join(missing)}")
    print()

    if not results['PyQt5']:
        print("PyQt5 is missing - GUI won't work")
        print("Try: pip install PyQt5")

    if not results['serial']:
        print("pyserial is missing - robot control won't work")
        print("Try: pip install pyserial")

    if not results['cv2']:
        print("OpenCV is missing - camera won't work")
        print("Try: pip install opencv-python")

print("=" * 60)

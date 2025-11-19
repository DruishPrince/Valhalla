#!/usr/bin/env micropython
"""
Sensor Gateway for Raspberry Pi Pico

MicroPython firmware for reading ADXL345 sensors via I2C and transmitting
data via USB serial to the main control system.

This is an alternative to the Pi Zero 2W gateway for the Mellow FLY Super ♾️ Pro
board which doesn't have exposed I2C pins.

Hardware Setup:
- Raspberry Pi Pico with MicroPython
- ADXL345 sensors connected to I2C0 or I2C1
- USB connection to main computer

Pin Configuration (default):
- I2C0: GP4 (SDA), GP5 (SCL)
- I2C1: GP14 (SDA), GP15 (SCL)
- LED: GP25 (built-in)

Installation:
1. Install MicroPython on Pico: https://micropython.org/download/rp2-pico/
2. Upload this file to Pico as main.py
3. Upload adxl345_pico.py (sensor driver)
4. Reset Pico

Usage:
- Connects to PC via USB serial
- Sends JSON sensor data at 10 Hz
- Responds to commands: CALIBRATE, GET, STATUS
"""

import time
import json
import sys
from machine import Pin, I2C
import math


# ============================================================================
# ADXL345 Sensor Driver for MicroPython
# ============================================================================

class ADXL345:
    """
    ADXL345 3-axis accelerometer driver for MicroPython

    Simplified version for Raspberry Pi Pico
    """

    # Register addresses
    REG_POWER_CTL = 0x2D
    REG_DATA_FORMAT = 0x31
    REG_DATAX0 = 0x32
    REG_OFSX = 0x1E

    # Power control bits
    POWER_MEASURE = 0x08

    def __init__(self, i2c, address=0x53):
        """
        Initialize ADXL345

        Args:
            i2c: I2C interface
            address: I2C address (0x53 or 0x1D)
        """
        self.i2c = i2c
        self.address = address

        # Calibration offsets
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.offset_z = 0.0

        # Zero orientation (for angle calculation)
        self.zero_roll = 0.0
        self.zero_pitch = 0.0

        # Initialize sensor
        self._init_sensor()

    def _init_sensor(self):
        """Initialize sensor registers"""
        try:
            # Set data format to ±4g, full resolution
            self.i2c.writeto_mem(self.address, self.REG_DATA_FORMAT, bytes([0x01]))

            # Enable measurement mode
            self.i2c.writeto_mem(self.address, self.REG_POWER_CTL, bytes([self.POWER_MEASURE]))

            time.sleep_ms(10)

        except Exception as e:
            print(f"Error initializing ADXL345 at 0x{self.address:02X}: {e}")
            raise

    def read_raw(self):
        """
        Read raw acceleration data

        Returns:
            Tuple (x, y, z) in raw units
        """
        try:
            # Read 6 bytes starting from DATAX0
            data = self.i2c.readfrom_mem(self.address, self.REG_DATAX0, 6)

            # Convert to signed 16-bit integers
            x = int.from_bytes(data[0:2], 'little', True)
            y = int.from_bytes(data[2:4], 'little', True)
            z = int.from_bytes(data[4:6], 'little', True)

            return (x, y, z)

        except Exception as e:
            print(f"Error reading ADXL345: {e}")
            return (0, 0, 0)

    def read(self):
        """
        Read acceleration in g (gravity units)

        Returns:
            Tuple (x, y, z) in g
        """
        x_raw, y_raw, z_raw = self.read_raw()

        # Scale factor: 4mg/LSB at ±4g range
        scale = 0.004

        x = x_raw * scale - self.offset_x
        y = y_raw * scale - self.offset_y
        z = z_raw * scale - self.offset_z

        return (x, y, z)

    def calculate_orientation(self):
        """
        Calculate roll and pitch from acceleration

        Returns:
            Tuple (roll, pitch) in degrees
        """
        x, y, z = self.read()

        # Calculate roll and pitch
        roll = math.atan2(y, z) * 180.0 / math.pi
        pitch = math.atan2(-x, math.sqrt(y*y + z*z)) * 180.0 / math.pi

        return (roll, pitch)

    def calibrate(self, num_samples=100):
        """
        Calibrate sensor at current position

        Args:
            num_samples: Number of samples to average
        """
        print(f"Calibrating ADXL345 at 0x{self.address:02X}...")

        sum_x = 0.0
        sum_y = 0.0
        sum_z = 0.0

        for i in range(num_samples):
            x, y, z = self.read()
            sum_x += x
            sum_y += y
            sum_z += z
            time.sleep_ms(10)

        # Calculate zero orientation
        avg_x = sum_x / num_samples
        avg_y = sum_y / num_samples
        avg_z = sum_z / num_samples

        self.zero_roll = math.atan2(avg_y, avg_z) * 180.0 / math.pi
        self.zero_pitch = math.atan2(-avg_x, math.sqrt(avg_y*avg_y + avg_z*avg_z)) * 180.0 / math.pi

        print(f"  Zero orientation: Roll={self.zero_roll:.1f}° Pitch={self.zero_pitch:.1f}°")

    def get_angle(self, axis='roll'):
        """
        Get angle relative to calibrated zero position

        Args:
            axis: 'roll' or 'pitch'

        Returns:
            Angle in degrees
        """
        roll, pitch = self.calculate_orientation()

        if axis == 'roll':
            return roll - self.zero_roll
        else:
            return pitch - self.zero_pitch


# ============================================================================
# Sensor Gateway for Pico
# ============================================================================

class SensorGatewayPico:
    """
    Sensor gateway for Raspberry Pi Pico

    Reads ADXL345 sensors and transmits data via USB serial
    """

    def __init__(self):
        """Initialize gateway"""
        # LED for status indication
        self.led = Pin(25, Pin.OUT)

        # I2C interfaces
        self.i2c0 = None
        self.i2c1 = None

        # Sensors
        self.sensors = {}  # {joint_id: sensor}
        self.joint_configs = {}  # {joint_id: {'name': str, 'axis': str}}

        # State
        self.running = False
        self.last_blink = 0

    def setup_i2c(self):
        """Setup I2C interfaces"""
        try:
            # I2C0 on GP4 (SDA) and GP5 (SCL)
            self.i2c0 = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
            print("✓ I2C0 initialized (GP4=SDA, GP5=SCL)")

            # I2C1 on GP14 (SDA) and GP15 (SCL)
            self.i2c1 = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
            print("✓ I2C1 initialized (GP14=SDA, GP15=SCL)")

            return True

        except Exception as e:
            print(f"✗ Failed to setup I2C: {e}")
            return False

    def scan_i2c(self):
        """Scan for I2C devices"""
        print("\nScanning I2C buses...")

        if self.i2c0:
            devices0 = self.i2c0.scan()
            print(f"  I2C0: {[hex(d) for d in devices0]}")

        if self.i2c1:
            devices1 = self.i2c1.scan()
            print(f"  I2C1: {[hex(d) for d in devices1]}")

    def add_sensor(self, joint_id, joint_name, i2c_bus=0, i2c_address=0x53, axis='roll'):
        """
        Add sensor configuration

        Args:
            joint_id: Joint identifier (A, B, D, etc.)
            joint_name: Human-readable name
            i2c_bus: 0 or 1
            i2c_address: I2C address (0x53 or 0x1D)
            axis: Primary axis ('roll' or 'pitch')
        """
        try:
            i2c = self.i2c0 if i2c_bus == 0 else self.i2c1

            sensor = ADXL345(i2c, i2c_address)

            self.sensors[joint_id] = sensor
            self.joint_configs[joint_id] = {
                'name': joint_name,
                'axis': axis,
                'bus': i2c_bus,
                'address': i2c_address
            }

            print(f"✓ Added sensor: {joint_name} ({joint_id}) on I2C{i2c_bus} at 0x{i2c_address:02X}")
            return True

        except Exception as e:
            print(f"✗ Failed to add sensor {joint_id}: {e}")
            return False

    def calibrate_all(self):
        """Calibrate all sensors"""
        print("\nCalibrating all sensors...")
        print("Keep robot stationary at home position!")

        time.sleep(2)

        for joint_id, sensor in self.sensors.items():
            sensor.calibrate(num_samples=100)

        print("✓ Calibration complete\n")

    def read_all(self):
        """
        Read all sensors and format as JSON

        Returns:
            Dictionary with sensor data
        """
        data = {
            'timestamp': time.time(),
            'joints': {}
        }

        for joint_id, sensor in self.sensors.items():
            config = self.joint_configs[joint_id]

            # Read acceleration
            accel_x, accel_y, accel_z = sensor.read()

            # Read orientation
            roll, pitch = sensor.calculate_orientation()

            # Get angle
            angle = sensor.get_angle(config['axis'])

            data['joints'][joint_id] = {
                'angle': round(angle, 2),
                'accel_x': round(accel_x, 4),
                'accel_y': round(accel_y, 4),
                'accel_z': round(accel_z, 4),
                'roll': round(roll, 2),
                'pitch': round(pitch, 2)
            }

        return data

    def send_data(self, data):
        """
        Send data via USB serial (stdout)

        Args:
            data: Dictionary to send as JSON
        """
        json_str = json.dumps(data)
        print(json_str)
        sys.stdout.flush()

    def process_command(self, command):
        """
        Process incoming command

        Args:
            command: Command string
        """
        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].upper()

        if cmd == 'CALIBRATE' and len(parts) > 1:
            joint_id = parts[1]
            if joint_id in self.sensors:
                self.sensors[joint_id].calibrate()
                response = {'status': 'ok', 'message': f'Calibrated {joint_id}'}
            else:
                response = {'status': 'error', 'message': f'Unknown joint {joint_id}'}
            self.send_data(response)

        elif cmd == 'CALIBRATE_ALL':
            self.calibrate_all()
            response = {'status': 'ok', 'message': 'Calibrated all joints'}
            self.send_data(response)

        elif cmd == 'GET' and len(parts) > 1:
            joint_id = parts[1]
            if joint_id in self.sensors:
                data = self.read_all()
                response = {
                    'status': 'ok',
                    'joint_id': joint_id,
                    'data': data['joints'][joint_id]
                }
            else:
                response = {'status': 'error', 'message': f'Unknown joint {joint_id}'}
            self.send_data(response)

        elif cmd == 'STATUS':
            response = {
                'status': 'ok',
                'num_sensors': len(self.sensors),
                'joints': list(self.sensors.keys())
            }
            self.send_data(response)

    def blink_led(self):
        """Blink LED to indicate activity"""
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self.last_blink) > 100:
            self.led.toggle()
            self.last_blink = current_time

    def run(self, rate=10.0):
        """
        Run sensor gateway continuously

        Args:
            rate: Update rate in Hz
        """
        interval_ms = int(1000 / rate)

        print(f"\n{'='*60}")
        print(f"Sensor Gateway Running @ {rate} Hz")
        print("Sending data via USB serial")
        print(f"{'='*60}\n")

        self.running = True

        last_send = time.ticks_ms()

        while self.running:
            current_time = time.ticks_ms()

            # Send sensor data at specified rate
            if time.ticks_diff(current_time, last_send) >= interval_ms:
                data = self.read_all()
                self.send_data(data)
                last_send = current_time

                # Blink LED
                self.blink_led()

            # Check for commands (non-blocking)
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                command = sys.stdin.readline()
                if command:
                    self.process_command(command)

            # Small delay
            time.sleep_ms(10)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for Pico gateway"""
    print("\n" + "="*60)
    print("ADXL345 Sensor Gateway for Raspberry Pi Pico")
    print("="*60)
    print("\nHardware: Mellow FLY Super ♾️ Pro + Raspberry Pi Pico")
    print("Purpose: Read I2C sensors and transmit via USB serial\n")

    # Create gateway
    gateway = SensorGatewayPico()

    # Setup I2C
    if not gateway.setup_i2c():
        print("Failed to setup I2C")
        return

    # Scan for devices
    gateway.scan_i2c()

    # Configure sensors for Thor robot
    # Adjust these based on your actual wiring
    print("\nConfiguring sensors...")

    gateway.add_sensor('A', 'Base', i2c_bus=0, i2c_address=0x53, axis='roll')
    gateway.add_sensor('B', 'Shoulder', i2c_bus=0, i2c_address=0x1D, axis='pitch')
    gateway.add_sensor('D', 'Elbow', i2c_bus=1, i2c_address=0x53, axis='pitch')

    # Note: For more than 2 sensors per bus, use I2C multiplexer
    # gateway.add_sensor('X', 'Wrist Pitch', i2c_bus=1, i2c_address=0x1D, axis='pitch')

    # Calibrate sensors
    gateway.calibrate_all()

    # Run gateway
    try:
        gateway.run(rate=10.0)
    except KeyboardInterrupt:
        print("\n\nGateway stopped")
        gateway.running = False


if __name__ == '__main__':
    main()

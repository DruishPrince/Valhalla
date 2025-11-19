"""
ADXL345 3-Axis Accelerometer Interface

Provides interface for reading ADXL345 sensors via I2C for joint angle sensing.
Each joint can have a sensor to determine its actual orientation.
"""

import time
import math
import numpy as np
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum


# Check if I2C libraries are available
try:
    import smbus2
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False
    print("Warning: smbus2 not available. Install with: pip install smbus2")


class DataRate(Enum):
    """Data rate options for ADXL345"""
    RATE_0_10_HZ = 0x00
    RATE_0_20_HZ = 0x01
    RATE_0_39_HZ = 0x02
    RATE_0_78_HZ = 0x03
    RATE_1_56_HZ = 0x04
    RATE_3_13_HZ = 0x05
    RATE_6_25_HZ = 0x06
    RATE_12_5_HZ = 0x07
    RATE_25_HZ = 0x08
    RATE_50_HZ = 0x09
    RATE_100_HZ = 0x0A
    RATE_200_HZ = 0x0B
    RATE_400_HZ = 0x0C
    RATE_800_HZ = 0x0D
    RATE_1600_HZ = 0x0E
    RATE_3200_HZ = 0x0F


class Range(Enum):
    """Measurement range options"""
    RANGE_2G = 0x00
    RANGE_4G = 0x01
    RANGE_8G = 0x02
    RANGE_16G = 0x03


@dataclass
class AccelData:
    """Accelerometer reading"""
    x: float  # g
    y: float  # g
    z: float  # g
    timestamp: float = 0.0

    def magnitude(self) -> float:
        """Calculate magnitude of acceleration vector"""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def to_array(self) -> np.ndarray:
        """Convert to numpy array"""
        return np.array([self.x, self.y, self.z])


@dataclass
class Orientation:
    """Orientation calculated from accelerometer"""
    roll: float   # degrees
    pitch: float  # degrees

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {'roll': self.roll, 'pitch': self.pitch}


class ADXL345:
    """
    Interface for ADXL345 3-axis accelerometer via I2C

    Registers and configuration for ADXL345
    """

    # I2C addresses
    ADDRESS_LOW = 0x53   # If SDO pin is LOW
    ADDRESS_HIGH = 0x1D  # If SDO pin is HIGH

    # Registers
    REG_DEVID = 0x00
    REG_POWER_CTL = 0x2D
    REG_DATA_FORMAT = 0x31
    REG_BW_RATE = 0x2C
    REG_DATAX0 = 0x32
    REG_DATAX1 = 0x33
    REG_DATAY0 = 0x34
    REG_DATAY1 = 0x35
    REG_DATAZ0 = 0x36
    REG_DATAZ1 = 0x37
    REG_OFSX = 0x1E
    REG_OFSY = 0x1F
    REG_OFSZ = 0x20

    # Device ID value
    DEVICE_ID = 0xE5

    # Scale factors for different ranges (LSB/g)
    SCALE_FACTORS = {
        Range.RANGE_2G: 256.0,
        Range.RANGE_4G: 128.0,
        Range.RANGE_8G: 64.0,
        Range.RANGE_16G: 32.0
    }

    def __init__(self,
                 bus_number: int = 1,
                 address: int = ADDRESS_LOW,
                 data_rate: DataRate = DataRate.RATE_100_HZ,
                 range_setting: Range = Range.RANGE_2G):
        """
        Initialize ADXL345 sensor

        Args:
            bus_number: I2C bus number (usually 1 on Raspberry Pi)
            address: I2C address (0x53 or 0x1D)
            data_rate: Sampling rate
            range_setting: Measurement range
        """
        if not I2C_AVAILABLE:
            raise ImportError("smbus2 library required. Install with: pip install smbus2")

        self.bus_number = bus_number
        self.address = address
        self.data_rate = data_rate
        self.range = range_setting
        self.scale_factor = self.SCALE_FACTORS[range_setting]

        self.bus: Optional[smbus2.SMBus] = None
        self.calibration_offset = AccelData(0, 0, 0)

    def connect(self) -> bool:
        """
        Connect to sensor and verify communication

        Returns:
            True if connected successfully
        """
        try:
            self.bus = smbus2.SMBus(self.bus_number)

            # Verify device ID
            device_id = self.bus.read_byte_data(self.address, self.REG_DEVID)
            if device_id != self.DEVICE_ID:
                print(f"Warning: Unexpected device ID: 0x{device_id:02X} (expected 0x{self.DEVICE_ID:02X})")
                return False

            # Configure sensor
            self._configure()

            print(f"✓ ADXL345 connected at 0x{self.address:02X}")
            return True

        except Exception as e:
            print(f"Error connecting to ADXL345: {e}")
            return False

    def disconnect(self):
        """Disconnect from sensor"""
        if self.bus:
            # Put sensor in standby
            try:
                self.bus.write_byte_data(self.address, self.REG_POWER_CTL, 0x00)
            except:
                pass
            self.bus.close()
            self.bus = None

    def _configure(self):
        """Configure sensor settings"""
        if not self.bus:
            return

        # Set data rate
        self.bus.write_byte_data(self.address, self.REG_BW_RATE, self.data_rate.value)

        # Set range
        self.bus.write_byte_data(self.address, self.REG_DATA_FORMAT, self.range.value)

        # Enable measurement mode
        self.bus.write_byte_data(self.address, self.REG_POWER_CTL, 0x08)

        time.sleep(0.01)  # Wait for sensor to stabilize

    def read_raw(self) -> Tuple[int, int, int]:
        """
        Read raw sensor values

        Returns:
            Tuple of (x, y, z) raw values
        """
        if not self.bus:
            raise RuntimeError("Sensor not connected")

        # Read 6 bytes starting from DATAX0
        data = self.bus.read_i2c_block_data(self.address, self.REG_DATAX0, 6)

        # Combine bytes (little endian, 2's complement)
        x = self._combine_bytes(data[0], data[1])
        y = self._combine_bytes(data[2], data[3])
        z = self._combine_bytes(data[4], data[5])

        return x, y, z

    def read(self) -> AccelData:
        """
        Read acceleration values in g's

        Returns:
            AccelData with x, y, z in g's
        """
        x_raw, y_raw, z_raw = self.read_raw()

        # Convert to g's
        x = x_raw / self.scale_factor - self.calibration_offset.x
        y = y_raw / self.scale_factor - self.calibration_offset.y
        z = z_raw / self.scale_factor - self.calibration_offset.z

        return AccelData(x, y, z, timestamp=time.time())

    def calculate_orientation(self, accel: Optional[AccelData] = None) -> Orientation:
        """
        Calculate roll and pitch from accelerometer data

        Assumes sensor is measuring gravity (stationary or slow movement)

        Args:
            accel: Acceleration data (reads new if None)

        Returns:
            Orientation with roll and pitch in degrees
        """
        if accel is None:
            accel = self.read()

        # Calculate roll (rotation around x-axis)
        # roll = atan2(y, z)
        roll = math.atan2(accel.y, accel.z) * 180.0 / math.pi

        # Calculate pitch (rotation around y-axis)
        # pitch = atan2(-x, sqrt(y^2 + z^2))
        pitch = math.atan2(-accel.x, math.sqrt(accel.y**2 + accel.z**2)) * 180.0 / math.pi

        return Orientation(roll, pitch)

    def calibrate(self, num_samples: int = 100) -> AccelData:
        """
        Calibrate sensor by averaging readings

        Place sensor in reference orientation before calling

        Args:
            num_samples: Number of samples to average

        Returns:
            Calibration offset
        """
        print(f"Calibrating sensor... (taking {num_samples} samples)")

        sum_x, sum_y, sum_z = 0.0, 0.0, 0.0

        for i in range(num_samples):
            data = self.read()
            sum_x += data.x
            sum_y += data.y
            sum_z += data.z
            time.sleep(0.01)

        # Average offset (assuming Z should be 1g when horizontal)
        self.calibration_offset = AccelData(
            x=sum_x / num_samples,
            y=sum_y / num_samples,
            z=(sum_z / num_samples) - 1.0  # Subtract 1g for Z axis
        )

        print(f"✓ Calibration complete: offset = ({self.calibration_offset.x:.3f}, "
              f"{self.calibration_offset.y:.3f}, {self.calibration_offset.z:.3f})")

        return self.calibration_offset

    def set_offsets(self, x: float, y: float, z: float):
        """
        Set hardware offset registers

        Args:
            x, y, z: Offset values in g's
        """
        if not self.bus:
            return

        # Convert to register values (15.6 mg/LSB)
        x_offset = int(x * 1000 / 15.6)
        y_offset = int(y * 1000 / 15.6)
        z_offset = int(z * 1000 / 15.6)

        # Clamp to int8 range
        x_offset = max(-128, min(127, x_offset))
        y_offset = max(-128, min(127, y_offset))
        z_offset = max(-128, min(127, z_offset))

        # Write to registers
        self.bus.write_byte_data(self.address, self.REG_OFSX, x_offset & 0xFF)
        self.bus.write_byte_data(self.address, self.REG_OFSY, y_offset & 0xFF)
        self.bus.write_byte_data(self.address, self.REG_OFSZ, z_offset & 0xFF)

    def _combine_bytes(self, lsb: int, msb: int) -> int:
        """Combine two bytes into signed 16-bit integer"""
        value = (msb << 8) | lsb

        # Convert to signed
        if value & 0x8000:
            value -= 65536

        return value

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


class ADXL345Simulator:
    """
    Simulated ADXL345 for testing without hardware
    """

    def __init__(self, *args, **kwargs):
        """Initialize simulator"""
        self.calibration_offset = AccelData(0, 0, 0)
        self.connected = False
        print("Using ADXL345 simulator (no hardware)")

    def connect(self) -> bool:
        """Simulate connection"""
        self.connected = True
        print("✓ ADXL345 simulator connected")
        return True

    def disconnect(self):
        """Simulate disconnection"""
        self.connected = False

    def read(self) -> AccelData:
        """Generate simulated readings"""
        # Simulate noisy gravity reading
        noise = 0.02
        x = np.random.normal(0, noise)
        y = np.random.normal(0, noise)
        z = np.random.normal(1.0, noise)  # 1g downward

        return AccelData(x, y, z, timestamp=time.time())

    def calculate_orientation(self, accel: Optional[AccelData] = None) -> Orientation:
        """Calculate orientation from simulated data"""
        if accel is None:
            accel = self.read()

        roll = math.atan2(accel.y, accel.z) * 180.0 / math.pi
        pitch = math.atan2(-accel.x, math.sqrt(accel.y**2 + accel.z**2)) * 180.0 / math.pi

        return Orientation(roll, pitch)

    def calibrate(self, num_samples: int = 100) -> AccelData:
        """Simulate calibration"""
        print("Simulating calibration...")
        time.sleep(0.5)
        self.calibration_offset = AccelData(0, 0, 0)
        print("✓ Simulation calibration complete")
        return self.calibration_offset

    def set_offsets(self, x: float, y: float, z: float):
        """Simulate setting offsets"""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def create_sensor(bus_number: int = 1,
                 address: int = ADXL345.ADDRESS_LOW,
                 simulate: bool = False) -> ADXL345:
    """
    Create sensor instance (real or simulated)

    Args:
        bus_number: I2C bus number
        address: I2C address
        simulate: Use simulator if True or if hardware unavailable

    Returns:
        ADXL345 or ADXL345Simulator instance
    """
    if simulate or not I2C_AVAILABLE:
        return ADXL345Simulator(bus_number, address)
    else:
        return ADXL345(bus_number, address)


def test_sensor():
    """Test ADXL345 sensor"""
    print("=== ADXL345 Sensor Test ===\n")

    # Try to connect to sensor
    sensor = create_sensor(simulate=not I2C_AVAILABLE)

    if sensor.connect():
        print("\nReading sensor data...")

        for i in range(10):
            data = sensor.read()
            orientation = sensor.calculate_orientation(data)

            print(f"Sample {i+1}:")
            print(f"  Accel: ({data.x:6.3f}, {data.y:6.3f}, {data.z:6.3f}) g")
            print(f"  Magnitude: {data.magnitude():.3f} g")
            print(f"  Orientation: Roll={orientation.roll:6.1f}° Pitch={orientation.pitch:6.1f}°")

            time.sleep(0.1)

        sensor.disconnect()
    else:
        print("Failed to connect to sensor")


if __name__ == '__main__':
    test_sensor()

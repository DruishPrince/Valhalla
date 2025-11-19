#!/usr/bin/env python3
"""
Asgard Minimal - Simplified GUI for testing

This is a minimal version that only requires PyQt5 and pyserial.
Use this to verify basic functionality if the full version has issues.
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox, QSlider,
    QSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("WARNING: pyserial not installed - robot control disabled")


class AsgardMinimal(QMainWindow):
    """Minimal GUI for basic robot control"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asgard Minimal - Basic Robot Control")
        self.setGeometry(100, 100, 800, 600)

        self.serial_port = None

        self.init_ui()

    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Title
        title = QLabel("Asgard Minimal - Basic Robot Control")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Connection group
        conn_group = QGroupBox("Connection")
        conn_layout = QHBoxLayout(conn_group)

        self.port_combo = QComboBox()
        if SERIAL_AVAILABLE:
            self.refresh_ports()
        else:
            self.port_combo.addItem("pyserial not installed")

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.refresh_btn.setEnabled(SERIAL_AVAILABLE)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setEnabled(SERIAL_AVAILABLE)

        conn_layout.addWidget(QLabel("Port:"))
        conn_layout.addWidget(self.port_combo)
        conn_layout.addWidget(self.refresh_btn)
        conn_layout.addWidget(self.connect_btn)

        layout.addWidget(conn_group)

        # Joint A control (example)
        joint_group = QGroupBox("Joint A - Base")
        joint_layout = QHBoxLayout(joint_group)

        self.joint_a_slider = QSlider(Qt.Horizontal)
        self.joint_a_slider.setMinimum(-180)
        self.joint_a_slider.setMaximum(180)
        self.joint_a_slider.setValue(0)

        self.joint_a_spin = QSpinBox()
        self.joint_a_spin.setMinimum(-180)
        self.joint_a_spin.setMaximum(180)
        self.joint_a_spin.setValue(0)
        self.joint_a_spin.setSuffix("°")

        self.joint_a_slider.valueChanged.connect(self.joint_a_spin.setValue)
        self.joint_a_spin.valueChanged.connect(self.joint_a_slider.setValue)

        joint_go_btn = QPushButton("Move")
        joint_go_btn.clicked.connect(self.move_joint_a)

        joint_layout.addWidget(QLabel("Angle:"))
        joint_layout.addWidget(self.joint_a_slider)
        joint_layout.addWidget(self.joint_a_spin)
        joint_layout.addWidget(joint_go_btn)

        layout.addWidget(joint_group)

        # Console
        console_group = QGroupBox("Console")
        console_layout = QVBoxLayout(console_group)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        console_layout.addWidget(self.console)

        layout.addWidget(console_group)

        # Info
        info_text = """
        This is a minimal version for testing basic functionality.

        Required: PyQt5, pyserial

        For full features, use asgard_enhanced.py
        """
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)

        self.log("Asgard Minimal started")
        if not SERIAL_AVAILABLE:
            self.log("ERROR: pyserial not installed")
            self.log("Install with: pip install pyserial")

    def refresh_ports(self):
        """Refresh serial port list"""
        if not SERIAL_AVAILABLE:
            return

        self.port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]

        if ports:
            self.port_combo.addItems(ports)
            self.log(f"Found {len(ports)} serial port(s)")
        else:
            self.port_combo.addItem("No ports found")
            self.log("No serial ports found")

    def toggle_connection(self):
        """Connect/disconnect serial port"""
        if not SERIAL_AVAILABLE:
            return

        if self.serial_port and self.serial_port.is_open:
            # Disconnect
            self.serial_port.close()
            self.serial_port = None
            self.connect_btn.setText("Connect")
            self.log("Disconnected")
        else:
            # Connect
            port_name = self.port_combo.currentText()

            if port_name == "No ports found":
                QMessageBox.warning(self, "Error", "No serial ports available")
                return

            try:
                self.serial_port = serial.Serial(port_name, 115200, timeout=1)
                self.connect_btn.setText("Disconnect")
                self.log(f"Connected to {port_name}")
            except Exception as e:
                QMessageBox.warning(self, "Connection Error", str(e))
                self.log(f"ERROR: {e}")

    def move_joint_a(self):
        """Move joint A"""
        if not self.serial_port or not self.serial_port.is_open:
            QMessageBox.warning(self, "Error", "Not connected to robot")
            return

        angle = self.joint_a_spin.value()
        command = f"G1 A{angle} F500\n"

        try:
            self.serial_port.write(command.encode())
            self.log(f"Sent: {command.strip()}")
        except Exception as e:
            self.log(f"ERROR sending command: {e}")

    def log(self, message):
        """Log message to console"""
        self.console.append(message)

    def closeEvent(self, event):
        """Handle window close"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        event.accept()


def main():
    """Main entry point"""
    print("=" * 60)
    print("Asgard Minimal - Testing basic functionality")
    print("=" * 60)
    print()

    # Check PyQt5
    try:
        from PyQt5 import QtCore
        print("✓ PyQt5 is installed")
    except ImportError:
        print("✗ PyQt5 is NOT installed")
        print()
        print("Install with: pip install PyQt5")
        print()
        input("Press Enter to exit...")
        return 1

    # Check pyserial
    if SERIAL_AVAILABLE:
        print("✓ pyserial is installed")
    else:
        print("✗ pyserial is NOT installed (robot control will be disabled)")
        print("  Install with: pip install pyserial")

    print()
    print("Launching minimal GUI...")
    print()

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = AsgardMinimal()
    window.show()

    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())

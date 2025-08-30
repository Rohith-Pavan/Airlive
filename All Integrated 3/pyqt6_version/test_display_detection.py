#!/usr/bin/env python3
"""
Test script for display detection and HDMI settings dialog
"""

import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt

from display_manager import DisplayManager
from stream_settings_dialog import StreamSettingsDialog


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Display Detection Test")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout(self)
        
        # Display info
        self.display_manager = DisplayManager()
        
        info_label = QLabel("Display Detection Test")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Display count
        displays = self.display_manager.get_displays()
        count_label = QLabel(f"Detected {len(displays)} display(s)")
        layout.addWidget(count_label)
        
        # List displays
        for display in displays:
            display_label = QLabel(f"  • {display}")
            layout.addWidget(display_label)
        
        # External displays
        external = self.display_manager.get_external_displays()
        external_label = QLabel(f"External displays: {len(external)}")
        layout.addWidget(external_label)
        
        # Test buttons
        test_settings_btn = QPushButton("Test Stream Settings Dialog")
        test_settings_btn.clicked.connect(self.test_settings_dialog)
        layout.addWidget(test_settings_btn)
        
        if self.display_manager.has_external_displays():
            test_hdmi_btn = QPushButton("Test HDMI Window")
            test_hdmi_btn.clicked.connect(self.test_hdmi_window)
            layout.addWidget(test_hdmi_btn)
        
    def test_settings_dialog(self):
        """Test the stream settings dialog"""
        dialog = StreamSettingsDialog("TestStream", self)
        dialog.exec()
        
    def test_hdmi_window(self):
        """Test HDMI window creation"""
        external_displays = self.display_manager.get_external_displays()
        if external_displays:
            display = external_displays[0]
            window = self.display_manager.create_hdmi_window(display.index)
            if window:
                window.show_windowed_on_display()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
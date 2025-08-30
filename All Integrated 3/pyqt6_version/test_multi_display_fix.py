#!/usr/bin/env python3
"""
Test multi-display detection and HDMI streaming with any display type
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt, QTimer

from display_manager import get_display_manager
from stream_settings_dialog import StreamSettingsDialog


class MultiDisplayTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Display Detection Test")
        self.setGeometry(100, 100, 800, 600)
        
        self.display_manager = get_display_manager()
        
        self.setup_ui()
        self.connect_signals()
        
        # Auto-refresh every 2 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_display_info)
        self.refresh_timer.start(2000)
        
        # Initial display
        self.refresh_display_info()
        
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Multi-Display Detection Test")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # Display info
        self.display_info = QTextEdit()
        self.display_info.setMaximumHeight(200)
        self.display_info.setReadOnly(True)
        layout.addWidget(self.display_info)
        
        # Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        self.refresh_btn = QPushButton("Force Refresh")
        self.refresh_btn.clicked.connect(self.force_refresh)
        controls_layout.addWidget(self.refresh_btn)
        
        self.test_settings_btn = QPushButton("Test Stream Settings")
        self.test_settings_btn.clicked.connect(self.test_stream_settings)
        controls_layout.addWidget(self.test_settings_btn)
        
        layout.addWidget(controls_group)
        
        # Status log
        status_group = QGroupBox("Status Log")
        status_layout = QVBoxLayout(status_group)
        
        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        status_layout.addWidget(self.status_log)
        
        layout.addWidget(status_group)
        
    def connect_signals(self):
        """Connect display manager signals"""
        self.display_manager.displays_changed.connect(self.on_displays_changed)
        
    def refresh_display_info(self):
        """Refresh display information"""
        displays = self.display_manager.get_displays()
        
        info_text = f"=== Display Detection Status ===\n"
        info_text += f"Total displays detected: {len(displays)}\n\n"
        
        for i, display in enumerate(displays):
            info_text += f"Display {i+1}:\n"
            info_text += f"  Name: {display.name}\n"
            info_text += f"  Resolution: {display.resolution_string}\n"
            info_text += f"  Primary: {'Yes' if display.is_primary else 'No'}\n"
            info_text += f"  Position: ({display.geometry.x()}, {display.geometry.y()})\n\n"
        
        # Check HDMI availability
        total_displays = len(displays)
        external_displays = self.display_manager.get_external_displays()
        
        info_text += f"=== HDMI Streaming Status ===\n"
        if total_displays > 1:
            info_text += f"✅ HDMI streaming AVAILABLE ({total_displays} displays)\n"
            info_text += f"External displays: {len(external_displays)}\n"
            info_text += f"All displays can be used for HDMI output\n"
        else:
            info_text += f"❌ HDMI streaming NOT AVAILABLE (only {total_displays} display)\n"
            info_text += f"Connect an external display to enable HDMI streaming\n"
        
        self.display_info.setText(info_text)
        
    def force_refresh(self):
        """Force display refresh"""
        self.log_status("Forcing display refresh...")
        self.display_manager.force_refresh()
        self.refresh_display_info()
        
    def test_stream_settings(self):
        """Test stream settings dialog"""
        self.log_status("Opening stream settings dialog...")
        dialog = StreamSettingsDialog("TestStream", self)
        
        # Check if HDMI option is available
        displays = self.display_manager.get_displays()
        if len(displays) > 1:
            self.log_status(f"✅ HDMI Display option should be available ({len(displays)} displays)")
        else:
            self.log_status(f"❌ HDMI Display option not available (only {len(displays)} display)")
            
        dialog.exec()
        
    def on_displays_changed(self):
        """Handle display configuration changes"""
        displays = self.display_manager.get_displays()
        self.log_status(f"🔄 Display configuration changed: {len(displays)} displays detected")
        self.refresh_display_info()
        
    def log_status(self, message):
        """Log status message"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.status_log.append(formatted_message)
        print(formatted_message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = MultiDisplayTestWindow()
    window.show()
    
    sys.exit(app.exec())
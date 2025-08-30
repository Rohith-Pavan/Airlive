#!/usr/bin/env python3
"""
Complete HDMI Integration Test with Main Application
Tests the full pipeline from NewStreamSettingsDialog to HDMI streaming
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor

class MockGraphicsView(QWidget):
    """Mock graphics view for testing"""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(640, 480)
        self.setStyleSheet("background-color: blue; border: 2px solid white;")
        
        # Create test content
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_content)
        self.timer.start(100)  # Update every 100ms
        self.counter = 0
        
    def update_content(self):
        """Update content for animation"""
        self.counter += 1
        color_value = (self.counter * 5) % 255
        self.setStyleSheet(f"background-color: rgb({color_value}, 100, {255-color_value}); border: 2px solid white;")
        
    def grab(self):
        """Grab the widget as pixmap"""
        return super().grab()

class HDMIIntegrationTestWindow(QMainWindow):
    """Main test window for HDMI integration"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Complete HDMI Integration Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Info label
        info_label = QLabel("Complete HDMI Integration Test")
        info_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(info_label)
        
        # Mock graphics view
        self.graphics_view = MockGraphicsView()
        layout.addWidget(self.graphics_view)
        
        # Test buttons
        self.setup_test_buttons(layout)
        
        # Status display
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        # Initialize stream manager
        self.stream_manager = None
        self.stream_control = None
        self.init_stream_manager()
        
    def setup_test_buttons(self, layout):
        """Setup test buttons"""
        
        # Open settings dialog button
        settings_button = QPushButton("Open Stream Settings Dialog")
        settings_button.clicked.connect(self.open_settings_dialog)
        layout.addWidget(settings_button)
        
        # Start HDMI stream button
        start_button = QPushButton("Start HDMI Stream")
        start_button.clicked.connect(self.start_hdmi_stream)
        layout.addWidget(start_button)
        
        # Stop stream button
        stop_button = QPushButton("Stop Stream")
        stop_button.clicked.connect(self.stop_stream)
        layout.addWidget(stop_button)
        
        # Test display detection button
        detect_button = QPushButton("Test Display Detection")
        detect_button.clicked.connect(self.test_display_detection)
        layout.addWidget(detect_button)
        
    def init_stream_manager(self):
        """Initialize stream manager"""
        try:
            from new_stream_manager import NewStreamManager, NewStreamControlWidget
            
            self.stream_manager = NewStreamManager()
            self.stream_manager.register_graphics_view("TestStream", self.graphics_view)
            
            # Connect signals
            self.stream_manager.stream_started.connect(self.on_stream_started)
            self.stream_manager.stream_stopped.connect(self.on_stream_stopped)
            self.stream_manager.stream_error.connect(self.on_stream_error)
            self.stream_manager.status_update.connect(self.on_status_update)
            
            # Create stream control widget
            self.stream_control = NewStreamControlWidget("TestStream", self.stream_manager, self)
            
            self.log_status("✅ Stream manager initialized successfully")
            
        except Exception as e:
            self.log_status(f"❌ Error initializing stream manager: {e}")
            import traceback
            traceback.print_exc()
    
    def open_settings_dialog(self):
        """Open the new stream settings dialog"""
        try:
            if self.stream_control:
                self.stream_control.open_settings_dialog()
            else:
                self.log_status("❌ Stream control not initialized")
                
        except Exception as e:
            self.log_status(f"❌ Error opening settings dialog: {e}")
            import traceback
            traceback.print_exc()
    
    def start_hdmi_stream(self):
        """Start HDMI stream with test settings"""
        try:
            # Create test HDMI settings
            hdmi_settings = {
                "platform": "HDMI Display",
                "is_hdmi": True,
                "hdmi_display_index": 1,  # Assuming second display
                "hdmi_mode": "Mirror",
                "resolution": "1920x1080",
                "fps": 30,
                "video_bitrate": 2500,
                "audio_bitrate": 128,
                "codec": "libx264",
                "preset": "veryfast",
                "profile": "main",
                "low_latency": False,
                "buffer_size": 2
            }
            
            # Configure and start stream
            if self.stream_manager.configure_stream("TestStream", hdmi_settings):
                self.log_status("✅ HDMI stream configured")
                
                if self.stream_manager.start_stream("TestStream"):
                    self.log_status("✅ HDMI stream start initiated")
                else:
                    self.log_status("❌ Failed to start HDMI stream")
            else:
                self.log_status("❌ Failed to configure HDMI stream")
                
        except Exception as e:
            self.log_status(f"❌ Error starting HDMI stream: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_stream(self):
        """Stop the current stream"""
        try:
            if self.stream_manager.stop_stream("TestStream"):
                self.log_status("✅ Stream stop initiated")
            else:
                self.log_status("❌ Failed to stop stream")
                
        except Exception as e:
            self.log_status(f"❌ Error stopping stream: {e}")
    
    def test_display_detection(self):
        """Test display detection"""
        try:
            from display_manager import DisplayManager
            
            display_manager = DisplayManager()
            displays = display_manager.get_displays()
            
            self.log_status(f"📺 Detected {len(displays)} displays:")
            for display in displays:
                self.log_status(f"  - {display.display_name}")
                
            if len(displays) > 1:
                self.log_status("✅ Multiple displays detected - HDMI streaming possible")
            else:
                self.log_status("⚠️ Only one display detected - HDMI streaming may not work")
                
        except Exception as e:
            self.log_status(f"❌ Error detecting displays: {e}")
            import traceback
            traceback.print_exc()
    
    def on_stream_started(self, stream_name):
        """Handle stream started"""
        self.log_status(f"🎥 Stream {stream_name} started successfully!")
    
    def on_stream_stopped(self, stream_name):
        """Handle stream stopped"""
        self.log_status(f"⏹️ Stream {stream_name} stopped")
    
    def on_stream_error(self, stream_name, error_msg):
        """Handle stream error"""
        self.log_status(f"❌ Stream {stream_name} error: {error_msg}")
    
    def on_status_update(self, stream_name, status):
        """Handle status update"""
        self.log_status(f"📊 {stream_name}: {status}")
    
    def log_status(self, message):
        """Log status message"""
        self.status_text.append(message)
        print(message)

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Create and show test window
    window = HDMIIntegrationTestWindow()
    window.show()
    
    print("Complete HDMI Integration Test")
    print("=" * 50)
    print("Instructions:")
    print("1. Click 'Test Display Detection' to check available displays")
    print("2. Click 'Open Stream Settings Dialog' to configure HDMI streaming")
    print("3. Select 'HDMI Display' platform and configure settings")
    print("4. Click 'Start HDMI Stream' to test programmatic HDMI streaming")
    print("5. Check status messages for results")
    print("=" * 50)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
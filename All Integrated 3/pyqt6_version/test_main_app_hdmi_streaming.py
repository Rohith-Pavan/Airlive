#!/usr/bin/env python3
"""
Test HDMI streaming functionality in the main application
"""

import sys
import time
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import QTimer

class MainAppHDMIStreamingTest(QWidget):
    """Test HDMI streaming in the main application"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main App HDMI Streaming Test")
        self.setGeometry(300, 300, 700, 500)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Main Application HDMI Streaming Test")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("""
This test verifies HDMI streaming functionality in the main GoLive Studio application.

Steps to test:
1. Make sure the main application (main.py) is running
2. Click 'Test HDMI Stream Configuration' to configure HDMI settings
3. Click 'Start HDMI Stream' to test streaming
4. Check your external display for video output
5. Click 'Stop Stream' when done

Note: You need an external display connected for HDMI streaming to work.
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Test buttons
        config_btn = QPushButton("Test HDMI Stream Configuration")
        config_btn.clicked.connect(self.test_hdmi_configuration)
        layout.addWidget(config_btn)
        
        start_btn = QPushButton("Start HDMI Stream")
        start_btn.clicked.connect(self.start_hdmi_stream)
        layout.addWidget(start_btn)
        
        stop_btn = QPushButton("Stop Stream")
        stop_btn.clicked.connect(self.stop_stream)
        layout.addWidget(stop_btn)
        
        # Status display
        self.status = QTextEdit()
        self.status.setMaximumHeight(200)
        layout.addWidget(self.status)
        
        # Initialize components
        self.stream_manager = None
        self.graphics_view = None
        self.init_components()
    
    def init_components(self):
        """Initialize stream manager and graphics components"""
        try:
            # Import the GStreamer stream manager (the one actually used by main app)
            from gstreamer.gst_stream_manager import NewStreamManager
            from graphics_output_widget import GraphicsOutputWidget
            
            # Create a mock graphics view for testing
            self.graphics_view = GraphicsOutputWidget()
            self.graphics_view.setFixedSize(320, 240)  # Small preview
            layout = self.layout()
            layout.insertWidget(4, self.graphics_view)  # Insert before status
            
            # Create stream manager
            self.stream_manager = NewStreamManager()
            self.stream_manager.register_graphics_view("TestHDMI", self.graphics_view)
            
            # Connect signals
            self.stream_manager.stream_started.connect(self.on_stream_started)
            self.stream_manager.stream_stopped.connect(self.on_stream_stopped)
            self.stream_manager.stream_error.connect(self.on_stream_error)
            self.stream_manager.status_update.connect(self.on_status_update)
            
            self.log("✅ Stream manager and graphics components initialized")
            
        except Exception as e:
            self.log(f"❌ Error initializing components: {e}")
            import traceback
            traceback.print_exc()
    
    def test_hdmi_configuration(self):
        """Test HDMI stream configuration"""
        try:
            from display_manager import DisplayManager
            
            # Check displays
            display_manager = DisplayManager()
            displays = display_manager.get_displays()
            
            self.log(f"🖥️ Found {len(displays)} displays:")
            for display in displays:
                self.log(f"   - {display.display_name}")
            
            if len(displays) < 2:
                self.log("⚠️ Only one display found. HDMI streaming requires an external display.")
                return
            
            # Find external display
            external_displays = [d for d in displays if not d.is_primary]
            if not external_displays:
                self.log("⚠️ No external displays found for HDMI streaming")
                return
            
            target_display = external_displays[0]
            
            # Create HDMI settings
            hdmi_settings = {
                "platform": "HDMI Display",
                "is_hdmi": True,
                "hdmi_display_index": target_display.index,
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
            
            # Test configuration
            if self.stream_manager.configure_stream("TestHDMI", hdmi_settings):
                self.log("✅ HDMI stream configured successfully")
                self.log(f"   Target display: {target_display.name}")
                self.log(f"   Resolution: {hdmi_settings['resolution']}")
                self.log(f"   Mode: {hdmi_settings['hdmi_mode']}")
            else:
                self.log("❌ Failed to configure HDMI stream")
                
        except Exception as e:
            self.log(f"❌ Error testing HDMI configuration: {e}")
            import traceback
            traceback.print_exc()
    
    def start_hdmi_stream(self):
        """Start HDMI streaming"""
        try:
            if not self.stream_manager:
                self.log("❌ Stream manager not initialized")
                return
            
            self.log("🚀 Starting HDMI stream...")
            
            if self.stream_manager.start_stream("TestHDMI"):
                self.log("✅ HDMI stream start initiated")
            else:
                self.log("❌ Failed to start HDMI stream")
                
        except Exception as e:
            self.log(f"❌ Error starting HDMI stream: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_stream(self):
        """Stop streaming"""
        try:
            if not self.stream_manager:
                self.log("❌ Stream manager not initialized")
                return
            
            self.log("⏹️ Stopping stream...")
            
            if self.stream_manager.stop_stream("TestHDMI"):
                self.log("✅ Stream stop initiated")
            else:
                self.log("❌ Failed to stop stream")
                
        except Exception as e:
            self.log(f"❌ Error stopping stream: {e}")
    
    def on_stream_started(self, stream_name):
        """Handle stream started"""
        self.log(f"🎥 Stream '{stream_name}' started successfully!")
        self.log("   Check your external display for HDMI output")
    
    def on_stream_stopped(self, stream_name):
        """Handle stream stopped"""
        self.log(f"⏹️ Stream '{stream_name}' stopped")
    
    def on_stream_error(self, stream_name, error_msg):
        """Handle stream error"""
        self.log(f"❌ Stream '{stream_name}' error: {error_msg}")
    
    def on_status_update(self, stream_name, status):
        """Handle status update"""
        self.log(f"📊 {stream_name}: {status}")
    
    def log(self, message):
        """Log message"""
        self.status.append(message)
        print(message)
        
        # Auto-scroll to bottom
        scrollbar = self.status.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    tester = MainAppHDMIStreamingTest()
    tester.show()
    
    print("Main Application HDMI Streaming Test")
    print("=" * 50)
    print("Testing HDMI streaming functionality with the actual main app components")
    print("Make sure you have an external display connected for testing")
    print("=" * 50)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Final HDMI Integration Test
Complete test of HDMI functionality from dialog to streaming
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor

class AnimatedGraphicsView(QWidget):
    """Animated graphics view for testing HDMI mirroring"""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(640, 480)
        self.counter = 0
        
        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(50)  # 20 FPS animation
        
    def animate(self):
        """Animate the widget"""
        self.counter += 1
        
        # Create animated colors
        r = int(127 + 127 * (self.counter % 100) / 100)
        g = int(127 + 127 * ((self.counter + 33) % 100) / 100)
        b = int(127 + 127 * ((self.counter + 66) % 100) / 100)
        
        self.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgb({r}, {g}, {b}),
                stop:1 rgb({b}, {r}, {g}));
            border: 3px solid white;
            border-radius: 10px;
        """)
        
    def grab(self):
        """Grab widget as pixmap for streaming"""
        return super().grab()

class FinalHDMITestWindow(QMainWindow):
    """Final HDMI integration test window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Final HDMI Integration Test - GoLive Studio")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize components
        self.stream_manager = None
        self.stream_control = None
        self.current_settings = None
        
        self.setup_ui()
        self.init_stream_system()
        
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Graphics view
        left_panel = QVBoxLayout()
        
        # Graphics view label
        graphics_label = QLabel("Live Graphics Output (This will be mirrored to HDMI)")
        graphics_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 5px;")
        left_panel.addWidget(graphics_label)
        
        # Animated graphics view
        self.graphics_view = AnimatedGraphicsView()
        left_panel.addWidget(self.graphics_view)
        
        # Add left panel to main layout
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        main_layout.addWidget(left_widget)
        
        # Right panel - Controls and status
        right_panel = QVBoxLayout()
        
        # Title
        title_label = QLabel("HDMI Streaming Controls")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        right_panel.addWidget(title_label)
        
        # Control buttons
        self.setup_control_buttons(right_panel)
        
        # Status display
        status_label = QLabel("Status Log:")
        status_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        right_panel.addWidget(status_label)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(200)
        self.status_text.setReadOnly(True)
        right_panel.addWidget(self.status_text)
        
        # Instructions
        instructions = QLabel("""
Instructions:
1. Test Display Detection to verify multiple displays
2. Open Stream Settings and select "HDMI Display"
3. Choose your target display and mode
4. Save settings and start streaming
5. The animated graphics should appear on your HDMI display
        """)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("margin: 10px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        right_panel.addWidget(instructions)
        
        # Add right panel to main layout
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        right_widget.setMaximumWidth(400)
        main_layout.addWidget(right_widget)
        
    def setup_control_buttons(self, layout):
        """Setup control buttons"""
        
        # Display detection
        detect_btn = QPushButton("🖥️ Test Display Detection")
        detect_btn.clicked.connect(self.test_display_detection)
        layout.addWidget(detect_btn)
        
        # Settings dialog
        settings_btn = QPushButton("⚙️ Open Stream Settings Dialog")
        settings_btn.clicked.connect(self.open_settings_dialog)
        layout.addWidget(settings_btn)
        
        # Quick HDMI test
        quick_btn = QPushButton("🚀 Quick HDMI Test (Auto-config)")
        quick_btn.clicked.connect(self.quick_hdmi_test)
        layout.addWidget(quick_btn)
        
        # Start/Stop buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Start Stream")
        self.start_btn.clicked.connect(self.start_stream)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop Stream")
        self.stop_btn.clicked.connect(self.stop_stream)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        layout.addLayout(button_layout)
        
    def init_stream_system(self):
        """Initialize the streaming system"""
        try:
            from new_stream_manager import NewStreamManager, NewStreamControlWidget
            
            # Create stream manager
            self.stream_manager = NewStreamManager()
            self.stream_manager.register_graphics_view("MainStream", self.graphics_view)
            
            # Connect signals
            self.stream_manager.stream_started.connect(self.on_stream_started)
            self.stream_manager.stream_stopped.connect(self.on_stream_stopped)
            self.stream_manager.stream_error.connect(self.on_stream_error)
            self.stream_manager.status_update.connect(self.on_status_update)
            
            # Create stream control
            self.stream_control = NewStreamControlWidget("MainStream", self.stream_manager, self)
            
            self.log_status("✅ Stream system initialized successfully")
            
        except Exception as e:
            self.log_status(f"❌ Failed to initialize stream system: {e}")
            import traceback
            traceback.print_exc()
    
    def test_display_detection(self):
        """Test display detection"""
        try:
            from display_manager import DisplayManager
            
            display_manager = DisplayManager()
            displays = display_manager.get_displays()
            
            self.log_status(f"🖥️ Display Detection Results:")
            self.log_status(f"   Found {len(displays)} display(s)")
            
            for i, display in enumerate(displays):
                primary_text = " (Primary)" if display.is_primary else ""
                self.log_status(f"   {i+1}. {display.name} - {display.resolution_string}{primary_text}")
            
            if len(displays) > 1:
                self.log_status("✅ Multiple displays detected - HDMI streaming ready!")
            else:
                self.log_status("⚠️ Only one display found - connect an external display for HDMI streaming")
                
        except Exception as e:
            self.log_status(f"❌ Display detection error: {e}")
    
    def open_settings_dialog(self):
        """Open stream settings dialog"""
        try:
            if self.stream_control:
                self.stream_control.open_settings_dialog()
            else:
                self.log_status("❌ Stream control not available")
        except Exception as e:
            self.log_status(f"❌ Error opening settings: {e}")
    
    def quick_hdmi_test(self):
        """Quick HDMI test with auto-configuration"""
        try:
            from display_manager import DisplayManager
            
            # Check for external displays
            display_manager = DisplayManager()
            displays = display_manager.get_displays()
            external_displays = [d for d in displays if not d.is_primary]
            
            if not external_displays:
                self.log_status("❌ No external displays found for HDMI test")
                return
            
            # Use first external display
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
            
            self.current_settings = hdmi_settings
            self.log_status(f"🚀 Auto-configured HDMI for {target_display.name}")
            self.log_status("   Click 'Start Stream' to begin HDMI output")
            
        except Exception as e:
            self.log_status(f"❌ Quick HDMI test error: {e}")
    
    def start_stream(self):
        """Start streaming"""
        try:
            if not self.current_settings:
                self.log_status("❌ No stream settings configured. Use settings dialog or quick test first.")
                return
            
            # Configure stream
            if self.stream_manager.configure_stream("MainStream", self.current_settings):
                self.log_status("✅ Stream configured")
                
                # Start stream
                if self.stream_manager.start_stream("MainStream"):
                    self.log_status("🎬 Starting stream...")
                else:
                    self.log_status("❌ Failed to start stream")
            else:
                self.log_status("❌ Failed to configure stream")
                
        except Exception as e:
            self.log_status(f"❌ Start stream error: {e}")
    
    def stop_stream(self):
        """Stop streaming"""
        try:
            if self.stream_manager.stop_stream("MainStream"):
                self.log_status("⏹️ Stopping stream...")
            else:
                self.log_status("❌ Failed to stop stream")
        except Exception as e:
            self.log_status(f"❌ Stop stream error: {e}")
    
    def on_stream_started(self, stream_name):
        """Handle stream started"""
        self.log_status(f"🎥 Stream '{stream_name}' started successfully!")
        self.log_status("   Check your HDMI display for the mirrored output")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def on_stream_stopped(self, stream_name):
        """Handle stream stopped"""
        self.log_status(f"⏹️ Stream '{stream_name}' stopped")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def on_stream_error(self, stream_name, error_msg):
        """Handle stream error"""
        self.log_status(f"❌ Stream '{stream_name}' error: {error_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def on_status_update(self, stream_name, status):
        """Handle status update"""
        self.log_status(f"📊 {stream_name}: {status}")
    
    def log_status(self, message):
        """Log status message"""
        self.status_text.append(message)
        print(message)
        
        # Auto-scroll to bottom
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Create and show main window
    window = FinalHDMITestWindow()
    window.show()
    
    print("Final HDMI Integration Test - GoLive Studio")
    print("=" * 60)
    print("This test verifies the complete HDMI streaming pipeline:")
    print("- Display detection")
    print("- Settings dialog with HDMI options")
    print("- Stream configuration and management")
    print("- Real-time video mirroring to HDMI displays")
    print("=" * 60)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
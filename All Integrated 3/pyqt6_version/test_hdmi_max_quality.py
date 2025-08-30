#!/usr/bin/env python3
"""
Test HDMI Maximum Quality Enhancement
Verifies the enhanced quality settings for HDMI streaming
"""

import sys
import math
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient

class HighQualityTestWidget(QWidget):
    """High-quality animated test widget for HDMI quality testing"""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(1920, 1080)  # Full HD for maximum quality
        self.counter = 0
        
        # High-quality animation timer - 60 FPS
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)  # 60 FPS (16.67ms)
        
        # Set high-quality rendering
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        
    def animate(self):
        """High-quality animation"""
        self.counter += 1
        self.update()
        
    def paintEvent(self, event):
        """High-quality paint event"""
        painter = QPainter(self)
        
        # Enable all high-quality rendering hints
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        
        # Create high-quality gradient background
        width, height = self.width(), self.height()
        
        # Animated gradient colors
        r1 = int(127 + 127 * abs(math.sin(self.counter * 0.02)))
        g1 = int(127 + 127 * abs(math.sin(self.counter * 0.03)))
        b1 = int(127 + 127 * abs(math.sin(self.counter * 0.04)))
        
        r2 = int(127 + 127 * abs(math.cos(self.counter * 0.025)))
        g2 = int(127 + 127 * abs(math.cos(self.counter * 0.035)))
        b2 = int(127 + 127 * abs(math.cos(self.counter * 0.045)))
        
        # Create gradient
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0, QColor(r1, g1, b1))
        gradient.setColorAt(1, QColor(r2, g2, b2))
        
        painter.fillRect(self.rect(), gradient)
        
        # Draw high-quality text
        font = QFont("Arial", 48, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        
        text = f"HDMI Quality Test - Frame {self.counter}"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
        
        # Draw quality indicators
        painter.setPen(QColor(0, 255, 0))
        painter.drawText(50, 100, "Resolution: 1920x1080 (Full HD)")
        painter.drawText(50, 150, "Frame Rate: 60 FPS")
        painter.drawText(50, 200, "Quality: Maximum")
        painter.drawText(50, 250, "Antialiasing: Enabled")
        painter.drawText(50, 300, "Smooth Transform: Enabled")
        
        painter.end()

class HDMIMaxQualityTest(QWidget):
    """HDMI Maximum Quality Test Application"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HDMI Maximum Quality Test - GoLive Studio")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize components
        self.stream_manager = None
        self.test_widget = None
        
        self.setup_ui()
        self.init_stream_system()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("HDMI Maximum Quality Test")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 15px; color: #2E86AB;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Quality info
        quality_info = QLabel("""
🎯 ENHANCED QUALITY SETTINGS:
• Resolution: 1920x1080 (Full HD)
• Frame Rate: 60 FPS (Ultra Smooth)
• Video Bitrate: 8 Mbps (High Quality)
• Audio Bitrate: 192 kbps (High Quality)
• Rendering: Maximum Quality with Antialiasing
• Scaling: Smooth Transformation
        """)
        quality_info.setStyleSheet("background-color: #f0f8ff; padding: 15px; border-radius: 8px; margin: 10px;")
        layout.addWidget(quality_info)
        
        # Test widget (scaled down for preview)
        self.test_widget = HighQualityTestWidget()
        self.test_widget.setFixedSize(640, 360)  # Scaled preview
        layout.addWidget(self.test_widget)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        config_btn = QPushButton("🔧 Configure Max Quality HDMI")
        config_btn.clicked.connect(self.configure_max_quality_hdmi)
        button_layout.addWidget(config_btn)
        
        start_btn = QPushButton("🚀 Start Max Quality Stream")
        start_btn.clicked.connect(self.start_max_quality_stream)
        button_layout.addWidget(start_btn)
        
        stop_btn = QPushButton("⏹️ Stop Stream")
        stop_btn.clicked.connect(self.stop_stream)
        button_layout.addWidget(stop_btn)
        
        layout.addLayout(button_layout)
        
        # Status display
        self.status = QTextEdit()
        self.status.setMaximumHeight(200)
        layout.addWidget(self.status)
        
    def init_stream_system(self):
        """Initialize the streaming system"""
        try:
            # Import the actual stream manager used by main app
            from gstreamer.gst_stream_manager import NewStreamManager
            
            # Create stream manager
            self.stream_manager = NewStreamManager()
            self.stream_manager.register_graphics_view("MaxQualityHDMI", self.test_widget)
            
            # Connect signals
            self.stream_manager.stream_started.connect(self.on_stream_started)
            self.stream_manager.stream_stopped.connect(self.on_stream_stopped)
            self.stream_manager.stream_error.connect(self.on_stream_error)
            self.stream_manager.status_update.connect(self.on_status_update)
            
            self.log("✅ Maximum quality stream system initialized")
            
        except Exception as e:
            self.log(f"❌ Error initializing stream system: {e}")
            # Fallback to new_stream_manager if gstreamer not available
            try:
                from new_stream_manager import NewStreamManager
                self.stream_manager = NewStreamManager()
                self.stream_manager.register_graphics_view("MaxQualityHDMI", self.test_widget)
                self.log("✅ Fallback stream system initialized")
            except Exception as e2:
                self.log(f"❌ Fallback also failed: {e2}")
    
    def configure_max_quality_hdmi(self):
        """Configure HDMI with maximum quality settings"""
        try:
            from display_manager import DisplayManager
            
            # Check displays
            display_manager = DisplayManager()
            displays = display_manager.get_displays()
            
            self.log(f"🖥️ Display Detection:")
            for display in displays:
                primary_text = " (Primary)" if display.is_primary else ""
                self.log(f"   - {display.name}: {display.resolution_string}{primary_text}")
            
            if len(displays) < 2:
                self.log("⚠️ Only one display found. Connect an external display for HDMI streaming.")
                return
            
            # Find best external display
            external_displays = [d for d in displays if not d.is_primary]
            if not external_displays:
                self.log("⚠️ No external displays found")
                return
            
            # Use the highest resolution external display
            target_display = max(external_displays, key=lambda d: d.geometry.width() * d.geometry.height())
            
            # MAXIMUM QUALITY HDMI SETTINGS
            max_quality_settings = {
                "platform": "HDMI Display",
                "is_hdmi": True,
                "hdmi_display_index": target_display.index,
                "hdmi_mode": "Mirror",
                "resolution": "1920x1080",  # Full HD
                "fps": 60,  # Ultra-smooth 60 FPS
                "video_bitrate": 12000,  # 12 Mbps for maximum quality
                "audio_bitrate": 320,  # Highest audio quality
                "codec": "libx264",
                "preset": "slow",  # Best quality preset
                "profile": "high",  # High profile
                "low_latency": False,
                "buffer_size": 4  # Larger buffer for quality
            }
            
            # Configure stream
            if self.stream_manager.configure_stream("MaxQualityHDMI", max_quality_settings):
                self.log("✅ Maximum quality HDMI configured successfully!")
                self.log(f"   Target: {target_display.name} ({target_display.resolution_string})")
                self.log(f"   Quality: 1920x1080 @ 60 FPS, 12 Mbps")
                self.log(f"   Audio: 320 kbps, Codec: H.264 High Profile")
            else:
                self.log("❌ Failed to configure maximum quality HDMI")
                
        except Exception as e:
            self.log(f"❌ Error configuring HDMI: {e}")
            import traceback
            traceback.print_exc()
    
    def start_max_quality_stream(self):
        """Start maximum quality HDMI streaming"""
        try:
            if not self.stream_manager:
                self.log("❌ Stream manager not initialized")
                return
            
            self.log("🚀 Starting maximum quality HDMI stream...")
            self.log("   This may take a moment to initialize high-quality encoding")
            
            if self.stream_manager.start_stream("MaxQualityHDMI"):
                self.log("✅ Maximum quality HDMI stream initiated")
            else:
                self.log("❌ Failed to start maximum quality stream")
                
        except Exception as e:
            self.log(f"❌ Error starting stream: {e}")
    
    def stop_stream(self):
        """Stop streaming"""
        try:
            if self.stream_manager:
                self.stream_manager.stop_stream("MaxQualityHDMI")
                self.log("⏹️ Stream stop initiated")
        except Exception as e:
            self.log(f"❌ Error stopping stream: {e}")
    
    def on_stream_started(self, stream_name):
        """Handle stream started"""
        self.log(f"🎥 Maximum quality stream '{stream_name}' started!")
        self.log("   Check your external display for ultra-high-quality HDMI output")
        self.log("   You should see smooth 60 FPS animation with crisp 1080p quality")
    
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
    
    tester = HDMIMaxQualityTest()
    tester.show()
    
    print("HDMI Maximum Quality Test - GoLive Studio")
    print("=" * 60)
    print("Testing ENHANCED HDMI streaming with maximum quality settings:")
    print("• 1920x1080 Full HD resolution")
    print("• 60 FPS ultra-smooth playback")
    print("• 12 Mbps video bitrate for crystal clear quality")
    print("• 320 kbps audio for professional sound")
    print("• Advanced antialiasing and smooth scaling")
    print("=" * 60)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
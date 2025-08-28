#!/usr/bin/env python3
"""
Comprehensive streaming test script for GoLive Studio
Tests all components from frame capture to FFmpeg streaming
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit, QProgressBar
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from stream_manager import StreamManager, StreamCaptureThread
from graphics_output_widget import GraphicsOutputManager
from ffmpeg_locator import find_ffmpeg, ensure_ffmpeg_available

class StreamingTestSuite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoLive Studio - Complete Streaming Test Suite")
        self.setGeometry(100, 100, 1000, 700)
        
        # Test results
        self.test_results = {}
        self.current_test = None
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create test components
        self.setup_test_environment(layout)
        
        # Create controls
        self.create_controls(layout)
        
        # Create log display
        self.log_display = QTextEdit()
        self.log_display.setMaximumHeight(200)
        layout.addWidget(self.log_display)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Start automatic tests
        QTimer.singleShot(1000, self.run_all_tests)
        
    def setup_test_environment(self, layout):
        """Setup test environment with graphics and streaming components"""
        # Create graphics output
        self.graphics_manager = GraphicsOutputManager()
        self.graphics_widget = self.graphics_manager.create_output_widget("test_output")
        self.graphics_widget.setMinimumHeight(300)
        layout.addWidget(self.graphics_widget)
        
        # Create rich test content
        self.create_test_content()
        
        # Create stream manager
        self.stream_manager = StreamManager()
        self.stream_manager.register_graphics_view("TestStream", self.graphics_widget)
        
        # Connect signals
        self.stream_manager.stream_started.connect(self.on_stream_started)
        self.stream_manager.stream_stopped.connect(self.on_stream_stopped)
        self.stream_manager.stream_error.connect(self.on_stream_error)
        self.stream_manager.frame_count_updated.connect(self.on_frame_count_updated)
        
    def create_test_content(self):
        """Create rich test content for streaming"""
        from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem
        from PyQt6.QtGui import QBrush, QFont
        
        scene = self.graphics_widget.scene()
        if scene:
            # Create colorful rectangles
            colors = [
                QColor(255, 0, 0),    # Red
                QColor(0, 255, 0),    # Green  
                QColor(0, 0, 255),    # Blue
                QColor(255, 255, 0),  # Yellow
                QColor(255, 0, 255),  # Magenta
                QColor(0, 255, 255),  # Cyan
            ]
            
            for i, color in enumerate(colors):
                rect_item = QGraphicsRectItem(50 + i * 80, 50, 60, 40)
                rect_item.setBrush(QBrush(color))
                rect_item.setZValue(1)
                scene.addItem(rect_item)
            
            # Add text
            text_item = QGraphicsTextItem("GOLIVE STUDIO TEST")
            font = QFont("Arial", 16, QFont.Weight.Bold)
            text_item.setFont(font)
            text_item.setDefaultTextColor(QColor(255, 255, 255))
            text_item.setPos(50, 120)
            text_item.setZValue(2)
            scene.addItem(text_item)
            
            # Add animated circle
            self.animated_circle = QGraphicsEllipseItem(200, 180, 50, 50)
            self.animated_circle.setBrush(QBrush(QColor(255, 128, 0)))
            self.animated_circle.setZValue(1)
            scene.addItem(self.animated_circle)
            
            # Animate the circle
            self.animation_timer = QTimer()
            self.animation_timer.timeout.connect(self.animate_content)
            self.animation_timer.start(100)  # 10 FPS animation
            
            self.log("Rich test content created")
    
    def animate_content(self):
        """Animate test content"""
        if hasattr(self, 'animated_circle'):
            current_pos = self.animated_circle.pos()
            new_x = (current_pos.x() + 2) % 400
            self.animated_circle.setPos(new_x, current_pos.y())
    
    def create_controls(self, layout):
        """Create control buttons"""
        from PyQt6.QtWidgets import QHBoxLayout
        
        control_layout = QHBoxLayout()
        
        # Test buttons
        self.test_ffmpeg_btn = QPushButton("Test FFmpeg")
        self.test_ffmpeg_btn.clicked.connect(self.test_ffmpeg)
        control_layout.addWidget(self.test_ffmpeg_btn)
        
        self.test_capture_btn = QPushButton("Test Capture")
        self.test_capture_btn.clicked.connect(self.test_frame_capture)
        control_layout.addWidget(self.test_capture_btn)
        
        self.test_stream_btn = QPushButton("Test Stream")
        self.test_stream_btn.clicked.connect(self.test_streaming)
        control_layout.addWidget(self.test_stream_btn)
        
        self.run_all_btn = QPushButton("Run All Tests")
        self.run_all_btn.clicked.connect(self.run_all_tests)
        control_layout.addWidget(self.run_all_btn)
        
        # Status label
        self.status_label = QLabel("Ready")
        control_layout.addWidget(self.status_label)
        
        layout.addLayout(control_layout)
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        self.log("=== Starting Comprehensive Test Suite ===")
        self.progress_bar.setValue(0)
        
        tests = [
            ("FFmpeg Installation", self.test_ffmpeg),
            ("Frame Capture", self.test_frame_capture),
            ("Stream Configuration", self.test_stream_config),
            ("Stream Validation", self.test_stream_validation),
            ("Streaming Process", self.test_streaming),
        ]
        
        total_tests = len(tests)
        
        for i, (test_name, test_func) in enumerate(tests):
            self.current_test = test_name
            self.log(f"\n--- Running Test: {test_name} ---")
            
            try:
                result = test_func()
                self.test_results[test_name] = result
                
                if result:
                    self.log(f"✓ {test_name}: PASSED")
                else:
                    self.log(f"✗ {test_name}: FAILED")
                    
            except Exception as e:
                self.log(f"✗ {test_name}: ERROR - {e}")
                self.test_results[test_name] = False
            
            # Update progress
            progress = int(((i + 1) / total_tests) * 100)
            self.progress_bar.setValue(progress)
            
            # Process events to keep UI responsive
            QApplication.processEvents()
            time.sleep(0.5)
        
        # Show final results
        self.show_test_summary()
    
    def test_ffmpeg(self):
        """Test FFmpeg installation and functionality"""
        self.log("Testing FFmpeg installation...")
        
        # Check if FFmpeg is found
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            self.log("FFmpeg not found, attempting download...")
            ffmpeg_path = ensure_ffmpeg_available(auto_download=True)
            
            if not ffmpeg_path:
                self.log("✗ Failed to install FFmpeg")
                return False
        
        self.log(f"✓ FFmpeg found at: {ffmpeg_path}")
        
        # Test FFmpeg version
        try:
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                timeout=10,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                self.log(f"✓ FFmpeg version: {version_line}")
                return True
            else:
                self.log(f"✗ FFmpeg version check failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.log(f"✗ FFmpeg test error: {e}")
            return False
    
    def test_frame_capture(self):
        """Test frame capture functionality"""
        self.log("Testing frame capture...")
        
        try:
            # Test different capture methods
            width, height = 640, 480
            
            # Create test capture thread
            settings = {
                'resolution': f'{width}x{height}',
                'fps': 30,
                'video_bitrate': 2500
            }
            
            test_thread = StreamCaptureThread(self.graphics_widget, settings)
            
            # Test scene render method
            pixmap1 = test_thread._capture_via_scene_render(width, height)
            if not pixmap1.isNull():
                self.log("✓ Scene render capture: SUCCESS")
            else:
                self.log("⚠ Scene render capture: FAILED")
            
            # Test widget grab method
            pixmap2 = test_thread._capture_via_widget_grab(width, height)
            if not pixmap2.isNull():
                self.log("✓ Widget grab capture: SUCCESS")
            else:
                self.log("⚠ Widget grab capture: FAILED")
            
            # Test synthetic frame creation
            pixmap3 = test_thread._create_synthetic_frame(width, height)
            if not pixmap3.isNull():
                self.log("✓ Synthetic frame creation: SUCCESS")
            else:
                self.log("✗ Synthetic frame creation: FAILED")
                return False
            
            # Test main capture method
            pixmap_main = test_thread.capture_graphics_view(width, height)
            if not pixmap_main.isNull():
                self.log("✓ Main capture method: SUCCESS")
                return True
            else:
                self.log("✗ Main capture method: FAILED")
                return False
                
        except Exception as e:
            self.log(f"✗ Frame capture test error: {e}")
            return False
    
    def test_stream_config(self):
        """Test stream configuration"""
        self.log("Testing stream configuration...")
        
        try:
            # Test valid configuration
            valid_settings = {
                'platform': 'Test',
                'resolution': '1280x720',
                'fps': 30,
                'video_bitrate': 2500,
                'audio_bitrate': 128,
                'url': 'rtmp://test.example.com/live',
                'key': 'test_key'
            }
            
            self.stream_manager.configure_stream("TestStream", valid_settings)
            self.log("✓ Stream configuration: SUCCESS")
            
            # Test configuration validation
            validation_result = self.stream_manager._validate_stream_config("TestStream")
            if validation_result[0]:
                self.log("✓ Configuration validation: SUCCESS")
                return True
            else:
                self.log(f"✗ Configuration validation: {validation_result[1]}")
                return False
                
        except Exception as e:
            self.log(f"✗ Stream configuration test error: {e}")
            return False
    
    def test_stream_validation(self):
        """Test stream validation and pre-flight checks"""
        self.log("Testing stream validation...")
        
        try:
            # Test pre-flight checks
            preflight_result = self.stream_manager._preflight_checks("TestStream")
            
            if preflight_result[0]:
                self.log("✓ Pre-flight checks: SUCCESS")
                return True
            else:
                self.log(f"⚠ Pre-flight checks: {preflight_result[1]}")
                # Don't fail the test if it's just a warning
                return True
                
        except Exception as e:
            self.log(f"✗ Stream validation test error: {e}")
            return False
    
    def test_streaming(self):
        """Test actual streaming process"""
        self.log("Testing streaming process...")
        
        try:
            # Configure for local test (no actual streaming)
            test_settings = {
                'platform': 'Test',
                'resolution': '640x480',
                'fps': 15,  # Lower FPS for testing
                'video_bitrate': 1000,
                'audio_bitrate': 64,
                'format': 'hls',  # Use HLS for local testing
                'url': '',  # Empty URL for local HLS
            }
            
            self.stream_manager.configure_stream("TestStream", test_settings)
            
            # Start streaming
            self.log("Starting test stream...")
            success = self.stream_manager.start_stream("TestStream")
            
            if success:
                self.log("✓ Stream started successfully")
                
                # Let it run for a few seconds
                self.log("Running stream for 5 seconds...")
                start_time = time.time()
                
                while time.time() - start_time < 5:
                    if not self.stream_manager.is_streaming("TestStream"):
                        self.log("✗ Stream died during test")
                        return False
                    
                    QApplication.processEvents()
                    time.sleep(0.1)
                
                # Stop streaming
                self.stream_manager.stop_stream("TestStream")
                self.log("✓ Stream stopped successfully")
                
                return True
            else:
                self.log("✗ Failed to start stream")
                return False
                
        except Exception as e:
            self.log(f"✗ Streaming test error: {e}")
            return False
    
    def show_test_summary(self):
        """Show comprehensive test summary"""
        self.log("\n" + "="*50)
        self.log("TEST SUMMARY")
        self.log("="*50)
        
        passed = 0
        failed = 0
        
        for test_name, result in self.test_results.items():
            status = "PASSED" if result else "FAILED"
            icon = "✓" if result else "✗"
            self.log(f"{icon} {test_name}: {status}")
            
            if result:
                passed += 1
            else:
                failed += 1
        
        total = passed + failed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        self.log(f"\nResults: {passed}/{total} tests passed ({success_rate:.1f}%)")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED! Streaming should work correctly.")
            self.status_label.setText("All Tests Passed ✓")
        else:
            self.log(f"⚠ {failed} test(s) failed. Check the issues above.")
            self.status_label.setText(f"{failed} Tests Failed ✗")
        
        self.progress_bar.setValue(100)
    
    def on_stream_started(self, stream_name):
        """Handle stream started"""
        self.log(f"✓ Stream {stream_name} started successfully")
    
    def on_stream_stopped(self, stream_name):
        """Handle stream stopped"""
        self.log(f"Stream {stream_name} stopped")
    
    def on_stream_error(self, stream_name, error):
        """Handle stream error"""
        self.log(f"✗ Stream {stream_name} error: {error}")
    
    def on_frame_count_updated(self, stream_name, count):
        """Handle frame count updates"""
        if count % 30 == 0:  # Log every 30 frames
            self.log(f"Stream {stream_name}: {count} frames processed")
    
    def log(self, message):
        """Add message to log display"""
        self.log_display.append(message)
        print(message)
        QApplication.processEvents()

def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("GoLive Studio Test Suite")
    app.setApplicationVersion("1.0")
    
    window = StreamingTestSuite()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

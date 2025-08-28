#!/usr/bin/env python3
"""
Test video widgets to ensure they display content properly
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QCamera, QMediaDevices, QMediaCaptureSession
from PyQt6.QtMultimediaWidgets import QVideoWidget

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

class VideoWidgetTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Widget Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create test pattern
        self.create_test_pattern()
        
        # Create video widgets
        self.create_video_widgets(main_layout)
        
        # Create controls
        self.create_controls(main_layout)
        
        # Status label
        self.status_label = QLabel("Ready - Click 'Test Camera' or 'Test Media' to start")
        main_layout.addWidget(self.status_label)
        
        # Initialize media components
        self.camera = None
        self.camera_session = None
        self.media_player = None
        
    def create_test_pattern(self):
        """Create a test pattern pixmap"""
        self.test_pattern = QPixmap(320, 240)
        self.test_pattern.fill(QColor(100, 150, 200))
        
        painter = QPainter(self.test_pattern)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(10, 30, "Test Pattern")
        painter.drawText(10, 60, "Video Widget Test")
        painter.end()
        
    def create_video_widgets(self, main_layout):
        """Create video widgets for testing"""
        # Create horizontal layout for video widgets
        video_layout = QHBoxLayout()
        
        # Input video widget
        input_group = QVBoxLayout()
        input_label = QLabel("Input Video Widget")
        input_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        input_group.addWidget(input_label)
        
        self.input_widget = QVideoWidget()
        self.input_widget.setMinimumSize(320, 240)
        self.input_widget.setStyleSheet("background-color: black; border: 2px solid blue;")
        input_group.addWidget(self.input_widget)
        
        video_layout.addLayout(input_group)
        
        # Media video widget
        media_group = QVBoxLayout()
        media_label = QLabel("Media Video Widget")
        media_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        media_group.addWidget(media_label)
        
        self.media_widget = QVideoWidget()
        self.media_widget.setMinimumSize(320, 240)
        self.media_widget.setStyleSheet("background-color: black; border: 2px solid green;")
        media_group.addWidget(self.media_widget)
        
        video_layout.addLayout(media_group)
        
        # Test pattern display
        pattern_group = QVBoxLayout()
        pattern_label = QLabel("Test Pattern")
        pattern_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pattern_group.addWidget(pattern_label)
        
        self.pattern_label = QLabel()
        self.pattern_label.setPixmap(self.test_pattern)
        self.pattern_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pattern_label.setStyleSheet("border: 2px solid red;")
        pattern_group.addWidget(self.pattern_label)
        
        video_layout.addLayout(pattern_group)
        
        main_layout.addLayout(video_layout)
        
    def create_controls(self, main_layout):
        """Create control buttons"""
        control_layout = QHBoxLayout()
        
        # Test camera button
        self.test_camera_btn = QPushButton("Test Camera")
        self.test_camera_btn.clicked.connect(self.test_camera)
        control_layout.addWidget(self.test_camera_btn)
        
        # Test media button
        self.test_media_btn = QPushButton("Test Media")
        self.test_media_btn.clicked.connect(self.test_media)
        control_layout.addWidget(self.test_media_btn)
        
        # Stop button
        self.stop_btn = QPushButton("Stop All")
        self.stop_btn.clicked.connect(self.stop_all)
        control_layout.addWidget(self.stop_btn)
        
        control_layout.addStretch()
        
        main_layout.addLayout(control_layout)
        
    def test_camera(self):
        """Test camera input"""
        try:
            self.status_label.setText("Testing camera...")
            
            # Get available cameras
            cameras = QMediaDevices.videoInputs()
            if not cameras:
                self.status_label.setText("No cameras found")
                return
            
            # Use first available camera
            camera_device = cameras[0]
            self.status_label.setText(f"Using camera: {camera_device.description()}")
            
            # Create camera and session
            self.camera = QCamera(camera_device)
            self.camera_session = QMediaCaptureSession()
            self.camera_session.setCamera(self.camera)
            self.camera_session.setVideoOutput(self.input_widget)
            
            # Start camera
            self.camera.start()
            
            print(f"Camera started: {camera_device.description()}")
            
        except Exception as e:
            self.status_label.setText(f"Camera error: {str(e)}")
            print(f"Camera error: {e}")
    
    def test_media(self):
        """Test media playback"""
        try:
            self.status_label.setText("Testing media playback...")
            
            # Create a simple test video using FFmpeg (if available)
            from ffmpeg_locator import find_ffmpeg
            
            ffmpeg_path = find_ffmpeg()
            if ffmpeg_path:
                # Create a test video file
                import subprocess
                import tempfile
                import os
                
                # Create temporary test video
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                    test_video_path = tmp_file.name
                
                # Generate test video using FFmpeg
                cmd = [
                    ffmpeg_path,
                    "-y",
                    "-f", "lavfi",
                    "-i", "testsrc=duration=5:size=320x240:rate=1",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    test_video_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and os.path.exists(test_video_path):
                    # Play the test video
                    self.media_player = QMediaPlayer()
                    self.media_player.setVideoOutput(self.media_widget)
                    
                    from PyQt6.QtCore import QUrl
                    self.media_player.setSource(QUrl.fromLocalFile(test_video_path))
                    self.media_player.play()
                    
                    self.status_label.setText("Playing test video...")
                    print(f"Playing test video: {test_video_path}")
                    
                    # Clean up file after playback
                    QTimer.singleShot(6000, lambda: self.cleanup_test_file(test_video_path))
                else:
                    self.status_label.setText("Failed to create test video")
                    print("Failed to create test video")
            else:
                self.status_label.setText("FFmpeg not found - cannot create test video")
                print("FFmpeg not found")
                
        except Exception as e:
            self.status_label.setText(f"Media error: {str(e)}")
            print(f"Media error: {e}")
    
    def cleanup_test_file(self, file_path):
        """Clean up temporary test file"""
        try:
            import os
            if os.path.exists(file_path):
                os.unlink(file_path)
                print(f"Cleaned up test file: {file_path}")
        except Exception as e:
            print(f"Error cleaning up test file: {e}")
    
    def stop_all(self):
        """Stop all video sources"""
        try:
            if self.camera:
                self.camera.stop()
                self.camera = None
                self.camera_session = None
                
            if self.media_player:
                self.media_player.stop()
                self.media_player = None
                
            self.status_label.setText("All video sources stopped")
            print("All video sources stopped")
            
        except Exception as e:
            self.status_label.setText(f"Error stopping: {str(e)}")
            print(f"Error stopping: {e}")
    
    def closeEvent(self, event):
        """Clean up on close"""
        self.stop_all()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = VideoWidgetTestWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

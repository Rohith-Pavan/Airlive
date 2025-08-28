#!/usr/bin/env python3
"""
Test input video widgets
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtMultimedia import QMediaDevices, QCamera, QMediaCaptureSession
from PyQt6.QtMultimediaWidgets import QVideoWidget

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

class InputWidgetTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Input Widget Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black; border: 2px solid red;")
        self.video_widget.setMinimumSize(640, 480)
        layout.addWidget(self.video_widget)
        
        # Create controls
        self.create_controls(layout)
        
        # Status label
        self.status_label = QLabel("Ready - Click 'Test Camera' to test input widget")
        layout.addWidget(self.status_label)
        
        # Initialize camera components
        self.camera = None
        self.session = None
        
    def create_controls(self, layout):
        """Create control buttons"""
        from PyQt6.QtWidgets import QHBoxLayout
        
        control_layout = QHBoxLayout()
        
        # Test camera button
        self.test_camera_btn = QPushButton("Test Camera")
        self.test_camera_btn.clicked.connect(self.test_camera)
        control_layout.addWidget(self.test_camera_btn)
        
        # Stop camera button
        self.stop_camera_btn = QPushButton("Stop Camera")
        self.stop_camera_btn.clicked.connect(self.stop_camera)
        control_layout.addWidget(self.stop_camera_btn)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
    
    def test_camera(self):
        """Test camera input"""
        try:
            self.status_label.setText("Testing camera input...")
            
            # Get available cameras
            cameras = QMediaDevices.videoInputs()
            if not cameras:
                self.status_label.setText("No cameras found")
                print("No cameras found")
                return
            
            print(f"Found {len(cameras)} camera(s):")
            for i, camera in enumerate(cameras):
                print(f"  {i}: {camera.description()}")
            
            # Use first camera
            camera_device = cameras[0]
            print(f"Using camera: {camera_device.description()}")
            
            # Create camera
            self.camera = QCamera(camera_device)
            
            # Create session
            self.session = QMediaCaptureSession()
            
            # Connect video output FIRST
            self.session.setVideoOutput(self.video_widget)
            print("Video output connected to widget")
            
            # Set camera to session
            self.session.setCamera(self.camera)
            print("Camera connected to session")
            
            # Start camera
            self.camera.start()
            print("Camera started")
            
            self.status_label.setText(f"Camera active: {camera_device.description()}")
            
        except Exception as e:
            self.status_label.setText(f"Camera error: {str(e)}")
            print(f"Camera error: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_camera(self):
        """Stop camera"""
        try:
            if self.camera:
                self.camera.stop()
                self.camera = None
            if self.session:
                self.session.setCamera(None)
                self.session.setVideoOutput(None)
                self.session = None
            
            self.status_label.setText("Camera stopped")
            print("Camera stopped")
            
        except Exception as e:
            print(f"Error stopping camera: {e}")

def main():
    app = QApplication(sys.argv)
    window = InputWidgetTestWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

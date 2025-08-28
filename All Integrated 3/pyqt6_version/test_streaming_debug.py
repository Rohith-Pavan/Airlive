#!/usr/bin/env python3
"""
Debug script for testing streaming functionality
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from stream_manager import StreamManager
from graphics_output_widget import GraphicsOutputManager
from ffmpeg_locator import find_ffmpeg, ensure_ffmpeg_available

class StreamingDebugWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Streaming Debug Tool")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create graphics output
        self.graphics_manager = GraphicsOutputManager()
        self.graphics_widget = self.graphics_manager.create_output_widget("debug_output")
        layout.addWidget(self.graphics_widget)
        
        # Create test pattern
        self.create_test_pattern()
        
        # Create stream manager
        self.stream_manager = StreamManager()
        self.stream_manager.register_graphics_view("TestStream", self.graphics_widget)
        
        # Create controls
        self.create_controls(layout)
        
        # Create log display
        self.log_display = QTextEdit()
        self.log_display.setMaximumHeight(150)
        layout.addWidget(self.log_display)
        
        # Connect signals
        self.stream_manager.stream_started.connect(self.on_stream_started)
        self.stream_manager.stream_stopped.connect(self.on_stream_stopped)
        self.stream_manager.stream_error.connect(self.on_stream_error)
        
        # Test FFmpeg
        self.test_ffmpeg()
        
    def create_test_pattern(self):
        """Create a simple test pattern for streaming"""
        # Create a colored rectangle in the graphics scene
        from PyQt6.QtWidgets import QGraphicsRectItem
        from PyQt6.QtGui import QBrush
        
        scene = self.graphics_widget.scene()
        if scene:
            # Create a colored rectangle
            rect_item = QGraphicsRectItem(50, 50, 200, 150)
            rect_item.setBrush(QBrush(QColor(255, 0, 0)))  # Red
            rect_item.setZValue(1)
            scene.addItem(rect_item)
            
            # Create another rectangle
            rect_item2 = QGraphicsRectItem(300, 100, 150, 100)
            rect_item2.setBrush(QBrush(QColor(0, 255, 0)))  # Green
            rect_item2.setZValue(1)
            scene.addItem(rect_item2)
            
            self.log("Test pattern created")
    
    def create_controls(self, layout):
        """Create control buttons"""
        from PyQt6.QtWidgets import QHBoxLayout
        
        control_layout = QHBoxLayout()
        
        # Test FFmpeg button
        self.test_ffmpeg_btn = QPushButton("Test FFmpeg")
        self.test_ffmpeg_btn.clicked.connect(self.test_ffmpeg)
        control_layout.addWidget(self.test_ffmpeg_btn)
        
        # Configure stream button
        self.configure_btn = QPushButton("Configure Stream")
        self.configure_btn.clicked.connect(self.configure_stream)
        control_layout.addWidget(self.configure_btn)
        
        # Start stream button
        self.start_btn = QPushButton("Start Stream")
        self.start_btn.clicked.connect(self.start_stream)
        control_layout.addWidget(self.start_btn)
        
        # Stop stream button
        self.stop_btn = QPushButton("Stop Stream")
        self.stop_btn.clicked.connect(self.stop_stream)
        control_layout.addWidget(self.stop_btn)
        
        # Status label
        self.status_label = QLabel("Ready")
        control_layout.addWidget(self.status_label)
        
        layout.addLayout(control_layout)
    
    def test_ffmpeg(self):
        """Test FFmpeg availability"""
        self.log("Testing FFmpeg availability...")
        
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path:
            self.log(f"✓ FFmpeg found at: {ffmpeg_path}")
            self.status_label.setText("FFmpeg: OK")
        else:
            self.log("✗ FFmpeg not found")
            self.status_label.setText("FFmpeg: NOT FOUND")
            
            # Try to download FFmpeg
            self.log("Attempting to download FFmpeg...")
            downloaded_path = ensure_ffmpeg_available(auto_download=True)
            if downloaded_path:
                self.log(f"✓ FFmpeg downloaded to: {downloaded_path}")
                self.status_label.setText("FFmpeg: DOWNLOADED")
            else:
                self.log("✗ Failed to download FFmpeg")
                self.status_label.setText("FFmpeg: FAILED")
    
    def configure_stream(self):
        """Configure stream settings"""
        from stream_settings_dialog import StreamSettingsDialog
        
        dialog = StreamSettingsDialog("TestStream", self, self.stream_manager)
        dialog.settings_saved.connect(self.on_settings_saved)
        dialog.exec()
    
    def on_settings_saved(self, settings):
        """Handle saved settings"""
        self.log(f"Stream configured: {settings.get('platform', 'Unknown')} - {settings.get('resolution', 'Unknown')}")
        self.stream_manager.configure_stream("TestStream", settings)
    
    def start_stream(self):
        """Start streaming"""
        if "TestStream" not in self.stream_manager.streams:
            self.log("✗ Stream not configured. Please configure first.")
            return
        
        self.log("Starting stream...")
        success = self.stream_manager.start_stream("TestStream")
        if success:
            self.log("✓ Stream start command sent")
        else:
            self.log("✗ Failed to start stream")
    
    def stop_stream(self):
        """Stop streaming"""
        self.log("Stopping stream...")
        self.stream_manager.stop_stream("TestStream")
    
    def on_stream_started(self, stream_name):
        """Handle stream started"""
        self.log(f"✓ Stream {stream_name} started successfully")
        self.status_label.setText(f"Streaming: {stream_name}")
    
    def on_stream_stopped(self, stream_name):
        """Handle stream stopped"""
        self.log(f"Stream {stream_name} stopped")
        self.status_label.setText("Ready")
    
    def on_stream_error(self, stream_name, error):
        """Handle stream error"""
        self.log(f"✗ Stream {stream_name} error: {error}")
        self.status_label.setText(f"Error: {stream_name}")
    
    def log(self, message):
        """Add message to log display"""
        self.log_display.append(f"[{QTimer().remainingTime()}] {message}")
        print(message)

def main():
    app = QApplication(sys.argv)
    window = StreamingDebugWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

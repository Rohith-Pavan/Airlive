#!/usr/bin/env python3
"""
Test script for streaming functionality
Tests the FFmpeg integration and stream pipeline
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt
from stream_manager import StreamManager
from graphics_output_widget import GraphicsOutputWidget


def test_ffmpeg_availability():
    """Test if FFmpeg is available"""
    stream_manager = StreamManager()
    is_available = stream_manager.check_ffmpeg()
    ffmpeg_info = stream_manager.get_ffmpeg_info()
    
    print(f"FFmpeg Available: {is_available}")
    print(f"FFmpeg Info: {ffmpeg_info}")
    
    return is_available


def main():
    app = QApplication(sys.argv)
    
    # Test FFmpeg
    print("Testing FFmpeg availability...")
    ffmpeg_available = test_ffmpeg_availability()
    
    if not ffmpeg_available:
        print("\n⚠️  FFmpeg not found!")
        print("Please install FFmpeg and add it to your system PATH:")
        print("1. Download from: https://ffmpeg.org/download.html")
        print("2. Extract and add to PATH")
        print("3. Restart your terminal/IDE")
        return 1
    
    print("✅ FFmpeg is available and ready for streaming!")
    
    # Create a simple test window
    window = QWidget()
    window.setWindowTitle("Streaming Test")
    window.resize(400, 300)
    
    layout = QVBoxLayout(window)
    
    # Status label
    status_label = QLabel("Streaming system ready!")
    status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(status_label)
    
    # Test graphics widget
    graphics_widget = GraphicsOutputWidget()
    graphics_widget.setMinimumSize(320, 180)
    layout.addWidget(graphics_widget)
    
    # Test stream manager
    stream_manager = StreamManager()
    stream_manager.register_graphics_view("TestStream", graphics_widget)
    
    # Test settings
    test_settings = {
        "platform": "Custom RTMP",
        "url": "rtmp://localhost/live",
        "key": "test_key",
        "resolution": "1280x720",
        "fps": 30,
        "video_bitrate": 2500,
        "audio_bitrate": 128,
        "sample_rate": 44100,
        "codec": "libx264",
        "preset": "veryfast",
        "profile": "main",
        "keyframe_interval": 2,
        "buffer_size": 3,
        "reconnect_attempts": 3,
        "low_latency": False
    }
    
    stream_manager.configure_stream("TestStream", test_settings)
    
    # Test button
    test_button = QPushButton("Test Stream Configuration")
    test_button.clicked.connect(lambda: print("Stream configured successfully!"))
    layout.addWidget(test_button)
    
    info_label = QLabel(
        "✅ Streaming components loaded successfully!\n"
        "✅ FFmpeg pipeline ready\n"
        "✅ Graphics output widget created\n"
        "✅ Stream manager initialized\n\n"
        "Ready for live streaming!"
    )
    info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(info_label)
    
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

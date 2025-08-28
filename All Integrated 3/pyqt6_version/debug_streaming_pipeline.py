#!/usr/bin/env python3
"""
Debug script to investigate the streaming pipeline and FFmpeg command generation
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import Qt

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from stream_manager import StreamManager, StreamCaptureThread
from graphics_output_widget import GraphicsOutputManager
from ffmpeg_locator import find_ffmpeg

class StreamingPipelineDebugger(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Streaming Pipeline Debugger")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create graphics output for testing
        self.graphics_manager = GraphicsOutputManager()
        self.graphics_widget = self.graphics_manager.create_output_widget("debug_output")
        self.graphics_widget.setMinimumHeight(200)
        layout.addWidget(self.graphics_widget)
        
        # Create stream manager
        self.stream_manager = StreamManager()
        self.stream_manager.register_graphics_view("DebugStream", self.graphics_widget)
        
        # Create controls
        self.create_controls(layout)
        
        # Create log display
        self.log_display = QTextEdit()
        layout.addWidget(self.log_display)
        
        # Auto-start debugging
        self.debug_pipeline()
        
    def create_controls(self, layout):
        """Create control buttons"""
        from PyQt6.QtWidgets import QHBoxLayout
        
        control_layout = QHBoxLayout()
        
        self.debug_btn = QPushButton("Debug Pipeline")
        self.debug_btn.clicked.connect(self.debug_pipeline)
        control_layout.addWidget(self.debug_btn)
        
        self.test_ffmpeg_btn = QPushButton("Test FFmpeg Command")
        self.test_ffmpeg_btn.clicked.connect(self.test_ffmpeg_command)
        control_layout.addWidget(self.test_ffmpeg_btn)
        
        layout.addLayout(control_layout)
    
    def debug_pipeline(self):
        """Debug the entire streaming pipeline"""
        self.log("=== STREAMING PIPELINE DEBUG ===\n")
        
        # 1. Check FFmpeg installation
        self.log("1. Checking FFmpeg installation:")
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path:
            self.log(f"   ✓ FFmpeg found at: {ffmpeg_path}")
        else:
            self.log("   ✗ FFmpeg not found!")
            return
        
        # 2. Test typical YouTube Live settings
        self.log("\n2. Testing YouTube Live configuration:")
        youtube_settings = {
            'platform': 'YouTube Live',
            'resolution': '1920x1080',
            'fps': 30,
            'video_bitrate': 4500,
            'audio_bitrate': 128,
            'sample_rate': 44100,
            'format': 'rtmp',
            'url': 'rtmp://a.rtmp.youtube.com/live2',
            'key': 'test-stream-key-placeholder'
        }
        
        self.log(f"   Platform: {youtube_settings['platform']}")
        self.log(f"   Resolution: {youtube_settings['resolution']}")
        self.log(f"   FPS: {youtube_settings['fps']}")
        self.log(f"   Video Bitrate: {youtube_settings['video_bitrate']} kbps")
        self.log(f"   URL: {youtube_settings['url']}")
        self.log(f"   Stream Key: {'*' * len(youtube_settings['key'])}")
        
        # 3. Generate FFmpeg command
        self.log("\n3. Generating FFmpeg command:")
        test_thread = StreamCaptureThread(self.graphics_widget, youtube_settings)
        ffmpeg_cmd = test_thread.build_ffmpeg_command(youtube_settings)
        
        if ffmpeg_cmd:
            self.log("   ✓ FFmpeg command generated successfully:")
            self.log(f"   Command: {' '.join(ffmpeg_cmd)}")
            
            # Analyze the command
            self.analyze_ffmpeg_command(ffmpeg_cmd)
        else:
            self.log("   ✗ Failed to generate FFmpeg command!")
        
        # 4. Test frame capture
        self.log("\n4. Testing frame capture:")
        width, height = 1920, 1080
        pixmap = test_thread.capture_graphics_view(width, height)
        
        if not pixmap.isNull():
            self.log(f"   ✓ Frame capture successful: {pixmap.width()}x{pixmap.height()}")
        else:
            self.log("   ✗ Frame capture failed!")
        
        # 5. Test RGB extraction
        self.log("\n5. Testing RGB data extraction:")
        if not pixmap.isNull():
            image = pixmap.toImage()
            rgb_data = test_thread.extract_rgb_data(image, width, height)
            if rgb_data:
                self.log(f"   ✓ RGB extraction successful: {len(rgb_data)} bytes")
                expected_size = width * height * 3
                if len(rgb_data) == expected_size:
                    self.log(f"   ✓ RGB data size correct: {len(rgb_data)} == {expected_size}")
                else:
                    self.log(f"   ⚠ RGB data size mismatch: {len(rgb_data)} != {expected_size}")
            else:
                self.log("   ✗ RGB extraction failed!")
        
        self.log("\n=== DEBUG COMPLETE ===")
    
    def analyze_ffmpeg_command(self, cmd):
        """Analyze the FFmpeg command for potential issues"""
        self.log("\n   FFmpeg Command Analysis:")
        
        # Check for RTMP URL
        rtmp_found = False
        for i, arg in enumerate(cmd):
            if arg.startswith('rtmp://'):
                rtmp_found = True
                self.log(f"   ✓ RTMP URL found: {arg}")
                
                # Check if it looks like a valid YouTube URL
                if 'youtube.com' in arg or 'rtmp.youtube.com' in arg:
                    self.log("   ✓ YouTube RTMP URL detected")
                else:
                    self.log("   ⚠ Non-YouTube RTMP URL")
                break
        
        if not rtmp_found:
            self.log("   ✗ No RTMP URL found in command!")
        
        # Check for video codec
        if '-c:v' in cmd and 'libx264' in cmd:
            self.log("   ✓ H.264 video codec configured")
        else:
            self.log("   ⚠ Video codec not found or incorrect")
        
        # Check for audio codec
        if '-c:a' in cmd and 'aac' in cmd:
            self.log("   ✓ AAC audio codec configured")
        else:
            self.log("   ⚠ Audio codec not found or incorrect")
        
        # Check for FLV format
        if '-f' in cmd and 'flv' in cmd:
            self.log("   ✓ FLV format configured for RTMP")
        else:
            self.log("   ⚠ FLV format not found")
        
        # Check for low latency settings
        if '-preset' in cmd and 'ultrafast' in cmd:
            self.log("   ✓ Low latency preset configured")
        else:
            self.log("   ⚠ Low latency preset not found")
    
    def test_ffmpeg_command(self):
        """Test the actual FFmpeg command execution"""
        self.log("\n=== TESTING FFMPEG COMMAND EXECUTION ===\n")
        
        # Create a simple test command
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            self.log("✗ FFmpeg not found!")
            return
        
        # Test basic FFmpeg functionality
        import subprocess
        try:
            self.log("Testing FFmpeg version...")
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                self.log(f"✓ {version_line}")
            else:
                self.log(f"✗ FFmpeg version check failed: {result.stderr}")
                return
        except Exception as e:
            self.log(f"✗ FFmpeg test failed: {e}")
            return
        
        # Test RTMP connectivity (without actually streaming)
        self.log("\nTesting RTMP connectivity to YouTube...")
        test_cmd = [
            ffmpeg_path,
            '-f', 'lavfi',
            '-i', 'testsrc=duration=1:size=320x240:rate=1',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-f', 'flv',
            '-t', '1',  # Only 1 second
            'rtmp://a.rtmp.youtube.com/live2/test-connection-check'
        ]
        
        self.log(f"Test command: {' '.join(test_cmd)}")
        
        try:
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.log(f"Return code: {result.returncode}")
            if result.stdout:
                self.log(f"Stdout: {result.stdout[-500:]}")  # Last 500 chars
            if result.stderr:
                self.log(f"Stderr: {result.stderr[-500:]}")  # Last 500 chars
                
                # Analyze stderr for common issues
                stderr_lower = result.stderr.lower()
                if 'connection refused' in stderr_lower:
                    self.log("⚠ Connection refused - check network/firewall")
                elif 'invalid stream key' in stderr_lower or 'unauthorized' in stderr_lower:
                    self.log("⚠ Stream key authentication issue")
                elif 'timeout' in stderr_lower:
                    self.log("⚠ Network timeout - check internet connection")
                elif 'rtmp' in stderr_lower and 'error' in stderr_lower:
                    self.log("⚠ RTMP protocol error")
                
        except subprocess.TimeoutExpired:
            self.log("⚠ Command timed out (this might be normal for connection test)")
        except Exception as e:
            self.log(f"✗ Command execution failed: {e}")
    
    def log(self, message):
        """Add message to log display"""
        self.log_display.append(message)
        print(message)

def main():
    app = QApplication(sys.argv)
    window = StreamingPipelineDebugger()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

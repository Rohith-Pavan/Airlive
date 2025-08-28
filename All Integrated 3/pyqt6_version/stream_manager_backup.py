#!/usr/bin/env python3
"""
Stream Manager for GoLive Studio
Handles streaming configuration and FFmpeg integration
"""

import subprocess
import threading
import time
import os
from pathlib import Path
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QMutex, QRectF
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QImage
from PyQt6.QtCore import Qt
from ffmpeg_locator import locate_ffmpeg, ensure_ffmpeg_available

def find_ffmpeg():
    """Find FFmpeg executable"""
    return locate_ffmpeg()

class StreamCaptureThread(QThread):
    """Thread for capturing frames from QGraphicsScene and feeding to FFmpeg"""
    
    stream_started = pyqtSignal()
    stream_stopped = pyqtSignal()
    stream_error = pyqtSignal(str)
    frame_captured = pyqtSignal(int)  # Frame count
    
    def __init__(self, graphics_view, stream_settings, parent=None):
        super().__init__(parent)
        self.graphics_view = graphics_view
        self.stream_settings = stream_settings
        self.ffmpeg_process = None
        self.is_streaming = False
        self.frame_count = 0
        self.running = False
        
    def run(self):
        """Main streaming loop"""
        try:
            print("Starting FFmpeg process...")
            if not self.start_ffmpeg_process():
                print("Failed to start FFmpeg process")
                return
                
            print("FFmpeg process started successfully")
            self.stream_started.emit()
            
            self.is_streaming = True
            self.running = True
            
            # Calculate frame interval based on FPS
            fps = self.stream_settings.get("fps", 30)
            frame_interval = 1.0 / fps
            
            print("Starting capture loop...")
            while self.running and self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                try:
                    # Record frame start time
                    frame_start = time.time()
                    
                    # Capture frame from graphics view
                    self.capture_and_send_frame()
                    
                    # Maintain consistent frame rate
                    elapsed = time.time() - frame_start
                    sleep_time = max(0, frame_interval - elapsed)
                    if sleep_time > 0:
                        self.msleep(int(sleep_time * 1000))
                        
                except Exception as e:
                    error_msg = f"Error in capture loop: {str(e)}"
                    print(error_msg)
                    self.stream_error.emit(error_msg)
                    break
                    
        except Exception as e:
            error_msg = f"Failed to start FFmpeg: {str(e)}"
            print(f"Stream error: {error_msg}")
            self.stream_error.emit(error_msg)
            
        finally:
            self.cleanup_ffmpeg()
            self.stream_stopped.emit()
            
    def start_ffmpeg_process(self):
        """Start FFmpeg process with proper settings"""
        try:
            # Build FFmpeg command
            cmd = self.build_ffmpeg_command()
            if not cmd:
                self.stream_error.emit("Failed to build FFmpeg command")
                return False
                
            # Try to locate FFmpeg
            ffmpeg_path = locate_ffmpeg()
            if not ffmpeg_path:
                self.stream_error.emit("FFmpeg not found")
                return False
                
            # Replace 'ffmpeg' with actual path
            cmd[0] = ffmpeg_path
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Check if process started successfully
            time.sleep(0.1)
            if self.ffmpeg_process.poll() is not None:
                stdout, stderr = self.ffmpeg_process.communicate()
                error_msg = stderr.decode() if stderr else "FFmpeg failed to start"
                self.stream_error.emit(error_msg)
                return False
            
            return True
            
        except Exception as e:
            self.stream_error.emit(f"Failed to start FFmpeg: {str(e)}")
            return False
            
    def build_ffmpeg_command(self):
        """Build FFmpeg command based on stream settings"""
        settings = self.stream_settings
        
        # Validate required settings
        if not settings.get("url") or not settings.get("key"):
            return None
            
        # Parse resolution
        resolution = settings.get("resolution", "1920x1080")
        try:
            width, height = map(int, resolution.split("x"))
        except:
            width, height = 1920, 1080
        
        # Base command
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo", 
            "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}",
            "-r", str(settings.get("fps", 30)),
            "-i", "-",
        ]
        
        # Video encoding
        cmd.extend([
            "-c:v", settings.get("codec", "libx264"),
            "-preset", settings.get("preset", "veryfast"),
            "-profile:v", settings.get("profile", "main"),
            "-pix_fmt", "yuv420p",
            "-b:v", f"{settings.get('video_bitrate', 2500)}k",
            "-maxrate", f"{settings.get('video_bitrate', 2500)}k",
            "-bufsize", f"{settings.get('video_bitrate', 2500) * 2}k",
            "-g", str(settings.get("fps", 30) * 2),
        ])
        
        # Audio (silent audio track)
        cmd.extend([
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:a", "aac",
            "-b:a", f"{settings.get('audio_bitrate', 128)}k",
        ])
        
        # Output format
        cmd.extend(["-f", "flv"])
        
        # Stream URL
        stream_url = settings.get("url", "")
        stream_key = settings.get("key", "")
        full_url = f"{stream_url.rstrip('/')}/{stream_key}"
        cmd.append(full_url)
        
        return cmd
        
    def capture_and_send_frame(self):
        """Capture frame from graphics view and send to FFmpeg"""
        if not self.is_streaming or not self.running:
            return
            
        if not self.ffmpeg_process or self.ffmpeg_process.poll() is not None:
            self.running = False
            return
            
        try:
            # Capture the graphics view
            scene = self.graphics_view.scene()
            if not scene:
                return
                
            scene_rect = scene.sceneRect()
            if scene_rect.isEmpty():
                return
                
            # Get target resolution
            resolution = self.stream_settings.get("resolution", "1920x1080")
            width, height = map(int, resolution.split("x"))
            
            # Create pixmap
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.black)
            
            painter = QPainter(pixmap)
            scene.render(painter, QRectF(0, 0, width, height), scene_rect)
            painter.end()
            
            # Convert to image
            image = pixmap.toImage()
            if image.isNull():
                return
                
            # Convert to RGB format
            rgb_image = image.convertToFormat(QImage.Format.Format_RGB888)
            if rgb_image.isNull():
                return
                
            # Get raw data
            total_bytes = width * height * 3
            try:
                bits = rgb_image.bits()
                if hasattr(bits, 'asstring'):
                    raw_data = bits.asstring(total_bytes)
                else:
                    raw_data = bytes(bits)[:total_bytes]
            except:
                return
            
            # Send to FFmpeg
            if self.ffmpeg_process and self.ffmpeg_process.stdin:
                try:
                    self.ffmpeg_process.stdin.write(raw_data)
                    self.ffmpeg_process.stdin.flush()
                    self.frame_count += 1
                    self.frame_captured.emit(self.frame_count)
                except (BrokenPipeError, OSError) as e:
                    print(f"FFmpeg pipe error: {e}")
                    self.running = False
                    self.is_streaming = False
                except Exception as e:
                    print(f"Error writing to FFmpeg: {e}")
                    self.running = False
                    
        except Exception as e:
            print(f"Error capturing frame: {e}")
            
    def cleanup_ffmpeg(self):
        """Clean up FFmpeg process"""
        try:
            if self.ffmpeg_process:
                if self.ffmpeg_process.stdin:
                    try:
                        self.ffmpeg_process.stdin.close()
                    except:
                        pass
                
                try:
                    self.ffmpeg_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.ffmpeg_process.terminate()
                    try:
                        self.ffmpeg_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.ffmpeg_process.kill()
                
                self.ffmpeg_process = None
        except Exception as e:
            print(f"Error cleaning up FFmpeg: {e}")
    
    def stop_streaming(self):
        """Stop streaming"""
        self.running = False
        self.is_streaming = False


class StreamManager(QObject):
    """Manages multiple streams and their configurations"""
    
    stream_started = pyqtSignal(str)  # stream_name
    stream_stopped = pyqtSignal(str)  # stream_name  
    stream_error = pyqtSignal(str, str)  # stream_name, error_message
    frame_count_updated = pyqtSignal(str, int)  # stream_name, frame_count
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.streams = {}  # stream_name -> settings dict
        self.capture_threads = {}  # stream_name -> StreamCaptureThread
        self.graphics_views = {}  # stream_name -> QGraphicsView
        
    def register_graphics_view(self, stream_name, graphics_view):
        """Register a graphics view for streaming"""
        self.graphics_views[stream_name] = graphics_view
        
    def configure_stream(self, stream_name, settings):
        """Configure stream settings"""
        self.streams[stream_name] = settings
        print(f"Stream {stream_name} configured: {settings.get('platform', 'Unknown')} - {settings.get('resolution', 'Unknown')}")
        
    def start_stream(self, stream_name):
        """Start streaming for the specified stream"""
        if stream_name not in self.streams:
            self.stream_error.emit(stream_name, "Stream not configured")
            return False
            
        if stream_name in self.capture_threads:
            self.stream_error.emit(stream_name, "Stream already running")
            return False
            
        if stream_name not in self.graphics_views:
            self.stream_error.emit(stream_name, "No graphics view registered")
            return False
            
        # Check FFmpeg availability
        if not self.check_ffmpeg():
            self.stream_error.emit(stream_name, "FFmpeg not found")
            return False
            
        try:
            # Create and start capture thread
            graphics_view = self.graphics_views[stream_name]
            settings = self.streams[stream_name]
            
            capture_thread = StreamCaptureThread(graphics_view, settings)
            capture_thread.stream_started.connect(lambda: self.stream_started.emit(stream_name))
            capture_thread.stream_stopped.connect(lambda: self._on_stream_stopped(stream_name))
            capture_thread.stream_error.connect(lambda msg: self._on_stream_error(stream_name, msg))
            capture_thread.frame_captured.connect(lambda count: self.frame_count_updated.emit(stream_name, count))
            
            self.capture_threads[stream_name] = capture_thread
            capture_thread.start()
            
            # Wait briefly to verify the stream actually starts
            time.sleep(0.5)
            
            # Check if the stream is actually running
            if not self.is_streaming(stream_name):
                print(f"Stream {stream_name} failed to start properly")
                self._on_stream_stopped(stream_name)
                return False
            
            return True
            
        except Exception as e:
            self.stream_error.emit(stream_name, f"Failed to start stream: {str(e)}")
            return False
            
    def stop_stream(self, stream_name):
        """Stop streaming for the specified stream"""
        if stream_name not in self.capture_threads:
            return False
            
        try:
            capture_thread = self.capture_threads[stream_name]
            capture_thread.stop_streaming()
            
            # Wait for thread to finish
            if not capture_thread.wait(3000):
                capture_thread.terminate()
                capture_thread.wait(1000)
            
            return True
            
        except Exception as e:
            self.stream_error.emit(stream_name, f"Error stopping stream: {str(e)}")
            return False
            
    def _on_stream_stopped(self, stream_name):
        """Handle stream stopped internally"""
        if stream_name in self.capture_threads:
            del self.capture_threads[stream_name]
        self.stream_stopped.emit(stream_name)
        
    def _on_stream_error(self, stream_name, error_msg):
        """Handle stream error internally"""
        print(f"Stream {stream_name} error: {error_msg}")
        if stream_name in self.capture_threads:
            try:
                self.capture_threads[stream_name].stop_streaming()
            except:
                pass
            del self.capture_threads[stream_name]
        self.stream_error.emit(stream_name, error_msg)
        
    def is_streaming(self, stream_name):
        """Check if a stream is currently active"""
        if stream_name not in self.capture_threads:
            return False
            
        thread = self.capture_threads[stream_name]
        if not thread.isRunning():
            del self.capture_threads[stream_name]
            return False
            
        return True
        
    def check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            ffmpeg_path = locate_ffmpeg()
            return ffmpeg_path is not None
        except:
            return False
            
    def stop_all_streams(self):
        """Stop all active streams"""
        stream_names = list(self.capture_threads.keys())
        for stream_name in stream_names:
            self.stop_stream(stream_name)


class StreamControlWidget(QObject):
    """Widget controller for stream buttons and status"""
    
    def __init__(self, stream_name, stream_manager, parent_window=None):
        super().__init__(parent_window)
        self.stream_name = stream_name
        self.stream_manager = stream_manager
        self.parent_window = parent_window
        self.settings_button = None
        self.stream_button = None
        self.is_streaming = False
        
        # Connect to stream manager signals
        self.stream_manager.stream_started.connect(self.on_stream_started)
        self.stream_manager.stream_stopped.connect(self.on_stream_stopped)
        self.stream_manager.stream_error.connect(self.on_stream_error)
        
    def set_buttons(self, settings_button, stream_button):
        """Set the UI buttons for this stream"""
        self.settings_button = settings_button
        self.stream_button = stream_button
        
        # Connect button signals
        if self.settings_button:
            self.settings_button.clicked.connect(self.open_settings_dialog)
            
        if self.stream_button:
            self.stream_button.clicked.connect(self.toggle_streaming)
            
        self.update_button_state()
        
    def open_settings_dialog(self):
        """Open stream settings dialog"""
        from stream_settings_dialog import StreamSettingsDialog
        
        dialog = StreamSettingsDialog(self.stream_name, self.parent_window, self.stream_manager)
        dialog.settings_saved.connect(self.on_settings_saved)
        dialog.exec()
        
    def on_settings_saved(self, settings):
        """Handle saved settings from dialog"""
        self.stream_manager.configure_stream(self.stream_name, settings)
        
    def toggle_streaming(self):
        """Toggle streaming on/off"""
        if self.is_streaming:
            self.stop_streaming()
        else:
            self.start_streaming()
            
    def start_streaming(self):
        """Start streaming"""
        try:
            if self.stream_name not in self.stream_manager.streams:
                print(f"{self.stream_name} not configured. Opening settings dialog...")
                self.open_settings_dialog()
                return
                
            success = self.stream_manager.start_stream(self.stream_name)
            if not success:
                print(f"Failed to start {self.stream_name}")
                self.is_streaming = False
                self.update_button_state()
        except Exception as e:
            print(f"Error starting {self.stream_name}: {e}")
            self.is_streaming = False
            self.update_button_state()
            
    def stop_streaming(self):
        """Stop streaming"""
        self.stream_manager.stop_stream(self.stream_name)
        
    def on_stream_started(self, stream_name):
        """Handle stream started signal"""
        if stream_name == self.stream_name:
            self.is_streaming = True
            self.update_button_state()
            print(f"{self.stream_name} started successfully")
            
    def on_stream_stopped(self, stream_name):
        """Handle stream stopped signal"""
        if stream_name == self.stream_name:
            self.is_streaming = False
            self.update_button_state()
            print(f"{self.stream_name} stopped")
            
    def on_stream_error(self, stream_name, error_message):
        """Handle stream error signal"""
        if stream_name == self.stream_name:
            self.is_streaming = False
            self.update_button_state()
            print(f"{self.stream_name} error: {error_message}")
            
    def update_button_state(self):
        """Update button icons and states"""
        if not self.stream_button:
            return
            
        try:
            from PyQt6.QtGui import QIcon
            icon_path = Path(__file__).parent / "icons"
            
            if self.is_streaming:
                # Show pause icon when streaming
                stop_icon = QIcon(str(icon_path / "Pause.png"))
                self.stream_button.setIcon(stop_icon)
                self.stream_button.setToolTip(f"Stop {self.stream_name}")
                self.stream_button.setStyleSheet("border-radius: 5px; background-color: #ff4444;")
            else:
                # Show stream icon when not streaming
                stream_icon = QIcon(str(icon_path / "Stream.png"))
                self.stream_button.setIcon(stream_icon)
                self.stream_button.setToolTip(f"Start {self.stream_name}")
                self.stream_button.setStyleSheet("border-radius: 5px; background-color: #404040;")
                
        except Exception as e:
            print(f"Error updating button state: {e}")

#!/usr/bin/env python3
"""
New Stream Manager for GoLive Studio - Complete Rewrite
Robust streaming implementation with comprehensive error handling and validation
"""

import subprocess
import threading
import time
import os
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer, QMutex, QMutexLocker
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QImage, QColor
from PyQt6.QtCore import Qt
from ffmpeg_locator import find_ffmpeg, ensure_ffmpeg_available


class StreamState:
    """Stream state enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class StreamCaptureWorker(QThread):
    """Robust streaming worker thread with comprehensive error handling"""
    
    # Signals
    stream_started = pyqtSignal()
    stream_stopped = pyqtSignal()
    stream_error = pyqtSignal(str)
    frame_captured = pyqtSignal(int)
    status_update = pyqtSignal(str)
    
    def __init__(self, stream_name: str, graphics_view, settings: Dict[str, Any]):
        super().__init__()
        self.stream_name = stream_name
        self.graphics_view = graphics_view
        self.settings = settings.copy()
        
        # Thread control
        self._running = False
        self._should_stop = False
        self._mutex = QMutex()
        
        # FFmpeg process
        self._ffmpeg_process = None
        self._ffmpeg_path = None
        
        # Stream metrics
        self._frame_count = 0
        self._start_time = 0
        self._last_frame_time = 0
        
        # Validation
        self._validate_settings()
        
    def _validate_settings(self) -> None:
        """Validate stream settings before starting"""
        required_keys = ['url', 'key', 'resolution', 'fps', 'video_bitrate']
        for key in required_keys:
            if key not in self.settings or not self.settings[key]:
                raise ValueError(f"Missing required setting: {key}")
        
        # Validate resolution format
        try:
            width, height = map(int, self.settings['resolution'].split('x'))
            if width <= 0 or height <= 0 or width > 3840 or height > 2160:
                raise ValueError(f"Invalid resolution: {self.settings['resolution']}")
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid resolution format: {self.settings['resolution']}")
        
        # Validate FPS
        fps = self.settings.get('fps', 30)
        if not isinstance(fps, int) or fps <= 0 or fps > 60:
            raise ValueError(f"Invalid FPS: {fps}")
        
        # Validate bitrate
        bitrate = self.settings.get('video_bitrate', 2500)
        if not isinstance(bitrate, int) or bitrate < 100 or bitrate > 50000:
            raise ValueError(f"Invalid bitrate: {bitrate}")
        
        # Validate URL format
        url = self.settings.get('url', '')
        if not (url.startswith('rtmp://') or url.startswith('rtmps://') or url.startswith('srt://')):
            raise ValueError(f"Invalid URL format: {url}")
    
    def run(self) -> None:
        """Main streaming loop with robust error handling"""
        try:
            with QMutexLocker(self._mutex):
                self._running = True
                self._should_stop = False
            
            self.status_update.emit("Initializing FFmpeg...")
            
            # Initialize FFmpeg
            if not self._initialize_ffmpeg():
                self.stream_error.emit("Failed to initialize FFmpeg")
                return
            
            self.status_update.emit("Starting FFmpeg process...")
            
            # Start FFmpeg process
            if not self._start_ffmpeg_process():
                self.stream_error.emit("Failed to start FFmpeg process")
                return
            
            self.status_update.emit("FFmpeg started, beginning frame capture...")
            
            # Mark as started
            self._start_time = time.time()
            self.stream_started.emit()
            
            # Main capture loop
            self._capture_loop()
            
        except Exception as e:
            self.stream_error.emit(f"Streaming error: {str(e)}")
        finally:
            self._cleanup()
            with QMutexLocker(self._mutex):
                self._running = False
            self.stream_stopped.emit()
    
    def _initialize_ffmpeg(self) -> bool:
        """Initialize FFmpeg with comprehensive checks"""
        try:
            # Find or download FFmpeg
            self._ffmpeg_path = find_ffmpeg()
            if not self._ffmpeg_path:
                self.status_update.emit("FFmpeg not found, attempting download...")
                self._ffmpeg_path = ensure_ffmpeg_available(auto_download=True)
                
            if not self._ffmpeg_path:
                return False
            
            # Test FFmpeg functionality
            if not self._test_ffmpeg():
                return False
            
            self.status_update.emit(f"FFmpeg initialized: {self._ffmpeg_path}")
            return True
            
        except Exception as e:
            self.status_update.emit(f"FFmpeg initialization error: {e}")
            return False
    
    def _test_ffmpeg(self) -> bool:
        """Test FFmpeg with a basic command"""
        try:
            result = subprocess.run(
                [self._ffmpeg_path, '-version'],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _start_ffmpeg_process(self) -> bool:
        """Start FFmpeg process with robust error handling"""
        try:
            cmd = self._build_ffmpeg_command()
            if not cmd:
                return False
            
            self.status_update.emit(f"Starting FFmpeg: {' '.join(cmd[:5])}...")
            
            # Start process
            self._ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Wait for process to initialize
            time.sleep(1.0)
            
            # Check if process started successfully
            if self._ffmpeg_process.poll() is not None:
                # Process died, get error info
                try:
                    stderr_data = self._ffmpeg_process.stderr.read(4096)
                    if stderr_data:
                        error_msg = stderr_data.decode('utf-8', errors='ignore')
                        self.status_update.emit(f"FFmpeg error: {error_msg}")
                except Exception:
                    pass
                return False
            
            return True
            
        except Exception as e:
            self.status_update.emit(f"Error starting FFmpeg: {e}")
            return False
    
    def _build_ffmpeg_command(self) -> Optional[list]:
        """Build FFmpeg command with optimized settings"""
        try:
            width, height = map(int, self.settings['resolution'].split('x'))
            fps = int(self.settings['fps'])
            video_bitrate = int(self.settings['video_bitrate'])
            audio_bitrate = int(self.settings.get('audio_bitrate', 128))
            
            # Build target URL
            url = self.settings['url'].rstrip('/')
            key = self.settings['key']
            target = f"{url}/{key}" if key else url
            
            cmd = [
                self._ffmpeg_path,
                '-y',  # Overwrite output files
                '-loglevel', 'error',  # Reduce log verbosity
                
                # Input: Raw video from stdin
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-s', f'{width}x{height}',
                '-r', str(fps),
                '-i', '-',
                
                # Input: Silent audio
                '-f', 'lavfi',
                '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',
                
                # Video encoding
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-profile:v', 'baseline',
                '-level', '3.0',
                '-pix_fmt', 'yuv420p',
                '-b:v', f'{video_bitrate}k',
                '-maxrate', f'{video_bitrate}k',
                '-bufsize', f'{video_bitrate * 2}k',
                '-g', str(fps),
                '-keyint_min', str(fps),
                '-sc_threshold', '0',
                
                # Audio encoding
                '-c:a', 'aac',
                '-b:a', f'{audio_bitrate}k',
                '-ar', '44100',
                '-ac', '2',
                
                # Output format
                '-f', 'flv',
                '-flvflags', 'no_duration_filesize',
                target
            ]
            
            return cmd
            
        except Exception as e:
            self.status_update.emit(f"Error building FFmpeg command: {e}")
            return None
    
    def _capture_loop(self) -> None:
        """Main frame capture loop with timing control"""
        fps = int(self.settings['fps'])
        frame_interval = 1.0 / fps
        
        while True:
            with QMutexLocker(self._mutex):
                if self._should_stop:
                    break
            
            start_time = time.time()
            
            # Capture and send frame
            if not self._capture_and_send_frame():
                self.status_update.emit("Frame capture failed")
                break
            
            # Check FFmpeg process health
            if self._ffmpeg_process and self._ffmpeg_process.poll() is not None:
                self.status_update.emit("FFmpeg process terminated unexpectedly")
                break
            
            # Frame timing
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _capture_and_send_frame(self) -> bool:
        """Capture frame from graphics view and send to FFmpeg"""
        try:
            # Get frame dimensions
            width, height = map(int, self.settings['resolution'].split('x'))
            
            # Capture frame
            pixmap = self._capture_graphics_view(width, height)
            if pixmap.isNull():
                # Use fallback pattern
                pixmap = self._create_fallback_frame(width, height)
            
            # Convert to RGB data
            rgb_data = self._pixmap_to_rgb(pixmap, width, height)
            if not rgb_data:
                return False
            
            # Send to FFmpeg
            if not self._send_frame_to_ffmpeg(rgb_data):
                return False
            
            self._frame_count += 1
            if self._frame_count % 30 == 0:  # Log every 30 frames
                self.frame_captured.emit(self._frame_count)
            
            return True
            
        except Exception as e:
            self.status_update.emit(f"Frame capture error: {e}")
            return False
    
    def _capture_graphics_view(self, width: int, height: int) -> QPixmap:
        """Capture graphics view with multiple fallback methods"""
        try:
            if not self.graphics_view:
                return QPixmap()
            
            # Method 1: Scene render
            scene = self.graphics_view.scene()
            if scene:
                pixmap = QPixmap(width, height)
                pixmap.fill(Qt.GlobalColor.black)
                
                painter = QPainter(pixmap)
                scene.render(painter)
                painter.end()
                
                if not pixmap.isNull():
                    return pixmap.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio, 
                                       Qt.TransformationMode.SmoothTransformation)
            
            # Method 2: Widget grab
            grabbed = self.graphics_view.grab()
            if not grabbed.isNull():
                return grabbed.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
            
            return QPixmap()
            
        except Exception:
            return QPixmap()
    
    def _create_fallback_frame(self, width: int, height: int) -> QPixmap:
        """Create a fallback frame with stream info"""
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.black)
        
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        
        # Draw stream info
        font = painter.font()
        font.setPointSize(max(16, width // 60))
        font.setBold(True)
        painter.setFont(font)
        
        text = f"LIVE - {self.stream_name}"
        painter.drawText(20, 50, text)
        
        # Frame counter
        painter.drawText(20, height - 60, f"Frame: {self._frame_count}")
        
        # Timestamp
        elapsed = time.time() - self._start_time if self._start_time else 0
        painter.drawText(20, height - 30, f"Time: {elapsed:.1f}s")
        
        painter.end()
        return pixmap
    
    def _pixmap_to_rgb(self, pixmap: QPixmap, width: int, height: int) -> Optional[bytes]:
        """Convert pixmap to RGB24 data for FFmpeg"""
        try:
            # Convert to image
            image = pixmap.toImage()
            if image.isNull():
                return None
            
            # Ensure correct format and size
            if image.format() != QImage.Format.Format_RGB888:
                image = image.convertToFormat(QImage.Format.Format_RGB888)
            
            if image.width() != width or image.height() != height:
                image = image.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            
            # Extract RGB data
            bits = image.bits()
            if not bits:
                return None
            
            bytes_per_line = image.bytesPerLine()
            total_bytes = bytes_per_line * height
            
            try:
                bits.setsize(total_bytes)
            except AttributeError:
                pass  # Some PyQt builds don't need this
            
            buffer = bytes(bits)
            
            # Remove padding if necessary
            if bytes_per_line == width * 3:
                return buffer
            else:
                # Remove line padding
                rgb_data = bytearray()
                for y in range(height):
                    line_start = y * bytes_per_line
                    line_data = buffer[line_start:line_start + width * 3]
                    rgb_data.extend(line_data)
                return bytes(rgb_data)
                
        except Exception as e:
            self.status_update.emit(f"RGB conversion error: {e}")
            return None
    
    def _send_frame_to_ffmpeg(self, rgb_data: bytes) -> bool:
        """Send frame data to FFmpeg process"""
        try:
            if not self._ffmpeg_process or not self._ffmpeg_process.stdin:
                return False
            
            # Check if process is still alive
            if self._ffmpeg_process.poll() is not None:
                return False
            
            # Write data
            self._ffmpeg_process.stdin.write(rgb_data)
            self._ffmpeg_process.stdin.flush()
            
            return True
            
        except (BrokenPipeError, OSError):
            return False
        except Exception as e:
            self.status_update.emit(f"Frame send error: {e}")
            return False
    
    def stop_streaming(self) -> None:
        """Stop the streaming thread"""
        with QMutexLocker(self._mutex):
            self._should_stop = True
    
    def is_running(self) -> bool:
        """Check if streaming is running"""
        with QMutexLocker(self._mutex):
            return self._running and not self._should_stop
    
    def _cleanup(self) -> None:
        """Clean up resources"""
        try:
            if self._ffmpeg_process:
                # Close stdin
                if self._ffmpeg_process.stdin:
                    try:
                        self._ffmpeg_process.stdin.close()
                    except Exception:
                        pass
                
                # Terminate process
                try:
                    self._ffmpeg_process.terminate()
                    self._ffmpeg_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._ffmpeg_process.kill()
                    self._ffmpeg_process.wait(timeout=2)
                except Exception:
                    pass
                
                self._ffmpeg_process = None
                
        except Exception as e:
            self.status_update.emit(f"Cleanup error: {e}")


class NewStreamManager(QObject):
    """New stream manager with robust error handling and validation"""
    
    # Signals
    stream_started = pyqtSignal(str)
    stream_stopped = pyqtSignal(str)
    stream_error = pyqtSignal(str, str)
    status_update = pyqtSignal(str, str)
    frame_count_updated = pyqtSignal(str, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._streams: Dict[str, Dict[str, Any]] = {}
        self._workers: Dict[str, StreamCaptureWorker] = {}
        self._graphics_views: Dict[str, Any] = {}
        self._stream_states: Dict[str, str] = {}
        
        # Health check timer
        self._health_timer = QTimer()
        self._health_timer.timeout.connect(self._check_stream_health)
        self._health_timer.start(5000)  # Check every 5 seconds
    
    def register_graphics_view(self, stream_name: str, graphics_view) -> None:
        """Register a graphics view for streaming"""
        self._graphics_views[stream_name] = graphics_view
        self._stream_states[stream_name] = StreamState.STOPPED
        print(f"Registered graphics view for {stream_name}")
    
    def configure_stream(self, stream_name: str, settings: Dict[str, Any]) -> bool:
        """Configure stream with validation"""
        try:
            # Check if this is HDMI streaming
            if settings.get('is_hdmi', False):
                # Validate HDMI settings
                if settings.get('hdmi_display_index', -1) == -1:
                    self.stream_error.emit(stream_name, "Invalid HDMI display selection")
                    return False
                
                # HDMI streams don't need URL/key validation
                required_keys = ['resolution', 'fps', 'video_bitrate']
            else:
                # Validate regular streaming settings
                required_keys = ['url', 'key', 'resolution', 'fps', 'video_bitrate']
            
            for key in required_keys:
                if key not in settings or not settings[key]:
                    self.stream_error.emit(stream_name, f"Missing required setting: {key}")
                    return False
            
            # Store settings
            self._streams[stream_name] = settings.copy()
            
            if settings.get('is_hdmi', False):
                print(f"Configured HDMI {stream_name}: Display {settings.get('hdmi_display_index')} - {settings.get('resolution')} @ {settings.get('fps')}fps")
            else:
                print(f"Configured {stream_name}: {settings.get('resolution')} @ {settings.get('fps')}fps")
            return True
            
        except Exception as e:
            self.stream_error.emit(stream_name, f"Configuration error: {e}")
            return False
    
    def start_stream(self, stream_name: str) -> bool:
        """Start streaming with comprehensive validation"""
        try:
            # Check if already running
            if self.is_streaming(stream_name):
                return True
            
            # Validate prerequisites
            if stream_name not in self._streams:
                self.stream_error.emit(stream_name, "Stream not configured")
                return False
            
            if stream_name not in self._graphics_views:
                self.stream_error.emit(stream_name, "Graphics view not registered")
                return False
            
            # Stop existing worker if any
            self._stop_worker(stream_name)
            
            settings = self._streams[stream_name]
            
            # Handle HDMI streaming
            if settings.get('is_hdmi', False):
                return self._start_hdmi_stream(stream_name, settings)
            else:
                return self._start_regular_stream(stream_name, settings)
            
        except Exception as e:
            self.stream_error.emit(stream_name, f"Failed to start stream: {e}")
            return False
    
    def _start_regular_stream(self, stream_name: str, settings: Dict[str, Any]) -> bool:
        """Start regular streaming"""
        try:
            graphics_view = self._graphics_views[stream_name]
            
            worker = StreamCaptureWorker(stream_name, graphics_view, settings)
            
            # Connect signals
            worker.stream_started.connect(lambda: self._on_stream_started(stream_name))
            worker.stream_stopped.connect(lambda: self._on_stream_stopped(stream_name))
            worker.stream_error.connect(lambda msg: self._on_stream_error(stream_name, msg))
            worker.status_update.connect(lambda msg: self._on_status_update(stream_name, msg))
            worker.frame_captured.connect(lambda count: self.frame_count_updated.emit(stream_name, count))
            
            # Start worker
            self._workers[stream_name] = worker
            self._stream_states[stream_name] = StreamState.STARTING
            worker.start()
            
            return True
            
        except Exception as e:
            self.stream_error.emit(stream_name, f"Failed to start regular stream: {e}")
            return False
    
    def _start_hdmi_stream(self, stream_name: str, settings: Dict[str, Any]) -> bool:
        """Start HDMI streaming"""
        try:
            from hdmi_stream_manager import HDMIStreamManager
            
            graphics_view = self._graphics_views[stream_name]
            
            # Create HDMI stream manager
            hdmi_manager = HDMIStreamManager()
            
            # Configure HDMI stream first
            hdmi_stream_name = f"hdmi_{stream_name}"
            if not hdmi_manager.configure_hdmi_stream(hdmi_stream_name, settings):
                self.stream_error.emit(stream_name, "Failed to configure HDMI stream")
                return False
            
            # Start HDMI streaming
            success = hdmi_manager.start_hdmi_stream(hdmi_stream_name, graphics_view)
            
            if success:
                # Store HDMI manager for cleanup
                self._workers[stream_name] = hdmi_manager
                self._stream_states[stream_name] = StreamState.RUNNING
                self._on_stream_started(stream_name)
                return True
            else:
                self.stream_error.emit(stream_name, "Failed to start HDMI stream")
                return False
                
        except Exception as e:
            self.stream_error.emit(stream_name, f"Failed to start HDMI stream: {e}")
            return False
    
    def stop_stream(self, stream_name: str) -> bool:
        """Stop streaming"""
        try:
            if not self.is_streaming(stream_name):
                return True
            
            self._stream_states[stream_name] = StreamState.STOPPING
            self._stop_worker(stream_name)
            return True
            
        except Exception as e:
            self.stream_error.emit(stream_name, f"Error stopping stream: {e}")
            return False
    
    def is_streaming(self, stream_name: str) -> bool:
        """Check if stream is active"""
        state = self._stream_states.get(stream_name, StreamState.STOPPED)
        return state in [StreamState.STARTING, StreamState.RUNNING]
    
    def get_stream_state(self, stream_name: str) -> str:
        """Get current stream state"""
        return self._stream_states.get(stream_name, StreamState.STOPPED)
    
    def stop_all_streams(self) -> None:
        """Stop all active streams"""
        for stream_name in list(self._workers.keys()):
            self.stop_stream(stream_name)
    
    def _stop_worker(self, stream_name: str) -> None:
        """Stop and cleanup worker thread"""
        if stream_name in self._workers:
            worker = self._workers[stream_name]
            try:
                # Check if this is an HDMI stream manager
                if hasattr(worker, 'stop_hdmi_stream'):
                    # HDMI stream manager - use the hdmi stream name
                    hdmi_stream_name = f"hdmi_{stream_name}"
                    worker.stop_hdmi_stream(hdmi_stream_name)
                else:
                    # Regular stream worker
                    worker.stop_streaming()
                    if hasattr(worker, 'wait'):
                        if not worker.wait(5000):  # Wait 5 seconds
                            worker.terminate()
                            worker.wait(2000)  # Wait 2 more seconds
            except Exception as e:
                print(f"Error stopping worker for {stream_name}: {e}")
            finally:
                del self._workers[stream_name]
    
    def _on_stream_started(self, stream_name: str) -> None:
        """Handle stream started"""
        self._stream_states[stream_name] = StreamState.RUNNING
        self.stream_started.emit(stream_name)
        print(f"Stream {stream_name} started successfully")
    
    def _on_stream_stopped(self, stream_name: str) -> None:
        """Handle stream stopped"""
        self._stream_states[stream_name] = StreamState.STOPPED
        if stream_name in self._workers:
            del self._workers[stream_name]
        self.stream_stopped.emit(stream_name)
        print(f"Stream {stream_name} stopped")
    
    def _on_stream_error(self, stream_name: str, error_msg: str) -> None:
        """Handle stream error"""
        self._stream_states[stream_name] = StreamState.ERROR
        self._stop_worker(stream_name)
        self.stream_error.emit(stream_name, error_msg)
        print(f"Stream {stream_name} error: {error_msg}")
    
    def _on_status_update(self, stream_name: str, status: str) -> None:
        """Handle status update"""
        self.status_update.emit(stream_name, status)
        print(f"{stream_name}: {status}")
    
    def _check_stream_health(self) -> None:
        """Periodic health check for streams"""
        for stream_name, worker in list(self._workers.items()):
            try:
                # Check if this is a regular stream worker (has isRunning method)
                if hasattr(worker, 'isRunning'):
                    if not worker.isRunning() and self._stream_states.get(stream_name) == StreamState.RUNNING:
                        self._on_stream_error(stream_name, "Worker thread died unexpectedly")
                # For HDMI stream managers, we assume they're running if they're in the workers dict
                # The HDMI manager will emit signals if there are issues
            except Exception as e:
                print(f"Health check error for {stream_name}: {e}")


class NewStreamControlWidget(QObject):
    """New stream control widget with improved UI feedback"""
    
    def __init__(self, stream_name: str, stream_manager: NewStreamManager, parent_window=None):
        super().__init__(parent_window)
        self.stream_name = stream_name
        self.stream_manager = stream_manager
        self.parent_window = parent_window
        self.settings_button = None
        self.stream_button = None
        
        # Connect to stream manager signals
        self.stream_manager.stream_started.connect(self._on_stream_started)
        self.stream_manager.stream_stopped.connect(self._on_stream_stopped)
        self.stream_manager.stream_error.connect(self._on_stream_error)
        self.stream_manager.status_update.connect(self._on_status_update)
    
    def open_settings_dialog(self) -> None:
        """Open stream settings dialog"""
        try:
            from new_stream_settings_dialog import NewStreamSettingsDialog
            
            dialog = NewStreamSettingsDialog(self.stream_name, self.parent_window, self.stream_manager)
            dialog.settings_saved.connect(self._on_settings_saved)
            dialog.exec()
            
        except Exception as e:
            print(f"Error opening settings dialog: {e}")
    
    def _on_settings_saved(self, settings: Dict[str, Any]) -> None:
        """Handle saved settings"""
        self.stream_manager.configure_stream(self.stream_name, settings)
    
    def _on_stream_started(self, stream_name: str) -> None:
        """Handle stream started"""
        if stream_name == self.stream_name:
            self._update_ui_state("streaming")
    
    def _on_stream_stopped(self, stream_name: str) -> None:
        """Handle stream stopped"""
        if stream_name == self.stream_name:
            self._update_ui_state("stopped")
    
    def _on_stream_error(self, stream_name: str, error_msg: str) -> None:
        """Handle stream error"""
        if stream_name == self.stream_name:
            self._update_ui_state("error")
            print(f"{self.stream_name} error: {error_msg}")
    
    def _on_status_update(self, stream_name: str, status: str) -> None:
        """Handle status update"""
        if stream_name == self.stream_name:
            print(f"{self.stream_name} status: {status}")
    
    def _update_ui_state(self, state: str) -> None:
        """Update UI based on stream state"""
        try:
            if not self.parent_window:
                return
            
            # Get the appropriate button
            if self.stream_name == "Stream1":
                button = getattr(self.parent_window, 'stream1AudioBtn', None)
            elif self.stream_name == "Stream2":
                button = getattr(self.parent_window, 'stream2AudioBtn', None)
            else:
                return
            
            if not button:
                return
            
            # Update button appearance based on state
            from PyQt6.QtGui import QIcon
            icon_path = Path(__file__).parent / "icons"
            
            if state == "streaming":
                button.setIcon(QIcon(str(icon_path / "Pause.png")))
                button.setStyleSheet("border-radius: 5px; background-color: #ff4444;")
                button.setToolTip(f"Stop {self.stream_name}")
            elif state == "error":
                button.setIcon(QIcon(str(icon_path / "Stream.png")))
                button.setStyleSheet("border-radius: 5px; background-color: #ff8800;")
                button.setToolTip(f"{self.stream_name} Error - Click to retry")
            else:  # stopped
                button.setIcon(QIcon(str(icon_path / "Stream.png")))
                button.setStyleSheet("border-radius: 5px; background-color: #404040;")
                button.setToolTip(f"Start {self.stream_name}")
                
        except Exception as e:
            print(f"Error updating UI state: {e}")

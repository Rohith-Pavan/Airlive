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
from ffmpeg_locator import find_ffmpeg, ensure_ffmpeg_available
from hdmi_stream_manager import get_hdmi_stream_manager

class StreamCaptureThread(QThread):
    """Thread for capturing frames from QGraphicsScene and feeding to FFmpeg"""
    
    stream_started = pyqtSignal()
    stream_stopped = pyqtSignal()
    stream_error = pyqtSignal(str)
    frame_captured = pyqtSignal(int)  # Frame count
    
    def __init__(self, graphics_view, stream_settings):
        super().__init__()
        self.graphics_view = graphics_view
        self.stream_settings = stream_settings
        self.running = False
        self.is_streaming = False
        self.ffmpeg_process = None
        self.frame_count = 0
        
        # Parse resolution from settings
        resolution = stream_settings.get("resolution", "1920x1080")
        try:
            self.width, self.height = map(int, resolution.split("x"))
        except:
            self.width, self.height = 1920, 1080
        
        # Get FFmpeg path
        self.ffmpeg_path = find_ffmpeg()
        if not self.ffmpeg_path:
            print("Warning: FFmpeg not found")
        
        # Connect signals
        self.frame_captured.connect(self.on_frame_captured)
        self.stream_error.connect(self.on_stream_error)
        
    def optimize_streaming_performance(self):
        """Optimize streaming performance by adjusting settings for low latency"""
        try:
            # Set high priority for the streaming thread
            import os
            if hasattr(os, 'nice'):
                try:
                    os.nice(-10)  # Higher priority (may require admin on Windows)
                except:
                    pass
            
            # Optimize Qt settings for real-time streaming
            from PyQt6.QtCore import QThread
            self.setPriority(QThread.Priority.HighPriority)
            
            print("Streaming performance optimized")
        except Exception as e:
            print(f"Error optimizing streaming performance: {e}")
        
    def run(self):
        """Main streaming loop with improved performance and error handling"""
        try:
            print("Starting streaming thread...")
            self.optimize_streaming_performance()
            
            # Start FFmpeg process
            if not self.start_ffmpeg_process():
                self.stream_error.emit("Failed to start FFmpeg process")
                return
            
            # Give FFmpeg more time to initialize
            time.sleep(1.0)
            
            # Check if FFmpeg died during initialization
            if self.ffmpeg_process.poll() is not None:
                self.stream_error.emit("FFmpeg process died during initialization")
                return
                
            print("FFmpeg process started successfully, beginning frame capture...")
            
            # Set streaming flags to start the capture loop
            self.running = True
            self.is_streaming = True
            
            # Emit stream started signal
            self.stream_started.emit()
            
            # Calculate frame interval for target FPS
            target_fps = self.stream_settings.get("fps", 30)
            frame_interval = 1.0 / target_fps
            
            last_frame_time = time.time()
            
            # Main capture loop
            while self.running and self.is_streaming:
                current_time = time.time()
                
                # Only capture at target frame rate
                if current_time - last_frame_time >= frame_interval:
                    if not self.capture_and_send_frame():
                        print("Frame capture failed, stopping stream")
                        break
                    last_frame_time = current_time
                    # Debug output every 30 frames
                    if self.frame_count % 30 == 0:
                        print(f"Streaming: {self.frame_count} frames sent")
                else:
                    # Small sleep to prevent CPU spinning
                    time.sleep(0.001)  # 1ms sleep
                    
        except Exception as e:
            print(f"Streaming thread error: {e}")
            import traceback
            traceback.print_exc()
            self.stream_error.emit(f"Streaming error: {e}")
        finally:
            self.cleanup_ffmpeg()
            
    def start_ffmpeg_process(self):
        """Start FFmpeg process for streaming"""
        try:
            # Build FFmpeg command
            cmd = self.build_ffmpeg_command(self.stream_settings)
            if not cmd:
                self.stream_error.emit("Failed to build FFmpeg command")
                return False
                
            print("Starting FFmpeg process...")
            
            # Log the actual command being executed
            print(f"\n=== Starting FFmpeg Process ===")
            print(f"Command: {' '.join(cmd)}")
            print(f"Working directory: {os.getcwd()}")
            print(f"FFmpeg path: {self.ffmpeg_path}")
            
            # Start FFmpeg process with proper error handling
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # Unbuffered
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            print(f"FFmpeg process started with PID: {self.ffmpeg_process.pid}")
            print(f"=== End Process Start ===\n")
            
            # Wait a bit for FFmpeg to start
            time.sleep(0.5)
            
            # Check if process started successfully
            if self.ffmpeg_process.poll() is not None:
                # Process died immediately, get error
                print(f"\n=== FFmpeg Process Failed ===")
                print(f"Return code: {self.ffmpeg_process.returncode}")
                
                try:
                    stderr_data = self.ffmpeg_process.stderr.read(4096)  # Read more data
                    stdout_data = self.ffmpeg_process.stdout.read(4096)
                    
                    if stderr_data:
                        error_msg = stderr_data.decode('utf-8', errors='ignore')
                        print(f"FFmpeg stderr: {error_msg}")
                        self.stream_error.emit(f"FFmpeg failed: {error_msg}")
                    
                    if stdout_data:
                        output_msg = stdout_data.decode('utf-8', errors='ignore')
                        print(f"FFmpeg stdout: {output_msg}")
                        
                except Exception as read_error:
                    print(f"Error reading FFmpeg output: {read_error}")
                
                print(f"=== End Process Failed ===\n")
                return False
            
            print("FFmpeg process started successfully")
            return True
            
        except Exception as e:
            print(f"Error starting FFmpeg process: {e}")
            self.stream_error.emit(f"Error starting FFmpeg: {e}")
            return False
            
    def _detect_output_mode(self, settings):
        """Return one of 'rtmp', 'srt', 'hls' based on explicit format or URL."""
        fmt = (settings.get('format') or '').strip().lower()
        url = (settings.get('url') or '').strip().lower()
        if fmt in ('rtmp', 'rtmps'):
            return 'rtmp'
        if fmt == 'srt':
            return 'srt'
        if fmt == 'hls':
            return 'hls'
        # Auto-detect by URL
        if url.startswith('rtmp://') or url.startswith('rtmps://'):
            return 'rtmp'
        if url.startswith('srt://'):
            return 'srt'
        if url.endswith('.m3u8') or 'm3u8' in url:
            return 'hls'
        # Fallback to RTMP
        return 'rtmp'

    def build_ffmpeg_command(self, settings):
        """Build FFmpeg command for streaming (RTMP/RTMPS, SRT, HLS)."""
        try:
            # Parse resolution
            width, height = map(int, settings.get('resolution', '1920x1080').split('x'))
            fps = int(settings.get('fps', 30))
            video_bitrate = int(settings.get('video_bitrate', 2500))
            audio_bitrate = int(settings.get('audio_bitrate', 128))
            sample_rate = int(settings.get('sample_rate', 44100))

            # Determine output mode and target
            mode = self._detect_output_mode(settings)
            url = settings.get('url', '').strip()
            key = settings.get('key', '').strip()

            if mode == 'rtmp':
                if not url:
                    print('Error: RTMP URL is required')
                    return None
                if key:
                    target = url.rstrip('/') + '/' + key
                else:
                    target = url
            elif mode == 'srt':
                if not url.startswith('srt://'):
                    print('Error: SRT URL must start with srt://')
                    return None
                target = url
            else:  # hls
                # For HLS, if URL is a path ending with .m3u8 we use it; otherwise default local path
                if url and url.lower().endswith('.m3u8'):
                    target = url
                else:
                    from pathlib import Path as _Path
                    hls_dir = _Path.cwd() / 'hls_out'
                    hls_dir.mkdir(parents=True, exist_ok=True)
                    target = str(hls_dir / 'index.m3u8')

            base = [
                self.ffmpeg_path,
                '-y',
                # Video stdin
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-s', f'{width}x{height}',
                '-r', str(fps),
                '-i', '-',  # raw video from stdin
                # Silent audio
                '-f', 'lavfi',
                '-i', f'anullsrc=channel_layout=stereo:sample_rate={sample_rate}',
                # Video encoding (low latency)
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-profile:v', 'baseline',
                '-level', '3.0',
                '-pix_fmt', 'yuv420p',
                '-b:v', f'{video_bitrate}k',
                '-maxrate', f'{video_bitrate}k',
                '-bufsize', f'{video_bitrate}k',
                '-g', str(fps),
                '-keyint_min', str(fps),
                '-sc_threshold', '0',
                # Audio encoding
                '-c:a', 'aac',
                '-b:a', f'{audio_bitrate}k',
                '-ar', str(sample_rate),
            ]

            # Muxer/output specifics
            if mode == 'rtmp':
                base += [
                    '-thread_queue_size', '512',
                    '-probesize', '32',
                    '-analyzeduration', '0',
                    '-fflags', '+genpts+igndts',
                    '-f', 'flv',
                    '-flvflags', 'no_duration_filesize',
                    target,
                ]
            elif mode == 'srt':
                # SRT prefers MPEG-TS
                base += [
                    '-muxdelay', '0',
                    '-mpegts_flags', '+pat_pmt_at_frames+initial_discontinuity',
                    '-f', 'mpegts',
                    target,
                ]
            else:  # hls
                # HLS to local files
                base += [
                    '-f', 'hls',
                    '-hls_time', '2',
                    '-hls_list_size', '6',
                    '-hls_flags', 'delete_segments+independent_segments+omit_endlist',
                    target,
                ]

            # Log the complete command for debugging
            cmd_str = ' '.join(base)
            print(f"\n=== FFmpeg Command ===")
            print(f"Target URL: {target}")
            print(f"Command: {cmd_str}")
            print(f"Command length: {len(cmd_str)} characters")
            print(f"=== End FFmpeg Command ===\n")
            return base

        except Exception as e:
            print(f"Error building FFmpeg command: {e}")
            return None
            
    def create_test_pattern(self, width, height, frame_number):
        """Create an optimized test pattern as fallback"""
        try:
            # Create a QImage with test pattern
            image = QImage(width, height, QImage.Format.Format_RGB888)
            image.fill(QColor(0, 0, 0))  # Start with black
            
            # Create a more efficient pattern using QPainter
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Animated gradient background
            from PyQt6.QtGui import QLinearGradient
            gradient = QLinearGradient(0, 0, width, height)
            
            # Animate colors based on frame number
            hue1 = (frame_number * 2) % 360
            hue2 = (frame_number * 3 + 180) % 360
            
            color1 = QColor.fromHsv(hue1, 100, 80)
            color2 = QColor.fromHsv(hue2, 100, 40)
            
            gradient.setColorAt(0, color1)
            gradient.setColorAt(1, color2)
            painter.fillRect(0, 0, width, height, QBrush(gradient))
            
            # Draw animated elements
            painter.setPen(QColor(255, 255, 255))
            
            # Moving circle
            circle_x = (frame_number * 5) % (width + 100) - 50
            circle_y = height // 2
            painter.drawEllipse(circle_x - 25, circle_y - 25, 50, 50)
            
            # Frame counter
            font = painter.font()
            font.setPointSize(max(16, width // 60))
            font.setBold(True)
            painter.setFont(font)
            
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(20, 40, f"Test Pattern - Frame {frame_number}")
            
            # Resolution info
            painter.drawText(20, height - 40, f"Resolution: {width}x{height}")
            
            # Timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            painter.drawText(20, height - 20, f"Time: {timestamp}")
            
            painter.end()
            
            return image
            
        except Exception as e:
            print(f"Error creating test pattern: {e}")
            # Fallback to simple solid color
            image = QImage(width, height, QImage.Format.Format_RGB888)
            image.fill(QColor(50, 50, 50))
            return image
        
    def capture_and_send_frame(self):
        """Capture frame from graphics view and send to FFmpeg"""
        if not self.running:
            return False
            
        try:
            # Try to capture from graphics view first
            pixmap = None
            if self.graphics_view:
                pixmap = self.capture_graphics_view(self.width, self.height)
            
            # If graphics capture failed, use test pattern
            if not pixmap or pixmap.isNull():
                print("Graphics capture failed, using test pattern")
                image = self.create_test_pattern(self.width, self.height, self.frame_count)
                if image.isNull():
                    print("Failed to create test pattern")
                    return False
            else:
                # Convert pixmap to image
                image = pixmap.toImage()
                if image.isNull():
                    print("Failed to convert pixmap to image")
                    return False
            
            # Extract RGB data
            raw_data = self.extract_rgb_data(image, self.width, self.height)
            if not raw_data:
                print("Failed to extract RGB data from image")
                return False
            
            # Send to FFmpeg with better error handling
            if self.ffmpeg_process and self.ffmpeg_process.stdin:
                try:
                    # Check if FFmpeg process is still alive before writing
                    if self.ffmpeg_process.poll() is not None:
                        print(f"\n=== FFmpeg Process Died During Streaming ===")
                        print(f"Return code: {self.ffmpeg_process.returncode}")
                        print(f"Frame count when died: {self.frame_count}")
                        
                        # Try to get error output
                        try:
                            stderr_data = self.ffmpeg_process.stderr.read(4096)
                            stdout_data = self.ffmpeg_process.stdout.read(4096)
                            
                            if stderr_data:
                                error_msg = stderr_data.decode('utf-8', errors='ignore')
                                print(f"FFmpeg stderr: {error_msg}")
                                
                                # Check for specific error patterns
                                if 'Connection refused' in error_msg:
                                    print("ERROR: Cannot connect to streaming server")
                                elif 'Invalid stream key' in error_msg or 'Unauthorized' in error_msg:
                                    print("ERROR: Invalid stream key or unauthorized")
                                elif 'Network is unreachable' in error_msg:
                                    print("ERROR: Network connectivity issue")
                                elif 'rtmp' in error_msg.lower() and 'error' in error_msg.lower():
                                    print("ERROR: RTMP protocol error")
                            
                            if stdout_data:
                                output_msg = stdout_data.decode('utf-8', errors='ignore')
                                print(f"FFmpeg stdout: {output_msg}")
                                
                        except Exception as read_error:
                            print(f"Error reading FFmpeg output: {read_error}")
                        
                        print(f"=== End Process Died ===\n")
                        self.running = False
                        self.is_streaming = False
                        return False
                    
                    # Write frame data in chunks to avoid blocking
                    total_bytes = len(raw_data)
                    bytes_written = 0
                    chunk_size = 1024 * 1024  # 1MB chunks
                    
                    while bytes_written < total_bytes:
                        chunk = raw_data[bytes_written:bytes_written + chunk_size]
                        try:
                            written = self.ffmpeg_process.stdin.write(chunk)
                            if written == 0:
                                print("FFmpeg stdin write returned 0")
                                return False
                            bytes_written += written
                        except (BrokenPipeError, OSError) as e:
                            print(f"Error writing chunk to FFmpeg: {e}")
                            return False
                        
                    # Flush immediately for real-time streaming
                    try:
                        self.ffmpeg_process.stdin.flush()
                    except (BrokenPipeError, OSError) as e:
                        print(f"Error flushing FFmpeg stdin: {e}")
                        return False
                    
                    self.frame_count += 1
                    if self.frame_count % 30 == 0:  # Log every 30 frames
                        print(f"Frames sent: {self.frame_count}")
                    self.frame_captured.emit(self.frame_count)
                    return True
                    
                except (BrokenPipeError, OSError) as e:
                    error_code = getattr(e, 'errno', 'unknown')
                    print(f"FFmpeg pipe error [errno {error_code}]: {e}")
                    # Check FFmpeg stderr for more details
                    if self.ffmpeg_process and self.ffmpeg_process.stderr:
                        try:
                            stderr_data = self.ffmpeg_process.stderr.read(1024)
                            if stderr_data:
                                print(f"FFmpeg stderr: {stderr_data.decode()}")
                        except:
                            pass
                    self.running = False
                    self.is_streaming = False
                    return False
                except Exception as e:
                    print(f"Error writing to FFmpeg: {e}")
                    return False
            else:
                print("No FFmpeg process or stdin available")
                return False
                    
        except Exception as e:
            print(f"Error in capture_and_send_frame: {e}")
            return False
    
    def capture_graphics_view(self, width, height):
        """Capture the graphics view using a robust method with multiple fallback strategies"""
        try:
            # Validate input parameters
            if width <= 0 or height <= 0:
                print(f"Invalid capture dimensions: {width}x{height}")
                return QPixmap()
            
            if not self.graphics_view:
                print("No graphics view available for capture")
                return QPixmap()
            
            # Method 1: Try direct scene rendering (most reliable)
            pixmap = self._capture_via_scene_render(width, height)
            if not pixmap.isNull():
                return pixmap
            
            # Method 2: Try widget grab as fallback
            print("Scene render failed, trying widget grab...")
            pixmap = self._capture_via_widget_grab(width, height)
            if not pixmap.isNull():
                return pixmap
            
            # Method 3: Create synthetic content as last resort
            print("Widget grab failed, creating synthetic content...")
            return self._create_synthetic_frame(width, height)
            
        except Exception as e:
            print(f"Error in capture_graphics_view: {e}")
            import traceback
            traceback.print_exc()
            return self._create_synthetic_frame(width, height)
    
    def _capture_via_scene_render(self, width, height):
        """Capture using QGraphicsScene.render() method"""
        try:
            # Create a pixmap of the target size
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.black)
            
            # Create a painter to draw the scene
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Get the scene from the graphics view
            scene = self.graphics_view.scene()
            if not scene:
                painter.end()
                return QPixmap()
            
            # Get scene rect with validation
            scene_rect = scene.sceneRect()
            if scene_rect.isEmpty():
                # Use view size if scene rect is empty
                view_size = self.graphics_view.size()
                if view_size.width() > 0 and view_size.height() > 0:
                    scene_rect = QRectF(0, 0, view_size.width(), view_size.height())
                else:
                    scene_rect = QRectF(0, 0, width, height)
            
            if scene_rect.isEmpty():
                painter.end()
                return QPixmap()
            
            # Render the scene to the pixmap with proper scaling
            target_rect = QRectF(0, 0, width, height)
            scene.render(painter, target_rect, scene_rect)
            
            painter.end()
            
            # Verify the pixmap is valid
            if pixmap.isNull():
                return QPixmap()
            
            # Ensure the pixmap has the correct size
            if pixmap.width() != width or pixmap.height() != height:
                pixmap = pixmap.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            return pixmap
            
        except Exception as e:
            print(f"Scene render capture failed: {e}")
            return QPixmap()
    
    def _capture_via_widget_grab(self, width, height):
        """Capture using QWidget.grab() method as fallback"""
        try:
            # Grab the widget content
            grabbed_pixmap = self.graphics_view.grab()
            if grabbed_pixmap.isNull():
                return QPixmap()
            
            # Scale to target size if needed
            if grabbed_pixmap.width() != width or grabbed_pixmap.height() != height:
                grabbed_pixmap = grabbed_pixmap.scaled(
                    width, height, 
                    Qt.AspectRatioMode.IgnoreAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
            
            return grabbed_pixmap
            
        except Exception as e:
            print(f"Widget grab capture failed: {e}")
            return QPixmap()
    
    def _create_synthetic_frame(self, width, height):
        """Create a synthetic frame with visual content as last resort"""
        try:
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.black)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw a gradient background
            from PyQt6.QtGui import QLinearGradient
            gradient = QLinearGradient(0, 0, width, height)
            gradient.setColorAt(0, QColor(40, 40, 40))
            gradient.setColorAt(1, QColor(20, 20, 20))
            painter.fillRect(0, 0, width, height, QBrush(gradient))
            
            # Draw "LIVE" text
            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(max(24, width // 40))
            font.setBold(True)
            painter.setFont(font)
            
            text_rect = painter.fontMetrics().boundingRect("LIVE STREAM")
            x = (width - text_rect.width()) // 2
            y = (height - text_rect.height()) // 2 + text_rect.height()
            painter.drawText(x, y, "LIVE STREAM")
            
            # Draw frame counter
            painter.setPen(QColor(200, 200, 200))
            font.setPointSize(max(12, width // 80))
            painter.setFont(font)
            frame_text = f"Frame: {self.frame_count}"
            painter.drawText(10, height - 20, frame_text)
            
            # Draw timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            painter.drawText(width - 100, height - 20, timestamp)
            
            painter.end()
            return pixmap
            
        except Exception as e:
            print(f"Failed to create synthetic frame: {e}")
            # Return a simple black frame as absolute fallback
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.black)
            return pixmap
    
    def extract_rgb_data(self, image, width, height):
        """Extract raw RGB data from QImage using a reliable method.
        Ensures the returned buffer is tightly packed RGB24 (no per-line padding),
        which is what FFmpeg expects for -pix_fmt rgb24 via stdin.
        """
        try:
            # Verify image dimensions
            if image.width() != width or image.height() != height:
                print(f"Image dimensions mismatch: expected {width}x{height}, got {image.width()}x{image.height()}")
                return None
            
            # Convert to RGB888 format if needed
            if image.format() != QImage.Format.Format_RGB888:
                image = image.convertToFormat(QImage.Format.Format_RGB888)
                if image.isNull():
                    print("Failed to convert image to RGB888 format")
                    return None
            
            # Bytes per line may be greater than width*3 due to padding
            bytes_per_line = image.bytesPerLine()
            if bytes_per_line <= 0:
                print("Invalid bytesPerLine from QImage")
                return None

            # Total bytes present in the QImage buffer
            total_buffer_bytes = bytes_per_line * height

            # Access the underlying data
            bits = image.bits()
            if not bits:
                print("Failed to get image bits")
                return None

            # Ensure Python knows how many bytes to read
            try:
                bits.setsize(total_buffer_bytes)  # type: ignore[attr-defined]
            except Exception:
                # Some PyQt builds auto-size; proceed anyway
                pass

            buffer_bytes = bytes(bits)
            if len(buffer_bytes) < total_buffer_bytes:
                print(f"Unexpected buffer size: {len(buffer_bytes)} < {total_buffer_bytes}")
                return None

            # Build a tightly packed RGB24 buffer (strip per-line padding)
            packed_row_bytes = width * 3
            raw_out = bytearray(height * packed_row_bytes)

            src_index = 0
            dst_index = 0
            for _ in range(height):
                # Copy only the visible pixel data for this row
                raw_out[dst_index:dst_index + packed_row_bytes] = buffer_bytes[src_index:src_index + packed_row_bytes]
                src_index += bytes_per_line
                dst_index += packed_row_bytes

            print(f"Successfully extracted RGB data: {len(raw_out)} bytes")
            return bytes(raw_out)

        except Exception as e:
            print(f"Error extracting RGB data: {e}")
            return None
            
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

    def on_frame_captured(self, count):
        """Handle frame captured signal from FFmpeg"""
        print(f"Frame captured: {count}")
        # This signal is now connected to the main thread's frame_count_updated signal
        # so we don't need to emit it here directly.

    def on_stream_error(self, error_msg):
        """Handle stream error signal from FFmpeg"""
        print(f"Stream error: {error_msg}")
        self.stream_error.emit(error_msg)


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
        print(f"Registered graphics view for {stream_name}")
        
    def configure_stream(self, stream_name, settings):
        """Configure stream settings"""
        self.streams[stream_name] = settings
        print(f"Stream {stream_name} configured: {settings.get('platform', 'Unknown')} - {settings.get('resolution', 'Unknown')}")
        
    def start_stream(self, stream_name):
        """Start streaming for the specified stream with comprehensive validation"""
        try:
            # Validate stream configuration
            validation_result = self._validate_stream_config(stream_name)
            if not validation_result[0]:
                self.stream_error.emit(stream_name, validation_result[1])
                return False
            
            # Check if stream is already running
            if stream_name in self.capture_threads:
                if self.is_streaming(stream_name):
                    print(f"Stream {stream_name} already running")
                    return True
                else:
                    # Clean up dead thread
                    self._cleanup_dead_thread(stream_name)
            
            # Pre-flight checks
            preflight_result = self._preflight_checks(stream_name)
            if not preflight_result[0]:
                self.stream_error.emit(stream_name, preflight_result[1])
                return False
            
            # Create and configure capture thread
            graphics_view = self.graphics_views[stream_name]
            settings = self.streams[stream_name]
            
            print(f"Starting stream {stream_name} with settings: {settings}")
            
            capture_thread = StreamCaptureThread(graphics_view, settings)
            
            # Connect signals with error handling
            capture_thread.stream_started.connect(
                lambda: self._on_stream_started_internal(stream_name)
            )
            capture_thread.stream_stopped.connect(
                lambda: self._on_stream_stopped(stream_name)
            )
            capture_thread.stream_error.connect(
                lambda msg: self._on_stream_error(stream_name, msg)
            )
            capture_thread.frame_captured.connect(
                lambda count: self.frame_count_updated.emit(stream_name, count)
            )
            
            # Store thread and start
            self.capture_threads[stream_name] = capture_thread
            capture_thread.start()
            
            # Monitor startup with timeout
            startup_success = self._monitor_stream_startup(stream_name, timeout=5.0)
            if not startup_success:
                print(f"Stream {stream_name} failed to start within timeout")
                self._cleanup_failed_stream(stream_name)
                return False
            
            print(f"Stream {stream_name} started successfully")
            return True
            
        except Exception as e:
            print(f"Exception starting stream {stream_name}: {e}")
            import traceback
            traceback.print_exc()
            self.stream_error.emit(stream_name, f"Failed to start stream: {str(e)}")
            self._cleanup_failed_stream(stream_name)
            return False
    
    def _validate_stream_config(self, stream_name):
        """Validate stream configuration before starting"""
        try:
            # Check if stream is configured
            if stream_name not in self.streams:
                return False, "Stream not configured"
            
            # Check if graphics view is registered
            if stream_name not in self.graphics_views:
                return False, "No graphics view registered"
            
            # Validate graphics view
            graphics_view = self.graphics_views[stream_name]
            if not graphics_view:
                return False, "Graphics view is None"
            
            # Validate stream settings
            settings = self.streams[stream_name]
            required_fields = ['resolution', 'fps', 'video_bitrate']
            for field in required_fields:
                if field not in settings:
                    return False, f"Missing required setting: {field}"
            
            # Validate resolution format
            try:
                width, height = map(int, settings['resolution'].split('x'))
                if width <= 0 or height <= 0:
                    return False, "Invalid resolution dimensions"
            except:
                return False, "Invalid resolution format"
            
            # Validate FPS
            try:
                fps = int(settings['fps'])
                if fps <= 0 or fps > 60:
                    return False, "FPS must be between 1 and 60"
            except:
                return False, "Invalid FPS value"
            
            return True, "Configuration valid"
            
        except Exception as e:
            return False, f"Configuration validation error: {e}"
    
    def _preflight_checks(self, stream_name):
        """Perform pre-flight checks before starting stream"""
        try:
            # Check FFmpeg availability
            if not self.check_ffmpeg():
                return False, "FFmpeg not found or not working"
            
            # Test FFmpeg with basic command
            ffmpeg_path = find_ffmpeg()
            if not self._test_ffmpeg_basic(ffmpeg_path):
                return False, "FFmpeg basic test failed"
            
            # Check graphics view scene
            graphics_view = self.graphics_views[stream_name]
            scene = graphics_view.scene()
            if not scene:
                return False, "Graphics view has no scene"
            
            # Test frame capture
            settings = self.streams[stream_name]
            width, height = map(int, settings['resolution'].split('x'))
            
            # Create a test capture thread to verify capture works
            test_thread = StreamCaptureThread(graphics_view, settings)
            test_pixmap = test_thread.capture_graphics_view(width, height)
            
            if test_pixmap.isNull():
                print("Warning: Test capture failed, will use fallback methods")
            
            return True, "Pre-flight checks passed"
            
        except Exception as e:
            return False, f"Pre-flight check error: {e}"
    
    def _test_ffmpeg_basic(self, ffmpeg_path):
        """Test FFmpeg with a basic command"""
        try:
            import subprocess
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except:
            return False
    
    def _monitor_stream_startup(self, stream_name, timeout=5.0):
        """Monitor stream startup with timeout"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.is_streaming(stream_name):
                    # Additional verification - check if FFmpeg process is alive
                    thread = self.capture_threads.get(stream_name)
                    if thread and hasattr(thread, 'ffmpeg_process') and thread.ffmpeg_process:
                        if thread.ffmpeg_process.poll() is None:
                            return True
                
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            print(f"Error monitoring stream startup: {e}")
            return False
    
    def _cleanup_failed_stream(self, stream_name):
        """Clean up resources after failed stream start"""
        try:
            if stream_name in self.capture_threads:
                thread = self.capture_threads[stream_name]
                try:
                    thread.stop_streaming()
                    if thread.isRunning():
                        thread.terminate()
                        thread.wait(1000)
                except:
                    pass
                del self.capture_threads[stream_name]
        except Exception as e:
            print(f"Error cleaning up failed stream: {e}")
    
    def _cleanup_dead_thread(self, stream_name):
        """Clean up a dead thread"""
        try:
            if stream_name in self.capture_threads:
                thread = self.capture_threads[stream_name]
                if not thread.isRunning():
                    del self.capture_threads[stream_name]
        except Exception as e:
            print(f"Error cleaning up dead thread: {e}")
    
    def _on_stream_started_internal(self, stream_name):
        """Internal handler for stream started with additional validation"""
        try:
            # Verify stream is actually working
            if self.is_streaming(stream_name):
                self.stream_started.emit(stream_name)
            else:
                # Stream reported started but isn't actually running
                self._on_stream_error(stream_name, "Stream reported started but is not running")
        except Exception as e:
            print(f"Error in stream started handler: {e}")
            
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
        """Check if a stream is currently active with comprehensive validation"""
        try:
            if stream_name not in self.capture_threads:
                return False
            
            thread = self.capture_threads[stream_name]
            
            # Check if thread is running
            if not thread.isRunning():
                self._cleanup_dead_thread(stream_name)
                return False
            
            # Check thread's internal streaming state
            if not getattr(thread, 'is_streaming', False):
                return False
            
            # Check if FFmpeg process is still alive
            if hasattr(thread, 'ffmpeg_process') and thread.ffmpeg_process:
                if thread.ffmpeg_process.poll() is not None:
                    print(f"FFmpeg process died for stream {stream_name}")
                    thread.stop_streaming()
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error checking streaming status for {stream_name}: {e}")
            return False
        
    def check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            ffmpeg_path = find_ffmpeg()
            if ffmpeg_path:
                print(f"FFmpeg found at: {ffmpeg_path}")
                return True
            else:
                print("FFmpeg not found")
                return False
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
        # Check actual streaming status from manager
        actual_streaming = self.stream_manager.is_streaming(self.stream_name)
        
        if actual_streaming:
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
            
            # Check actual streaming status from manager
            actual_streaming = self.stream_manager.is_streaming(self.stream_name)
            self.is_streaming = actual_streaming
            
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

#!/usr/bin/env python3
"""
HDMI Stream Manager for GoLive Studio
Handles streaming video output to HDMI displays
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QPixmap, QPainter, QImage
from typing import Dict, Any, Optional
import time

from display_manager import get_display_manager, HDMIDisplayWindow


class HDMIVideoWidget(QWidget):
    """Custom video widget for HDMI display that can receive QImage frames"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image = None
        self.setStyleSheet("background-color: black;")
        
        # Create layout with placeholder
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.placeholder_label = QLabel("HDMI Video Output")
        self.placeholder_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
            }
        """)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder_label)
        
    def set_qimage_frame(self, image: QImage):
        """Set a QImage frame to display - ENHANCED QUALITY"""
        if image is not None:
            # ENHANCED: Convert to optimal format for display
            if image.format() != QImage.Format.Format_ARGB32_Premultiplied:
                image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            
            self.current_image = image
            self.placeholder_label.hide()
        else:
            self.current_image = None
            self.placeholder_label.show()
        
        # Force immediate update for smooth playback
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event to draw the current image - ENHANCED MAXIMUM QUALITY"""
        super().paintEvent(event)
        
        if self.current_image is not None and not self.current_image.isNull():
            painter = QPainter(self)
            
            # ENHANCED: Set ALL high-quality rendering hints for maximum quality
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            
            # Scale image to fit widget while maintaining aspect ratio
            widget_rect = self.rect()
            image_size = self.current_image.size()
            
            # Calculate scaling to fit within widget
            scale_x = widget_rect.width() / image_size.width()
            scale_y = widget_rect.height() / image_size.height()
            scale = min(scale_x, scale_y)
            
            # Calculate target size and position
            target_width = int(image_size.width() * scale)
            target_height = int(image_size.height() * scale)
            x = (widget_rect.width() - target_width) // 2
            y = (widget_rect.height() - target_height) // 2
            
            # ENHANCED: Draw with maximum quality settings
            target_rect = widget_rect.__class__(x, y, target_width, target_height)
            painter.drawImage(target_rect, self.current_image, self.current_image.rect())
            
            painter.end()


class HDMIStreamManager(QObject):
    """Manager for HDMI display streaming"""
    
    hdmi_started = pyqtSignal(str)  # stream_name
    hdmi_stopped = pyqtSignal(str)  # stream_name
    hdmi_error = pyqtSignal(str, str)  # stream_name, error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.display_manager = get_display_manager()
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        
        # Monitor display changes
        self.display_manager.displays_changed.connect(self._on_displays_changed)
        
    def configure_hdmi_stream(self, stream_name: str, settings: Dict[str, Any]) -> bool:
        """Configure HDMI stream with given settings"""
        try:
            # Validate HDMI settings
            if not self._validate_hdmi_settings(settings):
                return False
            
            # Store configuration
            self.active_streams[stream_name] = {
                'settings': settings.copy(),
                'window': None,
                'video_widget': None,
                'is_active': False
            }
            
            return True
            
        except Exception as e:
            print(f"Error configuring HDMI stream {stream_name}: {e}")
            return False
    
    def start_hdmi_stream(self, stream_name: str, source_widget: QVideoWidget = None) -> bool:
        """Start HDMI display output"""
        try:
            if stream_name not in self.active_streams:
                print(f"HDMI stream {stream_name} not configured")
                return False
            
            stream_info = self.active_streams[stream_name]
            settings = stream_info['settings']
            
            # Get display info
            display_index = settings.get('hdmi_display_index', 0)
            display_info = self.display_manager.get_display_by_index(display_index)
            
            if not display_info:
                self.hdmi_error.emit(stream_name, f"Display {display_index} not found")
                return False
            
            # Create HDMI window
            hdmi_window = self.display_manager.create_hdmi_window(display_index)
            if not hdmi_window:
                self.hdmi_error.emit(stream_name, "Failed to create HDMI window")
                return False
            
            # Create specialized video widget for the HDMI display
            hdmi_video_widget = HDMIVideoWidget()
            hdmi_video_widget.setStyleSheet("background-color: black;")
            
            # Set up the window
            hdmi_window.set_video_widget(hdmi_video_widget)
            
            # Configure display mode
            display_mode = settings.get('hdmi_display_mode', 'Fullscreen')
            if display_mode == 'Fullscreen':
                hdmi_window.show_fullscreen_on_display()
            else:
                # Parse windowed mode
                if '800x600' in display_mode:
                    hdmi_window.show_windowed_on_display(800, 600)
                elif '1024x768' in display_mode:
                    hdmi_window.show_windowed_on_display(1024, 768)
                elif '1280x720' in display_mode:
                    hdmi_window.show_windowed_on_display(1280, 720)
                else:
                    hdmi_window.show_windowed_on_display()
            
            # Set always on top if requested
            if settings.get('hdmi_always_on_top', False):
                hdmi_window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                hdmi_window.show()
            
            # Store references
            stream_info['window'] = hdmi_window
            stream_info['video_widget'] = hdmi_video_widget
            stream_info['is_active'] = True
            
            # If source widget provided, set up mirroring
            if source_widget:
                self._setup_video_mirroring(source_widget, hdmi_video_widget)
            else:
                # Try to find the main graphics output widget automatically
                self._auto_connect_graphics_output(hdmi_video_widget)
            
            self.hdmi_started.emit(stream_name)
            print(f"HDMI stream {stream_name} started on display {display_index}")
            return True
            
        except Exception as e:
            error_msg = f"Error starting HDMI stream: {e}"
            print(error_msg)
            self.hdmi_error.emit(stream_name, error_msg)
            return False
    
    def stop_hdmi_stream(self, stream_name: str) -> bool:
        """Stop HDMI display output"""
        try:
            if stream_name not in self.active_streams:
                return False
            
            stream_info = self.active_streams[stream_name]
            
            # Clean up mirroring
            hdmi_widget = stream_info.get('video_widget')
            if hdmi_widget:
                # Remove from graphics widget mirroring
                app = QApplication.instance()
                if app:
                    for widget in app.allWidgets():
                        if hasattr(widget, 'remove_hdmi_mirror'):
                            widget.remove_hdmi_mirror(hdmi_widget)
                
                # Clean up manual timers
                if hasattr(self, '_capture_timers'):
                    timer = self._capture_timers.get(id(hdmi_widget))
                    if timer:
                        timer.stop()
                        del self._capture_timers[id(hdmi_widget)]
            
            # Close HDMI window
            if stream_info.get('window'):
                display_index = stream_info['settings'].get('hdmi_display_index', 0)
                self.display_manager.close_hdmi_window(display_index)
            
            # Clean up
            stream_info['window'] = None
            stream_info['video_widget'] = None
            stream_info['is_active'] = False
            
            self.hdmi_stopped.emit(stream_name)
            print(f"HDMI stream {stream_name} stopped")
            return True
            
        except Exception as e:
            print(f"Error stopping HDMI stream {stream_name}: {e}")
            return False
    
    def is_hdmi_streaming(self, stream_name: str) -> bool:
        """Check if HDMI stream is active"""
        if stream_name not in self.active_streams:
            return False
        return self.active_streams[stream_name].get('is_active', False)
    
    def get_hdmi_video_widget(self, stream_name: str) -> Optional[QVideoWidget]:
        """Get the video widget for HDMI display"""
        if stream_name not in self.active_streams:
            return None
        return self.active_streams[stream_name].get('video_widget')
    
    def update_hdmi_content(self, stream_name: str, source_widget: QVideoWidget):
        """Update HDMI display content from source widget"""
        if not self.is_hdmi_streaming(stream_name):
            return
        
        hdmi_widget = self.get_hdmi_video_widget(stream_name)
        if hdmi_widget and source_widget:
            self._setup_video_mirroring(source_widget, hdmi_widget)
    
    def _validate_hdmi_settings(self, settings: Dict[str, Any]) -> bool:
        """Validate HDMI stream settings"""
        required_fields = ['hdmi_display_index']
        
        for field in required_fields:
            if field not in settings:
                print(f"Missing required HDMI setting: {field}")
                return False
        
        # Check if display exists
        display_index = settings['hdmi_display_index']
        if not self.display_manager.get_display_by_index(display_index):
            print(f"Display {display_index} not found")
            return False
        
        return True
    
    def _setup_video_mirroring(self, source_widget, target_widget):
        """Set up video mirroring from source to target widget"""
        try:
            # Check if source is a GraphicsOutputWidget (main output)
            if hasattr(source_widget, 'scene_obj') and hasattr(source_widget, 'video_item'):
                # Source is GraphicsOutputWidget - set up frame capture and mirroring
                self._setup_graphics_mirroring(source_widget, target_widget)
            elif hasattr(source_widget, 'videoOutput'):
                # Source is a regular QVideoWidget - set up direct mirroring
                self._setup_direct_mirroring(source_widget, target_widget)
            else:
                print(f"Unknown source widget type: {type(source_widget)}")
                
        except Exception as e:
            print(f"Error setting up video mirroring: {e}")
    
    def _setup_graphics_mirroring(self, graphics_widget, target_widget):
        """Set up mirroring from GraphicsOutputWidget to HDMI display"""
        try:
            # Use the built-in mirroring system of GraphicsOutputWidget
            if hasattr(graphics_widget, 'add_hdmi_mirror'):
                graphics_widget.add_hdmi_mirror(target_widget)
                print("Graphics mirroring set up using built-in system")
            else:
                # Fallback to manual timer-based mirroring
                self._setup_manual_mirroring(graphics_widget, target_widget)
                
        except Exception as e:
            print(f"Error setting up graphics mirroring: {e}")
    
    def _setup_manual_mirroring(self, graphics_widget, target_widget):
        """Set up manual timer-based mirroring as fallback"""
        try:
            from PyQt6.QtCore import QTimer
            
            # Create a timer to capture frames from the graphics widget
            capture_timer = QTimer()
            capture_timer.setInterval(33)  # ~30 FPS (33ms)
            
            def capture_and_mirror():
                try:
                    # Capture the current frame from graphics widget
                    pixmap = graphics_widget.grab()
                    if not pixmap.isNull():
                        # Convert to QImage for the video item
                        image = pixmap.toImage()
                        
                        # Set the frame to the HDMI video widget
                        if hasattr(target_widget, 'set_qimage_frame'):
                            target_widget.set_qimage_frame(image)
                            
                except Exception as e:
                    print(f"Error in frame capture: {e}")
            
            capture_timer.timeout.connect(capture_and_mirror)
            capture_timer.start()
            
            # Store timer reference to prevent garbage collection
            if not hasattr(self, '_capture_timers'):
                self._capture_timers = {}
            self._capture_timers[id(target_widget)] = capture_timer
            
            print("Manual graphics mirroring set up successfully")
            
        except Exception as e:
            print(f"Error setting up manual mirroring: {e}")
    
    def _setup_direct_mirroring(self, source_widget, target_widget):
        """Set up direct mirroring between video widgets"""
        try:
            # For direct video widget mirroring, we need to share the video output
            # This is more complex and may require GStreamer tee elements
            print("Direct video mirroring not yet implemented")
            # TODO: Implement GStreamer tee-based mirroring for direct video sources
            
        except Exception as e:
            print(f"Error setting up direct mirroring: {e}")
    
    def _auto_connect_graphics_output(self, hdmi_widget):
        """Automatically connect to the main graphics output widget"""
        try:
            # Try to find GraphicsOutputWidget in the application
            app = QApplication.instance()
            if not app:
                return
                
            # Look for GraphicsOutputWidget instances
            for widget in app.allWidgets():
                if hasattr(widget, 'add_hdmi_mirror') and hasattr(widget, 'scene_obj'):
                    # Found a GraphicsOutputWidget
                    widget.add_hdmi_mirror(hdmi_widget)
                    print(f"Auto-connected HDMI widget to graphics output: {widget}")
                    return
                    
            print("No GraphicsOutputWidget found for auto-connection")
            
        except Exception as e:
            print(f"Error in auto-connect: {e}")
    
    def _on_displays_changed(self):
        """Handle display configuration changes"""
        print("Display configuration changed - checking active HDMI streams")
        
        # Check if any active streams are affected
        for stream_name, stream_info in self.active_streams.items():
            if not stream_info.get('is_active'):
                continue
            
            display_index = stream_info['settings'].get('hdmi_display_index')
            if not self.display_manager.get_display_by_index(display_index):
                # Display no longer available
                print(f"Display {display_index} for stream {stream_name} no longer available")
                self.stop_hdmi_stream(stream_name)
                self.hdmi_error.emit(stream_name, f"Display {display_index} disconnected")
    
    def get_active_hdmi_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active HDMI streams"""
        active = {}
        for stream_name, stream_info in self.active_streams.items():
            if stream_info.get('is_active'):
                active[stream_name] = {
                    'display_index': stream_info['settings'].get('hdmi_display_index'),
                    'display_mode': stream_info['settings'].get('hdmi_display_mode'),
                    'window': stream_info.get('window')
                }
        return active
    
    def cleanup(self):
        """Clean up all HDMI streams"""
        stream_names = list(self.active_streams.keys())
        for stream_name in stream_names:
            self.stop_hdmi_stream(stream_name)
        
        self.display_manager.close_all_hdmi_windows()


# Global HDMI stream manager instance
_hdmi_stream_manager = None

def get_hdmi_stream_manager() -> HDMIStreamManager:
    """Get global HDMI stream manager instance"""
    global _hdmi_stream_manager
    if _hdmi_stream_manager is None:
        _hdmi_stream_manager = HDMIStreamManager()
    return _hdmi_stream_manager
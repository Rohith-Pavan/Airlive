#!/usr/bin/env python3
"""
Video Compositor for GoLive Studio
Handles PNG overlay functionality on top of video streams
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QFrame, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QRect
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QBrush
from PyQt6.QtMultimediaWidgets import QVideoWidget

class OverlayWidget(QWidget):
    """Transparent overlay widget for displaying PNG effects on top of video"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.overlay_pixmap = None
        self.overlay_position = Qt.AlignmentFlag.AlignCenter
        self.overlay_opacity = 1.0
        
        # Make widget transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")
        
    def set_overlay_image(self, pixmap_path, position=Qt.AlignmentFlag.AlignCenter, opacity=1.0):
        """Set the overlay image from file path"""
        if pixmap_path and os.path.exists(pixmap_path):
            self.overlay_pixmap = QPixmap(pixmap_path)
            self.overlay_position = position
            self.overlay_opacity = opacity
            self.update()  # Trigger repaint
        else:
            self.clear_overlay()
    
    def clear_overlay(self):
        """Clear the current overlay"""
        self.overlay_pixmap = None
        self.update()
    
    def paintEvent(self, event):
        """Paint the overlay on top of the video"""
        if not self.overlay_pixmap:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set opacity
        painter.setOpacity(self.overlay_opacity)
        
        # Calculate position based on alignment
        widget_rect = self.rect()
        pixmap_size = self.overlay_pixmap.size()
        
        # Scale pixmap if it's too large for the widget
        scaled_pixmap = self.overlay_pixmap
        if (pixmap_size.width() > widget_rect.width() or 
            pixmap_size.height() > widget_rect.height()):
            scaled_pixmap = self.overlay_pixmap.scaled(
                widget_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            pixmap_size = scaled_pixmap.size()
        
        # Calculate position
        if self.overlay_position & Qt.AlignmentFlag.AlignLeft:
            x = 10  # Small margin from left
        elif self.overlay_position & Qt.AlignmentFlag.AlignRight:
            x = widget_rect.width() - pixmap_size.width() - 10
        else:  # Center
            x = (widget_rect.width() - pixmap_size.width()) // 2
            
        if self.overlay_position & Qt.AlignmentFlag.AlignTop:
            y = 10  # Small margin from top
        elif self.overlay_position & Qt.AlignmentFlag.AlignBottom:
            y = widget_rect.height() - pixmap_size.height() - 10
        else:  # Center
            y = (widget_rect.height() - pixmap_size.height()) // 2
        
        # Draw the overlay
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

class VideoCompositor(QObject):
    """Main video compositor class for managing overlays"""
    
    overlay_changed = pyqtSignal(str)  # Emitted when overlay changes
    
    def __init__(self, video_widget, parent=None):
        super().__init__(parent)
        self.video_widget = video_widget
        self.overlay_widget = None
        self.current_overlay_path = None
        
        # Create overlay widget
        self.setup_overlay_widget()
        
    def setup_overlay_widget(self):
        """Set up the overlay widget on top of the video widget"""
        if not self.video_widget:
            return
            
        # Create overlay widget as child of video widget
        self.overlay_widget = OverlayWidget(self.video_widget)
        
        # Position overlay to cover the entire video widget
        self.overlay_widget.setGeometry(self.video_widget.rect())
        
        # Connect to video widget resize events
        self.video_widget.resizeEvent = self.on_video_resize
        
        # Show overlay
        self.overlay_widget.show()
        
    def on_video_resize(self, event):
        """Handle video widget resize to update overlay size"""
        if self.overlay_widget:
            self.overlay_widget.setGeometry(self.video_widget.rect())
        
        # Call original resize event if it exists
        if hasattr(self.video_widget, '_original_resize_event'):
            self.video_widget._original_resize_event(event)
    
    def set_overlay_effect(self, effect_path, position=Qt.AlignmentFlag.AlignCenter, opacity=0.8):
        """Set PNG overlay effect on the video"""
        if not self.overlay_widget:
            self.setup_overlay_widget()
            
        if effect_path and os.path.exists(effect_path):
            self.current_overlay_path = effect_path
            self.overlay_widget.set_overlay_image(effect_path, position, opacity)
            self.overlay_changed.emit(effect_path)
            print(f"Overlay applied: {Path(effect_path).name}")
        else:
            self.clear_overlay()
    
    def clear_overlay(self):
        """Clear the current overlay effect"""
        if self.overlay_widget:
            self.overlay_widget.clear_overlay()
        self.current_overlay_path = None
        self.overlay_changed.emit("")
        print("Overlay cleared")
    
    def set_overlay_opacity(self, opacity):
        """Set overlay opacity (0.0 to 1.0)"""
        if self.overlay_widget and self.current_overlay_path:
            self.overlay_widget.overlay_opacity = opacity
            self.overlay_widget.update()
    
    def set_overlay_position(self, position):
        """Set overlay position using Qt alignment flags"""
        if self.overlay_widget and self.current_overlay_path:
            self.overlay_widget.overlay_position = position
            self.overlay_widget.update()
    
    def get_current_overlay(self):
        """Get the current overlay effect path"""
        return self.current_overlay_path
    
    def is_overlay_active(self):
        """Check if an overlay is currently active"""
        return self.current_overlay_path is not None

class OverlayManager(QObject):
    """Manager for handling multiple video compositors"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.compositors = {}  # Dictionary to store compositors by name
        
    def add_compositor(self, name, video_widget):
        """Add a video compositor for a specific video widget"""
        if video_widget:
            compositor = VideoCompositor(video_widget, self)
            self.compositors[name] = compositor
            return compositor
        return None
    
    def get_compositor(self, name):
        """Get compositor by name"""
        return self.compositors.get(name)
    
    def set_overlay_for_compositor(self, compositor_name, effect_path, position=Qt.AlignmentFlag.AlignCenter, opacity=0.8):
        """Set overlay for a specific compositor"""
        compositor = self.get_compositor(compositor_name)
        if compositor:
            compositor.set_overlay_effect(effect_path, position, opacity)
    
    def clear_overlay_for_compositor(self, compositor_name):
        """Clear overlay for a specific compositor"""
        compositor = self.get_compositor(compositor_name)
        if compositor:
            compositor.clear_overlay()
    
    def clear_all_overlays(self):
        """Clear all overlays from all compositors"""
        for compositor in self.compositors.values():
            compositor.clear_overlay()
    
    def get_active_overlays(self):
        """Get list of active overlays"""
        active = {}
        for name, compositor in self.compositors.items():
            if compositor.is_overlay_active():
                active[name] = compositor.get_current_overlay()
        return active
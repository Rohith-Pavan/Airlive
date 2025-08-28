#!/usr/bin/env python3
"""
Composite Output Widget for GoLive Studio
Handles layered display with video on bottom and PNG effects on top
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QBrush
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QMediaPlayer, QCamera, QMediaCaptureSession

class CompositeOutputWidget(QWidget):
    """Custom widget that combines video display with PNG overlay capabilities"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_effect_pixmap = None
        self.current_effect_path = None
        self.video_widget = None
        
        # Set up the widget
        self.setup_ui()
        
        # Set background color
        self.setStyleSheet("background-color: black;")
        
    def setup_ui(self):
        """Set up the composite widget UI"""
        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Create video widget for bottom layer
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        
        # Add video widget to layout
        self.layout.addWidget(self.video_widget)
        
        # Set size policy
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
    def get_video_widget(self):
        """Get the internal video widget for media player/camera connections"""
        return self.video_widget
    
    def set_effect_overlay(self, effect_path):
        """Set PNG effect to display on top of video"""
        if effect_path and os.path.exists(effect_path):
            self.current_effect_path = effect_path
            self.current_effect_pixmap = QPixmap(effect_path)
            print(f"Effect overlay set: {Path(effect_path).name}")
            print(f"Widget size: {self.size()}, Pixmap size: {self.current_effect_pixmap.size()}")
        else:
            self.current_effect_path = None
            self.current_effect_pixmap = None
            print("Effect overlay cleared")
        
        # Ensure widget is on top and trigger repaint
        self.raise_()
        self.update()
        print(f"Paint event triggered, has effect: {self.current_effect_pixmap is not None}")
    
    def clear_effect_overlay(self):
        """Clear the current effect overlay"""
        self.current_effect_path = None
        self.current_effect_pixmap = None
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event to draw PNG effect on top of video"""
        super().paintEvent(event)
        
        print(f"Paint event called, has effect: {self.current_effect_pixmap is not None}")
        
        # Only draw effect if we have one
        if not self.current_effect_pixmap:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get widget dimensions
        widget_rect = self.rect()
        pixmap_size = self.current_effect_pixmap.size()
        
        print(f"Drawing effect: widget_rect={widget_rect}, pixmap_size={pixmap_size}")
        
        # Scale pixmap to fit widget while maintaining aspect ratio
        scaled_pixmap = self.current_effect_pixmap.scaled(
            widget_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Calculate position to center the effect
        scaled_size = scaled_pixmap.size()
        x = (widget_rect.width() - scaled_size.width()) // 2
        y = (widget_rect.height() - scaled_size.height()) // 2
        
        print(f"Drawing at position: ({x}, {y}), scaled_size={scaled_size}")
        
        # Draw the effect overlay
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()
        
        print("Effect overlay drawn successfully")
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        # Trigger repaint to adjust effect overlay size
        self.update()
    
    def get_current_effect(self):
        """Get the current effect path"""
        return self.current_effect_path
    
    def has_effect(self):
        """Check if an effect is currently displayed"""
        return self.current_effect_pixmap is not None

class CompositeOutputManager(QObject):
    """Manager for handling composite output widgets"""
    
    effect_applied = pyqtSignal(str)  # Emitted when effect is applied
    effect_cleared = pyqtSignal()     # Emitted when effect is cleared
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.composite_widgets = {}  # Dictionary to store composite widgets
        
    def create_composite_widget(self, name, parent=None):
        """Create a new composite output widget"""
        widget = CompositeOutputWidget(parent)
        self.composite_widgets[name] = widget
        return widget
    
    def get_composite_widget(self, name):
        """Get composite widget by name"""
        return self.composite_widgets.get(name)
    
    def set_effect_for_widget(self, widget_name, effect_path):
        """Set effect for a specific composite widget"""
        widget = self.get_composite_widget(widget_name)
        if widget:
            widget.set_effect_overlay(effect_path)
            if effect_path:
                self.effect_applied.emit(effect_path)
            else:
                self.effect_cleared.emit()
    
    def clear_effect_for_widget(self, widget_name):
        """Clear effect for a specific composite widget"""
        widget = self.get_composite_widget(widget_name)
        if widget:
            widget.clear_effect_overlay()
            self.effect_cleared.emit()
    
    def clear_all_effects(self):
        """Clear effects from all composite widgets"""
        for widget in self.composite_widgets.values():
            widget.clear_effect_overlay()
        self.effect_cleared.emit()
    
    def get_video_widget_for_composite(self, widget_name):
        """Get the internal video widget from a composite widget for media connections"""
        widget = self.get_composite_widget(widget_name)
        if widget:
            return widget.get_video_widget()
        return None
    
    def get_active_effects(self):
        """Get list of active effects across all widgets"""
        active = {}
        for name, widget in self.composite_widgets.items():
            if widget.has_effect():
                active[name] = widget.get_current_effect()
        return active
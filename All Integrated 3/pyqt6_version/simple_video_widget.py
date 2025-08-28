#!/usr/bin/env python3
"""
Simple Video Widget with PNG Overlay
A cleaner approach to video compositing with PNG frame overlays
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimediaWidgets import QVideoWidget

class VideoWithOverlay(QWidget):
    """Widget that displays video with PNG overlay on top"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_widget = None
        self.overlay_label = None
        self.current_frame_path = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the video widget and overlay"""
        # Set background color
        self.setStyleSheet("background-color: black;")
        
        # Create video widget
        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet("background-color: black;")
        
        # Create overlay label
        self.overlay_label = QLabel(self)
        self.overlay_label.setStyleSheet("background-color: transparent;")
        self.overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.overlay_label.setScaledContents(True)
        
        # Initially hide overlay
        self.overlay_label.hide()
        
    def get_video_widget(self):
        """Get the internal video widget for media connections"""
        return self.video_widget
    
    def set_frame_overlay(self, frame_path):
        """Set PNG frame overlay"""
        if frame_path and os.path.exists(frame_path):
            self.current_frame_path = frame_path
            pixmap = QPixmap(frame_path)
            
            if not pixmap.isNull():
                self.overlay_label.setPixmap(pixmap)
                self.overlay_label.show()
                self.overlay_label.raise_()  # Bring to front
                print(f"Frame overlay applied: {Path(frame_path).name}")
            else:
                print(f"Failed to load frame: {frame_path}")
        else:
            self.clear_frame_overlay()
    
    def clear_frame_overlay(self):
        """Clear the frame overlay"""
        self.current_frame_path = None
        self.overlay_label.clear()
        self.overlay_label.hide()
        print("Frame overlay cleared")
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        
        # Resize video widget to fill the entire widget
        if self.video_widget:
            self.video_widget.setGeometry(self.rect())
        
        # Resize overlay to fill the entire widget
        if self.overlay_label:
            self.overlay_label.setGeometry(self.rect())
    
    def has_frame(self):
        """Check if a frame overlay is currently active"""
        return self.current_frame_path is not None
    
    def get_current_frame(self):
        """Get the current frame path"""
        return self.current_frame_path


class SimpleVideoManager:
    """Manager for handling simple video widgets with overlay support"""
    
    def __init__(self, parent=None):
        self.video_widgets = {}  # Dictionary to store video widgets
        
    def create_video_widget(self, name, parent=None):
        """Create a new video widget with overlay support"""
        widget = VideoWithOverlay(parent)
        self.video_widgets[name] = widget
        return widget
    
    def get_video_widget(self, name):
        """Get video widget by name"""
        return self.video_widgets.get(name)
    
    def get_video_widget_for_output(self, widget_name):
        """Get the internal video widget from a video widget for media connections"""
        widget = self.get_video_widget(widget_name)
        if widget:
            return widget.get_video_widget()
        return None
    
    def set_frame_for_widget(self, widget_name, frame_path):
        """Set frame for a specific video widget"""
        widget = self.get_video_widget(widget_name)
        if widget:
            widget.set_frame_overlay(frame_path)
    
    def clear_frame_for_widget(self, widget_name):
        """Clear frame for a specific video widget"""
        widget = self.get_video_widget(widget_name)
        if widget:
            widget.clear_frame_overlay()
    
    def clear_all_frames(self):
        """Clear frames from all video widgets"""
        for widget in self.video_widgets.values():
            widget.clear_frame_overlay()
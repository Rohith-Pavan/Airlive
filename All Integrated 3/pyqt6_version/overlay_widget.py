#!/usr/bin/env python3
"""
Simple Overlay Widget for GoLive Studio
Creates a transparent overlay on top of existing video widgets
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QPainter

class OverlayWidget(QWidget):
    """Simple transparent overlay widget for PNG effects"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_effect_pixmap = None
        self.current_effect_path = None
        
        # Make widget transparent and on top
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        
        # Ensure widget stays on top
        self.setWindowFlags(Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)
        
    def set_effect(self, effect_path):
        """Set PNG effect to display"""
        if effect_path and os.path.exists(effect_path):
            self.current_effect_path = effect_path
            self.current_effect_pixmap = QPixmap(effect_path)
            print(f"Overlay effect set: {Path(effect_path).name}")
            print(f"Overlay widget size: {self.size()}, Pixmap size: {self.current_effect_pixmap.size()}")
        else:
            self.current_effect_path = None
            self.current_effect_pixmap = None
            print("Overlay effect cleared")
        
        # Show widget and trigger repaint
        self.show()
        self.raise_()
        self.update()
        print(f"Overlay update triggered, has effect: {self.current_effect_pixmap is not None}")
    
    def clear_effect(self):
        """Clear the current effect"""
        self.current_effect_path = None
        self.current_effect_pixmap = None
        self.update()
        print("Overlay effect cleared")
    
    def paintEvent(self, event):
        """Paint the PNG effect overlay"""
        print(f"Overlay paint event called, has effect: {self.current_effect_pixmap is not None}")
        
        if not self.current_effect_pixmap:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get widget dimensions
        widget_rect = self.rect()
        
        print(f"Overlay drawing: widget_rect={widget_rect}")
        
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
        
        print(f"Overlay drawing at position: ({x}, {y}), scaled_size={scaled_size}")
        
        # Draw the effect
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()
        
        print("Overlay effect drawn successfully")
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self.update()
    
    def get_current_effect(self):
        """Get the current effect path"""
        return self.current_effect_path
    
    def has_effect(self):
        """Check if an effect is currently displayed"""
        return self.current_effect_pixmap is not None

class SimpleOverlayManager(QObject):
    """Simple manager for overlay widgets"""
    
    effect_applied = pyqtSignal(str)
    effect_cleared = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.overlay_widgets = {}
        
    def create_overlay(self, name, target_widget):
        """Create an overlay widget on top of target widget"""
        if target_widget:
            overlay = OverlayWidget(target_widget)
            
            # Position overlay to cover the entire target widget
            def update_overlay_geometry():
                if overlay and target_widget:
                    # Get the full geometry of the target widget
                    geometry = target_widget.geometry()
                    # Set overlay to cover the entire target widget
                    overlay.setGeometry(0, 0, geometry.width(), geometry.height())
                    print(f"Overlay geometry updated: {overlay.geometry()}")
            
            # Initial positioning
            update_overlay_geometry()
            
            # Connect to target widget resize events
            original_resize = target_widget.resizeEvent
            
            def new_resize_event(event):
                original_resize(event)
                update_overlay_geometry()
            
            target_widget.resizeEvent = new_resize_event
            
            self.overlay_widgets[name] = overlay
            overlay.show()
            overlay.raise_()  # Ensure overlay is on top
            print(f"Overlay created for {name} with geometry: {overlay.geometry()}")
            return overlay
        return None
    
    def get_overlay(self, name):
        """Get overlay by name"""
        return self.overlay_widgets.get(name)
    
    def set_effect_for_overlay(self, overlay_name, effect_path):
        """Set effect for a specific overlay"""
        overlay = self.get_overlay(overlay_name)
        if overlay:
            overlay.set_effect(effect_path)
            if effect_path:
                self.effect_applied.emit(effect_path)
            else:
                self.effect_cleared.emit()
    
    def clear_effect_for_overlay(self, overlay_name):
        """Clear effect for a specific overlay"""
        overlay = self.get_overlay(overlay_name)
        if overlay:
            overlay.clear_effect()
            self.effect_cleared.emit()
    
    def clear_all_effects(self):
        """Clear all overlay effects"""
        for overlay in self.overlay_widgets.values():
            overlay.clear_effect()
        self.effect_cleared.emit()
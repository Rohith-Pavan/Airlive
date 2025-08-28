#!/usr/bin/env python3
"""
Effects Manager for GoLive Studio
Handles PNG loading, display, and selection functionality for effects tabs
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor

class EffectFrame(QFrame):
    """Custom frame widget for displaying effect PNGs with selection functionality"""
    
    clicked = pyqtSignal(str, str)  # tab_name, effect_path
    
    def __init__(self, tab_name, effect_path=None, parent=None):
        super().__init__(parent)
        self.tab_name = tab_name
        self.effect_path = effect_path
        self.is_selected = False
        
        # Set up the frame properties
        self.setMinimumSize(160, 90)
        self.setStyleSheet("background-color: #404040; border-radius: 8px;")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        
        # Create layout and label for image display
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)
        self.layout.addWidget(self.image_label)
        
        # Load image if path is provided
        if effect_path:
            self.load_image(effect_path)
    
    def load_image(self, image_path):
        """Load and display PNG image"""
        self.effect_path = image_path
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # Scale pixmap to fit the frame while maintaining aspect ratio
                # Account for potential 2px border on selection
                scaled_pixmap = pixmap.scaled(
                    152, 82,  # Smaller to account for border and margins
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("Invalid Image")
        else:
            self.image_label.setText("No Image")
    
    def set_selected(self, selected):
        """Set selection state and update visual appearance"""
        self.is_selected = selected
        if selected:
            # Use a visible border for selection
            self.setStyleSheet(
                "background-color: #404040; border-radius: 8px; "
                "border: 2px solid #00ff00;"
            )
        else:
            self.setStyleSheet("background-color: #404040; border-radius: 8px;")
    
    def mousePressEvent(self, event):
        """Handle mouse click events"""
        if event.button() == Qt.MouseButton.LeftButton and self.effect_path:
            self.clicked.emit(self.tab_name, self.effect_path)
        super().mousePressEvent(event)

class EffectsManager(QObject):
    """Manager class for handling effects across all tabs"""
    
    effect_selected = pyqtSignal(str, str)  # tab_name, effect_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.effects_base_path = Path(__file__).parent / "effects"
        self.tab_names = ["Web01", "Web02", "Web03", "God01", "Muslim", "Stage", "Telugu"]
        self.effect_frames = {}  # Dictionary to store all effect frames by tab
        self.selected_effects = {}  # Track selected effect for each tab
        
    def get_png_files(self, tab_name):
        """Get all PNG files from the specified tab folder"""
        tab_folder = self.effects_base_path / tab_name
        if not tab_folder.exists():
            return []
        
        png_files = []
        for file_path in tab_folder.glob("*.png"):
            if file_path.is_file():
                png_files.append(str(file_path))
        
        return sorted(png_files)  # Sort alphabetically
    
    def populate_tab_effects(self, tab_name, scroll_area_widget, grid_layout):
        """Populate a tab with PNG effects from its folder"""
        png_files = self.get_png_files(tab_name)
        
        # Initialize tab in dictionaries if not exists
        if tab_name not in self.effect_frames:
            self.effect_frames[tab_name] = []
        if tab_name not in self.selected_effects:
            self.selected_effects[tab_name] = None
        
        # Clear existing widgets from grid layout
        self.clear_grid_layout(grid_layout)
        self.effect_frames[tab_name].clear()
        
        # Add PNG files to grid (4 columns)
        row, col = 0, 0
        max_cols = 4
        
        for png_path in png_files:
            effect_frame = EffectFrame(tab_name, png_path)
            effect_frame.clicked.connect(self.on_effect_clicked)
            
            grid_layout.addWidget(effect_frame, row, col)
            self.effect_frames[tab_name].append(effect_frame)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # If no PNG files found, show placeholder frames
        if not png_files:
            self.create_placeholder_frames(tab_name, grid_layout)
    
    def create_placeholder_frames(self, tab_name, grid_layout):
        """Create placeholder frames when no PNG files are found"""
        # Create 16 placeholder frames (4x4 grid) as shown in the original UI
        for row in range(4):
            for col in range(4):
                effect_frame = EffectFrame(tab_name)
                effect_frame.image_label.setText(f"Drop PNG\nHere")
                effect_frame.image_label.setStyleSheet("color: #888888; font-size: 10px;")
                
                grid_layout.addWidget(effect_frame, row, col)
                self.effect_frames[tab_name].append(effect_frame)
    
    def clear_grid_layout(self, layout):
        """Clear all widgets from a grid layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def on_effect_clicked(self, tab_name, effect_path):
        """Handle effect selection"""
        # Clear previous selection in this tab
        if self.selected_effects[tab_name]:
            for frame in self.effect_frames[tab_name]:
                if frame.effect_path == self.selected_effects[tab_name]:
                    frame.set_selected(False)
                    break
        
        # Set new selection
        self.selected_effects[tab_name] = effect_path
        for frame in self.effect_frames[tab_name]:
            if frame.effect_path == effect_path:
                frame.set_selected(True)
                break
        
        # Emit signals for external handling
        self.effect_selected.emit(tab_name, effect_path)
    
    def get_selected_effect(self, tab_name):
        """Get the currently selected effect for a tab"""
        return self.selected_effects.get(tab_name)
    
    def refresh_tab(self, tab_name, scroll_area_widget, grid_layout):
        """Refresh a specific tab to reload PNG files"""
        self.populate_tab_effects(tab_name, scroll_area_widget, grid_layout)
    
    def refresh_all_tabs(self, tab_widgets_dict):
        """Refresh all tabs - tab_widgets_dict should contain {tab_name: (scroll_widget, grid_layout)}"""
        for tab_name, (scroll_widget, grid_layout) in tab_widgets_dict.items():
            self.refresh_tab(tab_name, scroll_widget, grid_layout)
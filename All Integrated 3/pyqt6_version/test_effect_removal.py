#!/usr/bin/env python3
"""
Test script for effect removal functionality
Demonstrates single-click to apply effects and double-click to remove effects
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, QScrollArea, QGridLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

# Import our effects manager
from effects_manager import EffectsManager
from graphics_output_widget import GraphicsOutputManager

class EffectTestWindow(QMainWindow):
    """Test window for effect removal functionality"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Effect Removal Test - Single Click to Apply, Double Click to Remove")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create effects manager
        self.effects_manager = EffectsManager()
        
        # Create graphics output manager
        self.graphics_manager = GraphicsOutputManager()
        self.output_widget = self.graphics_manager.create_output_widget("main_output")
        
        # Connect effects manager signals
        self.effects_manager.effect_selected.connect(self.on_effect_selected)
        self.effects_manager.effect_removed.connect(self.on_effect_removed)
        
        # Create effects tabs
        self.create_effects_tabs(main_layout)
        
        # Create output preview
        self.create_output_preview(main_layout)
        
        # Status label
        self.status_label = QLabel("Ready - Click an effect to apply, double-click to remove")
        self.status_label.setStyleSheet("background-color: #333; color: white; padding: 5px;")
        
        # Add status to bottom
        layout = QVBoxLayout()
        layout.addLayout(main_layout)
        layout.addWidget(self.status_label)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
    def create_effects_tabs(self, parent_layout):
        """Create the effects tabs widget"""
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMaximumWidth(600)
        
        # Create tabs for each effect category
        for tab_name in self.effects_manager.tab_names:
            # Create scroll area for this tab
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
            # Create widget for scroll area
            scroll_widget = QWidget()
            scroll_area.setWidget(scroll_widget)
            
            # Create grid layout for effects
            grid_layout = QGridLayout(scroll_widget)
            grid_layout.setSpacing(5)
            
            # Populate with effects
            self.effects_manager.populate_tab_effects(tab_name, scroll_widget, grid_layout)
            
            # Add tab
            self.tab_widget.addTab(scroll_area, tab_name)
        
        parent_layout.addWidget(self.tab_widget)
    
    def create_output_preview(self, parent_layout):
        """Create the output preview widget"""
        preview_layout = QVBoxLayout()
        
        # Title
        title = QLabel("Output Preview")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white; background-color: #333; padding: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(title)
        
        # Output widget
        self.output_widget.setMinimumSize(640, 360)
        self.output_widget.setStyleSheet("border: 2px solid #555;")
        preview_layout.addWidget(self.output_widget)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "• Single click on any effect to apply it\n"
            "• Double click on a selected effect to remove it\n"
            "• Selected effects show a green border\n"
            "• Only one effect per tab can be active"
        )
        instructions.setStyleSheet("color: #ccc; background-color: #444; padding: 10px; border-radius: 5px;")
        instructions.setWordWrap(True)
        preview_layout.addWidget(instructions)
        
        parent_layout.addLayout(preview_layout)
    
    def on_effect_selected(self, tab_name, effect_path):
        """Handle effect selection"""
        try:
            # Apply effect to output widget
            self.graphics_manager.set_frame_for_widget("main_output", effect_path)
            
            # Update status
            effect_name = Path(effect_path).name
            self.status_label.setText(f"✅ Applied effect: {effect_name} from {tab_name}")
            self.status_label.setStyleSheet("background-color: #2d5a2d; color: white; padding: 5px;")
            
            print(f"Effect applied: {effect_name} from {tab_name}")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error applying effect: {e}")
            self.status_label.setStyleSheet("background-color: #5a2d2d; color: white; padding: 5px;")
            print(f"Error applying effect: {e}")
    
    def on_effect_removed(self, tab_name, effect_path):
        """Handle effect removal"""
        try:
            # Remove effect from output widget
            self.graphics_manager.clear_frame_for_widget("main_output")
            
            # Update status
            effect_name = Path(effect_path).name
            self.status_label.setText(f"🗑️ Removed effect: {effect_name} from {tab_name}")
            self.status_label.setStyleSheet("background-color: #5a4d2d; color: white; padding: 5px;")
            
            print(f"Effect removed: {effect_name} from {tab_name}")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error removing effect: {e}")
            self.status_label.setStyleSheet("background-color: #5a2d2d; color: white; padding: 5px;")
            print(f"Error removing effect: {e}")

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
        }
        QTabWidget::pane {
            border: 1px solid #555;
            background-color: #3b3b3b;
        }
        QTabBar::tab {
            background-color: #4b4b4b;
            color: white;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #6b6b6b;
        }
        QScrollArea {
            background-color: #3b3b3b;
            border: 1px solid #555;
        }
    """)
    
    # Create and show window
    window = EffectTestWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
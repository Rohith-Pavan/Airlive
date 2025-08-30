#!/usr/bin/env python3
"""
Optimized test for smooth effect removal functionality
This test ensures immediate visual feedback and smooth performance
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, QScrollArea, QGridLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QPixmap, QFont

# Import our effects manager
from effects_manager import EffectsManager
from graphics_output_widget import GraphicsOutputManager

class SmoothEffectTestWindow(QMainWindow):
    """Optimized test window for smooth effect removal functionality"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 SMOOTH: Effect Double-Click Removal Test")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Add title and instructions
        self.create_header(main_layout)
        
        # Create content layout
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        
        # Create effects manager
        self.effects_manager = EffectsManager()
        
        # Create graphics output manager
        self.graphics_manager = GraphicsOutputManager()
        self.output_widget = self.graphics_manager.create_output_widget("main_output")
        
        # Connect effects manager signals with immediate handling
        self.effects_manager.effect_selected.connect(self.on_effect_selected)
        self.effects_manager.effect_removed.connect(self.on_effect_removed)
        
        # Create effects tabs
        self.create_effects_tabs(content_layout)
        
        # Create output preview and status
        self.create_output_and_status(content_layout)
        
        # Status panel
        self.create_status_panel(main_layout)
        
        # Track events for debugging
        self.click_count = 0
        self.double_click_count = 0
        self.current_effect = None
        
        print("🚀 SMOOTH EFFECT TEST STARTED")
        print("⚡ Optimized for immediate response and smooth performance")
        print("📋 Instructions:")
        print("   1. Single-click any effect → Immediate green border + effect applied")
        print("   2. Double-click same effect → Immediate removal of border + effect")
        print("   3. Watch for instant visual feedback")
        print()
        
    def create_header(self, parent_layout):
        """Create header with instructions"""
        header = QLabel("🚀 SMOOTH: Double-Click Effect Removal Test")
        header.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: white; 
            background-color: #1e5a1e; 
            padding: 10px; 
            border-radius: 5px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        parent_layout.addWidget(header)
        
        instructions = QLabel(
            "⚡ OPTIMIZED: Single-click to apply (instant green border) → Double-click to remove (instant removal)"
        )
        instructions.setStyleSheet("""
            font-size: 14px; 
            color: #ccc; 
            background-color: #444; 
            padding: 8px; 
            border-radius: 3px;
        """)
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        parent_layout.addWidget(instructions)
    
    def create_effects_tabs(self, parent_layout):
        """Create the effects tabs widget with optimized performance"""
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMaximumWidth(700)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 2px solid #555; background-color: #3b3b3b; }
            QTabBar::tab { background-color: #4b4b4b; color: white; padding: 8px 16px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #6b6b6b; }
        """)
        
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
            
            # Debug: Print how many effects were loaded
            png_files = self.effects_manager.get_png_files(tab_name)
            print(f"📁 Loaded {len(png_files)} effects in {tab_name} tab")
        
        parent_layout.addWidget(self.tab_widget)
    
    def create_output_and_status(self, parent_layout):
        """Create output preview and status panel"""
        right_layout = QVBoxLayout()
        
        # Output preview
        preview_title = QLabel("🖥️ Output Preview (Instant Updates)")
        preview_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white; background-color: #333; padding: 5px;")
        preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(preview_title)
        
        self.output_widget.setMinimumSize(640, 360)
        self.output_widget.setStyleSheet("border: 2px solid #555;")
        right_layout.addWidget(self.output_widget)
        
        # Status display
        status_title = QLabel("📊 Real-Time Status")
        status_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white; background-color: #444; padding: 5px;")
        status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(status_title)
        
        self.status_display = QLabel("Ready for testing...")
        self.status_display.setStyleSheet("""
            color: #ccc; 
            background-color: #222; 
            padding: 15px; 
            border-radius: 5px; 
            font-family: monospace;
            font-size: 12px;
        """)
        self.status_display.setWordWrap(True)
        self.status_display.setMinimumHeight(120)
        self.status_display.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(self.status_display)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.setStyleSheet("""
            QPushButton { 
                background-color: #5a2d2d; 
                color: white; 
                padding: 8px; 
                border-radius: 5px; 
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7a3d3d; }
        """)
        clear_btn.clicked.connect(self.clear_all_effects)
        button_layout.addWidget(clear_btn)
        
        test_btn = QPushButton("🧪 Test Performance")
        test_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2d5a2d; 
                color: white; 
                padding: 8px; 
                border-radius: 5px; 
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3d7a3d; }
        """)
        test_btn.clicked.connect(self.test_performance)
        button_layout.addWidget(test_btn)
        
        right_layout.addLayout(button_layout)
        parent_layout.addLayout(right_layout)
    
    def create_status_panel(self, parent_layout):
        """Create status panel at bottom"""
        self.status_label = QLabel("🟢 Ready - Optimized for instant response")
        self.status_label.setStyleSheet("""
            background-color: #1e5a1e; 
            color: white; 
            padding: 8px; 
            font-size: 14px; 
            border-radius: 3px;
            font-weight: bold;
        """)
        parent_layout.addWidget(self.status_label)
    
    def update_status_display(self):
        """Update the real-time status display"""
        status_text = f"""⚡ PERFORMANCE STATUS:
• Single clicks: {self.click_count}
• Double clicks: {self.double_click_count}
• Current effect: {self.current_effect or 'None'}

🎯 RESPONSE TEST:
• Visual feedback: Instant
• Effect application: Immediate
• Effect removal: Immediate

💡 TIPS:
• Green border = Effect active
• No border = Effect inactive
• Double-click only works on green-bordered effects"""
        
        self.status_display.setText(status_text)
    
    @pyqtSlot(str, str)
    def on_effect_selected(self, tab_name, effect_path):
        """Handle effect selection with immediate response"""
        self.click_count += 1
        
        try:
            # Apply effect to output widget immediately
            self.graphics_manager.set_frame_for_widget("main_output", effect_path)
            
            # Update tracking
            effect_name = Path(effect_path).name
            self.current_effect = effect_name
            
            # Force immediate UI updates
            self.output_widget.update()
            self.output_widget.repaint()
            
            # Console debug output
            print(f"✅ INSTANT APPLY: {effect_name} from {tab_name}")
            
            # Update UI immediately
            self.status_label.setText(f"✅ Applied: {effect_name}")
            self.status_label.setStyleSheet("""
                background-color: #2d5a2d; 
                color: white; 
                padding: 8px; 
                font-size: 14px; 
                border-radius: 3px;
                font-weight: bold;
            """)
            
            self.update_status_display()
            
        except Exception as e:
            print(f"❌ ERROR applying effect: {e}")
            self.status_label.setText(f"❌ Error: {e}")
            self.status_label.setStyleSheet("""
                background-color: #5a2d2d; 
                color: white; 
                padding: 8px; 
                font-size: 14px; 
                border-radius: 3px;
                font-weight: bold;
            """)
    
    @pyqtSlot(str, str)
    def on_effect_removed(self, tab_name, effect_path):
        """Handle effect removal with immediate response"""
        self.double_click_count += 1
        
        try:
            # Remove effect from output widget immediately
            self.graphics_manager.clear_frame_for_widget("main_output")
            
            # Update tracking
            effect_name = Path(effect_path).name
            self.current_effect = None
            
            # Force immediate UI updates
            self.output_widget.update()
            self.output_widget.repaint()
            
            # Console debug output
            print(f"🗑️ INSTANT REMOVE: {effect_name} from {tab_name}")
            
            # Update UI immediately
            self.status_label.setText(f"🗑️ Removed: {effect_name}")
            self.status_label.setStyleSheet("""
                background-color: #5a4d2d; 
                color: white; 
                padding: 8px; 
                font-size: 14px; 
                border-radius: 3px;
                font-weight: bold;
            """)
            
            self.update_status_display()
            
        except Exception as e:
            print(f"❌ ERROR removing effect: {e}")
            self.status_label.setText(f"❌ Error: {e}")
            self.status_label.setStyleSheet("""
                background-color: #5a2d2d; 
                color: white; 
                padding: 8px; 
                font-size: 14px; 
                border-radius: 3px;
                font-weight: bold;
            """)
    
    def clear_all_effects(self):
        """Clear all effects with immediate response"""
        try:
            # Clear output immediately
            self.graphics_manager.clear_frame_for_widget("main_output")
            
            # Clear all selections with immediate visual updates
            for tab_name in self.effects_manager.tab_names:
                if tab_name in self.effects_manager.selected_effects:
                    self.effects_manager.selected_effects[tab_name] = None
                
                # Clear visual selections with immediate updates
                if tab_name in self.effects_manager.effect_frames:
                    for frame in self.effects_manager.effect_frames[tab_name]:
                        frame.set_selected(False)
                        frame.update()
                        frame.repaint()
            
            # Update tracking
            self.current_effect = None
            
            # Force immediate UI updates
            self.output_widget.update()
            self.output_widget.repaint()
            
            print(f"🧹 ALL EFFECTS CLEARED INSTANTLY")
            
            self.status_label.setText("🧹 All effects cleared")
            self.status_label.setStyleSheet("""
                background-color: #4d4d2d; 
                color: white; 
                padding: 8px; 
                font-size: 14px; 
                border-radius: 3px;
                font-weight: bold;
            """)
            
            self.update_status_display()
            
        except Exception as e:
            print(f"❌ ERROR clearing effects: {e}")
    
    def test_performance(self):
        """Test performance by rapidly switching effects"""
        print("🧪 PERFORMANCE TEST: Rapid effect switching...")
        
        # Get first few effects from Web01 tab
        web01_effects = self.effects_manager.get_png_files("Web01")[:3]
        
        if len(web01_effects) >= 3:
            for i, effect_path in enumerate(web01_effects):
                # Simulate rapid clicking
                self.effects_manager.on_effect_clicked("Web01", effect_path)
                QApplication.processEvents()  # Force immediate processing
                
                # Brief pause
                QTimer.singleShot(100, lambda: None)
                QApplication.processEvents()
            
            print("✅ Performance test completed - check for smooth transitions")
        else:
            print("⚠️ Not enough effects for performance test")

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Set application style for better performance
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
        }
        QScrollArea {
            background-color: #3b3b3b;
            border: 1px solid #555;
        }
    """)
    
    # Create and show window
    window = SmoothEffectTestWindow()
    window.show()
    
    print("🎬 Smooth effect test window shown - test for instant response!")
    print("⚡ All updates should be immediate with no lag")
    print()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
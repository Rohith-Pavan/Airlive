#!/usr/bin/env python3
"""
Debug test for double-click effect removal functionality
This test provides detailed console output to verify the double-click works
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, QScrollArea, QGridLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont

# Import our effects manager
from effects_manager import EffectsManager
from graphics_output_widget import GraphicsOutputManager

class DebugEffectTestWindow(QMainWindow):
    """Debug test window for effect removal functionality"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DEBUG: Effect Double-Click Removal Test")
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
        
        # Connect effects manager signals with debug output
        self.effects_manager.effect_selected.connect(self.on_effect_selected)
        self.effects_manager.effect_removed.connect(self.on_effect_removed)
        
        # Create effects tabs
        self.create_effects_tabs(content_layout)
        
        # Create output preview and debug panel
        self.create_output_and_debug(content_layout)
        
        # Status and debug info
        self.create_status_panel(main_layout)
        
        # Track events for debugging
        self.click_count = 0
        self.double_click_count = 0
        self.applied_effects = []
        self.removed_effects = []
        
        print("🚀 DEBUG TEST STARTED")
        print("📋 Instructions:")
        print("   1. Single-click any effect to apply it (green border will appear)")
        print("   2. Double-click the SAME effect to remove it (green border will disappear)")
        print("   3. Watch console output for detailed event information")
        print("   4. Check the debug panel for real-time status")
        print()
        
    def create_header(self, parent_layout):
        """Create header with instructions"""
        header = QLabel("🔧 DEBUG: Double-Click Effect Removal Test")
        header.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: white; 
            background-color: #2d5a2d; 
            padding: 10px; 
            border-radius: 5px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        parent_layout.addWidget(header)
        
        instructions = QLabel(
            "📋 INSTRUCTIONS: Single-click to apply effect (green border) → Double-click SAME effect to remove it"
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
        """Create the effects tabs widget"""
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
    
    def create_output_and_debug(self, parent_layout):
        """Create output preview and debug panel"""
        right_layout = QVBoxLayout()
        
        # Output preview
        preview_title = QLabel("🖥️ Output Preview")
        preview_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white; background-color: #333; padding: 5px;")
        preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(preview_title)
        
        self.output_widget.setMinimumSize(640, 360)
        self.output_widget.setStyleSheet("border: 2px solid #555;")
        right_layout.addWidget(self.output_widget)
        
        # Debug panel
        debug_title = QLabel("🔍 Debug Information")
        debug_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white; background-color: #444; padding: 5px;")
        debug_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(debug_title)
        
        self.debug_text = QLabel("Waiting for user interaction...")
        self.debug_text.setStyleSheet("""
            color: #ccc; 
            background-color: #222; 
            padding: 10px; 
            border-radius: 5px; 
            font-family: monospace;
        """)
        self.debug_text.setWordWrap(True)
        self.debug_text.setMinimumHeight(150)
        self.debug_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(self.debug_text)
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear All Effects")
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
        right_layout.addWidget(clear_btn)
        
        parent_layout.addLayout(right_layout)
    
    def create_status_panel(self, parent_layout):
        """Create status panel at bottom"""
        self.status_label = QLabel("🟢 Ready - Click an effect to apply, double-click to remove")
        self.status_label.setStyleSheet("""
            background-color: #333; 
            color: white; 
            padding: 8px; 
            font-size: 14px; 
            border-radius: 3px;
        """)
        parent_layout.addWidget(self.status_label)
    
    def update_debug_info(self):
        """Update debug information panel"""
        debug_info = f"""📊 EVENT STATISTICS:
• Single clicks: {self.click_count}
• Double clicks: {self.double_click_count}
• Effects applied: {len(self.applied_effects)}
• Effects removed: {len(self.removed_effects)}

🎯 CURRENT STATE:
• Active effects: {len([e for e in self.applied_effects if e not in self.removed_effects])}

📝 RECENT ACTIVITY:
• Last applied: {self.applied_effects[-1] if self.applied_effects else 'None'}
• Last removed: {self.removed_effects[-1] if self.removed_effects else 'None'}

💡 TIP: Double-click only works on effects with GREEN border!"""
        
        self.debug_text.setText(debug_info)
    
    def on_effect_selected(self, tab_name, effect_path):
        """Handle effect selection with detailed debug output"""
        self.click_count += 1
        
        try:
            # Apply effect to output widget
            self.graphics_manager.set_frame_for_widget("main_output", effect_path)
            
            # Update tracking
            effect_name = Path(effect_path).name
            self.applied_effects.append(effect_name)
            
            # Console debug output
            print(f"\n✅ EFFECT APPLIED:")
            print(f"   📁 Tab: {tab_name}")
            print(f"   🖼️  File: {effect_name}")
            print(f"   📊 Total clicks: {self.click_count}")
            print(f"   🎯 This effect now has GREEN BORDER - double-click it to remove!")
            
            # Update UI
            self.status_label.setText(f"✅ Applied: {effect_name} from {tab_name}")
            self.status_label.setStyleSheet("background-color: #2d5a2d; color: white; padding: 8px; font-size: 14px; border-radius: 3px;")
            
            self.update_debug_info()
            
        except Exception as e:
            print(f"❌ ERROR applying effect: {e}")
            self.status_label.setText(f"❌ Error applying effect: {e}")
            self.status_label.setStyleSheet("background-color: #5a2d2d; color: white; padding: 8px; font-size: 14px; border-radius: 3px;")
    
    def on_effect_removed(self, tab_name, effect_path):
        """Handle effect removal with detailed debug output"""
        self.double_click_count += 1
        
        try:
            # Remove effect from output widget
            self.graphics_manager.clear_frame_for_widget("main_output")
            
            # Update tracking
            effect_name = Path(effect_path).name
            self.removed_effects.append(effect_name)
            
            # Console debug output
            print(f"\n🗑️ EFFECT REMOVED:")
            print(f"   📁 Tab: {tab_name}")
            print(f"   🖼️  File: {effect_name}")
            print(f"   📊 Total double-clicks: {self.double_click_count}")
            print(f"   🎯 GREEN BORDER removed - effect is now inactive!")
            
            # Update UI
            self.status_label.setText(f"🗑️ Removed: {effect_name} from {tab_name}")
            self.status_label.setStyleSheet("background-color: #5a4d2d; color: white; padding: 8px; font-size: 14px; border-radius: 3px;")
            
            self.update_debug_info()
            
        except Exception as e:
            print(f"❌ ERROR removing effect: {e}")
            self.status_label.setText(f"❌ Error removing effect: {e}")
            self.status_label.setStyleSheet("background-color: #5a2d2d; color: white; padding: 8px; font-size: 14px; border-radius: 3px;")
    
    def clear_all_effects(self):
        """Clear all effects and reset state"""
        try:
            self.graphics_manager.clear_frame_for_widget("main_output")
            
            # Clear all selections
            for tab_name in self.effects_manager.tab_names:
                if tab_name in self.effects_manager.selected_effects:
                    self.effects_manager.selected_effects[tab_name] = None
                
                # Clear visual selections
                if tab_name in self.effects_manager.effect_frames:
                    for frame in self.effects_manager.effect_frames[tab_name]:
                        frame.set_selected(False)
            
            print(f"\n🧹 ALL EFFECTS CLEARED")
            print(f"   📊 Final stats - Clicks: {self.click_count}, Double-clicks: {self.double_click_count}")
            
            self.status_label.setText("🧹 All effects cleared")
            self.status_label.setStyleSheet("background-color: #4d4d2d; color: white; padding: 8px; font-size: 14px; border-radius: 3px;")
            
            self.update_debug_info()
            
        except Exception as e:
            print(f"❌ ERROR clearing effects: {e}")

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Set application style
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
    window = DebugEffectTestWindow()
    window.show()
    
    print("🎬 Application window shown - start testing!")
    print("🔍 Watch this console for detailed debug output")
    print()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
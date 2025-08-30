#!/usr/bin/env python3
"""
Example integration of effect removal functionality into main GoLive Studio application
This shows how to add the double-click effect removal to the existing main.py
"""

# Add these imports to your existing main.py imports
from effects_manager import EffectsManager
from graphics_output_widget import GraphicsOutputManager

# Add this to your main window class initialization
class MainWindowWithEffects:
    """Example showing how to integrate effect removal into main window"""
    
    def __init__(self):
        # ... existing initialization code ...
        
        # Initialize effects manager
        self.effects_manager = EffectsManager()
        
        # Initialize graphics output manager
        self.graphics_manager = GraphicsOutputManager()
        
        # Create main output widget (replace existing output preview)
        self.main_output_widget = self.graphics_manager.create_output_widget("main_output")
        
        # Connect effect signals
        self.effects_manager.effect_selected.connect(self.on_effect_selected)
        self.effects_manager.effect_removed.connect(self.on_effect_removed)
        
        # Setup effects UI (add this to your UI setup)
        self.setup_effects_ui()
    
    def setup_effects_ui(self):
        """Setup effects tabs in the UI"""
        # This would typically be added to your existing UI layout
        # For example, in a side panel or bottom panel
        
        from PyQt6.QtWidgets import QTabWidget, QScrollArea, QWidget, QGridLayout
        
        # Create effects tab widget
        self.effects_tab_widget = QTabWidget()
        self.effects_tab_widget.setMaximumHeight(300)  # Adjust as needed
        
        # Create tabs for each effect category
        for tab_name in self.effects_manager.tab_names:
            # Create scroll area for this tab
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            
            # Create widget for scroll area
            scroll_widget = QWidget()
            scroll_area.setWidget(scroll_widget)
            
            # Create grid layout for effects
            grid_layout = QGridLayout(scroll_widget)
            grid_layout.setSpacing(5)
            
            # Populate with effects
            self.effects_manager.populate_tab_effects(tab_name, scroll_widget, grid_layout)
            
            # Add tab
            self.effects_tab_widget.addTab(scroll_area, tab_name)
        
        # Add the effects tab widget to your main layout
        # Example: self.main_layout.addWidget(self.effects_tab_widget)
    
    def on_effect_selected(self, tab_name, effect_path):
        """Handle effect application - ADD THIS METHOD TO YOUR MAIN WINDOW"""
        try:
            from pathlib import Path
            
            # Apply effect to main output widget
            self.graphics_manager.set_frame_for_widget("main_output", effect_path)
            
            # Update status or show message
            effect_name = Path(effect_path).name
            print(f"✅ Applied effect: {effect_name} from {tab_name}")
            
            # Optional: Update UI status label if you have one
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"Applied effect: {effect_name}")
                
        except Exception as e:
            print(f"❌ Error applying effect: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"Error applying effect: {e}")
    
    def on_effect_removed(self, tab_name, effect_path):
        """Handle effect removal - ADD THIS METHOD TO YOUR MAIN WINDOW"""
        try:
            from pathlib import Path
            
            # Remove effect from main output widget
            self.graphics_manager.clear_frame_for_widget("main_output")
            
            # Update status or show message
            effect_name = Path(effect_path).name
            print(f"🗑️ Removed effect: {effect_name} from {tab_name}")
            
            # Optional: Update UI status label if you have one
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"Removed effect: {effect_name}")
                
        except Exception as e:
            print(f"❌ Error removing effect: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"Error removing effect: {e}")
    
    def replace_output_preview_with_graphics_widget(self):
        """Replace existing output preview with graphics widget"""
        # Find the existing output preview frame
        if hasattr(self, 'outputPreview'):
            output_frame = self.outputPreview
            
            # Clear existing layout
            if output_frame.layout():
                while output_frame.layout().count():
                    child = output_frame.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
            else:
                from PyQt6.QtWidgets import QVBoxLayout
                layout = QVBoxLayout(output_frame)
                layout.setContentsMargins(0, 0, 0, 0)
            
            # Add graphics output widget
            output_frame.layout().addWidget(self.main_output_widget)
            
            print("✅ Replaced output preview with graphics widget")

# INTEGRATION INSTRUCTIONS:
# 
# 1. Add the imports at the top of your main.py:
#    from effects_manager import EffectsManager
#    from graphics_output_widget import GraphicsOutputManager
#
# 2. In your main window __init__ method, add:
#    self.effects_manager = EffectsManager()
#    self.graphics_manager = GraphicsOutputManager()
#    self.main_output_widget = self.graphics_manager.create_output_widget("main_output")
#    self.effects_manager.effect_selected.connect(self.on_effect_selected)
#    self.effects_manager.effect_removed.connect(self.on_effect_removed)
#
# 3. Add the signal handler methods:
#    def on_effect_selected(self, tab_name, effect_path): ...
#    def on_effect_removed(self, tab_name, effect_path): ...
#
# 4. Add effects UI to your layout (modify setup_effects_ui as needed)
#
# 5. Replace your existing output preview with the graphics widget

print("Effect removal integration example loaded.")
print("Follow the integration instructions in the comments to add to your main.py")
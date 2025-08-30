#!/usr/bin/env python3
"""
Direct fix for the effect removal issue - works with existing UI
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap

def apply_direct_effect_removal_fix():
    """Apply a direct fix that works with the existing UI structure"""
    
    print("🔧 Applying Direct Effect Removal Fix")
    print("=" * 40)
    
    try:
        # Create application if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Import main window
        from mainwindow import MainWindow
        window = MainWindow()
        
        # Find all QLabel widgets that might be effect thumbnails
        effect_labels = []
        for widget in window.findChildren(QLabel):
            # Look for labels that might contain PNG effects
            if widget.pixmap() and not widget.pixmap().isNull():
                effect_labels.append(widget)
        
        print(f"📋 Found {len(effect_labels)} potential effect labels")
        
        # Create a global effect removal function
        def clear_all_effects_immediately():
            """Clear all effects from the output immediately"""
            try:
                print("🧹 Clearing all effects from output...")
                
                # Method 1: Clear from output preview widget
                if hasattr(window, 'output_preview_widget') and window.output_preview_widget:
                    output_widget = window.output_preview_widget
                    
                    # Clear any overlays
                    if hasattr(output_widget, 'scene'):
                        scene = output_widget.scene()
                        if scene:
                            # Remove overlay items
                            items_to_remove = []
                            for item in scene.items():
                                if hasattr(item, 'zValue') and item.zValue() > 0:
                                    items_to_remove.append(item)
                            
                            for item in items_to_remove:
                                scene.removeItem(item)
                    
                    # Force repaint
                    output_widget.update()
                    output_widget.repaint()
                
                # Method 2: Clear from graphics manager
                if hasattr(window, 'graphics_manager'):
                    window.graphics_manager.clear_all_frames()
                
                # Method 3: Find and clear any graphics output widgets
                from graphics_output_widget import GraphicsOutputWidget
                for widget in window.findChildren(GraphicsOutputWidget):
                    widget.clear_frame_overlay()
                
                print("✅ All effects cleared!")
                
            except Exception as e:
                print(f"❌ Error clearing effects: {e}")
        
        # Enhance existing effect labels with double-click removal
        for label in effect_labels:
            # Store original mouse events
            original_mousePressEvent = label.mousePressEvent
            original_mouseDoubleClickEvent = getattr(label, 'mouseDoubleClickEvent', None)
            
            # Track click timing
            label._click_count = 0
            label._click_timer = QTimer()
            label._click_timer.setSingleShot(True)
            label._click_timer.timeout.connect(lambda l=label: setattr(l, '_click_count', 0))
            
            def enhanced_mousePressEvent(event, label=label):
                """Enhanced mouse press with double-click detection"""
                try:
                    # Call original event
                    if original_mousePressEvent:
                        original_mousePressEvent(event)
                    
                    # Handle click counting
                    label._click_count += 1
                    
                    if label._click_count == 1:
                        # First click - start timer
                        label._click_timer.start(300)  # 300ms double-click window
                        print(f"👆 Single click on effect")
                    elif label._click_count == 2:
                        # Double click - clear effects
                        label._click_timer.stop()
                        label._click_count = 0
                        print(f"👆👆 Double click detected - removing effects!")
                        
                        # Clear all effects immediately
                        clear_all_effects_immediately()
                        
                        # Also remove green border if present
                        try:
                            label.setStyleSheet("")  # Clear any border styling
                        except:
                            pass
                
                except Exception as e:
                    print(f"❌ Error in enhanced mouse event: {e}")
            
            # Replace the mouse event
            label.mousePressEvent = enhanced_mousePressEvent
        
        # Add a global hotkey for clearing effects (Ctrl+C)
        from PyQt6.QtGui import QShortcut, QKeySequence
        from PyQt6.QtCore import Qt
        
        clear_shortcut = QShortcut(QKeySequence("Ctrl+C"), window)
        clear_shortcut.activated.connect(clear_all_effects_immediately)
        
        print(f"✅ Enhanced {len(effect_labels)} effect labels with double-click removal")
        print("✅ Added Ctrl+C hotkey for clearing effects")
        print("\\n🎯 How to use:")
        print("• Single-click effect = Apply effect")
        print("• Double-click effect = Remove all effects")
        print("• Ctrl+C = Clear all effects anytime")
        
        # Show the window
        window.show()
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("🎯 GoLive Studio Direct Effect Removal Fix")
    print("=" * 50)
    
    result = apply_direct_effect_removal_fix()
    
    if result == 0:
        print("\\n✅ Application closed successfully")
    else:
        print(f"\\n⚠️ Application closed with code: {result}")

if __name__ == "__main__":
    main()
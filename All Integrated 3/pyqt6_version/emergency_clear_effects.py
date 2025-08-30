#!/usr/bin/env python3
"""
Emergency Effect Clearer for GoLive Studio
Run this if effects are stuck on the output screen
"""

import sys
from PyQt6.QtWidgets import QApplication

def emergency_clear_effects():
    """Emergency function to clear all effects"""
    try:
        app = QApplication.instance()
        if not app:
            print("❌ No Qt application running - start GoLive Studio first!")
            return False
        
        print("🚨 EMERGENCY EFFECT CLEARING...")
        
        # Find main window
        main_window = None
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'output_preview_widget'):
                main_window = widget
                break
        
        if not main_window:
            print("❌ GoLive Studio main window not found!")
            return False
        
        cleared_count = 0
        
        # Clear output preview widget
        if hasattr(main_window, 'output_preview_widget') and main_window.output_preview_widget:
            output_widget = main_window.output_preview_widget
            
            # Clear graphics scene
            if hasattr(output_widget, 'scene'):
                scene = output_widget.scene()
                if scene:
                    items = scene.items()
                    for item in items:
                        if hasattr(item, 'zValue') and item.zValue() > 0:
                            scene.removeItem(item)
                            cleared_count += 1
            
            # Clear pixmap
            if hasattr(output_widget, 'setPixmap'):
                from PyQt6.QtGui import QPixmap
                output_widget.setPixmap(QPixmap())
            
            # Force repaint
            output_widget.update()
            output_widget.repaint()
        
        # Clear graphics manager
        if hasattr(main_window, 'graphics_manager'):
            main_window.graphics_manager.clear_all_frames()
        
        # Clear any graphics output widgets
        try:
            from graphics_output_widget import GraphicsOutputWidget
            for widget in main_window.findChildren(GraphicsOutputWidget):
                widget.clear_frame_overlay()
                cleared_count += 1
        except:
            pass
        
        print(f"🎉 EMERGENCY CLEAR COMPLETE! Cleared {cleared_count} items")
        return True
        
    except Exception as e:
        print(f"❌ Emergency clear failed: {e}")
        return False

if __name__ == "__main__":
    emergency_clear_effects()

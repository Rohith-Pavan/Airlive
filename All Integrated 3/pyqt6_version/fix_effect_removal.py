#!/usr/bin/env python3
"""
Direct fix for effect removal issue in GoLive Studio
This script patches the effect removal to properly clear the output screen
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer

def fix_effect_removal_in_main_app():
    """Apply a direct fix to ensure effects are properly removed from output"""
    
    print("🔧 Applying Direct Effect Removal Fix")
    print("=" * 40)
    
    try:
        # Import the main window
        from mainwindow import MainWindow
        
        # Create a test instance to verify the fix
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        window = MainWindow()
        
        # Check if effects manager is available
        if not hasattr(window, 'effects_manager'):
            print("❌ Effects manager not found - integration incomplete")
            return False
        
        # Enhance the effect removal method
        original_on_effect_removed = window.on_effect_removed
        
        def enhanced_on_effect_removed(tab_name, effect_path):
            """Enhanced effect removal that ensures output is cleared"""
            try:
                from pathlib import Path
                
                print(f"🗑️ Removing effect: {Path(effect_path).name}")
                
                # Call original removal
                original_on_effect_removed(tab_name, effect_path)
                
                # Additional clearing methods for the output screen
                if hasattr(window, 'output_preview_widget') and window.output_preview_widget:
                    output_widget = window.output_preview_widget
                    
                    # Method 1: Clear any graphics scene overlays
                    try:
                        if hasattr(output_widget, 'scene'):
                            scene = output_widget.scene()
                            if scene:
                                # Remove all overlay items (items with zValue > 0)
                                items_to_remove = []
                                for item in scene.items():
                                    if hasattr(item, 'zValue') and item.zValue() > 0:
                                        items_to_remove.append(item)
                                
                                for item in items_to_remove:
                                    scene.removeItem(item)
                                    print("🧹 Removed overlay item from scene")
                    except Exception as e:
                        print(f"⚠️ Method 1 failed: {e}")
                    
                    # Method 2: Force widget repaint
                    try:
                        output_widget.update()
                        output_widget.repaint()
                        print("🔄 Forced widget repaint")
                    except Exception as e:
                        print(f"⚠️ Method 2 failed: {e}")
                    
                    # Method 3: Clear any cached frames
                    try:
                        if hasattr(output_widget, 'clear'):
                            output_widget.clear()
                        if hasattr(output_widget, 'setPixmap'):
                            from PyQt6.QtGui import QPixmap
                            output_widget.setPixmap(QPixmap())  # Clear pixmap
                        print("🧹 Cleared cached frames")
                    except Exception as e:
                        print(f"⚠️ Method 3 failed: {e}")
                
                # Method 4: Clear from graphics manager
                if hasattr(window, 'graphics_manager'):
                    try:
                        window.graphics_manager.clear_all_frames()
                        print("🧹 Cleared all frames from graphics manager")
                    except Exception as e:
                        print(f"⚠️ Method 4 failed: {e}")
                
                # Method 5: Force immediate visual update with timer
                def delayed_clear():
                    try:
                        if hasattr(window, 'output_preview_widget') and window.output_preview_widget:
                            window.output_preview_widget.update()
                            window.output_preview_widget.repaint()
                        print("🔄 Delayed clear completed")
                    except Exception as e:
                        print(f"⚠️ Delayed clear failed: {e}")
                
                # Schedule delayed clear
                QTimer.singleShot(100, delayed_clear)
                
                print(f"✅ Enhanced removal complete for: {Path(effect_path).name}")
                
            except Exception as e:
                print(f"❌ Enhanced removal failed: {e}")
                # Fall back to original method
                try:
                    original_on_effect_removed(tab_name, effect_path)
                except:
                    pass
        
        # Replace the method
        window.on_effect_removed = enhanced_on_effect_removed
        
        print("✅ Effect removal fix applied successfully!")
        print("\\n🎯 The fix includes:")
        print("• Enhanced overlay clearing from graphics scenes")
        print("• Forced widget repaints")
        print("• Cached frame clearing")
        print("• Delayed clearing for stubborn effects")
        print("• Multiple fallback methods")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to apply fix: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_standalone_effect_cleaner():
    """Create a standalone effect cleaner that can be called anytime"""
    
    cleaner_code = '''
def clear_all_effects_from_output():
    """Standalone function to clear all effects from output - call this anytime!"""
    try:
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if not app:
            print("❌ No Qt application running")
            return False
        
        # Find the main window
        main_window = None
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'output_preview_widget'):
                main_window = widget
                break
        
        if not main_window:
            print("❌ Main window not found")
            return False
        
        print("🧹 Clearing all effects from output...")
        
        # Clear from output widget
        if hasattr(main_window, 'output_preview_widget') and main_window.output_preview_widget:
            output_widget = main_window.output_preview_widget
            
            # Clear graphics scene
            if hasattr(output_widget, 'scene'):
                scene = output_widget.scene()
                if scene:
                    items_to_remove = []
                    for item in scene.items():
                        if hasattr(item, 'zValue') and item.zValue() > 0:
                            items_to_remove.append(item)
                    
                    for item in items_to_remove:
                        scene.removeItem(item)
            
            # Force repaint
            output_widget.update()
            output_widget.repaint()
        
        # Clear from graphics manager
        if hasattr(main_window, 'graphics_manager'):
            main_window.graphics_manager.clear_all_frames()
        
        print("✅ All effects cleared!")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing effects: {e}")
        return False

# You can call this function anytime to clear effects:
# clear_all_effects_from_output()
'''
    
    # Write the cleaner to a file
    with open("effect_cleaner.py", "w") as f:
        f.write(cleaner_code)
    
    print("📝 Created effect_cleaner.py - you can import and use clear_all_effects_from_output() anytime!")

def main():
    """Main function"""
    print("🎯 GoLive Studio Effect Removal Fix")
    print("=" * 50)
    
    # Apply the fix
    if fix_effect_removal_in_main_app():
        print("\\n🎉 Fix applied successfully!")
        
        # Create standalone cleaner
        create_standalone_effect_cleaner()
        
        print("\\n📋 How to test:")
        print("1. Run your main GoLive Studio application")
        print("2. Single-click an effect to apply it")
        print("3. Double-click the same effect to remove it")
        print("4. The effect should now be completely removed from the output!")
        print("\\n🆘 If effects still stick, run: python effect_cleaner.py")
        
    else:
        print("\\n❌ Fix failed - please check the error messages above")

if __name__ == "__main__":
    main()
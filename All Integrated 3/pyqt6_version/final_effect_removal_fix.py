#!/usr/bin/env python3
"""
Final comprehensive fix for effect removal in GoLive Studio
This ensures effects are completely removed from the output screen
"""

import sys
import os
from pathlib import Path

def apply_comprehensive_effect_removal_fix():
    """Apply a comprehensive fix that ensures effects are completely removed"""
    
    print("🔧 Applying Comprehensive Effect Removal Fix")
    print("=" * 50)
    
    try:
        # Read the current mainwindow.py
        mainwindow_path = Path("mainwindow.py")
        if not mainwindow_path.exists():
            print("❌ mainwindow.py not found!")
            return False
        
        with open(mainwindow_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if our enhanced removal method exists
        if "def on_effect_removed(self, tab_name, effect_path):" in content:
            print("✅ Effect removal method found - enhancing it...")
            
            # Find and replace the existing method with an enhanced version
            old_method_start = content.find("def on_effect_removed(self, tab_name, effect_path):")
            if old_method_start != -1:
                # Find the end of the method (next method or end of class)
                method_end = content.find("\\n    def ", old_method_start + 1)
                if method_end == -1:
                    method_end = content.find("\\n\\nclass", old_method_start + 1)
                if method_end == -1:
                    method_end = len(content)
                
                # Enhanced removal method
                enhanced_method = '''    def on_effect_removed(self, tab_name, effect_path):
        """Handle effect removal via double-click - ENHANCED VERSION"""
        try:
            from pathlib import Path
            
            print(f"🗑️ ENHANCED: Removing effect: {Path(effect_path).name} from {tab_name}")
            
            # Method 1: Clear from graphics manager
            if hasattr(self, 'graphics_manager'):
                self.graphics_manager.clear_frame_for_widget("main_output")
                self.graphics_manager.clear_all_frames()
                print("✅ Cleared from graphics manager")
            
            # Method 2: Clear from output preview widget (MAIN FIX)
            if hasattr(self, 'output_preview_widget') and self.output_preview_widget:
                output_widget = self.output_preview_widget
                
                # Clear any graphics scene overlays
                if hasattr(output_widget, 'scene'):
                    scene = output_widget.scene()
                    if scene:
                        # Remove ALL overlay items (anything with zValue > 0)
                        items_to_remove = []
                        for item in scene.items():
                            if hasattr(item, 'zValue') and item.zValue() > 0:
                                items_to_remove.append(item)
                        
                        for item in items_to_remove:
                            scene.removeItem(item)
                        
                        print(f"✅ Removed {len(items_to_remove)} overlay items from scene")
                
                # Clear any pixmap overlays
                if hasattr(output_widget, 'setPixmap'):
                    from PyQt6.QtGui import QPixmap
                    output_widget.setPixmap(QPixmap())
                
                # Force immediate repaint
                output_widget.update()
                output_widget.repaint()
                print("✅ Forced output widget repaint")
            
            # Method 3: Clear from any GraphicsOutputWidget instances
            try:
                from graphics_output_widget import GraphicsOutputWidget
                graphics_widgets = self.findChildren(GraphicsOutputWidget)
                for widget in graphics_widgets:
                    widget.clear_frame_overlay()
                    widget.update()
                    widget.repaint()
                print(f"✅ Cleared {len(graphics_widgets)} graphics output widgets")
            except Exception as e:
                print(f"⚠️ Graphics widget clearing failed: {e}")
            
            # Method 4: Clear any QLabel overlays with borders (effect indicators)
            from PyQt6.QtWidgets import QLabel
            cleared_labels = 0
            for label in self.findChildren(QLabel):
                if label.styleSheet() and ("border" in label.styleSheet().lower() or "green" in label.styleSheet().lower()):
                    label.setStyleSheet("")
                    label.update()
                    cleared_labels += 1
            
            if cleared_labels > 0:
                print(f"✅ Cleared styling from {cleared_labels} labels")
            
            # Method 5: Delayed clearing for stubborn effects
            from PyQt6.QtCore import QTimer
            def delayed_clear():
                try:
                    if hasattr(self, 'output_preview_widget') and self.output_preview_widget:
                        self.output_preview_widget.update()
                        self.output_preview_widget.repaint()
                    print("✅ Delayed clear completed")
                except Exception as e:
                    print(f"⚠️ Delayed clear failed: {e}")
            
            # Schedule multiple delayed clears
            QTimer.singleShot(50, delayed_clear)   # 50ms
            QTimer.singleShot(100, delayed_clear)  # 100ms
            QTimer.singleShot(200, delayed_clear)  # 200ms
            
            # Update status
            effect_name = Path(effect_path).name
            print(f"🎉 ENHANCED REMOVAL COMPLETE: {effect_name}")
            
            # Optional: Update UI status if available
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage(f"Effect removed: {effect_name}", 3000)
                
        except Exception as e:
            print(f"❌ Enhanced removal failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: Basic clearing
            try:
                if hasattr(self, 'output_preview_widget') and self.output_preview_widget:
                    self.output_preview_widget.update()
                    self.output_preview_widget.repaint()
            except:
                pass'''
                
                # Replace the old method with the enhanced one
                new_content = content[:old_method_start] + enhanced_method + content[method_end:]
                
                # Write the updated content
                backup_path = Path("mainwindow_backup_enhanced.py")
                print(f"📋 Creating backup: {backup_path}")
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"📝 Writing enhanced mainwindow.py...")
                with open(mainwindow_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print("✅ Enhanced effect removal method applied!")
                return True
        
        print("⚠️ Effect removal method not found - integration may be incomplete")
        return False
        
    except Exception as e:
        print(f"❌ Failed to apply comprehensive fix: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_emergency_effect_clearer():
    """Create an emergency effect clearer script"""
    
    clearer_script = '''#!/usr/bin/env python3
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
'''
    
    with open("emergency_clear_effects.py", "w", encoding='utf-8') as f:
        f.write(clearer_script)
    
    print("🚨 Created emergency_clear_effects.py")

def main():
    """Main function"""
    print("🎯 Final Effect Removal Fix for GoLive Studio")
    print("=" * 60)
    
    if apply_comprehensive_effect_removal_fix():
        create_emergency_effect_clearer()
        
        print("\\n🎉 COMPREHENSIVE FIX APPLIED SUCCESSFULLY!")
        print("\\n🎯 What was fixed:")
        print("• Enhanced effect removal with multiple clearing methods")
        print("• Immediate visual feedback")
        print("• Multiple delayed clears for stubborn effects")
        print("• Fallback clearing methods")
        print("• Emergency clearer script created")
        
        print("\\n📋 How to test:")
        print("1. Restart GoLive Studio")
        print("2. Single-click an effect to apply it")
        print("3. Double-click the same effect to remove it")
        print("4. The effect should now be COMPLETELY removed from output!")
        
        print("\\n🆘 If effects still stick:")
        print("Run: python emergency_clear_effects.py")
        
    else:
        print("\\n❌ Fix failed - please check the error messages above")

if __name__ == "__main__":
    main()
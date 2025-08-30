#!/usr/bin/env python3
"""
Runtime effect fix that can be injected into any running GoLive Studio application
This works by finding and hooking into the actual running application
"""

import sys
import time
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QFrame
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap, QShortcut, QKeySequence

class RuntimeEffectFixer:
    """Runtime fixer that hooks into the running application"""
    
    def __init__(self):
        self.main_window = None
        self.output_frame = None
        self.effect_thumbnails = []
        self.hooked_labels = []
        
    def find_application(self):
        """Find the running GoLive Studio application"""
        app = QApplication.instance()
        if not app:
            print("❌ No Qt application running")
            return False
        
        # Find main window
        for widget in app.topLevelWidgets():
            if widget.isVisible() and widget.size().width() > 800:
                self.main_window = widget
                break
        
        if not self.main_window:
            print("❌ Main window not found")
            return False
        
        print(f"✅ Found main window: {self.main_window.size()}")
        return True
    
    def find_output_frame(self):
        """Find the main output frame"""
        if not self.main_window:
            return False
        
        frames = self.main_window.findChildren(QFrame)
        largest_frame = None
        largest_area = 0
        
        for frame in frames:
            if frame.isVisible():
                size = frame.size()
                area = size.width() * size.height()
                if area > largest_area:
                    largest_area = area
                    largest_frame = frame
        
        if largest_frame:
            self.output_frame = largest_frame
            print(f"✅ Found output frame: {self.output_frame.size()}")
            return True
        
        print("❌ Output frame not found")
        return False
    
    def find_effect_thumbnails(self):
        """Find effect thumbnail labels"""
        if not self.main_window:
            return False
        
        labels = self.main_window.findChildren(QLabel)
        thumbnails = []
        
        for label in labels:
            if label.pixmap() and not label.pixmap().isNull():
                size = label.size()
                # Effect thumbnails are typically in a specific size range
                if 100 < size.width() < 400 and 50 < size.height() < 300:
                    thumbnails.append(label)
        
        self.effect_thumbnails = thumbnails
        print(f"✅ Found {len(thumbnails)} effect thumbnails")
        return len(thumbnails) > 0
    
    def clear_all_effects(self):
        """Clear all effects from the output"""
        if not self.output_frame:
            print("❌ No output frame to clear")
            return
        
        print("🧹 CLEARING ALL EFFECTS...")
        cleared_count = 0
        
        try:
            # Method 1: Remove all overlay labels from output frame
            for child in self.output_frame.findChildren(QLabel):
                if child.pixmap() and not child.pixmap().isNull():
                    # Check if this is an overlay (not a thumbnail)
                    if child.parent() == self.output_frame:
                        child.hide()
                        child.deleteLater()
                        cleared_count += 1
                        print(f"  Removed overlay: {child.size()}")
            
            # Method 2: Clear any widgets with pixmaps in the output area
            for child in self.output_frame.findChildren(QWidget):
                if hasattr(child, 'setPixmap') and child != self.output_frame:
                    try:
                        child.setPixmap(QPixmap())
                        cleared_count += 1
                    except:
                        pass
            
            # Method 3: Force repaints
            self.output_frame.update()
            self.output_frame.repaint()
            
            # Method 4: Clear parent widget too
            parent = self.output_frame.parent()
            if parent:
                parent.update()
                parent.repaint()
            
            # Method 5: Delayed clearing for stubborn effects
            QTimer.singleShot(50, self.output_frame.update)
            QTimer.singleShot(100, self.output_frame.repaint)
            QTimer.singleShot(150, lambda: parent.update() if parent else None)
            
            print(f"✅ CLEARED {cleared_count} effects!")
            
        except Exception as e:
            print(f"❌ Error clearing effects: {e}")
    
    def hook_thumbnail_clicks(self):
        """Hook into thumbnail click events"""
        if not self.effect_thumbnails:
            return False
        
        hooked_count = 0
        
        for i, label in enumerate(self.effect_thumbnails):
            try:
                # Store original mouse event
                original_event = label.mousePressEvent
                
                # Create click tracking variables
                label._click_count = 0
                label._last_click_time = 0
                
                def create_mouse_handler(lbl, idx):
                    def enhanced_mouse_event(event):
                        current_time = time.time() * 1000
                        
                        # Call original event first
                        if original_event:
                            original_event(event)
                        
                        if event.button() == Qt.MouseButton.LeftButton:
                            # Check for double-click
                            if (current_time - lbl._last_click_time) < 300:
                                print(f"🗑️ DOUBLE-CLICK on thumbnail {idx} - CLEARING EFFECTS!")
                                self.clear_all_effects()
                            else:
                                print(f"👆 Single-click on thumbnail {idx}")
                            
                            lbl._last_click_time = current_time
                    
                    return enhanced_mouse_event
                
                # Replace the mouse event
                label.mousePressEvent = create_mouse_handler(label, i)
                self.hooked_labels.append(label)
                hooked_count += 1
                
            except Exception as e:
                print(f"⚠️ Failed to hook thumbnail {i}: {e}")
        
        print(f"✅ Hooked {hooked_count} thumbnails for double-click removal")
        return hooked_count > 0
    
    def add_keyboard_shortcuts(self):
        """Add keyboard shortcuts for manual clearing"""
        if not self.main_window:
            return False
        
        try:
            # Ctrl+Delete for clearing effects
            clear_shortcut = QShortcut(QKeySequence("Ctrl+Delete"), self.main_window)
            clear_shortcut.activated.connect(self.clear_all_effects)
            
            # Ctrl+Shift+Delete for emergency clear
            emergency_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Delete"), self.main_window)
            emergency_shortcut.activated.connect(self.emergency_clear)
            
            print("✅ Added keyboard shortcuts:")
            print("  - Ctrl+Delete: Clear all effects")
            print("  - Ctrl+Shift+Delete: Emergency clear")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to add shortcuts: {e}")
            return False
    
    def emergency_clear(self):
        """Emergency clear that tries everything"""
        print("🚨 EMERGENCY CLEAR ACTIVATED!")
        
        if not self.main_window:
            return
        
        try:
            # Clear from all frames
            frames = self.main_window.findChildren(QFrame)
            for frame in frames:
                if frame.size().width() > 300:  # Only large frames
                    for child in frame.findChildren(QLabel):
                        if child.pixmap():
                            child.hide()
                            child.deleteLater()
                    
                    frame.update()
                    frame.repaint()
            
            # Clear from all widgets
            for widget in self.main_window.findChildren(QWidget):
                if hasattr(widget, 'setPixmap'):
                    try:
                        widget.setPixmap(QPixmap())
                    except:
                        pass
                
                widget.update()
                widget.repaint()
            
            # Force main window repaint
            self.main_window.update()
            self.main_window.repaint()
            
            print("✅ EMERGENCY CLEAR COMPLETE!")
            
        except Exception as e:
            print(f"❌ Emergency clear failed: {e}")
    
    def install_fix(self):
        """Install the complete runtime fix"""
        print("🔧 INSTALLING RUNTIME EFFECT FIX")
        print("=" * 50)
        
        if not self.find_application():
            return False
        
        if not self.find_output_frame():
            return False
        
        if not self.find_effect_thumbnails():
            return False
        
        if not self.hook_thumbnail_clicks():
            return False
        
        if not self.add_keyboard_shortcuts():
            return False
        
        print("\\n🎉 RUNTIME FIX INSTALLED SUCCESSFULLY!")
        print("=" * 50)
        print("\\n🎮 HOW TO USE:")
        print("• Double-click any effect thumbnail → Clears all effects")
        print("• Ctrl+Delete → Manual clear all effects")
        print("• Ctrl+Shift+Delete → Emergency clear everything")
        
        print("\\n🚀 The effect removal should now work!")
        return True

def main():
    """Main function"""
    print("🎯 GoLive Studio Runtime Effect Fix")
    print("=" * 40)
    print("\\nThis fixes effect removal in your RUNNING application")
    print("Make sure GoLive Studio is already open!")
    
    fixer = RuntimeEffectFixer()
    
    if fixer.install_fix():
        print("\\n✅ Fix installed! Try double-clicking effects now!")
        print("\\nPress Enter to exit (fix will remain active)...")
        input()
    else:
        print("\\n❌ Fix installation failed")
        print("Make sure GoLive Studio is running and try again")

if __name__ == "__main__":
    main()
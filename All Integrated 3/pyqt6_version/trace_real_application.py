#!/usr/bin/env python3
"""
Trace the real running GoLive Studio application to understand how effects work
"""

import sys
import os
import time
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QFrame
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap

def trace_running_application():
    """Find and analyze the currently running GoLive Studio application"""
    
    print("🔍 TRACING REAL GOLIVE STUDIO APPLICATION")
    print("=" * 60)
    
    # Check if there's already a running QApplication
    app = QApplication.instance()
    if app is None:
        print("❌ No Qt application is currently running")
        print("Please start GoLive Studio first, then run this script")
        return False
    
    print("✅ Found running Qt application")
    
    # Find all top-level windows
    top_level_widgets = app.topLevelWidgets()
    print(f"📋 Found {len(top_level_widgets)} top-level widgets")
    
    main_window = None
    for widget in top_level_widgets:
        if widget.isVisible() and widget.windowTitle():
            print(f"  - {widget.windowTitle()}: {type(widget).__name__} ({widget.size()})")
            if "golive" in widget.windowTitle().lower() or "studio" in widget.windowTitle().lower():
                main_window = widget
    
    if not main_window:
        # Try to find the largest visible window
        largest_widget = None
        largest_size = 0
        for widget in top_level_widgets:
            if widget.isVisible():
                size = widget.size()
                area = size.width() * size.height()
                if area > largest_size:
                    largest_size = area
                    largest_widget = widget
        
        if largest_widget:
            main_window = largest_widget
            print(f"✅ Using largest visible window: {type(main_window).__name__}")
    
    if not main_window:
        print("❌ Could not find main GoLive Studio window")
        return False
    
    print(f"✅ Found main window: {main_window.windowTitle() or 'Untitled'}")
    print(f"   Type: {type(main_window).__name__}")
    print(f"   Size: {main_window.size()}")
    
    # Analyze the window structure
    print("\\n📋 Analyzing window structure...")
    
    # Find all frames (potential output areas)
    frames = main_window.findChildren(QFrame)
    print(f"Found {len(frames)} frames:")
    
    output_candidates = []
    for i, frame in enumerate(frames):
        size = frame.size()
        area = size.width() * size.height()
        if area > 100000:  # Large frames only
            output_candidates.append((frame, area))
            print(f"  Frame {i}: {size} (area: {area}) - Visible: {frame.isVisible()}")
    
    # Sort by size
    output_candidates.sort(key=lambda x: x[1], reverse=True)
    
    if output_candidates:
        main_output = output_candidates[0][0]
        print(f"\\n✅ Main output candidate: {main_output.size()}")
        
        # Check what's inside this frame
        children = main_output.findChildren(QWidget)
        print(f"   Children: {len(children)}")
        
        # Look for labels with pixmaps (potential effects)
        effect_labels = []
        for child in children:
            if isinstance(child, QLabel) and child.pixmap():
                effect_labels.append(child)
        
        print(f"   Labels with pixmaps: {len(effect_labels)}")
        
        # Look for the effect thumbnails at the bottom
        print("\\n📋 Looking for effect thumbnails...")
        all_labels = main_window.findChildren(QLabel)
        thumbnail_labels = []
        
        for label in all_labels:
            if label.pixmap() and not label.pixmap().isNull():
                size = label.size()
                # Effect thumbnails are typically smaller
                if 50 < size.width() < 300 and 50 < size.height() < 200:
                    thumbnail_labels.append(label)
        
        print(f"Found {len(thumbnail_labels)} potential effect thumbnails")
        
        # Try to hook into the thumbnail clicks
        print("\\n📋 Setting up effect removal hooks...")
        
        def create_effect_remover(label, index):
            """Create an effect remover for a specific label"""
            original_mousePressEvent = label.mousePressEvent
            click_count = 0
            last_click_time = 0
            
            def enhanced_mouse_event(event):
                nonlocal click_count, last_click_time
                
                current_time = time.time() * 1000
                
                # Call original event first
                if original_mousePressEvent:
                    original_mousePressEvent(event)
                
                # Handle double-click detection
                if event.button() == Qt.MouseButton.LeftButton:
                    if (current_time - last_click_time) < 300:  # Double-click
                        click_count = 0
                        print(f"🗑️ DOUBLE-CLICK DETECTED on thumbnail {index}")
                        
                        # Clear all effects from main output
                        clear_all_effects_from_output(main_output)
                        
                    else:  # Single click
                        click_count = 1
                        print(f"👆 Single-click on thumbnail {index}")
                    
                    last_click_time = current_time
            
            label.mousePressEvent = enhanced_mouse_event
            return label
        
        def clear_all_effects_from_output(output_frame):
            """Clear all effects from the output frame"""
            try:
                print("🧹 CLEARING ALL EFFECTS FROM OUTPUT...")
                
                cleared_count = 0
                
                # Method 1: Remove overlay labels
                for child in output_frame.findChildren(QLabel):
                    if child.pixmap() and not child.pixmap().isNull():
                        # Check if this is likely an effect overlay
                        parent = child.parent()
                        if parent == output_frame:
                            print(f"  Removing overlay label: {child.size()}")
                            child.hide()
                            child.deleteLater()
                            cleared_count += 1
                
                # Method 2: Clear any widgets with effects
                for child in output_frame.findChildren(QWidget):
                    if hasattr(child, 'clear_effect_overlay'):
                        child.clear_effect_overlay()
                        cleared_count += 1
                    elif hasattr(child, 'setPixmap'):
                        child.setPixmap(QPixmap())
                        cleared_count += 1
                
                # Method 3: Force repaint
                output_frame.update()
                output_frame.repaint()
                
                # Method 4: Clear from parent if needed
                parent = output_frame.parent()
                if parent:
                    parent.update()
                    parent.repaint()
                
                print(f"✅ CLEARED {cleared_count} effects from output!")
                
                # Schedule additional clears
                QTimer.singleShot(100, lambda: output_frame.update())
                QTimer.singleShot(200, lambda: output_frame.repaint())
                
            except Exception as e:
                print(f"❌ Error clearing effects: {e}")
        
        # Hook into all thumbnail labels
        hooked_count = 0
        for i, label in enumerate(thumbnail_labels[:20]):  # Limit to first 20
            try:
                create_effect_remover(label, i)
                hooked_count += 1
            except Exception as e:
                print(f"⚠️ Failed to hook label {i}: {e}")
        
        print(f"✅ Hooked into {hooked_count} effect thumbnails")
        
        # Add global keyboard shortcut
        try:
            from PyQt6.QtGui import QShortcut, QKeySequence
            
            clear_shortcut = QShortcut(QKeySequence("Ctrl+Delete"), main_window)
            clear_shortcut.activated.connect(lambda: clear_all_effects_from_output(main_output))
            
            print("✅ Added Ctrl+Delete shortcut for clearing effects")
            
        except Exception as e:
            print(f"⚠️ Shortcut creation failed: {e}")
        
        print("\\n🎯 REAL APPLICATION TRACING COMPLETE!")
        print("=" * 60)
        print("\\n📋 INSTRUCTIONS:")
        print("• Double-click any effect thumbnail to remove all effects")
        print("• Press Ctrl+Delete to manually clear all effects")
        print("• The hooks are now active in your running application")
        
        return True
    
    else:
        print("❌ No suitable output frame found")
        return False

def main():
    """Main function"""
    print("🎯 GoLive Studio Real Application Tracer")
    print("=" * 50)
    print("\\nThis script hooks into your RUNNING GoLive Studio application")
    print("Make sure GoLive Studio is already running before using this!")
    print("\\nPress Ctrl+C to exit")
    
    try:
        if trace_running_application():
            print("\\n✅ Successfully hooked into running application!")
            print("Try double-clicking effect thumbnails now!")
            
            # Keep the script running
            input("\\nPress Enter to exit...")
        else:
            print("\\n❌ Failed to hook into application")
    
    except KeyboardInterrupt:
        print("\\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\\n❌ Error: {e}")

if __name__ == "__main__":
    main()
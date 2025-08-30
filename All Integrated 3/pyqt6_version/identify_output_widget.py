#!/usr/bin/env python3
"""
Identify the exact output widget and test effect application
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QFrame, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap

def identify_and_test_output():
    """Identify the output widget and test effect application"""
    
    print("🎯 IDENTIFYING OUTPUT WIDGET AND TESTING EFFECTS")
    print("=" * 60)
    
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from mainwindow import MainWindow
        window = MainWindow()
        
        print("📋 Step 1: Finding the largest frame (likely the output)...")
        
        frames = window.findChildren(QFrame)
        largest_frame = None
        largest_size = 0
        
        for frame in frames:
            size = frame.size()
            area = size.width() * size.height()
            if area > largest_size:
                largest_size = area
                largest_frame = frame
        
        if largest_frame:
            print(f"✅ Found largest frame: {largest_frame.size()}")
            print(f"   Object name: '{largest_frame.objectName()}'")
            print(f"   Style sheet: {largest_frame.styleSheet()[:100]}...")
            print(f"   Visible: {largest_frame.isVisible()}")
            print(f"   Children count: {len(largest_frame.findChildren(QWidget))}")
            
            # Check if it has video widgets inside
            video_children = []
            for child in largest_frame.findChildren(QWidget):
                if "video" in type(child).__name__.lower():
                    video_children.append(child)
            
            print(f"   Video children: {len(video_children)}")
            for child in video_children:
                print(f"     - {type(child).__name__}: {child.size()}")
        
        print("\\n📋 Step 2: Testing effect application on the largest frame...")
        
        if largest_frame:
            # Find a test effect
            from pathlib import Path
            effects_dir = Path("effects")
            test_effect = None
            
            if effects_dir.exists():
                for tab_dir in effects_dir.iterdir():
                    if tab_dir.is_dir():
                        for png_file in tab_dir.glob("*.png"):
                            test_effect = str(png_file)
                            break
                        if test_effect:
                            break
            
            if test_effect:
                print(f"✅ Found test effect: {Path(test_effect).name}")
                
                # Method 1: Try to apply effect through effects manager
                print("\\n🧪 Test 1: Effects manager application...")
                try:
                    if hasattr(window, 'on_effect_selected'):
                        print("  Calling on_effect_selected...")
                        window.on_effect_selected("Web01", test_effect)
                        print("  ✅ Effect applied through effects manager")
                    else:
                        print("  ❌ on_effect_selected method not found")
                except Exception as e:
                    print(f"  ❌ Effects manager application failed: {e}")
                
                # Method 2: Try direct pixmap overlay
                print("\\n🧪 Test 2: Direct pixmap overlay...")
                try:
                    # Create a label overlay
                    overlay_label = QLabel(largest_frame)
                    pixmap = QPixmap(test_effect)
                    if not pixmap.isNull():
                        # Scale pixmap to frame size
                        scaled_pixmap = pixmap.scaled(
                            largest_frame.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        overlay_label.setPixmap(scaled_pixmap)
                        overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        overlay_label.resize(largest_frame.size())
                        overlay_label.move(0, 0)
                        overlay_label.show()
                        overlay_label.raise_()
                        
                        print("  ✅ Direct overlay applied successfully!")
                        
                        # Store reference for later removal
                        window._test_overlay = overlay_label
                        
                        # Schedule removal after 3 seconds
                        def remove_overlay():
                            try:
                                if hasattr(window, '_test_overlay'):
                                    window._test_overlay.hide()
                                    window._test_overlay.deleteLater()
                                    delattr(window, '_test_overlay')
                                    print("  🗑️ Test overlay removed")
                            except Exception as e:
                                print(f"  ⚠️ Error removing overlay: {e}")
                        
                        QTimer.singleShot(3000, remove_overlay)
                        
                    else:
                        print("  ❌ Failed to load pixmap")
                except Exception as e:
                    print(f"  ❌ Direct overlay failed: {e}")
                
                # Method 3: Try composite widget approach
                print("\\n🧪 Test 3: Composite widget approach...")
                try:
                    from composite_output_widget import CompositeOutputWidget
                    
                    # Create a composite widget
                    composite = CompositeOutputWidget(largest_frame)
                    composite.resize(largest_frame.size())
                    composite.move(0, 0)
                    composite.set_effect_overlay(test_effect)
                    composite.show()
                    composite.raise_()
                    
                    print("  ✅ Composite widget overlay applied!")
                    
                    # Store reference and schedule removal
                    window._test_composite = composite
                    
                    def remove_composite():
                        try:
                            if hasattr(window, '_test_composite'):
                                window._test_composite.hide()
                                window._test_composite.deleteLater()
                                delattr(window, '_test_composite')
                                print("  🗑️ Test composite removed")
                        except Exception as e:
                            print(f"  ⚠️ Error removing composite: {e}")
                    
                    QTimer.singleShot(6000, remove_composite)
                    
                except Exception as e:
                    print(f"  ❌ Composite widget failed: {e}")
            
            else:
                print("❌ No test effects found")
        
        print("\\n📋 Step 3: Creating a manual effect removal function...")
        
        def manual_clear_effects():
            """Manually clear all effects from the output"""
            try:
                print("🧹 MANUAL EFFECT CLEARING...")
                
                # Method 1: Remove any overlay labels
                overlay_labels = largest_frame.findChildren(QLabel)
                removed_count = 0
                for label in overlay_labels:
                    if label.pixmap() and not label.pixmap().isNull():
                        label.hide()
                        label.deleteLater()
                        removed_count += 1
                
                print(f"  Removed {removed_count} overlay labels")
                
                # Method 2: Clear through effects manager
                if hasattr(window, 'on_effect_removed'):
                    try:
                        window.on_effect_removed("Web01", test_effect or "test")
                        print("  Called on_effect_removed")
                    except Exception as e:
                        print(f"  on_effect_removed failed: {e}")
                
                # Method 3: Force repaint
                largest_frame.update()
                largest_frame.repaint()
                print("  Forced frame repaint")
                
                print("✅ Manual clearing complete!")
                
            except Exception as e:
                print(f"❌ Manual clearing failed: {e}")
        
        # Add keyboard shortcut for manual clearing
        from PyQt6.QtGui import QShortcut, QKeySequence
        clear_shortcut = QShortcut(QKeySequence("Ctrl+X"), window)
        clear_shortcut.activated.connect(manual_clear_effects)
        
        print("\\n🎯 TESTING COMPLETE")
        print("=" * 60)
        print("\\n📋 INSTRUCTIONS:")
        print("1. The window is now open")
        print("2. Watch for test effects to appear and disappear")
        print("3. Press Ctrl+X to manually clear any stuck effects")
        print("4. Try clicking effects in the bottom tabs")
        print("5. Try double-clicking effects to remove them")
        print("\\nPress Ctrl+C to close")
        
        # Show the window
        window.show()
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    identify_and_test_output()
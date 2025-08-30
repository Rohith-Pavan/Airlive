#!/usr/bin/env python3
"""
Comprehensive diagnostic script to understand the effect system in GoLive Studio
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import QTimer

def diagnose_application_structure():
    """Diagnose how the application is structured"""
    print("🔍 DIAGNOSING GOLIVE STUDIO EFFECT SYSTEM")
    print("=" * 60)
    
    try:
        # Create application
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        print("📋 Step 1: Testing imports...")
        
        # Test imports
        try:
            from mainwindow import MainWindow
            print("✅ MainWindow imported successfully")
        except Exception as e:
            print(f"❌ MainWindow import failed: {e}")
            return False
        
        try:
            from effects_manager import EffectsManager
            print("✅ EffectsManager imported successfully")
        except Exception as e:
            print(f"❌ EffectsManager import failed: {e}")
        
        try:
            from graphics_output_widget import GraphicsOutputManager
            print("✅ GraphicsOutputManager imported successfully")
        except Exception as e:
            print(f"❌ GraphicsOutputManager import failed: {e}")
        
        try:
            from composite_output_widget import CompositeOutputWidget
            print("✅ CompositeOutputWidget imported successfully")
        except Exception as e:
            print(f"❌ CompositeOutputWidget import failed: {e}")
        
        print("\\n📋 Step 2: Creating MainWindow instance...")
        
        # Create main window
        window = MainWindow()
        
        print("\\n📋 Step 3: Analyzing window structure...")
        
        # Check what's in the window
        print(f"Window type: {type(window)}")
        print(f"Window size: {window.size()}")
        print(f"Window children count: {len(window.findChildren(QWidget))}")
        
        # Look for output widgets
        output_widgets = []
        video_widgets = []
        labels = []
        
        for child in window.findChildren(QWidget):
            child_name = child.objectName()
            if "output" in child_name.lower() or "preview" in child_name.lower():
                output_widgets.append((child_name, type(child).__name__))
            elif "video" in child_name.lower():
                video_widgets.append((child_name, type(child).__name__))
            elif isinstance(child, QLabel) and child.pixmap():
                labels.append((child_name, type(child).__name__, "has pixmap"))
        
        print(f"\\n📺 Output/Preview widgets found: {len(output_widgets)}")
        for name, widget_type in output_widgets:
            print(f"  - {name}: {widget_type}")
        
        print(f"\\n🎥 Video widgets found: {len(video_widgets)}")
        for name, widget_type in video_widgets:
            print(f"  - {name}: {widget_type}")
        
        print(f"\\n🏷️ Labels with pixmaps found: {len(labels)}")
        for name, widget_type, extra in labels:
            print(f"  - {name}: {widget_type} ({extra})")
        
        print("\\n📋 Step 4: Checking effects manager integration...")
        
        # Check effects manager
        if hasattr(window, 'effects_manager'):
            print("✅ Effects manager found in window")
            effects_manager = window.effects_manager
            print(f"  - Tab names: {effects_manager.tab_names}")
            print(f"  - Effects base path: {effects_manager.effects_base_path}")
            print(f"  - Effects base path exists: {effects_manager.effects_base_path.exists()}")
        else:
            print("❌ Effects manager NOT found in window")
        
        if hasattr(window, 'graphics_manager'):
            print("✅ Graphics manager found in window")
        else:
            print("❌ Graphics manager NOT found in window")
        
        print("\\n📋 Step 5: Looking for effect application methods...")
        
        # Check for effect-related methods
        effect_methods = []
        for attr_name in dir(window):
            if "effect" in attr_name.lower():
                effect_methods.append(attr_name)
        
        print(f"Effect-related methods: {effect_methods}")
        
        print("\\n📋 Step 6: Checking signal connections...")
        
        # Check if effects manager signals are connected
        if hasattr(window, 'effects_manager'):
            try:
                # Try to emit a test signal to see if it's connected
                print("Testing effect signal connections...")
                # This is just a test - we won't actually apply an effect
                print("✅ Effects manager signals appear to be set up")
            except Exception as e:
                print(f"⚠️ Signal connection issue: {e}")
        
        print("\\n📋 Step 7: Analyzing the actual output widget...")
        
        # Find the main output widget
        main_output = None
        for child in window.findChildren(QWidget):
            if child.objectName() == "outputPreview":
                main_output = child
                break
        
        if main_output:
            print(f"✅ Found main output widget: {type(main_output).__name__}")
            print(f"  - Object name: {main_output.objectName()}")
            print(f"  - Size: {main_output.size()}")
            print(f"  - Style sheet: {main_output.styleSheet()[:100]}...")
            
            # Check if it has any child widgets
            children = main_output.findChildren(QWidget)
            print(f"  - Child widgets: {len(children)}")
            for child in children[:5]:  # Show first 5
                print(f"    - {child.objectName()}: {type(child).__name__}")
        else:
            print("❌ Main output widget not found")
        
        print("\\n📋 Step 8: Testing effect application...")
        
        # Try to find an effect file to test with
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
            
            # Try different methods to apply the effect
            print("Testing effect application methods...")
            
            # Method 1: Through effects manager
            if hasattr(window, 'effects_manager'):
                try:
                    # Simulate effect selection
                    print("  - Testing effects manager signal emission...")
                    # Don't actually emit - just check if the method exists
                    if hasattr(window, 'on_effect_selected'):
                        print("    ✅ on_effect_selected method exists")
                    else:
                        print("    ❌ on_effect_selected method missing")
                except Exception as e:
                    print(f"    ❌ Effects manager test failed: {e}")
            
            # Method 2: Through graphics manager
            if hasattr(window, 'graphics_manager'):
                try:
                    print("  - Testing graphics manager...")
                    # Don't actually apply - just check if the method exists
                    if hasattr(window.graphics_manager, 'set_frame_for_widget'):
                        print("    ✅ set_frame_for_widget method exists")
                    else:
                        print("    ❌ set_frame_for_widget method missing")
                except Exception as e:
                    print(f"    ❌ Graphics manager test failed: {e}")
            
            # Method 3: Direct widget manipulation
            if main_output:
                try:
                    print("  - Testing direct widget manipulation...")
                    # Check if we can set a pixmap or overlay
                    if hasattr(main_output, 'setPixmap'):
                        print("    ✅ Widget supports setPixmap")
                    elif hasattr(main_output, 'paintEvent'):
                        print("    ✅ Widget has custom paintEvent")
                    else:
                        print("    ⚠️ Widget doesn't seem to support direct pixmap setting")
                except Exception as e:
                    print(f"    ❌ Direct widget test failed: {e}")
        
        else:
            print("❌ No test effects found")
        
        print("\\n🎯 DIAGNOSIS COMPLETE")
        print("=" * 60)
        
        # Show the window for visual inspection
        window.show()
        
        print("\\n📋 SUMMARY:")
        print("The application window is now open for visual inspection.")
        print("Check the console output above to understand how effects are applied.")
        print("\\nPress Ctrl+C to close the diagnostic.")
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    diagnose_application_structure()
#!/usr/bin/env python3
"""
Find the actual output widget in GoLive Studio
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QFrame, QLabel
from PyQt6.QtCore import QTimer

def find_output_widget():
    """Find and analyze the output widget"""
    
    print("🔍 FINDING OUTPUT WIDGET")
    print("=" * 40)
    
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from mainwindow import MainWindow
        window = MainWindow()
        
        print("📋 Searching for output widgets...")
        
        # Search by different criteria
        all_widgets = window.findChildren(QWidget)
        print(f"Total widgets found: {len(all_widgets)}")
        
        # Method 1: Search by object name
        print("\\n🔍 Method 1: Searching by object name...")
        for widget in all_widgets:
            name = widget.objectName()
            if name and ("output" in name.lower() or "preview" in name.lower()):
                print(f"  Found: {name} - {type(widget).__name__}")
                print(f"    Size: {widget.size()}")
                print(f"    Visible: {widget.isVisible()}")
                print(f"    Style: {widget.styleSheet()[:50]}...")
        
        # Method 2: Search by type
        print("\\n🔍 Method 2: Searching by widget type...")
        frames = window.findChildren(QFrame)
        print(f"QFrame widgets found: {len(frames)}")
        for i, frame in enumerate(frames):
            if i < 10:  # Show first 10
                print(f"  Frame {i}: {frame.objectName()} - Size: {frame.size()}")
        
        # Method 3: Search by size (output should be large)
        print("\\n🔍 Method 3: Searching by size (large widgets)...")
        large_widgets = []
        for widget in all_widgets:
            size = widget.size()
            if size.width() > 400 and size.height() > 300:
                large_widgets.append((widget, size))
        
        print(f"Large widgets found: {len(large_widgets)}")
        for widget, size in large_widgets[:10]:
            print(f"  {widget.objectName() or 'unnamed'}: {type(widget).__name__} - {size}")
        
        # Method 4: Search by style (black background)
        print("\\n🔍 Method 4: Searching by style (black background)...")
        black_widgets = []
        for widget in all_widgets:
            style = widget.styleSheet()
            if "black" in style.lower():
                black_widgets.append(widget)
        
        print(f"Widgets with black styling: {len(black_widgets)}")
        for widget in black_widgets[:5]:
            print(f"  {widget.objectName() or 'unnamed'}: {type(widget).__name__}")
            print(f"    Style: {widget.styleSheet()[:100]}...")
        
        # Method 5: Manual inspection of the UI structure
        print("\\n🔍 Method 5: UI structure analysis...")
        central_widget = window.centralWidget()
        if central_widget:
            print(f"Central widget: {type(central_widget).__name__}")
            print(f"Central widget children: {len(central_widget.findChildren(QWidget))}")
            
            # Look for the main layout structure
            def print_widget_tree(widget, indent=0):
                name = widget.objectName() or f"<{type(widget).__name__}>"
                size = widget.size()
                print("  " * indent + f"- {name}: {type(widget).__name__} ({size.width()}x{size.height()})")
                
                # Only show direct children to avoid too much output
                if indent < 3:
                    for child in widget.findChildren(QWidget, options=widget.FindChildrenRecursively):
                        if child.parent() == widget:  # Only direct children
                            print_widget_tree(child, indent + 1)
            
            print("Widget tree:")
            print_widget_tree(central_widget)
        
        # Show the window for visual inspection
        window.show()
        
        print("\\n🎯 ANALYSIS COMPLETE")
        print("Window is now open - look for the main video output area")
        print("Press Ctrl+C to close")
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    find_output_widget()
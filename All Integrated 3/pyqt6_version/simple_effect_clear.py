#!/usr/bin/env python3
"""
Simple effect clearing utility for GoLive Studio
This creates a button that clears all effects from the output
"""

import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

def create_effect_clearer():
    """Create a simple window with a button to clear effects"""
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create a simple window
    window = QWidget()
    window.setWindowTitle("Effect Clearer")
    window.setGeometry(100, 100, 300, 100)
    
    layout = QVBoxLayout()
    
    # Create clear button
    clear_button = QPushButton("Clear All Effects from Output")
    clear_button.setStyleSheet("""
        QPushButton {
            background-color: #ff4444;
            color: white;
            font-size: 16px;
            font-weight: bold;
            padding: 10px;
            border: none;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #ff6666;
        }
    """)
    
    def clear_effects():
        """Clear all effects from the main application"""
        try:
            print("🧹 Clearing all effects...")
            
            # Find the main GoLive Studio window
            main_window = None
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'output_preview_widget'):
                    main_window = widget
                    break
            
            if not main_window:
                print("❌ Main GoLive Studio window not found!")
                print("Make sure GoLive Studio is running first.")
                return
            
            cleared_something = False
            
            # Method 1: Clear from output preview widget
            if hasattr(main_window, 'output_preview_widget') and main_window.output_preview_widget:
                output_widget = main_window.output_preview_widget
                
                # Clear graphics scene overlays
                if hasattr(output_widget, 'scene'):
                    scene = output_widget.scene()
                    if scene:
                        items_to_remove = []
                        for item in scene.items():
                            if hasattr(item, 'zValue') and item.zValue() > 0:
                                items_to_remove.append(item)
                        
                        for item in items_to_remove:
                            scene.removeItem(item)
                            cleared_something = True
                
                # Force repaint
                output_widget.update()
                output_widget.repaint()
            
            # Method 2: Clear from graphics manager
            if hasattr(main_window, 'graphics_manager'):
                main_window.graphics_manager.clear_all_frames()
                cleared_something = True
            
            # Method 3: Clear from any graphics output widgets
            try:
                from graphics_output_widget import GraphicsOutputWidget
                for widget in main_window.findChildren(GraphicsOutputWidget):
                    widget.clear_frame_overlay()
                    cleared_something = True
            except:
                pass
            
            # Method 4: Clear any QLabel pixmaps that might be overlays
            from PyQt6.QtWidgets import QLabel
            from PyQt6.QtGui import QPixmap
            for label in main_window.findChildren(QLabel):
                if label.pixmap() and not label.pixmap().isNull():
                    # Check if this might be an overlay (has high z-order or specific styling)
                    if "border" in label.styleSheet().lower() or "green" in label.styleSheet().lower():
                        label.setStyleSheet("")  # Clear border styling
                        cleared_something = True
            
            if cleared_something:
                print("✅ Effects cleared successfully!")
                clear_button.setText("✅ Effects Cleared!")
                # Reset button text after 2 seconds
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(2000, lambda: clear_button.setText("Clear All Effects from Output"))
            else:
                print("⚠️ No effects found to clear")
                clear_button.setText("⚠️ No Effects Found")
                QTimer.singleShot(2000, lambda: clear_button.setText("Clear All Effects from Output"))
                
        except Exception as e:
            print(f"❌ Error clearing effects: {e}")
            clear_button.setText("❌ Error Occurred")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: clear_button.setText("Clear All Effects from Output"))
    
    clear_button.clicked.connect(clear_effects)
    layout.addWidget(clear_button)
    
    # Add instructions
    from PyQt6.QtWidgets import QLabel
    instructions = QLabel("Instructions:\\n1. Start GoLive Studio\\n2. Apply an effect\\n3. Click the button above to clear it")
    instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(instructions)
    
    window.setLayout(layout)
    window.show()
    
    print("🎯 Effect Clearer Ready!")
    print("1. Make sure GoLive Studio is running")
    print("2. Apply an effect in GoLive Studio")
    print("3. Click the 'Clear All Effects' button")
    
    return app.exec()

if __name__ == "__main__":
    create_effect_clearer()
#!/usr/bin/env python3
"""
Test NewStreamSettingsDialog with HDMI functionality
"""

import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt

def test_new_stream_dialog():
    """Test the NewStreamSettingsDialog with HDMI support"""
    
    app = QApplication(sys.argv)
    
    # Create test window
    window = QWidget()
    window.setWindowTitle("Test New Stream Settings Dialog with HDMI")
    window.resize(400, 200)
    
    layout = QVBoxLayout(window)
    
    # Info label
    info_label = QLabel("Click the button to test the New Stream Settings Dialog with HDMI support")
    info_label.setWordWrap(True)
    layout.addWidget(info_label)
    
    def open_dialog():
        try:
            from new_stream_settings_dialog import NewStreamSettingsDialog
            
            dialog = NewStreamSettingsDialog("TestStream", window)
            
            def on_settings_saved(settings):
                print("Settings saved:")
                for key, value in settings.items():
                    print(f"  {key}: {value}")
                
                # Test HDMI specific settings
                if settings.get("is_hdmi", False):
                    print("\n✅ HDMI settings detected:")
                    print(f"  Display Index: {settings.get('hdmi_display_index')}")
                    print(f"  HDMI Mode: {settings.get('hdmi_mode')}")
                else:
                    print("\n📡 Regular streaming settings detected")
            
            dialog.settings_saved.connect(on_settings_saved)
            dialog.exec()
            
        except Exception as e:
            print(f"Error opening dialog: {e}")
            import traceback
            traceback.print_exc()
    
    # Test button
    test_button = QPushButton("Open New Stream Settings Dialog")
    test_button.clicked.connect(open_dialog)
    layout.addWidget(test_button)
    
    # Instructions
    instructions = QLabel("""
Instructions:
1. Click the button to open the dialog
2. Select "HDMI Display" from the Platform dropdown
3. Notice that URL/Key fields are hidden
4. HDMI Display and Mode options should appear
5. Try different platforms to see the UI changes
6. Save settings to test the functionality
    """)
    instructions.setWordWrap(True)
    layout.addWidget(instructions)
    
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_new_stream_dialog())
#!/usr/bin/env python3
"""
Test HDMI integration in the actual main application
"""

import sys
import subprocess
import time
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import QTimer, QThread, pyqtSignal

class MainAppHDMITester(QWidget):
    """Test HDMI functionality with the main application"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main App HDMI Integration Test")
        self.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Main Application HDMI Integration Test")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("""
This test verifies HDMI integration in the main GoLive Studio application:

1. The main app should be running with HDMI display detection
2. Stream settings should show "HDMI Display" option
3. HDMI streaming should work through the main interface

Check the main application for HDMI functionality.
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Test button
        test_btn = QPushButton("Test HDMI Settings Dialog Integration")
        test_btn.clicked.connect(self.test_hdmi_dialog)
        layout.addWidget(test_btn)
        
        # Status
        self.status = QTextEdit()
        self.status.setMaximumHeight(150)
        layout.addWidget(self.status)
        
        # Check main app status
        self.check_main_app_status()
    
    def check_main_app_status(self):
        """Check if main app components are available"""
        try:
            # Test import of main components
            from new_stream_settings_dialog import NewStreamSettingsDialog
            from display_manager import DisplayManager
            from hdmi_stream_manager import HDMIStreamManager
            
            self.log("✅ All HDMI components imported successfully")
            
            # Test display detection
            display_manager = DisplayManager()
            displays = display_manager.get_displays()
            self.log(f"✅ Display detection: {len(displays)} displays found")
            
            for display in displays:
                self.log(f"   - {display.display_name}")
            
            if len(displays) > 1:
                self.log("✅ Multiple displays available for HDMI streaming")
            else:
                self.log("⚠️ Only one display - HDMI may not be testable")
                
        except Exception as e:
            self.log(f"❌ Component check failed: {e}")
    
    def test_hdmi_dialog(self):
        """Test HDMI settings dialog"""
        try:
            from new_stream_settings_dialog import NewStreamSettingsDialog
            
            dialog = NewStreamSettingsDialog("TestHDMI", self)
            
            def on_settings_saved(settings):
                self.log("Settings saved:")
                for key, value in settings.items():
                    self.log(f"  {key}: {value}")
                
                if settings.get("is_hdmi", False):
                    self.log("✅ HDMI settings detected and saved successfully!")
                    self.log(f"   Display: {settings.get('hdmi_display_index')}")
                    self.log(f"   Mode: {settings.get('hdmi_mode')}")
                else:
                    self.log("📡 Regular streaming settings")
            
            dialog.settings_saved.connect(on_settings_saved)
            
            self.log("🎛️ Opening HDMI settings dialog...")
            self.log("   Select 'HDMI Display' platform to test HDMI functionality")
            
            dialog.exec()
            
        except Exception as e:
            self.log(f"❌ Dialog test failed: {e}")
            import traceback
            traceback.print_exc()
    
    def log(self, message):
        """Log message"""
        self.status.append(message)
        print(message)

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    tester = MainAppHDMITester()
    tester.show()
    
    print("Main Application HDMI Integration Test")
    print("=" * 50)
    print("Testing HDMI functionality in the main GoLive Studio application")
    print("Make sure the main application (main.py) is running")
    print("=" * 50)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
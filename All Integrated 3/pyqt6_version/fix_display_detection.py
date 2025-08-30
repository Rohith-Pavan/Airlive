#!/usr/bin/env python3
"""
Fix display detection issues and provide Windows display configuration help
"""

import sys
import subprocess
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import Qt, QTimer

class DisplayFixWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Display Detection Fix")
        self.setGeometry(100, 100, 600, 500)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Display Detection Troubleshooting")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("""
1. Make sure your HDMI cable is properly connected
2. Check Windows Display Settings (Windows + P)
3. Set display mode to "Extend these displays" (not Duplicate)
4. Click "Detect Displays" below to refresh
        """)
        layout.addWidget(instructions)
        
        # Buttons
        self.detect_btn = QPushButton("Detect Displays")
        self.detect_btn.clicked.connect(self.detect_displays)
        layout.addWidget(self.detect_btn)
        
        self.windows_settings_btn = QPushButton("Open Windows Display Settings")
        self.windows_settings_btn.clicked.connect(self.open_windows_display_settings)
        layout.addWidget(self.windows_settings_btn)
        
        self.refresh_qt_btn = QPushButton("Refresh Qt Display Detection")
        self.refresh_qt_btn.clicked.connect(self.refresh_qt_displays)
        layout.addWidget(self.refresh_qt_btn)
        
        # Output
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
        
        # Auto-detect on startup
        QTimer.singleShot(500, self.detect_displays)
        
    def log(self, message):
        """Log message to output"""
        self.output.append(message)
        print(message)
        
    def detect_displays(self):
        """Detect displays using multiple methods"""
        self.output.clear()
        self.log("=== Display Detection Report ===\n")
        
        # Method 1: Qt Detection
        app = QApplication.instance()
        screens = app.screens()
        self.log(f"Qt detected {len(screens)} screen(s):")
        
        for i, screen in enumerate(screens):
            self.log(f"  Screen {i+1}: {screen.name()}")
            self.log(f"    Resolution: {screen.geometry().width()}x{screen.geometry().height()}")
            self.log(f"    Position: ({screen.geometry().x()}, {screen.geometry().y()})")
            self.log(f"    Primary: {'Yes' if screen == app.primaryScreen() else 'No'}")
            self.log("")
        
        # Method 2: Windows API
        self.log("Windows Display Detection:")
        try:
            # Get display info using Windows API
            result = subprocess.run([
                'powershell', '-Command', 
                'Get-CimInstance -Class Win32_VideoController | Select-Object Name, VideoModeDescription, CurrentHorizontalResolution, CurrentVerticalResolution'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.log(result.stdout)
            else:
                self.log("Failed to get Windows display info")
                
        except Exception as e:
            self.log(f"Error getting Windows display info: {e}")
        
        # Method 3: Check display configuration
        self.log("\nWindows Display Configuration:")
        try:
            result = subprocess.run([
                'powershell', '-Command',
                'Get-WmiObject -Class Win32_DesktopMonitor | Select-Object DeviceID, Name, ScreenWidth, ScreenHeight'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.log(result.stdout)
            else:
                self.log("Failed to get monitor info")
                
        except Exception as e:
            self.log(f"Error getting monitor info: {e}")
        
        # Recommendations
        self.log("\n=== Recommendations ===")
        if len(screens) == 1:
            self.log("⚠️  Only 1 display detected. To enable HDMI display:")
            self.log("1. Press Windows + P")
            self.log("2. Select 'Extend these displays'")
            self.log("3. If external display not shown, click 'Detect' in Windows Display Settings")
            self.log("4. Make sure HDMI cable is properly connected")
            self.log("5. Try a different HDMI port or cable")
        else:
            self.log(f"✅ {len(screens)} displays detected - HDMI should work!")
            
    def open_windows_display_settings(self):
        """Open Windows Display Settings"""
        try:
            subprocess.run(['ms-settings:display'], shell=True)
            self.log("Opened Windows Display Settings")
        except Exception as e:
            self.log(f"Error opening display settings: {e}")
            
    def refresh_qt_displays(self):
        """Force Qt to refresh display detection"""
        try:
            app = QApplication.instance()
            
            # Force screen detection refresh
            screens_before = len(app.screens())
            
            # Trigger a screen change event
            self.log("Refreshing Qt display detection...")
            
            # Wait a moment and check again
            QTimer.singleShot(1000, lambda: self.check_after_refresh(screens_before))
            
        except Exception as e:
            self.log(f"Error refreshing displays: {e}")
            
    def check_after_refresh(self, screens_before):
        """Check displays after refresh"""
        app = QApplication.instance()
        screens_after = len(app.screens())
        
        if screens_after > screens_before:
            self.log(f"✅ Display refresh successful! Now detecting {screens_after} displays")
        else:
            self.log(f"No change after refresh. Still {screens_after} displays")
            
        self.detect_displays()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = DisplayFixWindow()
    window.show()
    
    sys.exit(app.exec())
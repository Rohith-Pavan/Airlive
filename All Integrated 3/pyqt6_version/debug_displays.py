#!/usr/bin/env python3
"""
Debug script to check display detection
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QScreen

def debug_displays():
    app = QApplication(sys.argv)
    
    print("=== Display Detection Debug ===")
    
    # Get all screens
    screens = app.screens()
    print(f"Total screens detected by Qt: {len(screens)}")
    
    for i, screen in enumerate(screens):
        print(f"\nScreen {i}:")
        print(f"  Name: {screen.name()}")
        print(f"  Geometry: {screen.geometry()}")
        print(f"  Available Geometry: {screen.availableGeometry()}")
        print(f"  Device Pixel Ratio: {screen.devicePixelRatio()}")
        print(f"  Is Primary: {screen == app.primaryScreen()}")
        print(f"  Manufacturer: {screen.manufacturer()}")
        print(f"  Model: {screen.model()}")
        print(f"  Serial Number: {screen.serialNumber()}")
    
    # Check primary screen
    primary = app.primaryScreen()
    if primary:
        print(f"\nPrimary Screen: {primary.name()}")
    
    print("\n=== Windows Display Check ===")
    try:
        import subprocess
        result = subprocess.run(['powershell', '-Command', 'Get-WmiObject -Class Win32_DesktopMonitor | Select-Object Name, ScreenWidth, ScreenHeight'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("Windows WMI Display Info:")
            print(result.stdout)
        else:
            print("Failed to get Windows display info")
    except Exception as e:
        print(f"Error getting Windows display info: {e}")
    
    print("\n=== Qt Screen Change Test ===")
    print("Connect/disconnect your HDMI display now...")
    print("Watching for screen changes for 30 seconds...")
    
    def on_screen_added(screen):
        print(f"Screen ADDED: {screen.name()} - {screen.geometry()}")
    
    def on_screen_removed(screen):
        print(f"Screen REMOVED: {screen.name()}")
    
    app.screenAdded.connect(on_screen_added)
    app.screenRemoved.connect(on_screen_removed)
    
    # Run for 30 seconds to catch changes
    from PyQt6.QtCore import QTimer
    timer = QTimer()
    timer.timeout.connect(lambda: print(f"Current screen count: {len(app.screens())}"))
    timer.start(2000)  # Check every 2 seconds
    
    exit_timer = QTimer()
    exit_timer.timeout.connect(app.quit)
    exit_timer.start(30000)  # Exit after 30 seconds
    
    app.exec()

if __name__ == "__main__":
    debug_displays()
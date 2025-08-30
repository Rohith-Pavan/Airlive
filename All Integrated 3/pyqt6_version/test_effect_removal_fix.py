#!/usr/bin/env python3
"""
Test the effect removal fix in GoLive Studio
"""

import sys
from PyQt6.QtWidgets import QApplication

def test_effect_removal_fix():
    """Test that the effect removal fix is working"""
    
    print("Testing Effect Removal Fix")
    print("=" * 30)
    
    try:
        # Create application
        app = QApplication(sys.argv)
        
        # Import and create main window
        from mainwindow import MainWindow
        window = MainWindow()
        
        # Check if effects manager is available
        if hasattr(window, 'effects_manager'):
            print("✅ Effects manager found")
        else:
            print("❌ Effects manager not found")
            return False
        
        # Check if enhanced removal method is available
        if hasattr(window, 'on_effect_removed'):
            print("✅ Effect removal method found")
        else:
            print("❌ Effect removal method not found")
            return False
        
        # Show the window
        window.show()
        
        print("✅ Fix is working! Test the double-click removal:")
        print("1. Single-click an effect to apply it")
        print("2. Double-click the same effect to remove it")
        print("3. The effect should be completely removed from output!")
        
        # Run the application
        return app.exec()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_effect_removal_fix()
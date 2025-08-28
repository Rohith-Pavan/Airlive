#!/usr/bin/env python3
"""
Quick test to verify StreamControlWidget functionality
"""

import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PyQt6.QtCore import QObject
from stream_manager import StreamManager, StreamControlWidget

def test_stream_control():
    app = QApplication(sys.argv)
    
    # Create a simple test window
    window = QWidget()
    layout = QVBoxLayout(window)
    
    # Create test button
    test_button = QPushButton("Test Stream Button")
    layout.addWidget(test_button)
    
    # Create stream manager and control
    stream_manager = StreamManager()
    stream_control = StreamControlWidget("TestStream", stream_manager, window)
    
    # Test set_stream_button method
    print("Testing set_stream_button method...")
    try:
        stream_control.set_stream_button(test_button)
        print("✅ set_stream_button method works!")
        
        # Test available methods
        methods = [m for m in dir(stream_control) if not m.startswith('_')]
        print(f"Available methods: {methods}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    window.show()
    return app.exec()

if __name__ == "__main__":
    test_stream_control()

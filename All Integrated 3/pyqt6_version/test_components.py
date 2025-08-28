#!/usr/bin/env python3
"""
Test script for GoLive Studio components
Validates core functionality without full GUI launch
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

def test_imports():
    """Test that all modules can be imported successfully"""
    print("Testing imports...")
    try:
        from main import VideoInputManager
        from mainwindow import MainWindow
        from graphics_output_widget import GraphicsOutputManager
        from effects_manager import EffectsManager
        from stream_manager import StreamManager
        from stream_settings_dialog import StreamSettingsDialog
        from ffmpeg_locator import locate_ffmpeg
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_ffmpeg_location():
    """Test FFmpeg location and availability"""
    print("\nTesting FFmpeg location...")
    try:
        from ffmpeg_locator import locate_ffmpeg
        ffmpeg_path = locate_ffmpeg()
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            print(f"✓ FFmpeg found at: {ffmpeg_path}")
            return True
        else:
            print("✗ FFmpeg not found")
            return False
    except Exception as e:
        print(f"✗ FFmpeg location error: {e}")
        return False

def test_effects_loading():
    """Test effects directory and PNG loading"""
    print("\nTesting effects loading...")
    try:
        effects_dir = Path("effects")
        if not effects_dir.exists():
            print("✗ Effects directory not found")
            return False
        
        categories = [d.name for d in effects_dir.iterdir() if d.is_dir()]
        print(f"✓ Found effect categories: {categories}")
        
        total_effects = 0
        for category in categories:
            png_files = list((effects_dir / category).glob("*.png"))
            total_effects += len(png_files)
            print(f"  - {category}: {len(png_files)} PNG files")
        
        print(f"✓ Total effects loaded: {total_effects}")
        return True
    except Exception as e:
        print(f"✗ Effects loading error: {e}")
        return False

def test_video_input_manager():
    """Test VideoInputManager initialization"""
    print("\nTesting VideoInputManager...")
    try:
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        
        from main import VideoInputManager
        manager = VideoInputManager()
        print("✓ VideoInputManager created successfully")
        
        # Test camera enumeration
        from PyQt6.QtMultimedia import QMediaDevices
        cameras = QMediaDevices.videoInputs()
        print(f"✓ Found {len(cameras)} camera devices")
        
        return True
    except Exception as e:
        print(f"✗ VideoInputManager error: {e}")
        return False

def test_graphics_output():
    """Test GraphicsOutputManager initialization"""
    print("\nTesting GraphicsOutputManager...")
    try:
        from graphics_output_widget import GraphicsOutputManager
        manager = GraphicsOutputManager()
        print("✓ GraphicsOutputManager created successfully")
        return True
    except Exception as e:
        print(f"✗ GraphicsOutputManager error: {e}")
        return False

def test_stream_manager():
    """Test StreamManager initialization"""
    print("\nTesting StreamManager...")
    try:
        from stream_manager import StreamManager
        manager = StreamManager()
        print("✓ StreamManager created successfully")
        return True
    except Exception as e:
        print(f"✗ StreamManager error: {e}")
        return False

def main():
    """Run all component tests"""
    print("GoLive Studio Component Testing")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_ffmpeg_location,
        test_effects_loading,
        test_video_input_manager,
        test_graphics_output,
        test_stream_manager
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All components are working correctly!")
        return 0
    else:
        print("✗ Some components have issues that need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())

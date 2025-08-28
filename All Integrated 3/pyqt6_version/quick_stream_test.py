#!/usr/bin/env python3
"""
Quick streaming test - Validate new streaming system works
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test if all modules can be imported"""
    print("Testing imports...")
    
    try:
        from new_stream_manager import NewStreamManager, NewStreamControlWidget
        print("✅ new_stream_manager imported successfully")
    except Exception as e:
        print(f"❌ new_stream_manager import failed: {e}")
        return False
    
    try:
        from new_stream_settings_dialog import NewStreamSettingsDialog
        print("✅ new_stream_settings_dialog imported successfully")
    except Exception as e:
        print(f"❌ new_stream_settings_dialog import failed: {e}")
        return False
    
    try:
        from ffmpeg_locator import find_ffmpeg, ensure_ffmpeg_available
        print("✅ ffmpeg_locator imported successfully")
    except Exception as e:
        print(f"❌ ffmpeg_locator import failed: {e}")
        return False
    
    return True

def test_ffmpeg():
    """Test FFmpeg availability"""
    print("\nTesting FFmpeg...")
    
    try:
        from ffmpeg_locator import find_ffmpeg, ensure_ffmpeg_available
        
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path:
            print(f"✅ FFmpeg found at: {ffmpeg_path}")
            return True
        else:
            print("⚠️ FFmpeg not found, attempting download...")
            ffmpeg_path = ensure_ffmpeg_available(auto_download=True)
            if ffmpeg_path:
                print(f"✅ FFmpeg downloaded to: {ffmpeg_path}")
                return True
            else:
                print("❌ FFmpeg download failed")
                return False
    except Exception as e:
        print(f"❌ FFmpeg test error: {e}")
        return False

def test_basic_functionality():
    """Test basic streaming functionality"""
    print("\nTesting basic functionality...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        from new_stream_manager import NewStreamManager
        
        # Create QApplication
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        
        # Create stream manager
        manager = NewStreamManager()
        print("✅ Stream manager created")
        
        # Test settings validation
        valid_settings = {
            "url": "rtmp://live.twitch.tv/live/",
            "key": "test_key_123",
            "resolution": "1920x1080",
            "fps": 30,
            "video_bitrate": 2500,
            "audio_bitrate": 128
        }
        
        success = manager.configure_stream("TestStream", valid_settings)
        if success:
            print("✅ Stream configuration successful")
        else:
            print("❌ Stream configuration failed")
            return False
        
        # Test invalid settings
        invalid_settings = valid_settings.copy()
        del invalid_settings["url"]
        
        success = manager.configure_stream("TestStream2", invalid_settings)
        if not success:
            print("✅ Invalid settings properly rejected")
        else:
            print("❌ Invalid settings not rejected")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test error: {e}")
        return False

def main():
    """Run quick tests"""
    print("🚀 Quick Streaming System Test")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("FFmpeg Test", test_ffmpeg),
        ("Basic Functionality Test", test_basic_functionality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 40)
    print(f"🏁 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Streaming system is ready.")
    else:
        print("⚠️ Some tests failed. Check the output above.")
    
    print("=" * 40)

if __name__ == "__main__":
    main()

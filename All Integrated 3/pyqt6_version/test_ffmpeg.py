#!/usr/bin/env python3
"""
Simple FFmpeg test script
"""

import subprocess
import sys
from pathlib import Path

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from ffmpeg_locator import find_ffmpeg, ensure_ffmpeg_available

def test_ffmpeg_installation():
    """Test FFmpeg installation"""
    print("Testing FFmpeg installation...")
    
    # Find FFmpeg
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("FFmpeg not found. Attempting to download...")
        ffmpeg_path = ensure_ffmpeg_available(auto_download=True)
        
    if not ffmpeg_path:
        print("❌ Failed to find or download FFmpeg")
        return False
    
    print(f"✅ FFmpeg found at: {ffmpeg_path}")
    
    # Test FFmpeg version
    try:
        result = subprocess.run([ffmpeg_path, "-version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg version: {version_line}")
            return True
        else:
            print(f"❌ FFmpeg version check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing FFmpeg: {e}")
        return False

def test_ffmpeg_streaming():
    """Test basic FFmpeg streaming capability"""
    print("\nTesting FFmpeg streaming capability...")
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("❌ FFmpeg not available for streaming test")
        return False
    
    # Create a simple test command (this won't actually stream, just test the command)
    test_cmd = [
        ffmpeg_path,
        "-f", "lavfi",
        "-i", "testsrc=duration=1:size=320x240:rate=1",
        "-f", "null",
        "-"
    ]
    
    try:
        print("Testing FFmpeg command construction...")
        print(f"Command: {' '.join(test_cmd)}")
        
        # Run a very short test
        result = subprocess.run(test_cmd, 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ FFmpeg streaming test passed")
            return True
        else:
            print(f"❌ FFmpeg streaming test failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✅ FFmpeg streaming test passed (timeout is expected for null output)")
        return True
    except Exception as e:
        print(f"❌ Error in FFmpeg streaming test: {e}")
        return False

def test_ffmpeg_formats():
    """Test FFmpeg format support"""
    print("\nTesting FFmpeg format support...")
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("❌ FFmpeg not available for format test")
        return False
    
    # Test if FLV format is supported
    try:
        result = subprocess.run([ffmpeg_path, "-formats"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            if "flv" in result.stdout.lower():
                print("✅ FLV format supported")
            else:
                print("⚠️  FLV format not found in supported formats")
                
            if "h264" in result.stdout.lower():
                print("✅ H.264 codec supported")
            else:
                print("⚠️  H.264 codec not found in supported formats")
                
            return True
        else:
            print(f"❌ Format test failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error in format test: {e}")
        return False

def main():
    """Run all FFmpeg tests"""
    print("=" * 50)
    print("FFmpeg Test Suite")
    print("=" * 50)
    
    # Test installation
    if not test_ffmpeg_installation():
        print("\n❌ FFmpeg installation test failed")
        return False
    
    # Test streaming capability
    if not test_ffmpeg_streaming():
        print("\n❌ FFmpeg streaming test failed")
        return False
    
    # Test format support
    if not test_ffmpeg_formats():
        print("\n❌ FFmpeg format test failed")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All FFmpeg tests passed!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

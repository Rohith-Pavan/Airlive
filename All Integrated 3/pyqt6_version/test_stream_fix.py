#!/usr/bin/env python3
"""
Test streaming fixes
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_ffmpeg_command():
    """Test FFmpeg command building"""
    from stream_manager import StreamCaptureThread
    
    # Test settings
    test_settings = {
        'platform': 'YouTube Live',
        'url': 'rtmp://a.rtmp.youtube.com/live2/',
        'key': 'test-key',
        'resolution': '1920x1080',
        'fps': 30,
        'video_bitrate': 2500,
        'audio_bitrate': 128,
        'sample_rate': 44100,
        'codec': 'libx264',
        'preset': 'ultrafast',
        'profile': 'baseline'
    }
    
    # Create thread (without graphics view for testing)
    thread = StreamCaptureThread(None, test_settings)
    
    # Test command building
    cmd = thread.build_ffmpeg_command(test_settings)
    if cmd:
        print("✓ FFmpeg command built successfully")
        print(f"Command: {' '.join(cmd)}")
        return True
    else:
        print("✗ Failed to build FFmpeg command")
        return False

def test_ffmpeg_installation():
    """Test FFmpeg installation"""
    from ffmpeg_locator import find_ffmpeg
    
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        print(f"✓ FFmpeg found at: {ffmpeg_path}")
        return True
    else:
        print("✗ FFmpeg not found")
        return False

def main():
    print("Testing streaming fixes...")
    print("=" * 50)
    
    # Test 1: FFmpeg installation
    print("\n1. Testing FFmpeg installation:")
    ffmpeg_ok = test_ffmpeg_installation()
    
    # Test 2: Command building
    print("\n2. Testing FFmpeg command building:")
    command_ok = test_ffmpeg_command()
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"FFmpeg installation: {'✓ OK' if ffmpeg_ok else '✗ FAILED'}")
    print(f"Command building: {'✓ OK' if command_ok else '✗ FAILED'}")
    
    if ffmpeg_ok and command_ok:
        print("\n✓ All tests passed! Streaming should work now.")
    else:
        print("\n✗ Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main()

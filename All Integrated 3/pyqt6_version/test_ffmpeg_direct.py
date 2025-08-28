#!/usr/bin/env python3
"""
Direct FFmpeg command test to isolate streaming issues
"""

import sys
import os
import subprocess
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ffmpeg_locator import find_ffmpeg

def test_ffmpeg_installation():
    """Test FFmpeg installation and capabilities"""
    print("=== TESTING FFMPEG INSTALLATION ===")
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("✗ FFmpeg not found!")
        return False
    
    print(f"✓ FFmpeg found at: {ffmpeg_path}")
    
    # Test version
    try:
        result = subprocess.run(
            [ffmpeg_path, '-version'],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✓ {version_line}")
            
            # Check for required codecs
            if 'libx264' in result.stdout:
                print("✓ H.264 encoder available")
            else:
                print("⚠ H.264 encoder not found")
                
            if 'aac' in result.stdout:
                print("✓ AAC encoder available")
            else:
                print("⚠ AAC encoder not found")
                
        else:
            print(f"✗ FFmpeg version check failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ FFmpeg test failed: {e}")
        return False
    
    return True

def load_stream_settings():
    """Load stream settings from JSON file"""
    settings_file = Path("stream1_settings.json")
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            return json.load(f)
    else:
        # Default YouTube Live settings
        return {
            'platform': 'YouTube Live',
            'url': 'rtmp://a.rtmp.youtube.com/live2',
            'key': 'test-stream-key-placeholder',
            'resolution': '1920x1080',
            'fps': 30,
            'video_bitrate': 2500,
            'audio_bitrate': 128,
            'sample_rate': 44100,
            'codec': 'libx264',
            'preset': 'ultrafast',
            'format': 'rtmp'
        }

def build_test_ffmpeg_command(settings):
    """Build FFmpeg command exactly like the stream manager does"""
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return None
    
    try:
        # Parse resolution
        resolution = settings.get('resolution', '1920x1080')
        width, height = map(int, resolution.split('x'))
        fps = int(settings.get('fps', 30))
        video_bitrate = int(settings.get('video_bitrate', 2500))
        audio_bitrate = int(settings.get('audio_bitrate', 128))
        sample_rate = int(settings.get('sample_rate', 44100))
        
        # Build target URL
        url = settings.get('url', '').strip()
        key = settings.get('key', '').strip()
        
        if not url:
            print("✗ No RTMP URL provided")
            return None
            
        if key:
            target = url.rstrip('/') + '/' + key
        else:
            target = url
        
        print(f"Target URL: {target}")
        
        # Build command
        cmd = [
            ffmpeg_path,
            '-y',
            # Video input from stdin
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'rgb24',
            '-s', f'{width}x{height}',
            '-r', str(fps),
            '-i', '-',
            # Silent audio
            '-f', 'lavfi',
            '-i', f'anullsrc=channel_layout=stereo:sample_rate={sample_rate}',
            # Video encoding
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-profile:v', 'baseline',
            '-level', '3.0',
            '-pix_fmt', 'yuv420p',
            '-b:v', f'{video_bitrate}k',
            '-maxrate', f'{video_bitrate}k',
            '-bufsize', f'{video_bitrate}k',
            '-g', str(fps),
            '-keyint_min', str(fps),
            '-sc_threshold', '0',
            # Audio encoding
            '-c:a', 'aac',
            '-b:a', f'{audio_bitrate}k',
            '-ar', str(sample_rate),
            # RTMP output
            '-thread_queue_size', '512',
            '-probesize', '32',
            '-analyzeduration', '0',
            '-fflags', '+genpts+igndts',
            '-f', 'flv',
            '-flvflags', 'no_duration_filesize',
            target
        ]
        
        return cmd
        
    except Exception as e:
        print(f"✗ Error building command: {e}")
        return None

def test_rtmp_connection(settings):
    """Test RTMP connection to YouTube without sending video"""
    print("\n=== TESTING RTMP CONNECTION ===")
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return False
    
    # Build target URL
    url = settings.get('url', '').strip()
    key = settings.get('key', '').strip()
    
    if not url or not key:
        print("✗ Missing URL or stream key")
        return False
    
    target = url.rstrip('/') + '/' + key
    print(f"Testing connection to: {target}")
    
    # Create a minimal test command that just tries to connect
    test_cmd = [
        ffmpeg_path,
        '-f', 'lavfi',
        '-i', 'testsrc=duration=3:size=320x240:rate=1',  # 3 second test
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-b:v', '500k',
        '-f', 'flv',
        '-t', '3',
        target
    ]
    
    print(f"Test command: {' '.join(test_cmd)}")
    
    try:
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print(f"Stdout:\n{result.stdout}")
        
        if result.stderr:
            print(f"Stderr:\n{result.stderr}")
            
            # Analyze common errors
            stderr_lower = result.stderr.lower()
            if 'connection refused' in stderr_lower:
                print("\n❌ DIAGNOSIS: Connection refused - check firewall/network")
            elif 'unauthorized' in stderr_lower or 'invalid stream key' in stderr_lower:
                print("\n❌ DIAGNOSIS: Invalid stream key or unauthorized")
            elif 'timeout' in stderr_lower:
                print("\n❌ DIAGNOSIS: Network timeout")
            elif 'rtmp handshake failed' in stderr_lower:
                print("\n❌ DIAGNOSIS: RTMP handshake failed")
            elif result.returncode == 0:
                print("\n✅ DIAGNOSIS: Connection successful!")
            else:
                print(f"\n⚠ DIAGNOSIS: Unknown error (code {result.returncode})")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⚠ Test timed out (may indicate connection issues)")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def main():
    """Main test function"""
    print("FFMPEG DIRECT STREAMING TEST\n")
    
    # Test 1: FFmpeg installation
    if not test_ffmpeg_installation():
        return 1
    
    # Test 2: Load settings
    print("\n=== LOADING STREAM SETTINGS ===")
    settings = load_stream_settings()
    print(f"Platform: {settings['platform']}")
    print(f"Resolution: {settings['resolution']}")
    print(f"FPS: {settings['fps']}")
    print(f"Video Bitrate: {settings['video_bitrate']} kbps")
    print(f"URL: {settings['url']}")
    print(f"Stream Key: {'*' * len(settings['key'])}")
    
    # Test 3: Build command
    print("\n=== BUILDING FFMPEG COMMAND ===")
    cmd = build_test_ffmpeg_command(settings)
    if not cmd:
        print("✗ Failed to build FFmpeg command")
        return 1
    
    print("✓ FFmpeg command built successfully")
    print(f"Command length: {len(' '.join(cmd))} characters")
    print(f"Full command:\n{' '.join(cmd)}")
    
    # Test 4: RTMP connection
    connection_success = test_rtmp_connection(settings)
    
    if connection_success:
        print("\n🎉 ALL TESTS PASSED - Streaming should work!")
    else:
        print("\n❌ CONNECTION TEST FAILED - Check stream key and network")
    
    return 0 if connection_success else 1

if __name__ == "__main__":
    sys.exit(main())

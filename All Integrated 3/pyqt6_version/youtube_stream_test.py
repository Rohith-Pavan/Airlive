#!/usr/bin/env python3
"""
YouTube Live streaming test with real stream key validation
"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ffmpeg_locator import find_ffmpeg

def get_youtube_stream_key():
    """Get YouTube stream key from user input"""
    print("=== YOUTUBE STREAM KEY SETUP ===")
    print("To test YouTube Live streaming, you need a valid stream key.")
    print("Get your stream key from: https://studio.youtube.com/channel/UC.../livestreaming")
    print()
    
    # Check if we have a saved key
    settings_file = Path("stream1_settings.json")
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            current_key = settings.get('key', '')
            if current_key and current_key != 'test-stream-key-placeholder':
                print(f"Current stream key: {current_key[:8]}...{current_key[-4:]}")
                use_current = input("Use current stream key? (y/n): ").lower().strip()
                if use_current == 'y':
                    return current_key
    
    # Get new key from user
    stream_key = input("Enter your YouTube Live stream key: ").strip()
    if not stream_key:
        print("No stream key provided, using test placeholder")
        return "test-stream-key-placeholder"
    
    # Save the key
    settings = {
        'platform': 'YouTube Live',
        'url': 'rtmp://a.rtmp.youtube.com/live2',
        'key': stream_key,
        'resolution': '1920x1080',
        'fps': 30,
        'video_bitrate': 2500,
        'audio_bitrate': 128,
        'sample_rate': 44100,
        'codec': 'libx264',
        'preset': 'ultrafast',
        'format': 'rtmp'
    }
    
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    print(f"Stream key saved to {settings_file}")
    return stream_key

def test_youtube_connection(stream_key):
    """Test connection to YouTube Live with actual stream key"""
    print(f"\n=== TESTING YOUTUBE LIVE CONNECTION ===")
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("✗ FFmpeg not found")
        return False
    
    # YouTube RTMP URL
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    print(f"Testing connection to YouTube Live...")
    print(f"Stream key: {stream_key[:8]}...{stream_key[-4:]}")
    
    # Create a 5-second test stream with color bars
    test_cmd = [
        ffmpeg_path,
        '-f', 'lavfi',
        '-i', 'testsrc=duration=5:size=1280x720:rate=30',
        '-f', 'lavfi', 
        '-i', 'sine=frequency=1000:duration=5',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-profile:v', 'baseline',
        '-pix_fmt', 'yuv420p',
        '-b:v', '2500k',
        '-maxrate', '2500k',
        '-bufsize', '2500k',
        '-g', '30',
        '-keyint_min', '30',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ar', '44100',
        '-f', 'flv',
        '-flvflags', 'no_duration_filesize',
        rtmp_url
    ]
    
    print(f"\nExecuting test command...")
    print(f"Command: {' '.join(test_cmd[:10])}... [truncated for readability]")
    
    try:
        print("Starting FFmpeg process...")
        process = subprocess.Popen(
            test_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Wait for process to complete or timeout
        try:
            stdout, stderr = process.communicate(timeout=15)
            
            print(f"Process completed with return code: {process.returncode}")
            
            if stdout:
                stdout_str = stdout.decode('utf-8', errors='ignore')
                print(f"FFmpeg output:\n{stdout_str}")
            
            if stderr:
                stderr_str = stderr.decode('utf-8', errors='ignore')
                print(f"FFmpeg errors:\n{stderr_str}")
                
                # Analyze the error output
                stderr_lower = stderr_str.lower()
                
                if process.returncode == 0:
                    print("\n✅ SUCCESS: YouTube Live connection test passed!")
                    print("Your stream key is valid and RTMP connection works.")
                    return True
                elif 'connection refused' in stderr_lower:
                    print("\n❌ ERROR: Connection refused")
                    print("Possible causes:")
                    print("- Firewall blocking RTMP traffic")
                    print("- Network restrictions")
                    print("- YouTube servers temporarily unavailable")
                elif 'unauthorized' in stderr_lower or 'invalid' in stderr_lower:
                    print("\n❌ ERROR: Authentication failed")
                    print("Possible causes:")
                    print("- Invalid stream key")
                    print("- Stream not started in YouTube Studio")
                    print("- Stream key expired or revoked")
                elif 'timeout' in stderr_lower:
                    print("\n❌ ERROR: Connection timeout")
                    print("Check your internet connection")
                elif 'rtmp' in stderr_lower and ('error' in stderr_lower or 'failed' in stderr_lower):
                    print("\n❌ ERROR: RTMP protocol error")
                    print("Check stream configuration")
                else:
                    print(f"\n⚠ WARNING: Unknown error (return code: {process.returncode})")
                
                return False
            
        except subprocess.TimeoutExpired:
            process.kill()
            print("\n⚠ Test timed out after 15 seconds")
            print("This might indicate network connectivity issues")
            return False
            
    except Exception as e:
        print(f"✗ Test execution failed: {e}")
        return False

def test_local_streaming():
    """Test streaming to a local file to verify FFmpeg pipeline"""
    print(f"\n=== TESTING LOCAL STREAMING PIPELINE ===")
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return False
    
    output_file = Path("test_stream_output.mp4")
    if output_file.exists():
        output_file.unlink()
    
    # Test command that saves to local file
    test_cmd = [
        ffmpeg_path,
        '-f', 'lavfi',
        '-i', 'testsrc=duration=3:size=1280x720:rate=30',
        '-f', 'lavfi',
        '-i', 'sine=frequency=1000:duration=3',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-c:a', 'aac',
        '-t', '3',
        str(output_file)
    ]
    
    print(f"Testing local file output...")
    
    try:
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0 and output_file.exists():
            file_size = output_file.stat().st_size
            print(f"✅ Local streaming test passed!")
            print(f"Output file: {output_file} ({file_size} bytes)")
            
            # Clean up
            output_file.unlink()
            return True
        else:
            print(f"✗ Local streaming test failed (code: {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Local test failed: {e}")
        return False

def main():
    """Main function"""
    print("🎥 YOUTUBE LIVE STREAMING DIAGNOSTIC TOOL\n")
    
    # Test 1: FFmpeg installation
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("❌ FFmpeg not found! Please install FFmpeg first.")
        return 1
    
    print(f"✅ FFmpeg found: {ffmpeg_path}")
    
    # Test 2: Local streaming pipeline
    if not test_local_streaming():
        print("❌ Local streaming pipeline failed")
        return 1
    
    # Test 3: Get stream key and test YouTube connection
    stream_key = get_youtube_stream_key()
    
    if stream_key == "test-stream-key-placeholder":
        print("\n⚠ Using placeholder stream key - YouTube connection will fail")
        print("To test actual streaming, provide a real YouTube Live stream key")
        return 0
    
    # Test actual YouTube connection
    success = test_youtube_connection(stream_key)
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("Your GoLive Studio should now be able to stream to YouTube Live.")
        print("Make sure to:")
        print("1. Start your live stream in YouTube Studio")
        print("2. Use the same stream key in GoLive Studio")
        print("3. Check that your stream appears live on YouTube")
    else:
        print("\n❌ STREAMING TEST FAILED")
        print("Check the error messages above for troubleshooting steps.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

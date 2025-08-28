#!/usr/bin/env python3
"""
Test stream credentials with FFmpeg directly
"""

import subprocess
import sys
import time
from pathlib import Path

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from ffmpeg_locator import find_ffmpeg

def test_stream_credentials(stream_url, stream_key, duration=10):
    """Test stream credentials with FFmpeg"""
    print("=" * 60)
    print("Stream Credentials Test")
    print("=" * 60)
    
    # Find FFmpeg
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("❌ FFmpeg not found")
        return False
    
    print(f"✅ FFmpeg found at: {ffmpeg_path}")
    
    # Build the full stream URL
    full_url = f"{stream_url.rstrip('/')}/{stream_key}"
    print(f"Stream URL: {stream_url}")
    print(f"Stream Key: {'*' * len(stream_key)}")
    print(f"Full URL: {stream_url.rstrip('/')}/{'*' * len(stream_key)}")
    
    # Create FFmpeg command for testing
    cmd = [
        ffmpeg_path,
        "-y",  # Overwrite output
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size=640x480:rate=1",
        "-f", "lavfi", 
        "-i", "sine=frequency=1000:duration=10",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-b:v", "1000k",
        "-c:a", "aac",
        "-b:a", "128k",
        "-f", "flv",
        full_url
    ]
    
    print(f"\nFFmpeg Command:")
    print(" ".join(cmd))
    
    print(f"\nStarting stream test (duration: {duration} seconds)...")
    print("This will attempt to connect to your streaming platform.")
    print("Check your streaming dashboard to see if the test stream appears.")
    
    try:
        # Start FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor the process
        start_time = time.time()
        while process.poll() is None and (time.time() - start_time) < duration + 5:
            # Read stderr for real-time output
            stderr_line = process.stderr.readline()
            if stderr_line:
                stderr_line = stderr_line.strip()
                if stderr_line:
                    print(f"FFmpeg: {stderr_line}")
            
            time.sleep(0.1)
        
        # Get final output
        stdout, stderr = process.communicate(timeout=5)
        
        if process.returncode == 0:
            print("\n✅ Stream test completed successfully!")
            print("Check your streaming platform dashboard to see if the test stream appeared.")
            return True
        else:
            print(f"\n❌ Stream test failed with return code: {process.returncode}")
            print("FFmpeg stderr output:")
            print(stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n⏰ Stream test timed out after {duration + 5} seconds")
        process.terminate()
        return False
    except Exception as e:
        print(f"\n❌ Error during stream test: {e}")
        return False

def main():
    """Main function to test stream credentials"""
    print("Stream Credentials Test Tool")
    print("This tool will test your stream credentials with FFmpeg directly.")
    print()
    
    # Get credentials from user
    print("Enter your stream credentials:")
    stream_url = input("Stream URL (e.g., rtmp://a.rtmp.youtube.com/live2/): ").strip()
    stream_key = input("Stream Key: ").strip()
    
    if not stream_url or not stream_key:
        print("❌ Stream URL and key are required")
        return False
    
    # Validate URL format
    if not (stream_url.startswith("rtmp://") or stream_url.startswith("rtmps://")):
        print("❌ Stream URL must start with rtmp:// or rtmps://")
        return False
    
    print()
    print("Starting stream test in 3 seconds...")
    print("Make sure your streaming platform is ready to receive the test stream.")
    time.sleep(3)
    
    # Test the credentials
    success = test_stream_credentials(stream_url, stream_key, duration=10)
    
    if success:
        print("\n🎉 Stream credentials appear to be working!")
        print("You should see a test pattern on your streaming platform.")
    else:
        print("\n💡 Troubleshooting tips:")
        print("1. Double-check your stream URL and key")
        print("2. Ensure your streaming platform is ready to receive")
        print("3. Check your internet connection")
        print("4. Verify the stream key hasn't expired")
        print("5. Try a different streaming platform for testing")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

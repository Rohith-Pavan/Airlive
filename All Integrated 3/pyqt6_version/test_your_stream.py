#!/usr/bin/env python3
"""
Test your stream credentials - Edit the credentials below and run this script
"""

import subprocess
import sys
import time
from pathlib import Path

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from ffmpeg_locator import find_ffmpeg

# ============================================================================
# EDIT THESE CREDENTIALS WITH YOUR ACTUAL STREAM DETAILS
# ============================================================================
STREAM_URL = "rtmp://a.rtmp.youtube.com/live2/"  # Replace with your stream URL
STREAM_KEY = "your-stream-key-here"              # Replace with your actual stream key
# ============================================================================

def test_stream():
    """Test stream with the credentials above"""
    print("=" * 60)
    print("Stream Credentials Test")
    print("=" * 60)
    
    # Find FFmpeg
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("❌ FFmpeg not found")
        return False
    
    print(f"✅ FFmpeg found at: {ffmpeg_path}")
    
    # Check if credentials are set
    if STREAM_KEY == "your-stream-key-here":
        print("❌ Please edit this script and set your actual stream key!")
        print("   Open test_your_stream.py and replace 'your-stream-key-here' with your real stream key")
        return False
    
    # Build the full stream URL
    full_url = f"{STREAM_URL.rstrip('/')}/{STREAM_KEY}"
    print(f"Stream URL: {STREAM_URL}")
    print(f"Stream Key: {'*' * len(STREAM_KEY)}")
    print(f"Full URL: {STREAM_URL.rstrip('/')}/{'*' * len(STREAM_KEY)}")
    
    # Create FFmpeg command for testing
    cmd = [
        ffmpeg_path,
        "-y",  # Overwrite output
        "-f", "lavfi",
        "-i", "testsrc=duration=10:size=640x480:rate=1",
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
    
    print(f"\nStarting stream test (duration: 10 seconds)...")
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
        while process.poll() is None and (time.time() - start_time) < 15:
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
        print(f"\n⏰ Stream test timed out after 15 seconds")
        process.terminate()
        return False
    except Exception as e:
        print(f"\n❌ Error during stream test: {e}")
        return False

def main():
    """Main function"""
    print("Stream Credentials Test")
    print("Make sure you've edited the credentials in this script first!")
    print()
    
    # Validate URL format
    if not (STREAM_URL.startswith("rtmp://") or STREAM_URL.startswith("rtmps://")):
        print("❌ Stream URL must start with rtmp:// or rtmps://")
        return False
    
    print("Starting stream test in 3 seconds...")
    print("Make sure your streaming platform is ready to receive the test stream.")
    time.sleep(3)
    
    # Test the credentials
    success = test_stream()
    
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

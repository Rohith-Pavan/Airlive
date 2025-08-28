#!/usr/bin/env python3
"""
Test simple streaming with basic test pattern
"""

import sys
import time
import subprocess
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def create_test_frame(width, height, frame_number):
    """Create a simple test frame with moving pattern"""
    # Create a simple RGB pattern that changes over time
    frame_data = bytearray(width * height * 3)
    
    for y in range(height):
        for x in range(width):
            # Calculate position in frame data
            pos = (y * width + x) * 3
            
            # Create a moving pattern
            r = (x + frame_number * 10) % 256
            g = (y + frame_number * 5) % 256
            b = (frame_number * 20) % 256
            
            frame_data[pos] = r
            frame_data[pos + 1] = g
            frame_data[pos + 2] = b
    
    return bytes(frame_data)

def test_simple_stream():
    """Test streaming with simple test pattern"""
    from ffmpeg_locator import find_ffmpeg
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("FFmpeg not found")
        return False
    
    # Test settings
    width, height = 640, 480
    fps = 30
    duration = 5  # seconds
    
    # Build FFmpeg command for test
    cmd = [
        ffmpeg_path,
        '-y',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'rgb24',
        '-s', f'{width}x{height}',
        '-r', str(fps),
        '-i', '-',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-b:v', '1000k',
        '-f', 'flv',
        'test_output.flv'  # Save to file instead of streaming
    ]
    
    print(f"Testing FFmpeg command: {' '.join(cmd)}")
    
    try:
        # Start FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
        print("FFmpeg process started")
        
        # Wait a bit for FFmpeg to initialize
        time.sleep(0.5)
        
        if process.poll() is not None:
            stderr_data = process.stderr.read(1024)
            print(f"FFmpeg failed to start: {stderr_data.decode()}")
            return False
        
        # Send test frames
        total_frames = fps * duration
        print(f"Sending {total_frames} test frames...")
        
        for frame_num in range(total_frames):
            # Create test frame
            frame_data = create_test_frame(width, height, frame_num)
            
            # Send to FFmpeg
            try:
                process.stdin.write(frame_data)
                process.stdin.flush()
                
                if frame_num % 30 == 0:
                    print(f"Sent frame {frame_num}/{total_frames}")
                    
            except (BrokenPipeError, OSError) as e:
                print(f"Error writing frame {frame_num}: {e}")
                break
        
        # Close stdin to signal end of input
        process.stdin.close()
        
        # Wait for FFmpeg to finish
        stdout, stderr = process.communicate(timeout=10)
        
        if process.returncode == 0:
            print("✓ Test streaming successful!")
            print(f"Output saved to: test_output.flv")
            return True
        else:
            print(f"✗ FFmpeg failed with return code: {process.returncode}")
            if stderr:
                print(f"FFmpeg stderr: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"Error during test: {e}")
        return False

def main():
    print("Testing simple streaming...")
    print("=" * 50)
    
    success = test_simple_stream()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ Simple streaming test PASSED!")
        print("This confirms FFmpeg can receive raw video data correctly.")
    else:
        print("✗ Simple streaming test FAILED!")
        print("There's an issue with FFmpeg or the data format.")

if __name__ == "__main__":
    main()

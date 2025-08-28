# Streaming Troubleshooting Guide

This guide helps you diagnose and fix streaming issues in GoLive Studio.

## Quick Diagnostic Steps

### 1. Test FFmpeg Installation
Run the FFmpeg test script:
```bash
python test_ffmpeg.py
```

This will:
- Check if FFmpeg is installed
- Download FFmpeg if needed
- Test basic functionality
- Verify format support

### 2. Test Streaming with Debug Tool
Run the streaming debug tool:
```bash
python test_streaming_debug.py
```

This provides:
- Visual test pattern
- Real-time logging
- Step-by-step testing
- Error reporting

## Common Issues and Solutions

### Issue: "Stream started" but no actual stream

**Symptoms:**
- Application says "Stream started" 
- No video appears on streaming platform
- No error messages

**Possible Causes:**
1. **FFmpeg not found or not working**
2. **Invalid stream credentials**
3. **Network connectivity issues**
4. **Graphics capture problems**

**Solutions:**

#### 1. Check FFmpeg
```bash
python test_ffmpeg.py
```

If FFmpeg fails:
- Check if FFmpeg is in PATH
- Try manual FFmpeg installation
- Verify FFmpeg can run basic commands

#### 2. Verify Stream Credentials
- Double-check stream URL format (must start with `rtmp://` or `rtmps://`)
- Verify stream key is correct
- Test with a known working stream key

#### 3. Test Network Connectivity
```bash
# Test basic connectivity to streaming server
ping live.twitch.tv
ping a.rtmp.youtube.com
```

#### 4. Check Graphics Capture
- Ensure there's content in the main preview area
- Try adding a test pattern or video source
- Verify the graphics widget is properly initialized

### Issue: FFmpeg Process Dies Immediately

**Symptoms:**
- Stream starts then immediately stops
- Error messages about FFmpeg process termination

**Solutions:**

#### 1. Check FFmpeg Command
Look for the FFmpeg command in the console output:
```
Starting FFmpeg with command: ffmpeg -y -f rawvideo ...
```

#### 2. Test FFmpeg Command Manually
Copy the command and run it manually in terminal to see specific errors.

#### 3. Check FFmpeg Version
```bash
ffmpeg -version
```

Ensure you have a recent version (4.0+ recommended).

### Issue: Frame Capture Failures

**Symptoms:**
- "Failed to capture graphics view" messages
- "Frame data size mismatch" errors

**Solutions:**

#### 1. Check Graphics Scene
- Ensure the graphics widget has content
- Verify scene dimensions are valid
- Check if video sources are connected

#### 2. Test with Simple Content
- Use the debug tool with test patterns
- Try streaming without complex overlays
- Verify basic graphics rendering works

### Issue: Stream Quality Problems

**Symptoms:**
- Poor video quality
- Audio issues
- High latency

**Solutions:**

#### 1. Adjust Bitrate Settings
- Increase video bitrate for better quality
- Match bitrate to your internet upload speed
- Use recommended settings for your platform

#### 2. Optimize Encoding Settings
- Use "veryfast" preset for lower CPU usage
- Enable "tune=zerolatency" for reduced latency
- Adjust GOP size based on your needs

## Platform-Specific Issues

### YouTube Live
**Common Issues:**
- Invalid stream key format
- Wrong ingest server
- Bitrate too high/low

**Solutions:**
- Use `rtmp://a.rtmp.youtube.com/live2/` as URL
- Ensure stream key is exactly as provided by YouTube
- Use 4500-6000 kbps for 1080p

### Twitch
**Common Issues:**
- Wrong ingest server
- Stream key issues
- Bitrate limits

**Solutions:**
- Use `rtmp://live.twitch.tv/live/` as URL
- Verify stream key in Twitch dashboard
- Keep bitrate under 6000 kbps

### Facebook Live
**Common Issues:**
- HTTPS/RTMPS requirements
- Authentication issues
- Format restrictions

**Solutions:**
- Use `rtmps://live-api-s.facebook.com:443/rtmp/` as URL
- Ensure proper authentication
- Use recommended bitrates (2500-4000 kbps)

## Debugging Steps

### 1. Enable Verbose Logging
Look for these log messages:
- "FFmpeg found at: [path]"
- "Starting FFmpeg with command: [command]"
- "FFmpeg process started successfully"
- "Frames sent: [count]"

### 2. Check Console Output
Monitor the application console for:
- Error messages
- FFmpeg stderr output
- Frame capture status
- Process termination reasons

### 3. Use Debug Tools
- Run `test_streaming_debug.py` for step-by-step testing
- Use `test_ffmpeg.py` to verify FFmpeg installation
- Check network connectivity manually

### 4. Test with Minimal Setup
1. Start with basic test pattern
2. Use simple stream settings
3. Test with local RTMP server first
4. Gradually add complexity

## Advanced Troubleshooting

### Check System Resources
```bash
# Monitor CPU usage during streaming
top

# Check available memory
free -h

# Monitor network usage
iftop
```

### Test FFmpeg Manually
```bash
# Test basic FFmpeg functionality
ffmpeg -f lavfi -i testsrc=duration=5:size=320x240:rate=1 -f null -

# Test RTMP connection (replace with your details)
ffmpeg -f lavfi -i testsrc=duration=10:size=640x480:rate=1 -c:v libx264 -preset veryfast -f flv rtmp://your-server/live/stream-key
```

### Check Firewall/Antivirus
- Ensure FFmpeg is not blocked
- Check if outbound RTMP traffic is allowed
- Verify no antivirus is interfering

## Getting Help

If you're still experiencing issues:

1. **Collect Debug Information:**
   - Run `test_ffmpeg.py` and save output
   - Run `test_streaming_debug.py` and save logs
   - Note any error messages from the main application

2. **Check System Requirements:**
   - Python 3.8+
   - FFmpeg 4.0+
   - Sufficient CPU/RAM for encoding
   - Stable internet connection

3. **Common Solutions:**
   - Restart the application
   - Reinstall FFmpeg
   - Check stream credentials
   - Test with different streaming platforms

## Prevention Tips

1. **Always test FFmpeg first** before attempting to stream
2. **Use the debug tool** to verify basic functionality
3. **Start with simple settings** and gradually increase complexity
4. **Monitor system resources** during streaming
5. **Keep FFmpeg updated** to the latest stable version
6. **Test stream credentials** before going live

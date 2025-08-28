# GoLive Studio - PyQt6 Version

A professional video streaming application converted from Qt C++ to PyQt6. This application provides multi-input video switching, media file playback, real-time transitions, and streaming capabilities.

## Key Features

### Automatic FFmpeg Handling
- **No Manual Installation Needed**: FFmpeg is automatically downloaded during build
- **Self-Contained**: All dependencies are bundled with the application
- **Auto-Update**: FFmpeg can be updated through the application

## Features

### Core Functionality
- **Multi-Input Support**: 3 camera inputs + 3 media file inputs
- **Real-time Switching**: Seamless switching between video sources
- **Video Transitions**: Zoom and fade transition effects
- **Live Streaming**: Dual stream support with FFmpeg integration
- **Media Playback**: Support for various video formats (MP4, AVI, MKV, MOV, WMV, FLV)

### Technical Features
- **Camera Integration**: Automatic detection and setup of webcams
- **File Support**: Drag-and-drop video file loading with looping
- **Stream Settings**: Configurable RTMP/HLS streaming to platforms like Twitch, YouTube
- **Custom Bitrate**: Adjustable streaming quality settings
- **Professional UI**: Clean, intuitive interface designed for live production

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows 10/11 (for build script)
- FFmpeg will be automatically downloaded during build

### Development Setup
1. Create and activate a virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Building the Application

#### Option 1: Using the build script (Recommended for Windows)
1. Run the build script:
```bash
build.bat
```

2. The built application will be in the `dist/GoLiveStudio` folder

#### Option 2: Manual Build
1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Run PyInstaller with the spec file:
```bash
pyinstaller --clean --noconfirm golive.spec
```

3. The built application will be in the `dist/GoLiveStudio` folder
```

2. Install FFmpeg:
   - Download from https://ffmpeg.org/download.html
   - Add to system PATH

3. Run the application:
```bash
python main.py
```

## Usage

### Camera Setup
1. Click "Settings" button under any Input (1-3)
2. Select your webcam from the dropdown menu
3. Camera feed will appear in the input preview

### Media File Setup
1. Click "Settings" button under any Media (1-3)
2. Select "Open Video File..." 
3. Choose your video file
4. File will start playing with infinite loop

### Switching Inputs
- Use **1A** or **2B** buttons to switch any input to the main output
- The output preview shows the currently active source

### Transitions
- **ZOOM**: Toggle between normal and 1.5x zoom
- **FADE**: Toggle between full opacity and 30% fade

### Streaming
1. Click "Stream Settings" button
2. Configure Stream 1 and/or Stream 2:
   - Format: RTMP, HLS, or WebRTC
   - Stream URL: Your streaming platform URL
   - Stream Key: Your private streaming key
3. Set custom bitrate if needed
4. Click "Start Stream" to begin broadcasting

## Architecture

### Core Components
- **MainWindow**: Primary application interface and control logic
- **Switching**: Handles video source switching and routing
- **VideoSelectorWindow**: Camera and file selection interface
- **StreamSettingsWindow**: Streaming configuration and control

### Key Classes
- **MainWindow**: Main application window with all UI components
- **Switching**: Video switching logic and output routing
- **VideoSelectorWindow**: Source selection dialog
- **StreamSettingsWindow**: Streaming configuration interface

## Converted Features from C++

All original Qt C++ functionality has been preserved:

✅ **Multi-input video switching**  
✅ **Camera integration with QCamera/QMediaCaptureSession**  
✅ **Media file playback with QMediaPlayer**  
✅ **Real-time video transitions (zoom/fade)**  
✅ **FFmpeg streaming integration**  
✅ **Professional UI layout**  
✅ **Resource management and cleanup**  
✅ **Signal-slot connections**  
✅ **Menu-based source selection**  

## Requirements

See `requirements.txt` for complete dependency list:
- PyQt6 6.6.1
- PyQt6-Qt6 6.6.1  
- PyQt6-sip 13.6.0
- opencv-python 4.8.1.78
- numpy 1.24.3

## Troubleshooting

### Common Issues
1. **No cameras detected**: Ensure webcam drivers are installed and camera isn't in use by another application
2. **Video files won't play**: Check codec support and file permissions
3. **Streaming fails**: Verify FFmpeg installation and network connectivity
4. **Performance issues**: Reduce video resolution or bitrate settings

### FFmpeg Installation
- Windows: Download from https://ffmpeg.org/download.html and add to PATH
- Linux: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`

## Development

The codebase follows PyQt6 best practices:
- Proper signal-slot connections
- Resource cleanup in closeEvent
- Modular component design
- Type hints where applicable

## License

This project maintains the same license as the original Qt C++ version.

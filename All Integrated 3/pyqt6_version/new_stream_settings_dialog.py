#!/usr/bin/env python3
"""
New Stream Settings Dialog for GoLive Studio - Complete Rewrite
Robust settings interface with comprehensive validation and testing
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QComboBox, QSpinBox, QPushButton, 
                             QLabel, QGroupBox, QCheckBox, QTabWidget, QWidget, 
                             QTextEdit, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
from ffmpeg_locator import find_ffmpeg, ensure_ffmpeg_available


class StreamTestWorker(QThread):
    """Worker thread for testing stream connections"""
    
    test_started = pyqtSignal()
    test_progress = pyqtSignal(str)
    test_completed = pyqtSignal(bool, str)
    
    def __init__(self, settings: Dict[str, Any]):
        super().__init__()
        self.settings = settings.copy()
        self._should_stop = False
    
    def run(self):
        """Run comprehensive stream test"""
        try:
            self.test_started.emit()
            
            # Test 1: FFmpeg availability
            self.test_progress.emit("Testing FFmpeg availability...")
            if not self._test_ffmpeg():
                self.test_completed.emit(False, "FFmpeg not found or not working")
                return
            
            # Test 2: Settings validation
            self.test_progress.emit("Validating stream settings...")
            validation_error = self._validate_settings()
            if validation_error:
                self.test_completed.emit(False, f"Settings validation failed: {validation_error}")
                return
            
            # Test 3: Network connectivity
            self.test_progress.emit("Testing network connectivity...")
            if not self._test_network():
                self.test_completed.emit(False, "Network connectivity test failed")
                return
            
            # Test 4: FFmpeg command test
            self.test_progress.emit("Testing FFmpeg command...")
            if not self._test_ffmpeg_command():
                self.test_completed.emit(False, "FFmpeg command test failed")
                return
            
            # Test 5: Short stream test
            self.test_progress.emit("Running short stream test...")
            if not self._test_short_stream():
                self.test_completed.emit(False, "Short stream test failed")
                return
            
            self.test_completed.emit(True, "All tests passed successfully!")
            
        except Exception as e:
            self.test_completed.emit(False, f"Test error: {str(e)}")
    
    def _test_ffmpeg(self) -> bool:
        """Test FFmpeg availability"""
        try:
            ffmpeg_path = find_ffmpeg()
            if not ffmpeg_path:
                ffmpeg_path = ensure_ffmpeg_available(auto_download=True)
            
            if not ffmpeg_path:
                return False
            
            # Test basic FFmpeg command
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _validate_settings(self) -> Optional[str]:
        """Validate stream settings"""
        try:
            # Check required fields
            required = ['url', 'key', 'resolution', 'fps', 'video_bitrate']
            for field in required:
                if field not in self.settings or not self.settings[field]:
                    return f"Missing {field}"
            
            # Validate URL format
            url = self.settings['url']
            if not (url.startswith('rtmp://') or url.startswith('rtmps://') or url.startswith('srt://')):
                return "Invalid URL format"
            
            # Validate resolution
            try:
                width, height = map(int, self.settings['resolution'].split('x'))
                if width <= 0 or height <= 0 or width > 3840 or height > 2160:
                    return "Invalid resolution"
            except (ValueError, AttributeError):
                return "Invalid resolution format"
            
            # Validate FPS
            fps = self.settings.get('fps', 30)
            if not isinstance(fps, int) or fps <= 0 or fps > 60:
                return "Invalid FPS"
            
            # Validate bitrate
            bitrate = self.settings.get('video_bitrate', 2500)
            if not isinstance(bitrate, int) or bitrate < 100 or bitrate > 50000:
                return "Invalid bitrate"
            
            return None
            
        except Exception as e:
            return f"Validation error: {e}"
    
    def _test_network(self) -> bool:
        """Test basic network connectivity"""
        try:
            url = self.settings['url']
            
            # Extract hostname from URL
            if url.startswith('rtmp://'):
                hostname = url[7:].split('/')[0].split(':')[0]
            elif url.startswith('rtmps://'):
                hostname = url[8:].split('/')[0].split(':')[0]
            elif url.startswith('srt://'):
                hostname = url[6:].split('/')[0].split(':')[0]
            else:
                return False
            
            # Simple ping test (platform independent)
            import socket
            try:
                socket.create_connection((hostname, 80), timeout=5)
                return True
            except (socket.timeout, socket.error):
                # Try RTMP port
                try:
                    socket.create_connection((hostname, 1935), timeout=5)
                    return True
                except (socket.timeout, socket.error):
                    return False
                    
        except Exception:
            return False
    
    def _test_ffmpeg_command(self) -> bool:
        """Test FFmpeg command construction"""
        try:
            ffmpeg_path = find_ffmpeg()
            if not ffmpeg_path:
                return False
            
            # Build test command
            width, height = map(int, self.settings['resolution'].split('x'))
            fps = int(self.settings['fps'])
            
            cmd = [
                ffmpeg_path,
                '-f', 'lavfi',
                '-i', f'testsrc=duration=1:size={width}x{height}:rate={fps}',
                '-f', 'null',
                '-'
            ]
            
            # Test command execution
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _test_short_stream(self) -> bool:
        """Test short stream to verify connection"""
        try:
            if self._should_stop:
                return False
            
            ffmpeg_path = find_ffmpeg()
            if not ffmpeg_path:
                return False
            
            # Build stream command
            width, height = map(int, self.settings['resolution'].split('x'))
            fps = int(self.settings['fps'])
            url = self.settings['url'].rstrip('/')
            key = self.settings['key']
            target = f"{url}/{key}" if key else url
            
            cmd = [
                ffmpeg_path,
                '-f', 'lavfi',
                '-i', f'testsrc=duration=3:size={width}x{height}:rate={fps}',
                '-f', 'lavfi',
                '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-b:v', f"{self.settings['video_bitrate']}k",
                '-c:a', 'aac',
                '-b:a', '128k',
                '-f', 'flv',
                '-t', '3',
                target
            ]
            
            # Run test stream
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=10)
                return process.returncode == 0
            except subprocess.TimeoutExpired:
                process.kill()
                return False
                
        except Exception:
            return False
    
    def stop_test(self):
        """Stop the test"""
        self._should_stop = True


class NewStreamSettingsDialog(QDialog):
    """New stream settings dialog with comprehensive testing and validation"""
    
    settings_saved = pyqtSignal(dict)
    
    def __init__(self, stream_name: str = "Stream1", parent=None, stream_manager=None):
        super().__init__(parent)
        self.stream_name = stream_name
        self.stream_manager = stream_manager
        self.test_worker = None
        
        self.settings = self._load_default_settings()
        self._setup_ui()
        self._load_saved_settings()
        self._update_ui_from_settings()
    
    def _setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle(f"{self.stream_name} Settings")
        self.setModal(True)
        self.resize(600, 700)
        
        layout = QVBoxLayout(self)
        
        # Create tabs
        tab_widget = QTabWidget()
        
        # Basic settings tab
        basic_tab = self._create_basic_tab()
        tab_widget.addTab(basic_tab, "Basic Settings")
        
        # Advanced settings tab
        advanced_tab = self._create_advanced_tab()
        tab_widget.addTab(advanced_tab, "Advanced Settings")
        
        # Test tab
        test_tab = self._create_test_tab()
        tab_widget.addTab(test_tab, "Connection Test")
        
        layout.addWidget(tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Stream control buttons
        if self.stream_manager:
            self.start_button = QPushButton("Start Stream")
            self.start_button.clicked.connect(self._start_stream)
            button_layout.addWidget(self.start_button)
            
            self.stop_button = QPushButton("Stop Stream")
            self.stop_button.clicked.connect(self._stop_stream)
            button_layout.addWidget(self.stop_button)
            
            button_layout.addStretch()
        
        # Dialog buttons
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_settings)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        # Update stream control buttons
        self._update_stream_buttons()
    
    def _create_basic_tab(self) -> QWidget:
        """Create basic settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Stream destination
        dest_group = QGroupBox("Stream Destination")
        dest_layout = QFormLayout(dest_group)
        
        # Platform presets
        self.platform_combo = QComboBox()
        self.platform_combo.addItems([
            "Custom RTMP",
            "Twitch",
            "YouTube Live",
            "Facebook Live",
            "Custom SRT",
            "HDMI Display"
        ])
        self.platform_combo.currentTextChanged.connect(self._on_platform_changed)
        dest_layout.addRow("Platform:", self.platform_combo)
        
        # URL
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("rtmps://a.rtmps.youtube.com/live2/")
        dest_layout.addRow("Stream URL:", self.url_edit)
        
        # Key
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("Your stream key")
        dest_layout.addRow("Stream Key:", self.key_edit)
        
        # HDMI Display selection (initially hidden)
        self.hdmi_display_combo = QComboBox()
        self.hdmi_display_label = QLabel("HDMI Display:")
        dest_layout.addRow(self.hdmi_display_label, self.hdmi_display_combo)
        self.hdmi_display_combo.setVisible(False)
        self.hdmi_display_label.setVisible(False)
        
        # HDMI Mode selection (initially hidden)
        self.hdmi_mode_combo = QComboBox()
        self.hdmi_mode_combo.addItems(["Mirror", "Extend", "Fullscreen"])
        self.hdmi_mode_label = QLabel("HDMI Mode:")
        dest_layout.addRow(self.hdmi_mode_label, self.hdmi_mode_combo)
        self.hdmi_mode_combo.setVisible(False)
        self.hdmi_mode_label.setVisible(False)
        
        # Show key checkbox
        self.show_key_check = QCheckBox("Show stream key")
        self.show_key_check.toggled.connect(self._toggle_key_visibility)
        dest_layout.addRow("", self.show_key_check)
        
        layout.addWidget(dest_group)
        
        # Video settings
        video_group = QGroupBox("Video Settings")
        video_layout = QFormLayout(video_group)
        
        # Resolution
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1920x1080",
            "1280x720", 
            "854x480",
            "640x360"
        ])
        video_layout.addRow("Resolution:", self.resolution_combo)
        
        # FPS - ENHANCED: 60 FPS as default for maximum smoothness
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["60", "30", "25", "24"])  # 60 FPS first for HDMI quality
        video_layout.addRow("Frame Rate:", self.fps_combo)
        
        # Video bitrate - ENHANCED: Higher default for maximum quality
        self.video_bitrate_spin = QSpinBox()
        self.video_bitrate_spin.setRange(100, 50000)
        self.video_bitrate_spin.setValue(8000)  # ENHANCED: 8 Mbps for high quality
        self.video_bitrate_spin.setSuffix(" kbps")
        video_layout.addRow("Video Bitrate:", self.video_bitrate_spin)
        
        layout.addWidget(video_group)
        
        # Audio settings
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QFormLayout(audio_group)
        
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems(["128", "192", "256"])
        audio_layout.addRow("Audio Bitrate (kbps):", self.audio_bitrate_combo)
        
        layout.addWidget(audio_group)
        layout.addStretch()
        
        return tab
    
    def _create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Encoder settings
        encoder_group = QGroupBox("Encoder Settings")
        encoder_layout = QFormLayout(encoder_group)
        
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["libx264", "libx265", "h264_nvenc"])
        encoder_layout.addRow("Video Codec:", self.codec_combo)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast"])
        encoder_layout.addRow("Encoding Preset:", self.preset_combo)
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["baseline", "main", "high"])
        encoder_layout.addRow("H.264 Profile:", self.profile_combo)
        
        layout.addWidget(encoder_group)
        
        # Network settings
        network_group = QGroupBox("Network Settings")
        network_layout = QFormLayout(network_group)
        
        self.low_latency_check = QCheckBox("Enable low latency mode")
        network_layout.addRow("", self.low_latency_check)
        
        self.buffer_size_spin = QSpinBox()
        self.buffer_size_spin.setRange(1, 10)
        self.buffer_size_spin.setValue(2)
        self.buffer_size_spin.setSuffix(" seconds")
        network_layout.addRow("Buffer Size:", self.buffer_size_spin)
        
        layout.addWidget(network_group)
        layout.addStretch()
        
        return tab
    
    def _create_test_tab(self) -> QWidget:
        """Create connection test tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Test controls
        test_group = QGroupBox("Connection Test")
        test_layout = QVBoxLayout(test_group)
        
        # Test button
        self.test_button = QPushButton("Run Connection Test")
        self.test_button.clicked.connect(self._run_test)
        test_layout.addWidget(self.test_button)
        
        # Progress bar
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        test_layout.addWidget(self.test_progress)
        
        # Test results
        self.test_results = QTextEdit()
        self.test_results.setMaximumHeight(200)
        self.test_results.setReadOnly(True)
        test_layout.addWidget(self.test_results)
        
        layout.addWidget(test_group)
        
        # Quick presets
        presets_group = QGroupBox("Quick Presets")
        presets_layout = QVBoxLayout(presets_group)
        
        preset_buttons = [
            ("Twitch 1080p30", {
                "platform": "Twitch",
                "url": "rtmp://live.twitch.tv/live/",
                "resolution": "1920x1080",
                "fps": 30,
                "video_bitrate": 4500
            }),
            ("YouTube 720p30", {
                "platform": "YouTube Live",
                "url": "rtmps://a.rtmps.youtube.com/live2/",
                "resolution": "1280x720",
                "fps": 30,
                "video_bitrate": 2500
            }),
            ("Low Bandwidth 480p30", {
                "resolution": "854x480",
                "fps": 30,
                "video_bitrate": 1000
            })
        ]
        
        for name, preset in preset_buttons:
            button = QPushButton(name)
            button.clicked.connect(lambda checked, p=preset: self._apply_preset(p))
            presets_layout.addWidget(button)
        
        layout.addWidget(presets_group)
        layout.addStretch()
        
        return tab
    
    def _on_platform_changed(self, platform: str):
        """Handle platform change"""
        platform_urls = {
            "Twitch": "rtmp://live.twitch.tv/live/",
            "YouTube Live": "rtmps://a.rtmps.youtube.com/live2/",
            "Facebook Live": "rtmps://live-api-s.facebook.com:443/rtmp/",
            "Custom SRT": "srt://",
            "Custom RTMP": ""
        }
        
        # Handle HDMI Display platform
        if platform == "HDMI Display":
            self._setup_hdmi_display()
            # Hide URL and Key fields for HDMI
            self.url_edit.setVisible(False)
            self.key_edit.setVisible(False)
            self.show_key_check.setVisible(False)
            # Show HDMI specific fields
            self.hdmi_display_combo.setVisible(True)
            self.hdmi_display_label.setVisible(True)
            self.hdmi_mode_combo.setVisible(True)
            self.hdmi_mode_label.setVisible(True)
        else:
            # Show URL and Key fields for streaming platforms
            self.url_edit.setVisible(True)
            self.key_edit.setVisible(True)
            self.show_key_check.setVisible(True)
            # Hide HDMI specific fields
            self.hdmi_display_combo.setVisible(False)
            self.hdmi_display_label.setVisible(False)
            self.hdmi_mode_combo.setVisible(False)
            self.hdmi_mode_label.setVisible(False)
            
            if platform in platform_urls:
                self.url_edit.setText(platform_urls[platform])
    
    def _setup_hdmi_display(self):
        """Setup HDMI display options"""
        try:
            from display_manager import DisplayManager
            
            display_manager = DisplayManager()
            displays = display_manager.get_displays()
            
            self.hdmi_display_combo.clear()
            if displays:
                for display in displays:
                    display_name = display.display_name
                    self.hdmi_display_combo.addItem(display_name, display.index)
            else:
                self.hdmi_display_combo.addItem("No displays found", -1)
                
        except Exception as e:
            print(f"Error setting up HDMI displays: {e}")
            self.hdmi_display_combo.clear()
            self.hdmi_display_combo.addItem("Error detecting displays", -1)
    
    def _toggle_key_visibility(self, show: bool):
        """Toggle stream key visibility"""
        if show:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
    
    def _apply_preset(self, preset: Dict[str, Any]):
        """Apply preset values"""
        if "platform" in preset:
            index = self.platform_combo.findText(preset["platform"])
            if index >= 0:
                self.platform_combo.setCurrentIndex(index)
        
        if "url" in preset:
            self.url_edit.setText(preset["url"])
        
        if "resolution" in preset:
            index = self.resolution_combo.findText(preset["resolution"])
            if index >= 0:
                self.resolution_combo.setCurrentIndex(index)
        
        if "fps" in preset:
            index = self.fps_combo.findText(str(preset["fps"]))
            if index >= 0:
                self.fps_combo.setCurrentIndex(index)
        
        if "video_bitrate" in preset:
            self.video_bitrate_spin.setValue(preset["video_bitrate"])
    
    def _run_test(self):
        """Run connection test"""
        if self.test_worker and self.test_worker.isRunning():
            self.test_worker.stop_test()
            self.test_worker.wait()
        
        # Get current settings
        settings = self._get_current_settings()
        
        # Validate basic requirements
        if not settings.get('url') or not settings.get('key'):
            self.test_results.setText("Error: URL and Stream Key are required for testing")
            return
        
        # Start test
        self.test_worker = StreamTestWorker(settings)
        self.test_worker.test_started.connect(self._on_test_started)
        self.test_worker.test_progress.connect(self._on_test_progress)
        self.test_worker.test_completed.connect(self._on_test_completed)
        
        self.test_worker.start()
    
    def _on_test_started(self):
        """Handle test started"""
        self.test_button.setText("Stop Test")
        self.test_progress.setVisible(True)
        self.test_progress.setRange(0, 0)  # Indeterminate
        self.test_results.clear()
    
    def _on_test_progress(self, message: str):
        """Handle test progress"""
        self.test_results.append(message)
    
    def _on_test_completed(self, success: bool, message: str):
        """Handle test completion"""
        self.test_button.setText("Run Connection Test")
        self.test_progress.setVisible(False)
        
        if success:
            self.test_results.append(f"\n✅ {message}")
        else:
            self.test_results.append(f"\n❌ {message}")
    
    def _get_current_settings(self) -> Dict[str, Any]:
        """Get current settings from UI"""
        settings = {
            "platform": self.platform_combo.currentText(),
            "url": self.url_edit.text().strip(),
            "key": self.key_edit.text().strip(),
            "resolution": self.resolution_combo.currentText(),
            "fps": int(self.fps_combo.currentText()),
            "video_bitrate": self.video_bitrate_spin.value(),
            "audio_bitrate": int(self.audio_bitrate_combo.currentText()),
            "codec": self.codec_combo.currentText(),
            "preset": self.preset_combo.currentText(),
            "profile": self.profile_combo.currentText(),
            "low_latency": self.low_latency_check.isChecked(),
            "buffer_size": self.buffer_size_spin.value()
        }
        
        # Add HDMI specific settings if HDMI platform is selected
        if self.platform_combo.currentText() == "HDMI Display":
            settings.update({
                "hdmi_display_index": self.hdmi_display_combo.currentData(),
                "hdmi_mode": self.hdmi_mode_combo.currentText(),
                "is_hdmi": True
            })
        else:
            settings["is_hdmi"] = False
            
        return settings
    
    def _update_ui_from_settings(self):
        """Update UI from current settings"""
        # Platform
        index = self.platform_combo.findText(self.settings.get("platform", "Custom RTMP"))
        if index >= 0:
            self.platform_combo.setCurrentIndex(index)
        
        # URL and Key
        self.url_edit.setText(self.settings.get("url", ""))
        self.key_edit.setText(self.settings.get("key", ""))
        
        # HDMI specific settings
        if self.settings.get("is_hdmi", False):
            # Set HDMI display if saved
            hdmi_index = self.settings.get("hdmi_display_index", -1)
            for i in range(self.hdmi_display_combo.count()):
                if self.hdmi_display_combo.itemData(i) == hdmi_index:
                    self.hdmi_display_combo.setCurrentIndex(i)
                    break
            
            # Set HDMI mode
            hdmi_mode = self.settings.get("hdmi_mode", "Mirror")
            index = self.hdmi_mode_combo.findText(hdmi_mode)
            if index >= 0:
                self.hdmi_mode_combo.setCurrentIndex(index)
        
        # Resolution
        index = self.resolution_combo.findText(self.settings.get("resolution", "1920x1080"))
        if index >= 0:
            self.resolution_combo.setCurrentIndex(index)
        
        # FPS
        index = self.fps_combo.findText(str(self.settings.get("fps", 30)))
        if index >= 0:
            self.fps_combo.setCurrentIndex(index)
        
        # Bitrates
        self.video_bitrate_spin.setValue(self.settings.get("video_bitrate", 2500))
        
        index = self.audio_bitrate_combo.findText(str(self.settings.get("audio_bitrate", 128)))
        if index >= 0:
            self.audio_bitrate_combo.setCurrentIndex(index)
        
        # Advanced settings
        index = self.codec_combo.findText(self.settings.get("codec", "libx264"))
        if index >= 0:
            self.codec_combo.setCurrentIndex(index)
        
        index = self.preset_combo.findText(self.settings.get("preset", "veryfast"))
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        
        index = self.profile_combo.findText(self.settings.get("profile", "main"))
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
        
        self.low_latency_check.setChecked(self.settings.get("low_latency", False))
        self.buffer_size_spin.setValue(self.settings.get("buffer_size", 2))
    
    def _start_stream(self):
        """Start streaming"""
        if not self.stream_manager:
            return
        
        settings = self._get_current_settings()
        
        # Validate based on platform
        if settings.get("platform") == "HDMI Display":
            if settings.get("hdmi_display_index", -1) == -1:
                QMessageBox.warning(self, "Error", "Please select a valid HDMI display")
                return
        else:
            if not settings.get('url') or not settings.get('key'):
                QMessageBox.warning(self, "Error", "URL and Stream Key are required")
                return
        
        # Configure and start
        self.stream_manager.configure_stream(self.stream_name, settings)
        success = self.stream_manager.start_stream(self.stream_name)
        
        if success:
            self._update_stream_buttons()
        else:
            QMessageBox.warning(self, "Error", "Failed to start stream")
    
    def _stop_stream(self):
        """Stop streaming"""
        if not self.stream_manager:
            return
        
        self.stream_manager.stop_stream(self.stream_name)
        self._update_stream_buttons()
    
    def _update_stream_buttons(self):
        """Update stream control buttons"""
        if not self.stream_manager:
            return
        
        is_streaming = self.stream_manager.is_streaming(self.stream_name)
        
        if hasattr(self, 'start_button'):
            self.start_button.setEnabled(not is_streaming)
        if hasattr(self, 'stop_button'):
            self.stop_button.setEnabled(is_streaming)
    
    def _save_settings(self):
        """Save settings"""
        settings = self._get_current_settings()
        
        # Validate required fields based on platform
        if settings.get("platform") == "HDMI Display":
            # For HDMI, validate display selection
            if settings.get("hdmi_display_index", -1) == -1:
                QMessageBox.warning(self, "Error", "Please select a valid HDMI display")
                return
        else:
            # For streaming platforms, validate URL and key
            if not settings.get('url'):
                QMessageBox.warning(self, "Error", "Stream URL is required")
                return
            
            if not settings.get('key'):
                QMessageBox.warning(self, "Error", "Stream Key is required")
                return
        
        # Save to file
        self._save_settings_to_file(settings)
        
        # Emit signal
        self.settings_saved.emit(settings)
        
        self.accept()
    
    def _load_default_settings(self) -> Dict[str, Any]:
        """Load default settings - ENHANCED FOR MAXIMUM QUALITY"""
        return {
            "platform": "Custom RTMP",
            "url": "",
            "key": "",
            "resolution": "1920x1080",  # Full HD default
            "fps": 60,  # ENHANCED: 60 FPS for ultra-smooth playback
            "video_bitrate": 8000,  # ENHANCED: Higher bitrate for maximum quality
            "audio_bitrate": 192,  # ENHANCED: Higher audio quality
            "codec": "libx264",
            "preset": "medium",  # ENHANCED: Better quality preset
            "profile": "high",  # ENHANCED: High profile for better quality
            "low_latency": False,
            "buffer_size": 2,
            "is_hdmi": False,
            "hdmi_display_index": -1,
            "hdmi_mode": "Mirror"
        }
    
    def _load_saved_settings(self):
        """Load saved settings from file"""
        settings_file = Path(__file__).parent / f"{self.stream_name.lower()}_settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
            except Exception as e:
                print(f"Error loading settings: {e}")
    
    def _save_settings_to_file(self, settings: Dict[str, Any]):
        """Save settings to file"""
        settings_file = Path(__file__).parent / f"{self.stream_name.lower()}_settings.json"
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

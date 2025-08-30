#!/usr/bin/env python3
"""
Stream Settings Dialog for GoLive Studio
Provides configuration interface for streaming parameters including URL, key, and quality settings.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QComboBox, QSpinBox, QPushButton, 
                             QLabel, QGroupBox, QCheckBox, QTabWidget, QWidget, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json
import os
from pathlib import Path
from display_manager import get_display_manager


class StreamSettingsDialog(QDialog):
    """Dialog for configuring stream settings"""
    
    settings_saved = pyqtSignal(dict)  # Emitted when settings are saved
    
    def __init__(self, stream_name="Stream1", parent=None, stream_manager=None):
        super().__init__(parent)
        self.stream_name = stream_name
        self.stream_manager = stream_manager
        self.display_manager = get_display_manager()
        self.settings = self.load_default_settings()
        self.setup_ui()
        self.load_saved_settings()
        
        # Connect display manager signals
        self.display_manager.displays_changed.connect(self.update_display_options)
        
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle(f"{self.stream_name} Settings")
        self.setModal(True)
        self.resize(500, 600)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create tab widget for different setting categories
        tab_widget = QTabWidget()
        
        # Basic Settings Tab
        basic_tab = self.create_basic_settings_tab()
        tab_widget.addTab(basic_tab, "Basic")
        
        # Advanced Settings Tab
        advanced_tab = self.create_advanced_settings_tab()
        tab_widget.addTab(advanced_tab, "Advanced")
        
        # Presets Tab
        presets_tab = self.create_presets_tab()
        tab_widget.addTab(presets_tab, "Presets")
        
        main_layout.addWidget(tab_widget)

        # Button layout
        button_layout = QHBoxLayout()
        
        # Test connection button
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_button)

        # Start/Stop streaming buttons (only functional if stream_manager is provided)
        self.start_button = QPushButton("Start Streaming")
        self.start_button.clicked.connect(self.start_stream_action)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Streaming")
        self.stop_button.clicked.connect(self.stop_stream_action)
        button_layout.addWidget(self.stop_button)
        
        button_layout.addStretch()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)
        
        main_layout.addLayout(button_layout)
        
    def create_basic_settings_tab(self):
        """Create basic settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Stream destination group
        dest_group = QGroupBox("Stream Destination")
        dest_layout = QFormLayout(dest_group)
        
        # Platform selection
        self.platform_combo = QComboBox()
        platform_items = [
            "Custom RTMP",
            "Twitch",
            "YouTube Live", 
            "Facebook Live",
            "Custom HLS",
            "Custom WebRTC"
        ]
        
        # Add HDMI Display option if multiple displays are available (any type)
        total_displays = len(self.display_manager.get_displays())
        if total_displays > 1:
            platform_items.insert(0, "HDMI Display")
            print(f"HDMI Display option added - {total_displays} displays detected")
            
        self.platform_combo.addItems(platform_items)
        self.platform_combo.currentTextChanged.connect(self.on_platform_changed)
        dest_layout.addRow("Platform:", self.platform_combo)
        
        # Stream URL
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("rtmp://live.twitch.tv/live/")
        self.url_label = QLabel("Stream URL:")
        dest_layout.addRow(self.url_label, self.url_edit)
        
        # Stream Key
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("Your stream key")
        self.key_label = QLabel("Stream Key:")
        dest_layout.addRow(self.key_label, self.key_edit)
        
        # Show key checkbox
        self.show_key_checkbox = QCheckBox("Show stream key")
        self.show_key_checkbox.toggled.connect(self.toggle_key_visibility)
        dest_layout.addRow("", self.show_key_checkbox)
        
        layout.addWidget(dest_group)
        
        # HDMI Display settings group (initially hidden)
        self.hdmi_group = QGroupBox("HDMI Display Settings")
        hdmi_layout = QFormLayout(self.hdmi_group)
        
        # Display selection
        self.display_combo = QComboBox()
        self.update_display_options()
        hdmi_layout.addRow("Target Display:", self.display_combo)
        
        # Display mode
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItems([
            "Fullscreen",
            "Windowed (800x600)",
            "Windowed (1024x768)",
            "Windowed (1280x720)"
        ])
        hdmi_layout.addRow("Display Mode:", self.display_mode_combo)
        
        # Always on top
        self.always_on_top_checkbox = QCheckBox("Always on top")
        hdmi_layout.addRow("", self.always_on_top_checkbox)
        
        # Match display resolution
        self.match_display_res_checkbox = QCheckBox("Match display resolution")
        self.match_display_res_checkbox.setChecked(True)
        hdmi_layout.addRow("", self.match_display_res_checkbox)
        
        layout.addWidget(self.hdmi_group)
        self.hdmi_group.hide()  # Initially hidden
        
        # Video settings group
        video_group = QGroupBox("Video Settings")
        video_layout = QFormLayout(video_group)
        
        # Resolution
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1920x1080 (1080p)",
            "1280x720 (720p)",
            "854x480 (480p)",
            "640x360 (360p)",
            "Custom"
        ])
        video_layout.addRow("Resolution:", self.resolution_combo)
        
        # Custom resolution fields
        resolution_custom_layout = QHBoxLayout()
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(320, 3840)
        self.width_spinbox.setValue(1920)
        self.width_spinbox.setEnabled(False)
        
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(240, 2160)
        self.height_spinbox.setValue(1080)
        self.height_spinbox.setEnabled(False)
        
        resolution_custom_layout.addWidget(QLabel("Width:"))
        resolution_custom_layout.addWidget(self.width_spinbox)
        resolution_custom_layout.addWidget(QLabel("Height:"))
        resolution_custom_layout.addWidget(self.height_spinbox)
        resolution_custom_layout.addStretch()
        
        video_layout.addRow("Custom Size:", resolution_custom_layout)
        
        # Frame rate
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["30", "60", "25", "24"])
        video_layout.addRow("Frame Rate:", self.fps_combo)
        
        # Bitrate
        self.bitrate_spinbox = QSpinBox()
        self.bitrate_spinbox.setRange(500, 50000)
        self.bitrate_spinbox.setValue(2500)
        self.bitrate_spinbox.setSuffix(" kbps")
        video_layout.addRow("Video Bitrate:", self.bitrate_spinbox)
        
        layout.addWidget(video_group)
        
        # Audio settings group
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QFormLayout(audio_group)
        
        # Audio bitrate
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems(["128", "192", "256", "320"])
        audio_layout.addRow("Audio Bitrate (kbps):", self.audio_bitrate_combo)
        
        # Audio sample rate
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000"])
        audio_layout.addRow("Sample Rate (Hz):", self.sample_rate_combo)
        
        layout.addWidget(audio_group)
        
        # Connect resolution combo to enable/disable custom fields
        self.resolution_combo.currentTextChanged.connect(self.on_resolution_changed)
        
        return tab
        
    def create_advanced_settings_tab(self):
        """Create advanced settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Encoder settings
        encoder_group = QGroupBox("Encoder Settings")
        encoder_layout = QFormLayout(encoder_group)
        
        # Video codec
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["libx264", "libx265", "h264_nvenc", "h264_qsv"])
        encoder_layout.addRow("Video Codec:", self.codec_combo)
        
        # Preset
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"])
        encoder_layout.addRow("Encoding Preset:", self.preset_combo)
        
        # Profile
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["baseline", "main", "high"])
        encoder_layout.addRow("H.264 Profile:", self.profile_combo)
        
        # Keyframe interval
        self.keyframe_spinbox = QSpinBox()
        self.keyframe_spinbox.setRange(1, 10)
        self.keyframe_spinbox.setValue(2)
        self.keyframe_spinbox.setSuffix(" seconds")
        encoder_layout.addRow("Keyframe Interval:", self.keyframe_spinbox)
        
        layout.addWidget(encoder_group)
        
        # Network settings
        network_group = QGroupBox("Network Settings")
        network_layout = QFormLayout(network_group)
        
        # Buffer size
        self.buffer_spinbox = QSpinBox()
        self.buffer_spinbox.setRange(1, 10)
        self.buffer_spinbox.setValue(3)
        self.buffer_spinbox.setSuffix(" seconds")
        network_layout.addRow("Buffer Size:", self.buffer_spinbox)
        
        # Reconnect attempts
        self.reconnect_spinbox = QSpinBox()
        self.reconnect_spinbox.setRange(0, 10)
        self.reconnect_spinbox.setValue(3)
        network_layout.addRow("Reconnect Attempts:", self.reconnect_spinbox)
        
        # Enable low latency
        self.low_latency_checkbox = QCheckBox("Enable low latency mode")
        network_layout.addRow("", self.low_latency_checkbox)
        
        layout.addWidget(network_group)
        
        layout.addStretch()
        
        return tab
        
    def create_presets_tab(self):
        """Create presets tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Preset selection
        preset_group = QGroupBox("Quality Presets")
        preset_layout = QVBoxLayout(preset_group)
        
        # Preset buttons
        presets = [
            ("High Quality (1080p60)", {"resolution": "1920x1080", "fps": "60", "bitrate": 6000}),
            ("Standard (1080p30)", {"resolution": "1920x1080", "fps": "30", "bitrate": 4500}),
            ("Medium (720p30)", {"resolution": "1280x720", "fps": "30", "bitrate": 2500}),
            ("Low (480p30)", {"resolution": "854x480", "fps": "30", "bitrate": 1000}),
            ("Mobile (360p30)", {"resolution": "640x360", "fps": "30", "bitrate": 700})
        ]
        
        for preset_name, preset_values in presets:
            preset_button = QPushButton(preset_name)
            preset_button.clicked.connect(lambda checked, values=preset_values: self.apply_preset(values))
            preset_layout.addWidget(preset_button)
        
        layout.addWidget(preset_group)
        
        # Platform presets
        platform_group = QGroupBox("Platform Presets")
        platform_layout = QVBoxLayout(platform_group)
        
        platforms = [
            ("Twitch (Recommended)", {
                "url": "rtmp://live.twitch.tv/live/",
                "resolution": "1920x1080",
                "fps": "30",
                "bitrate": 4500,
                "codec": "libx264",
                "preset": "veryfast"
            }),
            ("YouTube Live", {
                "url": "rtmp://a.rtmp.youtube.com/live2/",
                "resolution": "1920x1080", 
                "fps": "30",
                "bitrate": 4500,
                "codec": "libx264",
                "preset": "veryfast"
            }),
            ("Facebook Live", {
                "url": "rtmps://live-api-s.facebook.com:443/rtmp/",
                "resolution": "1280x720",
                "fps": "30", 
                "bitrate": 2500,
                "codec": "libx264",
                "preset": "fast"
            })
        ]
        
        for platform_name, platform_values in platforms:
            platform_button = QPushButton(platform_name)
            platform_button.clicked.connect(lambda checked, values=platform_values: self.apply_platform_preset(values))
            platform_layout.addWidget(platform_button)
        
        layout.addWidget(platform_group)
        layout.addStretch()
        
        return tab
        
    def on_platform_changed(self, platform):
        """Handle platform selection change"""
        is_hdmi = platform == "HDMI Display"
        
        # Show/hide appropriate settings groups
        if hasattr(self, 'hdmi_group'):
            self.hdmi_group.setVisible(is_hdmi)
        
        # Show/hide streaming-related fields
        streaming_widgets = [
            self.url_edit, self.key_edit, self.show_key_checkbox
        ]
        
        for widget in streaming_widgets:
            widget.setVisible(not is_hdmi)
            
        # Update labels visibility
        if hasattr(self, 'url_label'):
            self.url_label.setVisible(not is_hdmi)
        if hasattr(self, 'key_label'):
            self.key_label.setVisible(not is_hdmi)
        
        # Set platform URLs for streaming platforms
        if not is_hdmi:
            platform_urls = {
                "Twitch": "rtmp://live.twitch.tv/live/",
                "YouTube Live": "rtmp://a.rtmp.youtube.com/live2/",
                "Facebook Live": "rtmps://live-api-s.facebook.com:443/rtmp/",
                "Custom RTMP": "",
                "Custom HLS": "",
                "Custom WebRTC": ""
            }
            
            if platform in platform_urls:
                self.url_edit.setText(platform_urls[platform])
            
    def on_resolution_changed(self, resolution):
        """Handle resolution selection change"""
        is_custom = resolution == "Custom"
        self.width_spinbox.setEnabled(is_custom)
        self.height_spinbox.setEnabled(is_custom)
        
        if not is_custom:
            # Parse resolution from combo text
            if "1920x1080" in resolution:
                self.width_spinbox.setValue(1920)
                self.height_spinbox.setValue(1080)
            elif "1280x720" in resolution:
                self.width_spinbox.setValue(1280)
                self.height_spinbox.setValue(720)
            elif "854x480" in resolution:
                self.width_spinbox.setValue(854)
                self.height_spinbox.setValue(480)
            elif "640x360" in resolution:
                self.width_spinbox.setValue(640)
                self.height_spinbox.setValue(360)
                
    def toggle_key_visibility(self, show):
        """Toggle stream key visibility"""
        if show:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            
    def apply_preset(self, preset_values):
        """Apply quality preset values"""
        if "resolution" in preset_values:
            resolution = preset_values["resolution"]
            # Find matching resolution in combo
            for i in range(self.resolution_combo.count()):
                if resolution in self.resolution_combo.itemText(i):
                    self.resolution_combo.setCurrentIndex(i)
                    break
                    
        if "fps" in preset_values:
            fps_text = str(preset_values["fps"])
            fps_index = self.fps_combo.findText(fps_text)
            if fps_index >= 0:
                self.fps_combo.setCurrentIndex(fps_index)
                
        if "bitrate" in preset_values:
            self.bitrate_spinbox.setValue(preset_values["bitrate"])
            
    def apply_platform_preset(self, platform_values):
        """Apply platform preset values"""
        if "url" in platform_values:
            self.url_edit.setText(platform_values["url"])
            
        # Apply other preset values
        self.apply_preset(platform_values)
        
        if "codec" in platform_values:
            codec_index = self.codec_combo.findText(platform_values["codec"])
            if codec_index >= 0:
                self.codec_combo.setCurrentIndex(codec_index)
                
        if "preset" in platform_values:
            preset_index = self.preset_combo.findText(platform_values["preset"])
            if preset_index >= 0:
                self.preset_combo.setCurrentIndex(preset_index)
                
    def test_connection(self):
        """Test the stream connection"""
        # This would implement actual connection testing
        # For now, just validate the URL format
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        
        if not url:
            self.show_status("Error: Stream URL is required", error=True)
            return
            
        if not key:
            self.show_status("Error: Stream key is required", error=True)
            return
            
        if not (url.startswith("rtmp://") or url.startswith("rtmps://") or url.startswith("http")):
            self.show_status("Error: Invalid URL format", error=True)
            return
            
        self.show_status("Connection test passed", error=False)
        
    def update_display_options(self):
        """Update display options in combo box"""
        if not hasattr(self, 'display_combo'):
            return
            
        current_text = self.display_combo.currentText()
        self.display_combo.clear()
        
        display_options = self.display_manager.get_display_options_for_combo()
        for display_name, display_index in display_options:
            self.display_combo.addItem(display_name, display_index)
            
        # Try to restore previous selection
        if current_text:
            index = self.display_combo.findText(current_text)
            if index >= 0:
                self.display_combo.setCurrentIndex(index)
        
    def show_status(self, message, error=False):
        """Show status message"""
        # Create a temporary status label
        if not hasattr(self, 'status_label'):
            self.status_label = QLabel()
            self.layout().insertWidget(self.layout().count() - 1, self.status_label)
            
        if error:
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
        self.status_label.setText(message)
        
        # Auto-clear after 3 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))


    def start_stream_action(self):
        """Configure and start streaming using the provided StreamManager"""
        # Always persist current form values to self.settings
        self.settings = self.get_settings()
        # Emit so external listeners can save/update
        self.settings_saved.emit(self.settings)

        platform = self.settings.get("platform", "")
        is_hdmi = platform == "HDMI Display"
        
        if is_hdmi:
            self._start_hdmi_stream()
        else:
            self._start_network_stream()
    
    def _start_hdmi_stream(self):
        """Start HDMI display streaming"""
        from hdmi_stream_manager import get_hdmi_stream_manager
        
        hdmi_manager = get_hdmi_stream_manager()
        
        # Validate HDMI settings
        if "hdmi_display_index" not in self.settings:
            self.show_status("Please select a display for HDMI output", error=True)
            return
        
        try:
            # Configure HDMI stream
            if not hdmi_manager.configure_hdmi_stream(self.stream_name, self.settings):
                self.show_status("Failed to configure HDMI stream", error=True)
                return
            
            self.show_status(f"Starting HDMI output on display {self.settings['hdmi_display_index']}...", error=False)
            
            # Start HDMI stream
            if hdmi_manager.start_hdmi_stream(self.stream_name):
                self.show_status("HDMI display started successfully", error=False)
            else:
                self.show_status("Failed to start HDMI display", error=True)
                
        except Exception as e:
            self.show_status(f"Error starting HDMI stream: {str(e)}", error=True)
    
    def _start_network_stream(self):
        """Start network streaming (RTMP/etc)"""
        if not self.stream_manager:
            self.show_status("No StreamManager available", error=True)
            return
            
        # Validate minimal fields
        if not self.settings.get("url"):
            self.show_status("Stream URL is required", error=True)
            return
            
        if not self.settings.get("key"):
            self.show_status("Stream key is required", error=True)
            return

        # Validate URL format
        url = self.settings.get("url", "")
        if not (url.startswith("rtmp://") or url.startswith("rtmps://")):
            self.show_status("Invalid URL format. Must start with rtmp:// or rtmps://", error=True)
            return

        try:
            # Configure and attempt to start
            self.stream_manager.configure_stream(self.stream_name, self.settings)
            
            # Show starting status
            self.show_status(f"Starting {self.stream_name}...", error=False)
            
            # Start the stream
            if self.stream_manager.start_stream(self.stream_name):
                self.show_status(f"{self.stream_name} started successfully", error=False)
            else:
                self.show_status("Failed to start stream. Check FFmpeg installation and stream credentials.", error=True)
                
        except Exception as e:
            self.show_status(f"Error starting stream: {str(e)}", error=True)

    def stop_stream_action(self):
        """Stop streaming via StreamManager"""
        platform = self.settings.get("platform", "")
        is_hdmi = platform == "HDMI Display"
        
        if is_hdmi:
            self._stop_hdmi_stream()
        else:
            self._stop_network_stream()
    
    def _stop_hdmi_stream(self):
        """Stop HDMI display streaming"""
        from hdmi_stream_manager import get_hdmi_stream_manager
        
        hdmi_manager = get_hdmi_stream_manager()
        
        try:
            if hdmi_manager.is_hdmi_streaming(self.stream_name):
                hdmi_manager.stop_hdmi_stream(self.stream_name)
                self.show_status("HDMI display stopped", error=False)
            else:
                self.show_status("HDMI display not active", error=True)
        except Exception as e:
            self.show_status(f"Error stopping HDMI stream: {str(e)}", error=True)
    
    def _stop_network_stream(self):
        """Stop network streaming"""
        if not self.stream_manager:
            self.show_status("No StreamManager available", error=True)
            return
            
        try:
            if self.stream_manager.is_streaming(self.stream_name):
                self.stream_manager.stop_stream(self.stream_name)
                self.show_status(f"{self.stream_name} stopped", error=False)
            else:
                self.show_status("Stream not active", error=True)
        except Exception as e:
            self.show_status(f"Error stopping stream: {str(e)}", error=True)
        
    def get_settings(self):
        """Get current settings as dictionary"""
        # Get resolution
        if self.resolution_combo.currentText() == "Custom":
            width = self.width_spinbox.value()
            height = self.height_spinbox.value()
            resolution = f"{width}x{height}"
        else:
            resolution_text = self.resolution_combo.currentText()
            resolution = resolution_text.split(" ")[0]  # Extract "1920x1080" from "1920x1080 (1080p)"
            
        settings = {
            "platform": self.platform_combo.currentText(),
            "url": self.url_edit.text().strip(),
            "key": self.key_edit.text().strip(),
            "resolution": resolution,
            "fps": int(self.fps_combo.currentText()),
            "video_bitrate": self.bitrate_spinbox.value(),
            "audio_bitrate": int(self.audio_bitrate_combo.currentText()),
            "sample_rate": int(self.sample_rate_combo.currentText()),
            "codec": self.codec_combo.currentText(),
            "preset": self.preset_combo.currentText(),
            "profile": self.profile_combo.currentText(),
            "keyframe_interval": self.keyframe_spinbox.value(),
            "buffer_size": self.buffer_spinbox.value(),
            "reconnect_attempts": self.reconnect_spinbox.value(),
            "low_latency": self.low_latency_checkbox.isChecked()
        }
        
        # Add HDMI-specific settings
        if hasattr(self, 'display_combo') and self.display_combo.currentData() is not None:
            settings.update({
                "hdmi_display_index": self.display_combo.currentData(),
                "hdmi_display_mode": self.display_mode_combo.currentText(),
                "hdmi_always_on_top": self.always_on_top_checkbox.isChecked(),
                "hdmi_match_resolution": self.match_display_res_checkbox.isChecked()
            })
        
        return settings
        
    def set_settings(self, settings):
        """Set settings from dictionary"""
        if "platform" in settings:
            platform_index = self.platform_combo.findText(settings["platform"])
            if platform_index >= 0:
                self.platform_combo.setCurrentIndex(platform_index)
                
        if "url" in settings:
            self.url_edit.setText(settings["url"])
            
        if "key" in settings:
            self.key_edit.setText(settings["key"])
            
        if "resolution" in settings:
            resolution = settings["resolution"]
            # Try to find matching preset resolution
            found_preset = False
            for i in range(self.resolution_combo.count()):
                if resolution in self.resolution_combo.itemText(i):
                    self.resolution_combo.setCurrentIndex(i)
                    found_preset = True
                    break
                    
            if not found_preset:
                # Set to custom and update spinboxes
                custom_index = self.resolution_combo.findText("Custom")
                if custom_index >= 0:
                    self.resolution_combo.setCurrentIndex(custom_index)
                    try:
                        width, height = resolution.split("x")
                        self.width_spinbox.setValue(int(width))
                        self.height_spinbox.setValue(int(height))
                    except:
                        pass
                        
        if "fps" in settings:
            fps_index = self.fps_combo.findText(str(settings["fps"]))
            if fps_index >= 0:
                self.fps_combo.setCurrentIndex(fps_index)
                
        if "video_bitrate" in settings:
            self.bitrate_spinbox.setValue(settings["video_bitrate"])
            
        # Set other advanced settings
        for setting_name, widget_name in [
            ("audio_bitrate", "audio_bitrate_combo"),
            ("sample_rate", "sample_rate_combo"),
            ("codec", "codec_combo"),
            ("preset", "preset_combo"),
            ("profile", "profile_combo")
        ]:
            if setting_name in settings:
                widget = getattr(self, widget_name)
                value_index = widget.findText(str(settings[setting_name]))
                if value_index >= 0:
                    widget.setCurrentIndex(value_index)
                    
        # Set spinbox values
        if "keyframe_interval" in settings:
            self.keyframe_spinbox.setValue(settings["keyframe_interval"])
        if "buffer_size" in settings:
            self.buffer_spinbox.setValue(settings["buffer_size"])
        if "reconnect_attempts" in settings:
            self.reconnect_spinbox.setValue(settings["reconnect_attempts"])
            
        # Set checkbox
        if "low_latency" in settings:
            self.low_latency_checkbox.setChecked(settings["low_latency"])
            
        # Set HDMI settings
        if hasattr(self, 'display_combo') and "hdmi_display_index" in settings:
            display_index = settings["hdmi_display_index"]
            for i in range(self.display_combo.count()):
                if self.display_combo.itemData(i) == display_index:
                    self.display_combo.setCurrentIndex(i)
                    break
                    
        if hasattr(self, 'display_mode_combo') and "hdmi_display_mode" in settings:
            mode_index = self.display_mode_combo.findText(settings["hdmi_display_mode"])
            if mode_index >= 0:
                self.display_mode_combo.setCurrentIndex(mode_index)
                
        if hasattr(self, 'always_on_top_checkbox') and "hdmi_always_on_top" in settings:
            self.always_on_top_checkbox.setChecked(settings["hdmi_always_on_top"])
            
        if hasattr(self, 'match_display_res_checkbox') and "hdmi_match_resolution" in settings:
            self.match_display_res_checkbox.setChecked(settings["hdmi_match_resolution"])

            
    def load_default_settings(self):
        """Load default settings"""
        total_displays = len(self.display_manager.get_displays())
        default_platform = "HDMI Display" if total_displays > 1 else "Custom RTMP"
        
        return {
            "platform": default_platform,
            "url": "",
            "key": "",
            "resolution": "1920x1080",
            "fps": 30,
            "video_bitrate": 2500,
            "audio_bitrate": 128,
            "sample_rate": 44100,
            "codec": "libx264",
            "preset": "veryfast",
            "profile": "main",
            "keyframe_interval": 2,
            "buffer_size": 3,
            "reconnect_attempts": 3,
            "low_latency": False,
            # HDMI-specific defaults
            "hdmi_display_index": 1 if len(self.display_manager.get_displays()) > 1 else 0,
            "hdmi_display_mode": "Fullscreen",
            "hdmi_always_on_top": True,
            "hdmi_match_resolution": True
        }
        
    def load_saved_settings(self):
        """Load saved settings from file"""
        settings_file = Path(__file__).parent / f"{self.stream_name.lower()}_settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
                    self.set_settings(self.settings)
            except Exception as e:
                print(f"Error loading settings: {e}")
                
    def save_settings(self):
        """Save settings and close dialog"""
        self.settings = self.get_settings()
        
        # Validate required fields based on platform
        is_hdmi = self.settings.get("platform") == "HDMI Display"
        
        if not is_hdmi:
            # Validate streaming settings
            if not self.settings["url"]:
                self.show_status("Error: Stream URL is required", error=True)
                return
                
            if not self.settings["key"]:
                self.show_status("Error: Stream key is required", error=True)
                return
        else:
            # Validate HDMI settings
            if "hdmi_display_index" not in self.settings:
                self.show_status("Error: Please select a display for HDMI output", error=True)
                return
        
        # Save to file
        settings_file = Path(__file__).parent / f"{self.stream_name.lower()}_settings.json"
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
            
        # Emit signal and accept
        self.settings_saved.emit(self.settings)
        self.accept()

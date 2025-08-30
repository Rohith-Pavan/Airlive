#!/usr/bin/env python3
"""
Test script for HDMI streaming functionality
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl

from display_manager import get_display_manager
from hdmi_stream_manager import get_hdmi_stream_manager
from stream_settings_dialog import StreamSettingsDialog


class HDMITestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HDMI Streaming Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Managers
        self.display_manager = get_display_manager()
        self.hdmi_manager = get_hdmi_stream_manager()
        
        # Test media player for source content
        self.media_player = None
        self.source_video_widget = None
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("HDMI Streaming Test Application")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # Display info group
        display_group = QGroupBox("Display Information")
        display_layout = QVBoxLayout(display_group)
        
        displays = self.display_manager.get_displays()
        display_layout.addWidget(QLabel(f"Total displays detected: {len(displays)}"))
        
        for display in displays:
            display_layout.addWidget(QLabel(f"  • {display}"))
        
        external_displays = self.display_manager.get_external_displays()
        display_layout.addWidget(QLabel(f"External displays: {len(external_displays)}"))
        
        layout.addWidget(display_group)
        
        # Source video group
        source_group = QGroupBox("Source Video (Simulated)")
        source_layout = QVBoxLayout(source_group)
        
        # Video widget for source
        self.source_video_widget = QVideoWidget()
        self.source_video_widget.setMinimumHeight(200)
        self.source_video_widget.setStyleSheet("background-color: #333; border: 2px solid #666;")
        source_layout.addWidget(self.source_video_widget)
        
        # Source controls
        source_controls = QHBoxLayout()
        
        self.load_video_btn = QPushButton("Load Test Video")
        self.load_video_btn.clicked.connect(self.load_test_video)
        source_controls.addWidget(self.load_video_btn)
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_video)
        self.play_btn.setEnabled(False)
        source_controls.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_video)
        self.stop_btn.setEnabled(False)
        source_controls.addWidget(self.stop_btn)
        
        source_controls.addStretch()
        source_layout.addLayout(source_controls)
        
        layout.addWidget(source_group)
        
        # HDMI controls group
        hdmi_group = QGroupBox("HDMI Streaming Controls")
        hdmi_layout = QVBoxLayout(hdmi_group)
        
        # HDMI controls
        hdmi_controls = QHBoxLayout()
        
        self.settings_btn = QPushButton("Stream Settings")
        self.settings_btn.clicked.connect(self.open_stream_settings)
        hdmi_controls.addWidget(self.settings_btn)
        
        self.start_hdmi_btn = QPushButton("Start HDMI Display")
        self.start_hdmi_btn.clicked.connect(self.start_hdmi_test)
        self.start_hdmi_btn.setEnabled(self.display_manager.has_external_displays())
        hdmi_controls.addWidget(self.start_hdmi_btn)
        
        self.stop_hdmi_btn = QPushButton("Stop HDMI Display")
        self.stop_hdmi_btn.clicked.connect(self.stop_hdmi_test)
        self.stop_hdmi_btn.setEnabled(False)
        hdmi_controls.addWidget(self.stop_hdmi_btn)
        
        hdmi_controls.addStretch()
        hdmi_layout.addLayout(hdmi_controls)
        
        # Status display
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        hdmi_layout.addWidget(QLabel("Status:"))
        hdmi_layout.addWidget(self.status_text)
        
        layout.addWidget(hdmi_group)
        
        # Initial status
        if not self.display_manager.has_external_displays():
            self.log_status("⚠️ No external displays detected. Connect an HDMI display to test.")
        else:
            self.log_status("✅ External displays detected. Ready for HDMI streaming test.")
    
    def connect_signals(self):
        """Connect manager signals"""
        self.hdmi_manager.hdmi_started.connect(self.on_hdmi_started)
        self.hdmi_manager.hdmi_stopped.connect(self.on_hdmi_stopped)
        self.hdmi_manager.hdmi_error.connect(self.on_hdmi_error)
        
        self.display_manager.displays_changed.connect(self.on_displays_changed)
    
    def load_test_video(self):
        """Load a test video file"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Test Video", 
            "", 
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
        )
        
        if file_path:
            # Create media player if not exists
            if not self.media_player:
                self.media_player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.media_player.setAudioOutput(self.audio_output)
                self.media_player.setVideoOutput(self.source_video_widget)
            
            # Load video
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.play_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            
            self.log_status(f"📹 Loaded video: {file_path}")
    
    def play_video(self):
        """Play the loaded video"""
        if self.media_player:
            self.media_player.play()
            self.log_status("▶️ Playing source video")
    
    def stop_video(self):
        """Stop the video"""
        if self.media_player:
            self.media_player.stop()
            self.log_status("⏹️ Stopped source video")
    
    def open_stream_settings(self):
        """Open stream settings dialog"""
        dialog = StreamSettingsDialog("TestHDMI", self)
        if dialog.exec():
            self.log_status("💾 Stream settings saved")
    
    def start_hdmi_test(self):
        """Start HDMI streaming test"""
        if not self.display_manager.has_external_displays():
            self.log_status("❌ No external displays available")
            return
        
        # Use first external display
        external_displays = self.display_manager.get_external_displays()
        target_display = external_displays[0]
        
        # Create test settings
        settings = {
            'platform': 'HDMI Display',
            'hdmi_display_index': target_display.index,
            'hdmi_display_mode': 'Windowed (800x600)',
            'hdmi_always_on_top': True,
            'hdmi_match_resolution': False
        }
        
        # Configure and start
        if self.hdmi_manager.configure_hdmi_stream("TestHDMI", settings):
            if self.hdmi_manager.start_hdmi_stream("TestHDMI", self.source_video_widget):
                self.start_hdmi_btn.setEnabled(False)
                self.stop_hdmi_btn.setEnabled(True)
                self.log_status(f"🖥️ Started HDMI display on {target_display.name}")
            else:
                self.log_status("❌ Failed to start HDMI display")
        else:
            self.log_status("❌ Failed to configure HDMI stream")
    
    def stop_hdmi_test(self):
        """Stop HDMI streaming test"""
        if self.hdmi_manager.stop_hdmi_stream("TestHDMI"):
            self.start_hdmi_btn.setEnabled(True)
            self.stop_hdmi_btn.setEnabled(False)
            self.log_status("⏹️ Stopped HDMI display")
        else:
            self.log_status("❌ Failed to stop HDMI display")
    
    def on_hdmi_started(self, stream_name):
        """Handle HDMI stream started"""
        self.log_status(f"✅ HDMI stream '{stream_name}' started successfully")
    
    def on_hdmi_stopped(self, stream_name):
        """Handle HDMI stream stopped"""
        self.log_status(f"⏹️ HDMI stream '{stream_name}' stopped")
    
    def on_hdmi_error(self, stream_name, error_message):
        """Handle HDMI stream error"""
        self.log_status(f"❌ HDMI stream '{stream_name}' error: {error_message}")
    
    def on_displays_changed(self):
        """Handle display configuration changes"""
        displays = self.display_manager.get_displays()
        external = self.display_manager.get_external_displays()
        
        self.log_status(f"🔄 Display configuration changed: {len(displays)} total, {len(external)} external")
        
        # Update button states
        has_external = self.display_manager.has_external_displays()
        self.start_hdmi_btn.setEnabled(has_external and not self.hdmi_manager.is_hdmi_streaming("TestHDMI"))
    
    def log_status(self, message):
        """Log status message"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.status_text.append(formatted_message)
        print(formatted_message)  # Also print to console
    
    def closeEvent(self, event):
        """Handle window close"""
        # Clean up
        if self.media_player:
            self.media_player.stop()
        
        self.hdmi_manager.cleanup()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = HDMITestWindow()
    window.show()
    
    sys.exit(app.exec())
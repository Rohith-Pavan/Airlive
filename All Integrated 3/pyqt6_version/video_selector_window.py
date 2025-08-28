"""
Video Selector Window for selecting video sources (cameras and files)
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QComboBox, QLabel, QPushButton, QFileDialog)
from PyQt6.QtCore import QTimer, QUrl, pyqtSlot
from PyQt6.QtMultimedia import QMediaPlayer, QCamera, QMediaDevices, QAudioOutput, QMediaCaptureSession
from PyQt6.QtMultimediaWidgets import QVideoWidget
from dataclasses import dataclass
from typing import Any, List
from enum import Enum

class VideoSourceType(Enum):
    NONE = "None"
    WEBCAM = "Webcam"
    FILE = "File"

@dataclass
class VideoSource:
    type: VideoSourceType
    name: str
    data: Any  # QCameraDevice for Webcam, QUrl for File

class VideoSelectorWindow(QMainWindow):
    def __init__(self, target_widget: QVideoWidget, parent=None):
        super().__init__(parent)
        self.target_video_widget = target_widget
        self.video_sources: List[VideoSource] = []
        
        # Media components
        self.media_player = None
        self.audio_output = None
        self.current_camera = None
        self.capture_session = None
        self.active_camera_device = None
        
        # Timer for periodic refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.populate_video_sources)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
        self.setup_ui()
        self.populate_video_sources()
    
    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("Video Source Selector")
        self.setFixedSize(400, 200)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Source selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Video Source:"))
        
        self.source_combo_box = QComboBox()
        self.source_combo_box.currentIndexChanged.connect(self.on_source_selected)
        source_layout.addWidget(self.source_combo_box)
        
        layout.addLayout(source_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        browse_button = QPushButton("Browse Files...")
        browse_button.clicked.connect(self.browse_files)
        button_layout.addWidget(browse_button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.populate_video_sources)
        button_layout.addWidget(refresh_button)
        
        layout.addLayout(button_layout)
    
    def populate_video_sources(self):
        """Populate the combo box with available video sources"""
        self.video_sources.clear()
        self.source_combo_box.clear()
        
        # Add "None" option
        none_source = VideoSource(VideoSourceType.NONE, "None", None)
        self.video_sources.append(none_source)
        self.source_combo_box.addItem("None")
        
        # Add webcam sources
        cameras = QMediaDevices.videoInputs()
        for camera in cameras:
            webcam_source = VideoSource(
                VideoSourceType.WEBCAM, 
                f"Webcam: {camera.description()}", 
                camera
            )
            self.video_sources.append(webcam_source)
            self.source_combo_box.addItem(webcam_source.name)
    
    def browse_files(self):
        """Open file dialog to select video files"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Video File", 
            "", 
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;All Files (*)"
        )
        
        if file_path:
            file_url = QUrl.fromLocalFile(file_path)
            file_source = VideoSource(
                VideoSourceType.FILE,
                f"File: {file_path.split('/')[-1]}",
                file_url
            )
            self.video_sources.append(file_source)
            self.source_combo_box.addItem(file_source.name)
            # Select the newly added file
            self.source_combo_box.setCurrentIndex(len(self.video_sources) - 1)
    
    @pyqtSlot(int)
    def on_source_selected(self, index: int):
        """Handle source selection from combo box"""
        if index < 0 or index >= len(self.video_sources):
            return
        
        source = self.video_sources[index]
        
        # Stop current source first
        self.stop_current_source()
        
        if source.type == VideoSourceType.WEBCAM:
            self.start_camera(source.data)
        elif source.type == VideoSourceType.FILE:
            self.play_media_file(source.data)
        else:  # None
            self.status_label.setText("No source selected")
    
    def start_camera(self, camera_device):
        """Start camera with the given device"""
        try:
            self.current_camera = QCamera(camera_device)
            self.capture_session = QMediaCaptureSession()
            
            self.capture_session.setCamera(self.current_camera)
            self.capture_session.setVideoOutput(self.target_video_widget)
            
            self.current_camera.start()
            self.active_camera_device = camera_device
            
            self.status_label.setText(f"Camera started: {camera_device.description()}")
            
        except Exception as e:
            self.status_label.setText(f"Camera error: {str(e)}")
    
    def play_media_file(self, file_url: QUrl):
        """Play media file from the given URL"""
        try:
            self.media_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            
            self.media_player.setAudioOutput(self.audio_output)
            self.media_player.setVideoOutput(self.target_video_widget)
            
            # Connect error handling
            self.media_player.errorOccurred.connect(self.handle_media_player_error)
            self.media_player.playbackStateChanged.connect(self.handle_playback_state_changed)
            
            self.media_player.setSource(file_url)
            self.media_player.play()
            
            self.status_label.setText(f"Playing: {file_url.fileName()}")
            
        except Exception as e:
            self.status_label.setText(f"Media error: {str(e)}")
    
    def stop_current_source(self):
        """Stop the current video source"""
        if self.media_player:
            self.media_player.stop()
            self.media_player = None
            
        if self.audio_output:
            self.audio_output = None
            
        if self.current_camera:
            self.current_camera.stop()
            self.current_camera = None
            
        if self.capture_session:
            self.capture_session = None
    
    @pyqtSlot(QMediaPlayer.PlaybackState)
    def handle_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        """Handle media player playback state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.status_label.setText("Playing")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.status_label.setText("Paused")
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.status_label.setText("Stopped")
    
    @pyqtSlot(QMediaPlayer.Error, str)
    def handle_media_player_error(self, error: QMediaPlayer.Error, error_string: str):
        """Handle media player errors"""
        self.status_label.setText(f"Error: {error_string}")
    
    def closeEvent(self, event):
        """Clean up when window is closed"""
        self.refresh_timer.stop()
        self.stop_current_source()
        super().closeEvent(event)

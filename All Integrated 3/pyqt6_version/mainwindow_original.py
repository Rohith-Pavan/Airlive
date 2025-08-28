"""
MainWindow using the original UI design with PyQt6 functionality integrated
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QFrame, QFileDialog, QLabel)
from PyQt6.QtCore import QTimer, QUrl, pyqtSlot
from PyQt6.QtMultimedia import QMediaPlayer, QCamera, QMediaDevices, QAudioOutput, QMediaCaptureSession
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6 import uic

from video_selector_window import VideoSelectorWindow

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load the original UI file
        uic.loadUi('mainwindow.ui', self)
        
        # Make settings buttons more visible by adding text and styling
        self.make_buttons_visible()
        
        # Initialize media components
        self.init_media_components()
        
        # Setup video widgets in frames
        self.setup_video_widgets()
        
        # Setup connections
        self.setup_connections()
    
    def make_buttons_visible(self):
        """Make settings buttons more visible by adding text and styling"""
        button_style = """
        QPushButton {
            color: white;
            font-weight: bold;
            border: 1px solid #8f8f91;
            border-radius: 3px;
            background-color: #4a4a4a;
            min-width: 24px;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #5a5a5a;
        }
        QPushButton:pressed {
            background-color: #6a6a6a;
        }
        """
        
        # Style input settings buttons
        try:
            self.input1SettingsButton.setText("⚙")
            self.input1SettingsButton.setStyleSheet(button_style)
            self.input2SettingsButton.setText("⚙")
            self.input2SettingsButton.setStyleSheet(button_style)
            self.input3SettingsButton.setText("⚙")
            self.input3SettingsButton.setStyleSheet(button_style)
        except AttributeError as e:
            print(f"Input settings buttons not found: {e}")
        
        # Style media settings buttons
        try:
            self.media1SettingsButton.setText("⚙")
            self.media1SettingsButton.setStyleSheet(button_style)
            self.media2SettingsButton.setText("⚙")
            self.media2SettingsButton.setStyleSheet(button_style)
            self.media3SettingsButton.setText("⚙")
            self.media3SettingsButton.setStyleSheet(button_style)
        except AttributeError as e:
            print(f"Media settings buttons not found: {e}")
        
        # Stream buttons disabled for now
        # Intentionally no styling or connections for streaming controls
        
    def init_media_components(self):
        """Initialize all media-related components"""
        # Input cameras
        self.camera1 = None
        self.camera2 = None
        self.camera3 = None
        self.session1 = None
        self.session2 = None
        self.session3 = None
        
        # Media players for file uploads
        self.media_player1 = None
        self.media_player2 = None
        self.media_player3 = None
        
        # Video widgets
        self.video_widget1 = None
        self.video_widget2 = None
        self.video_widget3 = None
        self.media_video_widget1 = None
        self.media_video_widget2 = None
        self.media_video_widget3 = None
        self.output_preview_widget = None
        
        # No auxiliary windows needed (streaming disabled)
        
        # Current active input tracking
        self.current_active_input = None
        
    def setup_video_widgets(self):
        """Setup video widgets in the UI frames"""
        # Output preview video widget
        self.output_preview_widget = QVideoWidget(self.outputPreview)
        output_layout = QVBoxLayout(self.outputPreview)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output_preview_widget)
        
        # Track which source is currently shown on the output preview
        self.current_active_input = None
        
        # Setup input and media preview widgets
        self.setup_input_widgets()
        self.setup_media_widgets()
        
        # Initialize cameras and media players
        self.init_cameras()
        self.init_media_players()
        
    def init_transition_properties(self):
        """No-op: transitions disabled"""
        self.transition_animation = None
        self.transition_timer = QTimer()
        self.transition_timer.setSingleShot(True)
        
    def setup_connections(self):
        """Set up all signal-slot connections"""
        # Input switching connections (correct button names from UI)
        self.input1_1A_btn.clicked.connect(lambda: self.switch_to_input(1))
        self.input2_1A_btn.clicked.connect(lambda: self.switch_to_input(2))
        self.input3_1A_btn.clicked.connect(lambda: self.switch_to_input(3))
        
        # Media switching connections (correct button names from UI)
        self.media1_1A_btn.clicked.connect(lambda: self.switch_to_media(1))
        self.media2_1A_btn.clicked.connect(lambda: self.switch_to_media(2))
        self.media3_1A_btn.clicked.connect(lambda: self.switch_to_media(3))
        
        # Settings buttons (correct names from UI)
        self.input1SettingsButton.clicked.connect(lambda: self.open_video_selector(1))
        self.input2SettingsButton.clicked.connect(lambda: self.open_video_selector(2))
        self.input3SettingsButton.clicked.connect(lambda: self.open_video_selector(3))
        
        self.media1SettingsButton.clicked.connect(lambda: self.open_media_selector(1))
        self.media2SettingsButton.clicked.connect(lambda: self.open_media_selector(2))
        self.media3SettingsButton.clicked.connect(lambda: self.open_media_selector(3))
        
    
    # All transition/effect methods removed
    
    def setup_input_widgets(self):
        """Setup video widgets for camera inputs"""
        # Input 1 video widget (correct frame name from UI)
        self.video_widget1 = QVideoWidget(self.inputVideoFrame1)
        if self.inputVideoFrame1.layout() is None:
            layout1 = QVBoxLayout(self.inputVideoFrame1)
            layout1.setContentsMargins(0, 0, 0, 0)
            layout1.addWidget(self.video_widget1)
        
        # Input 2 video widget (correct frame name from UI)
        self.video_widget2 = QVideoWidget(self.inputVideoFrame2)
        if self.inputVideoFrame2.layout() is None:
            layout2 = QVBoxLayout(self.inputVideoFrame2)
            layout2.setContentsMargins(0, 0, 0, 0)
            layout2.addWidget(self.video_widget2)
        
        # Input 3 video widget (correct frame name from UI)
        self.video_widget3 = QVideoWidget(self.inputVideoFrame3)
        if self.inputVideoFrame3.layout() is None:
            layout3 = QVBoxLayout(self.inputVideoFrame3)
            layout3.setContentsMargins(0, 0, 0, 0)
            layout3.addWidget(self.video_widget3)
    
    def setup_media_widgets(self):
        """Setup video widgets for media files"""
        # Media 1 video widget (correct frame name from UI)
        self.media_video_widget1 = QVideoWidget(self.mediaVideoFrame1)
        if self.mediaVideoFrame1.layout() is None:
            layout1 = QVBoxLayout(self.mediaVideoFrame1)
            layout1.setContentsMargins(0, 0, 0, 0)
            layout1.addWidget(self.media_video_widget1)
        
        # Media 2 video widget (correct frame name from UI)
        self.media_video_widget2 = QVideoWidget(self.mediaVideoFrame2)
        if self.mediaVideoFrame2.layout() is None:
            layout2 = QVBoxLayout(self.mediaVideoFrame2)
            layout2.setContentsMargins(0, 0, 0, 0)
            layout2.addWidget(self.media_video_widget2)
        
        # Media 3 video widget (correct frame name from UI)
        self.media_video_widget3 = QVideoWidget(self.mediaVideoFrame3)
        if self.mediaVideoFrame3.layout() is None:
            layout3 = QVBoxLayout(self.mediaVideoFrame3)
            layout3.setContentsMargins(0, 0, 0, 0)
            layout3.addWidget(self.media_video_widget3)
    
    def init_cameras(self):
        """Initialize camera inputs"""
        available_cameras = QMediaDevices.videoInputs()
        
        if len(available_cameras) >= 1:
            self.camera1 = QCamera(available_cameras[0])
            self.session1 = QMediaCaptureSession()
            self.session1.setCamera(self.camera1)
            self.session1.setVideoOutput(self.video_widget1)
            
        if len(available_cameras) >= 2:
            self.camera2 = QCamera(available_cameras[1])
            self.session2 = QMediaCaptureSession()
            self.session2.setCamera(self.camera2)
            self.session2.setVideoOutput(self.video_widget2)
            
        if len(available_cameras) >= 3:
            self.camera3 = QCamera(available_cameras[2])
            self.session3 = QMediaCaptureSession()
            self.session3.setCamera(self.camera3)
            self.session3.setVideoOutput(self.video_widget3)
    
    def init_media_players(self):
        """Initialize media players"""
        # Media player 1
        self.media_player1 = QMediaPlayer()
        self.audio_output1 = QAudioOutput()
        self.media_player1.setAudioOutput(self.audio_output1)
        self.media_player1.setVideoOutput(self.media_video_widget1)
        
        # Media player 2
        self.media_player2 = QMediaPlayer()
        self.audio_output2 = QAudioOutput()
        self.media_player2.setAudioOutput(self.audio_output2)
        self.media_player2.setVideoOutput(self.media_video_widget2)
        
        # Media player 3
        self.media_player3 = QMediaPlayer()
        self.audio_output3 = QAudioOutput()
        self.media_player3.setAudioOutput(self.audio_output3)
        self.media_player3.setVideoOutput(self.media_video_widget3)
    
    def switch_to_input(self, input_number):
        """Route selected camera input to the output preview"""
        # Re-route the capture session's video output to the main preview
        if input_number == 1 and self.camera1 and self.session1:
            self.session1.setVideoOutput(self.output_preview_widget)
            self.camera1.start()
            self.current_active_input = 'camera1'
        elif input_number == 2 and self.camera2 and self.session2:
            self.session2.setVideoOutput(self.output_preview_widget)
            self.camera2.start()
            self.current_active_input = 'camera2'
        elif input_number == 3 and self.camera3 and self.session3:
            self.session3.setVideoOutput(self.output_preview_widget)
            self.camera3.start()
            self.current_active_input = 'camera3'
    
    def switch_to_media(self, media_number):
        """Route selected media player to the output preview and play"""
        if media_number == 1 and self.media_player1:
            self.media_player1.setVideoOutput(self.output_preview_widget)
            self.media_player1.play()
            self.current_active_input = 'media1'
        elif media_number == 2 and self.media_player2:
            self.media_player2.setVideoOutput(self.output_preview_widget)
            self.media_player2.play()
            self.current_active_input = 'media2'
        elif media_number == 3 and self.media_player3:
            self.media_player3.setVideoOutput(self.output_preview_widget)
            self.media_player3.play()
            self.current_active_input = 'media3'
    
    def open_video_selector(self, input_number):
        """Open video selector for camera input"""
        if input_number == 1:
            target_widget = self.video_widget1
        elif input_number == 2:
            target_widget = self.video_widget2
        elif input_number == 3:
            target_widget = self.video_widget3
        else:
            return
            
        selector = VideoSelectorWindow(target_widget, self)
        selector.show()
    
    def open_media_selector(self, media_number):
        """Open media file selector"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            f"Select Media File {media_number}",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )
        
        if file_path:
            if media_number == 1 and self.media_player1:
                self.media_player1.setSource(QUrl.fromLocalFile(file_path))
            elif media_number == 2 and self.media_player2:
                self.media_player2.setSource(QUrl.fromLocalFile(file_path))
            elif media_number == 3 and self.media_player3:
                self.media_player3.setSource(QUrl.fromLocalFile(file_path))
    
    # Removed signal handlers related to external switcher/streaming
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Clean up media resources
        if self.camera1:
            self.camera1.stop()
        if self.camera2:
            self.camera2.stop()
        if self.camera3:
            self.camera3.stop()
        
        if self.media_player1:
            self.media_player1.stop()
        if self.media_player2:
            self.media_player2.stop()
        if self.media_player3:
            self.media_player3.stop()
        
        super().closeEvent(event)

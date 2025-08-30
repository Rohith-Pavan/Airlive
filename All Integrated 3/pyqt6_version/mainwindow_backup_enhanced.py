"""
Main Window for GoLive Studio - PyQt6 Version
Handles video inputs, media playback, switching, and streaming functionality
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QFrame, QMenu, QFileDialog, QLabel)
from PyQt6.QtCore import QTimer, QUrl, pyqtSlot, QPropertyAnimation, QEasingCurve, QVariant, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtMultimedia import QMediaPlayer, QCamera, QMediaDevices, QAudioOutput, QMediaCaptureSession
from PyQt6.QtMultimediaWidgets import QVideoWidget

from switching import Switching
from video_selector_window import VideoSelectorWindow
from stream_settings_dialog import StreamSettingsDialog
from effects_manager import EffectsManager
from graphics_output_widget import GraphicsOutputManager


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize media components
        self.init_media_components()
        
        # Initialize UI components
        self.init_ui_components()
        
        # Setup UI
        self.setup_ui()
        
        # Setup connections
        self.setup_connections()
        
        # Initialize transition properties
        self.init_transition_properties()
        
        # Initialize effects manager for double-click removal
        self.init_effects_manager()
        
    def init_media_components(self):
        """Initialize all media-related components"""
        # Input cameras (camera-only)
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
        # Audio outputs for media players (kept to control mute/unmute)
        self.media_audio_output1 = None
        self.media_audio_output2 = None
        self.media_audio_output3 = None
        
        # Video widgets for inputs (cameras)
        self.video_widget1 = None
        self.video_widget2 = None
        self.video_widget3 = None
        
        # Video widgets for media (files)
        self.media_video_widget1 = None
        self.media_video_widget2 = None
        self.media_video_widget3 = None
        
        # Output preview widget
        self.output_preview_widget = None
        
        # Switcher
        self.switcher = None
        
        # Windows
        self.video_selector_window2 = None
        self.video_selector_window3 = None
        self.current_stream_window = None
        self.stream_settings_window = None
        
    def init_ui_components(self):
        """Initialize UI component references"""
        # Input frames
        self.input_video_frame1 = None
        self.input_video_frame2 = None
        self.input_video_frame3 = None
        
        # Media frames
        self.media_video_frame1 = None
        self.media_video_frame2 = None
        self.media_video_frame3 = None
        
        # Output preview frame
        self.output_preview = None
        
        # Buttons - Input switching
        self.input1_1A_btn = None
        self.input2_1A_btn = None
        self.input3_1A_btn = None
        self.input1_2B_btn = None
        self.input2_2B_btn = None
        self.input3_2B_btn = None
        
        # Buttons - Media switching
        self.media1_1A_btn = None
        self.media2_1A_btn = None
        self.media3_1A_btn = None
        self.media1_2B_btn = None
        self.media2_2B_btn = None
        self.media3_2B_btn = None
        
        # Settings buttons
        self.input1_settings_button = None
        self.input2_settings_button = None
        self.input3_settings_button = None
        self.media1_settings_button = None
        self.media2_settings_button = None
        self.media3_settings_button = None
        self.stream1_settings_btn = None
        
        # Transition buttons (consolidated)
        self.zoom_transition_btn = None
        self.fade_transition_btn = None
        
    def init_transition_properties(self):
        """Initialize transition-related properties"""
        self.transition_animation = None
        self.transition_timer = QTimer()
        self.transition_timer.setSingleShot(True)
        
        self.current_active_input = None
        self.next_active_input = None
        
        self.is_zoomed = False
        self.current_zoom_level = 1.0
        self.current_opacity = 1.0
        
    def setup_ui(self):
        """Set up the main user interface"""
        self.setWindowTitle("GoLive Studio")
        self.setGeometry(100, 100, 1371, 790)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(3)
        main_layout.setContentsMargins(9, 9, 9, 9)
        
        # Left panel
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setSpacing(9)
        
        # Top container with output preview
        top_container_layout = QHBoxLayout()
        top_container_layout.setSpacing(0)
        
        # Output preview frame
        self.output_preview = QFrame()
        self.output_preview.setFrameStyle(QFrame.Shape.StyledPanel)
        self.output_preview.setMinimumSize(800, 450)
        
        # Create output preview video widget
        self.output_preview_widget = QVideoWidget(self.output_preview)
        output_layout = QVBoxLayout(self.output_preview)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output_preview_widget)
        
        top_container_layout.addWidget(self.output_preview)
        left_panel_layout.addLayout(top_container_layout)
        
        # Input section
        input_section_layout = self.create_input_section()
        left_panel_layout.addLayout(input_section_layout)
        
        # Media section
        media_section_layout = self.create_media_section()
        left_panel_layout.addLayout(media_section_layout)
        
        # Transition section
        transition_section_layout = self.create_transition_section()
        left_panel_layout.addLayout(transition_section_layout)
        
        main_layout.addLayout(left_panel_layout)
        
        # Right panel with controls
        right_panel_layout = self.create_right_panel()
        main_layout.addLayout(right_panel_layout)
        
        # Initialize switcher
        self.switcher = Switching(self.output_preview_widget, self)
        
    def create_input_section(self):
        """Create the input section with camera inputs"""
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        
        # Input 1
        input1_layout = QVBoxLayout()
        input1_layout.addWidget(QLabel("Input 1"))
        
        self.input_video_frame1 = QFrame()
        self.input_video_frame1.setFrameStyle(QFrame.Shape.StyledPanel)
        self.input_video_frame1.setMinimumSize(200, 150)
        
        self.video_widget1 = QVideoWidget(self.input_video_frame1)
        frame1_layout = QVBoxLayout(self.input_video_frame1)
        frame1_layout.setContentsMargins(0, 0, 0, 0)
        frame1_layout.addWidget(self.video_widget1)
        
        input1_layout.addWidget(self.input_video_frame1)
        
        # Input 1 buttons
        input1_btn_layout = QHBoxLayout()
        self.input1_1A_btn = QPushButton("1A")
        self.input1_2B_btn = QPushButton("2B")
        self.input1_settings_button = QPushButton("Settings")
        input1_btn_layout.addWidget(self.input1_1A_btn)
        input1_btn_layout.addWidget(self.input1_2B_btn)
        input1_btn_layout.addWidget(self.input1_settings_button)
        input1_layout.addLayout(input1_btn_layout)
        
        input_layout.addLayout(input1_layout)
        
        # Input 2
        input2_layout = QVBoxLayout()
        input2_layout.addWidget(QLabel("Input 2"))
        
        self.input_video_frame2 = QFrame()
        self.input_video_frame2.setFrameStyle(QFrame.Shape.StyledPanel)
        self.input_video_frame2.setMinimumSize(200, 150)
        
        self.video_widget2 = QVideoWidget(self.input_video_frame2)
        frame2_layout = QVBoxLayout(self.input_video_frame2)
        frame2_layout.setContentsMargins(0, 0, 0, 0)
        frame2_layout.addWidget(self.video_widget2)
        
        input2_layout.addWidget(self.input_video_frame2)
        
        # Input 2 buttons
        input2_btn_layout = QHBoxLayout()
        self.input2_1A_btn = QPushButton("1A")
        self.input2_2B_btn = QPushButton("2B")
        self.input2_settings_button = QPushButton("Settings")
        input2_btn_layout.addWidget(self.input2_1A_btn)
        input2_btn_layout.addWidget(self.input2_2B_btn)
        input2_btn_layout.addWidget(self.input2_settings_button)
        input2_layout.addLayout(input2_btn_layout)
        
        input_layout.addLayout(input2_layout)
        
        # Input 3
        input3_layout = QVBoxLayout()
        input3_layout.addWidget(QLabel("Input 3"))
        
        self.input_video_frame3 = QFrame()
        self.input_video_frame3.setFrameStyle(QFrame.Shape.StyledPanel)
        self.input_video_frame3.setMinimumSize(200, 150)
        
        self.video_widget3 = QVideoWidget(self.input_video_frame3)
        frame3_layout = QVBoxLayout(self.input_video_frame3)
        frame3_layout.setContentsMargins(0, 0, 0, 0)
        frame3_layout.addWidget(self.video_widget3)
        
        input3_layout.addWidget(self.input_video_frame3)
        
        # Input 3 buttons
        input3_btn_layout = QHBoxLayout()
        self.input3_1A_btn = QPushButton("1A")
        self.input3_2B_btn = QPushButton("2B")
        self.input3_settings_button = QPushButton("Settings")
        input3_btn_layout.addWidget(self.input3_1A_btn)
        input3_btn_layout.addWidget(self.input3_2B_btn)
        input3_btn_layout.addWidget(self.input3_settings_button)
        input3_layout.addLayout(input3_btn_layout)
        
        input_layout.addLayout(input3_layout)
        
        return input_layout
    
    def create_media_section(self):
        """Create the media section with file inputs"""
        media_layout = QHBoxLayout()
        media_layout.setSpacing(5)
        
        # Media 1
        media1_layout = QVBoxLayout()
        media1_layout.addWidget(QLabel("Media 1"))
        
        self.media_video_frame1 = QFrame()
        self.media_video_frame1.setFrameStyle(QFrame.Shape.StyledPanel)
        self.media_video_frame1.setMinimumSize(200, 150)
        
        self.media_video_widget1 = QVideoWidget(self.media_video_frame1)
        media_frame1_layout = QVBoxLayout(self.media_video_frame1)
        media_frame1_layout.setContentsMargins(0, 0, 0, 0)
        media_frame1_layout.addWidget(self.media_video_widget1)
        
        media1_layout.addWidget(self.media_video_frame1)
        
        # Media 1 buttons
        media1_btn_layout = QHBoxLayout()
        self.media1_1A_btn = QPushButton("1A")
        self.media1_2B_btn = QPushButton("2B")
        self.media1_settings_button = QPushButton("Settings")
        media1_btn_layout.addWidget(self.media1_1A_btn)
        media1_btn_layout.addWidget(self.media1_2B_btn)
        media1_btn_layout.addWidget(self.media1_settings_button)
        media1_layout.addLayout(media1_btn_layout)
        
        media_layout.addLayout(media1_layout)
        
        # Media 2
        media2_layout = QVBoxLayout()
        media2_layout.addWidget(QLabel("Media 2"))
        
        self.media_video_frame2 = QFrame()
        self.media_video_frame2.setFrameStyle(QFrame.Shape.StyledPanel)
        self.media_video_frame2.setMinimumSize(200, 150)
        
        self.media_video_widget2 = QVideoWidget(self.media_video_frame2)
        media_frame2_layout = QVBoxLayout(self.media_video_frame2)
        media_frame2_layout.setContentsMargins(0, 0, 0, 0)
        media_frame2_layout.addWidget(self.media_video_widget2)
        
        media2_layout.addWidget(self.media_video_frame2)
        
        # Media 2 buttons
        media2_btn_layout = QHBoxLayout()
        self.media2_1A_btn = QPushButton("1A")
        self.media2_2B_btn = QPushButton("2B")
        self.media2_settings_button = QPushButton("Settings")
        media2_btn_layout.addWidget(self.media2_1A_btn)
        media2_btn_layout.addWidget(self.media2_2B_btn)
        media2_btn_layout.addWidget(self.media2_settings_button)
        media2_layout.addLayout(media2_btn_layout)
        
        media_layout.addLayout(media2_layout)
        
        # Media 3
        media3_layout = QVBoxLayout()
        media3_layout.addWidget(QLabel("Media 3"))
        
        self.media_video_frame3 = QFrame()
        self.media_video_frame3.setFrameStyle(QFrame.Shape.StyledPanel)
        self.media_video_frame3.setMinimumSize(200, 150)
        
        self.media_video_widget3 = QVideoWidget(self.media_video_frame3)
        media_frame3_layout = QVBoxLayout(self.media_video_frame3)
        media_frame3_layout.setContentsMargins(0, 0, 0, 0)
        media_frame3_layout.addWidget(self.media_video_widget3)
        
        media3_layout.addWidget(self.media_video_frame3)
        
        # Media 3 buttons
        media3_btn_layout = QHBoxLayout()
        self.media3_1A_btn = QPushButton("1A")
        self.media3_2B_btn = QPushButton("2B")
        self.media3_settings_button = QPushButton("Settings")
        media3_btn_layout.addWidget(self.media3_1A_btn)
        media3_btn_layout.addWidget(self.media3_2B_btn)
        media3_btn_layout.addWidget(self.media3_settings_button)
        media3_layout.addLayout(media3_btn_layout)
        
        media_layout.addLayout(media3_layout)
        
        return media_layout
    
    def create_transition_section(self):
        """Create the transition section"""
        transition_layout = QHBoxLayout()
        
        transition_layout.addWidget(QLabel("Transitions:"))
        
        self.zoom_transition_btn = QPushButton("ZOOM")
        self.fade_transition_btn = QPushButton("FADE")
        
        transition_layout.addWidget(self.zoom_transition_btn)
        transition_layout.addWidget(self.fade_transition_btn)
        
        return transition_layout
    
    def create_right_panel(self):
        """Create the right panel with stream controls"""
        right_layout = QVBoxLayout()
        
        # Stream settings button
        self.stream1_settings_btn = QPushButton("Stream Settings")
        right_layout.addWidget(self.stream1_settings_btn)
        
        # Add some spacing
        right_layout.addStretch()
        
        return right_layout
    
    def setup_connections(self):
        """Set up all signal-slot connections"""
        # Input switching connections
        self.input1_1A_btn.clicked.connect(lambda: self.switch_to_input1())
        self.input2_1A_btn.clicked.connect(lambda: self.switch_to_input2())
        self.input3_1A_btn.clicked.connect(lambda: self.switch_to_input3())
        self.input1_2B_btn.clicked.connect(lambda: self.switch_to_input1())
        self.input2_2B_btn.clicked.connect(lambda: self.switch_to_input2())
        self.input3_2B_btn.clicked.connect(lambda: self.switch_to_input3())
        
        # Media switching connections
        self.media1_1A_btn.clicked.connect(lambda: self.switch_to_media1())
        self.media2_1A_btn.clicked.connect(lambda: self.switch_to_media2())
        self.media3_1A_btn.clicked.connect(lambda: self.switch_to_media3())
        self.media1_2B_btn.clicked.connect(lambda: self.switch_to_media1())
        self.media2_2B_btn.clicked.connect(lambda: self.switch_to_media2())
        self.media3_2B_btn.clicked.connect(lambda: self.switch_to_media3())
        
        # Settings connections
        self.input1_settings_button.clicked.connect(self.show_video_source_menu_for_input1)
        self.input2_settings_button.clicked.connect(self.show_video_source_menu_for_input2)
        self.input3_settings_button.clicked.connect(self.show_video_source_menu_for_input3)
        
        self.media1_settings_button.clicked.connect(self.on_media1_settings_btn_clicked)
        self.media2_settings_button.clicked.connect(self.on_media2_settings_btn_clicked)
        self.media3_settings_button.clicked.connect(self.on_media3_settings_btn_clicked)
        
        # Stream settings connection
        self.stream1_settings_btn.clicked.connect(self.on_stream1_settings_btn_clicked)
        
        # Transition connections
        self.zoom_transition_btn.clicked.connect(self.apply_zoom_transition)
        self.fade_transition_btn.clicked.connect(self.apply_fade_transition)
        
        # Switcher signal connection
        self.switcher.mediaSourceSwitched.connect(self.on_media_source_switched)
    
    # Input switching methods
    def switch_to_input1(self):
        """Switch to camera input 1"""
        self.switcher.switch_to_input(self.video_widget1, None, self.camera1, self.session1)
        self.current_active_input = self.video_widget1
        # Mute all media when switching to camera
        self.update_media_audio(None)
    
    def switch_to_input2(self):
        """Switch to camera input 2"""
        self.switcher.switch_to_input(self.video_widget2, None, self.camera2, self.session2)
        self.current_active_input = self.video_widget2
        self.update_media_audio(None)
    
    def switch_to_input3(self):
        """Switch to camera input 3"""
        self.switcher.switch_to_input(self.video_widget3, None, self.camera3, self.session3)
        self.current_active_input = self.video_widget3
        self.update_media_audio(None)
    
    # Media switching methods
    def switch_to_media1(self):
        """Switch to media file 1"""
        self.switcher.switch_to_input(self.media_video_widget1, self.media_player1, None, None)
        self.current_active_input = self.media_video_widget1
        self.update_media_audio(self.media_player1)
    
    def switch_to_media2(self):
        """Switch to media file 2"""
        self.switcher.switch_to_input(self.media_video_widget2, self.media_player2, None, None)
        self.current_active_input = self.media_video_widget2
        self.update_media_audio(self.media_player2)
    
    def switch_to_media3(self):
        """Switch to media file 3"""
        self.switcher.switch_to_input(self.media_video_widget3, self.media_player3, None, None)
        self.current_active_input = self.media_video_widget3
        self.update_media_audio(self.media_player3)
    
    # Video source menu methods
    def show_video_source_menu_for_input1(self):
        """Show video source selection menu for input 1"""
        menu = QMenu()
        cameras = QMediaDevices.videoInputs()
        
        for camera in cameras:
            action = menu.addAction(f"Webcam: {camera.description()}")
            action.triggered.connect(lambda checked, cam=camera: self.setup_camera1(cam))
        
        menu.exec(self.input1_settings_button.mapToGlobal(self.input1_settings_button.rect().bottomLeft()))
    
    def show_video_source_menu_for_input2(self):
        """Show video source selection menu for input 2"""
        menu = QMenu()
        cameras = QMediaDevices.videoInputs()
        
        for camera in cameras:
            action = menu.addAction(f"Webcam: {camera.description()}")
            action.triggered.connect(lambda checked, cam=camera: self.setup_camera2(cam))
        
        menu.exec(self.input2_settings_button.mapToGlobal(self.input2_settings_button.rect().bottomLeft()))
    
    def show_video_source_menu_for_input3(self):
        """Show video source selection menu for input 3"""
        menu = QMenu()
        cameras = QMediaDevices.videoInputs()
        
        for camera in cameras:
            action = menu.addAction(f"Webcam: {camera.description()}")
            action.triggered.connect(lambda checked, cam=camera: self.setup_camera3(cam))
        
        menu.exec(self.input3_settings_button.mapToGlobal(self.input3_settings_button.rect().bottomLeft()))
    
    # Camera setup methods
    def setup_camera1(self, camera_device):
        """Set up camera 1 with the given device"""
        if self.camera1:
            self.camera1.stop()
            self.camera1 = None
        if self.session1:
            self.session1 = None
        
        self.session1 = QMediaCaptureSession()
        self.camera1 = QCamera(camera_device)
        self.session1.setCamera(self.camera1)
        self.session1.setVideoOutput(self.video_widget1)
        self.camera1.start()
    
    def setup_camera2(self, camera_device):
        """Set up camera 2 with the given device"""
        if self.camera2:
            self.camera2.stop()
            self.camera2 = None
        if self.session2:
            self.session2 = None
        
        self.session2 = QMediaCaptureSession()
        self.camera2 = QCamera(camera_device)
        self.session2.setCamera(self.camera2)
        self.session2.setVideoOutput(self.video_widget2)
        self.camera2.start()
    
    def setup_camera3(self, camera_device):
        """Set up camera 3 with the given device"""
        if self.camera3:
            self.camera3.stop()
            self.camera3 = None
        if self.session3:
            self.session3 = None
        
        self.session3 = QMediaCaptureSession()
        self.camera3 = QCamera(camera_device)
        self.session3.setCamera(self.camera3)
        self.session3.setVideoOutput(self.video_widget3)
        self.camera3.start()
    
    # Media settings methods
    def on_media1_settings_btn_clicked(self):
        """Handle media 1 settings button click"""
        self.show_media_source_menu_for_media1()
    
    def on_media2_settings_btn_clicked(self):
        """Handle media 2 settings button click"""
        self.show_media_source_menu_for_media2()
    
    def on_media3_settings_btn_clicked(self):
        """Handle media 3 settings button click"""
        self.show_media_source_menu_for_media3()
    
    def show_media_source_menu_for_media1(self):
        """Show media source selection menu for media 1"""
        menu = QMenu()
        action = menu.addAction("Open Video File...")
        action.triggered.connect(lambda: self.open_video_file_for_media1())
        menu.exec(self.media1_settings_button.mapToGlobal(self.media1_settings_button.rect().bottomLeft()))
    
    def show_media_source_menu_for_media2(self):
        """Show media source selection menu for media 2"""
        menu = QMenu()
        action = menu.addAction("Open Video File...")
        action.triggered.connect(lambda: self.open_video_file_for_media2())
        menu.exec(self.media2_settings_button.mapToGlobal(self.media2_settings_button.rect().bottomLeft()))
    
    def show_media_source_menu_for_media3(self):
        """Show media source selection menu for media 3"""
        menu = QMenu()
        action = menu.addAction("Open Video File...")
        action.triggered.connect(lambda: self.open_video_file_for_media3())
        menu.exec(self.media3_settings_button.mapToGlobal(self.media3_settings_button.rect().bottomLeft()))
    
    # Video file opening methods
    def open_video_file_for_media1(self):
        """Open video file for media 1"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Video File for Media 1", "", 
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;All Files (*)"
        )
        
        if file_name:
            if self.media_player1:
                self.media_player1.stop()
                self.media_player1 = None
                self.media_audio_output1 = None
            
            self.media_player1 = QMediaPlayer()
            # Attach dedicated audio output, muted by default (only active source will be unmuted)
            self.media_audio_output1 = QAudioOutput()
            self.media_audio_output1.setMuted(True)
            self.media_player1.setAudioOutput(self.media_audio_output1)
            self.media_player1.setVideoOutput(self.media_video_widget1)
            self.media_player1.setSource(QUrl.fromLocalFile(file_name))
            self.media_player1.setLoops(QMediaPlayer.Loops.Infinite)
            self.media_player1.play()
            # Ensure audio policy consistent
            self.update_media_audio(None)
    
    def open_video_file_for_media2(self):
        """Open video file for media 2"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Video File for Media 2", "", 
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;All Files (*)"
        )
        
        if file_name:
            if self.media_player2:
                self.media_player2.stop()
                self.media_player2 = None
                self.media_audio_output2 = None
            
            self.media_player2 = QMediaPlayer()
            self.media_audio_output2 = QAudioOutput()
            self.media_audio_output2.setMuted(True)
            self.media_player2.setAudioOutput(self.media_audio_output2)
            self.media_player2.setVideoOutput(self.media_video_widget2)
            self.media_player2.setSource(QUrl.fromLocalFile(file_name))
            self.media_player2.setLoops(QMediaPlayer.Loops.Infinite)
            self.media_player2.play()
            self.update_media_audio(None)
    
    def open_video_file_for_media3(self):
        """Open video file for media 3"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Video File for Media 3", "", 
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;All Files (*)"
        )
        
        if file_name:
            if self.media_player3:
                self.media_player3.stop()
                self.media_player3 = None
                self.media_audio_output3 = None
            
            self.media_player3 = QMediaPlayer()
            self.media_audio_output3 = QAudioOutput()
            self.media_audio_output3.setMuted(True)
            self.media_player3.setAudioOutput(self.media_audio_output3)
            self.media_player3.setVideoOutput(self.media_video_widget3)
            self.media_player3.setSource(QUrl.fromLocalFile(file_name))
            self.media_player3.setLoops(QMediaPlayer.Loops.Infinite)
            self.media_player3.play()
            self.update_media_audio(None)
    
    # Stream settings method
    def on_stream1_settings_btn_clicked(self):
        """Handle stream settings button click"""
        if self.current_stream_window:
            if not self.current_stream_window.isVisible():
                self.current_stream_window.show()
                self.current_stream_window.raise_()
                self.current_stream_window.activateWindow()
            else:
                self.current_stream_window.raise_()
                self.current_stream_window.activateWindow()
            self.update_stream_settings_media_source()
            return
        
        self.current_stream_window = StreamSettingsDialog(self, self.output_preview_widget)
        self.current_stream_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self.update_stream_settings_media_source()
        
        # Connect to cleanup when window is destroyed
        self.current_stream_window.destroyed.connect(lambda: setattr(self, 'current_stream_window', None))
        
        self.current_stream_window.show()
    
    # Transition methods
    def apply_zoom_transition(self):
        """Apply zoom transition effect"""
        try:
            if not self.output_preview_widget:
                print("Warning: No output preview widget for zoom transition")
                return
                
            if not self.is_zoomed:
                self.perform_video_zoom(1.5)
                self.is_zoomed = True
            else:
                self.perform_video_zoom(1.0)
                self.is_zoomed = False
        except Exception as e:
            print(f"Error applying zoom transition: {e}")
    
    def apply_fade_transition(self):
        """Apply fade transition effect"""
        try:
            if not self.output_preview_widget:
                print("Warning: No output preview widget for fade transition")
                return
                
            if self.current_opacity > 0.5:
                self.perform_video_fade(0.3)
            else:
                self.perform_video_fade(1.0)
        except Exception as e:
            print(f"Error applying fade transition: {e}")
    
    def perform_video_zoom(self, zoom_level):
        """Perform video zoom animation"""
        try:
            if not self.output_preview_widget:
                print("Warning: No output preview widget for zoom")
                return
            
            # Stop any existing animation
            if hasattr(self, 'transition_animation') and self.transition_animation:
                self.transition_animation.stop()
            
            # Create zoom animation
            self.transition_animation = QPropertyAnimation(self, b"currentZoomLevel")
            self.transition_animation.setDuration(500)
            self.transition_animation.setStartValue(self.current_zoom_level)
            self.transition_animation.setEndValue(zoom_level)
            self.transition_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            def update_zoom(value):
                try:
                    self.current_zoom_level = value
                    # Apply zoom styling
                    original_size = self.output_preview_widget.size()
                    if original_size.width() > 0 and original_size.height() > 0:
                        scaled_width = int(original_size.width() * value)
                        scaled_height = int(original_size.height() * value)
                        
                        style = f"QVideoWidget {{ min-width: {scaled_width}px; min-height: {scaled_height}px; max-width: {scaled_width}px; max-height: {scaled_height}px; }}"
                        self.output_preview_widget.setStyleSheet(style)
                except Exception as e:
                    print(f"Error updating zoom: {e}")
            
            self.transition_animation.valueChanged.connect(update_zoom)
            self.transition_animation.start()
        except Exception as e:
            print(f"Error performing video zoom: {e}")
    
    def perform_video_fade(self, opacity):
        """Perform video fade animation"""
        try:
            if not self.output_preview_widget:
                print("Warning: No output preview widget for fade")
                return
            
            # Stop any existing animation
            if hasattr(self, 'transition_animation') and self.transition_animation:
                self.transition_animation.stop()
            
            # Create fade animation
            self.transition_animation = QPropertyAnimation(self, b"currentOpacity")
            self.transition_animation.setDuration(400)
            self.transition_animation.setStartValue(self.current_opacity)
            self.transition_animation.setEndValue(opacity)
            self.transition_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            def update_opacity(value):
                try:
                    self.current_opacity = value
                    # Apply opacity styling
                    alpha = int((1.0 - value) * 255)
                    alpha = max(0, min(255, alpha))  # Clamp alpha value
                    style = f"QVideoWidget {{ background-color: rgba(0,0,0,{alpha}); }}"
                    self.output_preview_widget.setStyleSheet(style)
                except Exception as e:
                    print(f"Error updating opacity: {e}")
            
            self.transition_animation.valueChanged.connect(update_opacity)
            self.transition_animation.start()
        except Exception as e:
            print(f"Error performing video fade: {e}")
    
    def reset_video_effects(self):
        """Reset all video effects to normal"""
        try:
            # Stop any running animations
            if hasattr(self, 'transition_animation') and self.transition_animation:
                self.transition_animation.stop()
                self.transition_animation = None
            
            if not self.output_preview_widget:
                print("Warning: No output preview widget to reset")
                return
            
            self.current_zoom_level = 1.0
            self.current_opacity = 1.0
            self.is_zoomed = False
            
            self.output_preview_widget.setStyleSheet("")
        except Exception as e:
            print(f"Error resetting video effects: {e}")
    
    # Signal handlers
    @pyqtSlot(object, object, object)
    def on_media_source_switched(self, player, camera, session):
        """Handle media source switched signal"""
        try:
            if self.current_stream_window:
                self.current_stream_window.set_current_media_source(player, camera, session)
            else:
                print("Warning: No stream window available for media source switch")
            # Enforce audio: unmute only the active media player, mute all others
            self.update_media_audio(player if player else None)
        except Exception as e:
            print(f"Error handling media source switch: {e}")

    def update_media_audio(self, active_player):
        """Mute all media players except the active one. If active_player is None, mute all."""
        try:
            pairs = [
                (self.media_player1, self.media_audio_output1),
                (self.media_player2, self.media_audio_output2),
                (self.media_player3, self.media_audio_output3),
            ]
            for p, audio in pairs:
                if p and audio:
                    audio.setMuted(p is not active_player)
        except Exception as e:
            print(f"Error updating media audio: {e}")
    
    def update_stream_settings_media_source(self):
        """Update stream settings with current media source"""
        try:
            if not self.current_stream_window:
                print("Warning: No stream window available for media source update")
                return
            
            # Determine which input is currently active
            if self.current_active_input == self.video_widget1:
                self.current_stream_window.set_current_media_source(None, self.camera1, self.session1)
            elif self.current_active_input == self.video_widget2:
                self.current_stream_window.set_current_media_source(None, self.camera2, self.session2)
            elif self.current_active_input == self.video_widget3:
                self.current_stream_window.set_current_media_source(None, self.camera3, self.session3)
            elif self.current_active_input == self.media_video_widget1:
                self.current_stream_window.set_current_media_source(self.media_player1, None, None)
            elif self.current_active_input == self.media_video_widget2:
                self.current_stream_window.set_current_media_source(self.media_player2, None, None)
            elif self.current_active_input == self.media_video_widget3:
                self.current_stream_window.set_current_media_source(self.media_player3, None, None)
            else:
                self.current_stream_window.set_current_media_source(None, None, None)
        except Exception as e:
            print(f"Error updating stream settings media source: {e}")
    
    def closeEvent(self, event):
        """Handle application close event"""
        try:
            print("Cleaning up resources before closing...")
            
            # Stop any running animations
            if hasattr(self, 'transition_animation') and self.transition_animation:
                self.transition_animation.stop()
                self.transition_animation = None
            
            # Clean up stream manager
            if hasattr(self, 'stream_manager') and self.stream_manager:
                try:
                    self.stream_manager.stop_stream()
                except Exception as e:
                    print(f"Error stopping stream: {e}")
            
            # Clean up media resources
            cameras = [getattr(self, f'camera{i}', None) for i in range(1, 4)]
            for camera in cameras:
                if camera:
                    try:
                        camera.stop()
                    except Exception as e:
                        print(f"Error stopping camera: {e}")
            
            players = [getattr(self, f'media_player{i}', None) for i in range(1, 4)]
            for player in players:
                if player:
                    try:
                        player.stop()
                    except Exception as e:
                        print(f"Error stopping media player: {e}")
            
            # Clean up sessions
            sessions = [getattr(self, f'session{i}', None) for i in range(1, 4)]
            for session in sessions:
                if session:
                    try:
                        session.setCamera(None)
                        session.setVideoOutput(None)
                    except Exception as e:
                        print(f"Error cleaning session: {e}")
            
            print("Resource cleanup completed")
            super().closeEvent(event)
        except Exception as e:
            print(f"Error in close event: {e}")
    
    def init_effects_manager(self):
        """Initialize effects manager for double-click removal"""
        try:
            # Initialize effects manager
            self.effects_manager = EffectsManager()
            self.graphics_manager = GraphicsOutputManager()
            
            # Connect effect signals
            self.effects_manager.effect_selected.connect(self.on_effect_selected)
            self.effects_manager.effect_removed.connect(self.on_effect_removed)
            
            # Setup effects UI
            self.setup_effects_ui()
            
            print("✅ Effects manager initialized with double-click removal")
            
        except Exception as e:
            print(f"❌ Error initializing effects manager: {e}")
    
    def setup_effects_ui(self):
        """Setup effects tabs in the UI"""
        try:
            from PyQt6.QtWidgets import QTabWidget, QScrollArea, QWidget, QGridLayout
            
            # Find effects tab widget in the UI
            effects_tab_widget = None
            for child in self.findChildren(QTabWidget):
                if "effect" in child.objectName().lower() or child.objectName() == "effectsTabWidget":
                    effects_tab_widget = child
                    break
            
            if not effects_tab_widget:
                print("⚠️ No effects tab widget found in UI")
                return
            
            # Clear existing tabs
            effects_tab_widget.clear()
            
            # Create tabs for each effect category
            for tab_name in self.effects_manager.tab_names:
                # Create scroll area for this tab
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_area.setObjectName(f"scrollArea_{tab_name}")
                
                # Create widget for scroll area
                scroll_widget = QWidget()
                scroll_area.setWidget(scroll_widget)
                
                # Create grid layout for effects
                grid_layout = QGridLayout(scroll_widget)
                grid_layout.setSpacing(5)
                
                # Populate with effects
                self.effects_manager.populate_tab_effects(tab_name, scroll_widget, grid_layout)
                
                # Add tab
                effects_tab_widget.addTab(scroll_area, tab_name)
                
                print(f"📁 Setup {tab_name} effects tab")
            
            print("✅ Effects UI setup complete")
            
        except Exception as e:
            print(f"❌ Error setting up effects UI: {e}")
    
    def on_effect_selected(self, tab_name, effect_path):
        """Handle effect application"""
        try:
            from pathlib import Path
            
            # Apply effect to main output widget
            if hasattr(self, 'graphics_manager'):
                self.graphics_manager.set_frame_for_widget("main_output", effect_path)
            
            # Update status
            effect_name = Path(effect_path).name
            print(f"✅ Applied effect: {effect_name} from {tab_name}")
            
            # Optional: Update UI status if available
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage(f"Applied effect: {effect_name}", 3000)
                
        except Exception as e:
            print(f"❌ Error applying effect: {e}")
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage(f"Error applying effect: {e}", 5000)
    
    def on_effect_removed(self, tab_name, effect_path):
        """Handle effect removal via double-click"""
        try:
            from pathlib import Path
            
            # Remove effect from main output widget
            if hasattr(self, 'graphics_manager'):
                self.graphics_manager.clear_frame_for_widget("main_output")
            
            # Also clear from output preview widget if it exists
            if hasattr(self, 'output_preview_widget') and self.output_preview_widget:
                # Clear any overlay effects from the output widget
                try:
                    # If the output widget has a graphics scene, clear it
                    if hasattr(self.output_preview_widget, 'clear_frame_overlay'):
                        self.output_preview_widget.clear_frame_overlay()
                    elif hasattr(self.output_preview_widget, 'scene'):
                        # Clear graphics scene overlays
                        scene = self.output_preview_widget.scene()
                        if scene:
                            # Remove overlay items
                            for item in scene.items():
                                if hasattr(item, 'zValue') and item.zValue() > 0:
                                    scene.removeItem(item)
                except Exception as clear_error:
                    print(f"⚠️ Error clearing output widget overlay: {clear_error}")
            
            # Update status
            effect_name = Path(effect_path).name
            print(f"🗑️ Removed effect: {effect_name} from {tab_name}")
            
            # Optional: Update UI status if available
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage(f"Removed effect: {effect_name}", 3000)
                
        except Exception as e:
            print(f"❌ Error removing effect: {e}")
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage(f"Error removing effect: {e}", 5000)
            super().closeEvent(event)

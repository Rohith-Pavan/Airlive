"""
Switching module for video input switching functionality
Handles switching between camera inputs and media file inputs
"""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QCamera, QMediaCaptureSession
from PyQt6.QtMultimediaWidgets import QVideoWidget

class Switching(QObject):
    # Signal emitted when media source is switched
    mediaSourceSwitched = pyqtSignal(object, object, object)  # player, camera, session
    
    def __init__(self, output_preview_widget, parent=None):
        super().__init__(parent)
        self.output_preview_widget = output_preview_widget
        self.current_output_player = None
        self.current_output_camera = None
        self.current_output_session = None
    
    def switch_to_input(self, input_widget, player=None, camera=None, session=None):
        """Switch the output to a specific input source"""
        # Clean up previous output connections
        if self.current_output_player:
            self.current_output_player.setVideoOutput(None)
            self.current_output_player = None
            
        if self.current_output_camera and self.current_output_session:
            self.current_output_session.setVideoOutput(None)
            self.current_output_camera = None
            self.current_output_session = None
        
        # Set up new output connection
        if player:
            # For media file input
            self.current_output_player = player
            player.setVideoOutput(self.output_preview_widget)
        elif camera and session:
            # For camera input
            self.current_output_camera = camera
            self.current_output_session = session
            session.setVideoOutput(self.output_preview_widget)
        
        # Emit signal to notify that the media source has switched
        self.mediaSourceSwitched.emit(
            self.current_output_player, 
            self.current_output_camera, 
            self.current_output_session
        )

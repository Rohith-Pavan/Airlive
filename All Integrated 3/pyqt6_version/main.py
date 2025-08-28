#!/usr/bin/env python3
"""
GoLive Studio - UI-only launcher
Loads and displays the original Qt Designer UI with video source selection functionality.
"""
    
import sys
from pathlib import Path
from PyQt6 import uic, QtGui
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from video_source_dialog import VideoSourceDialog
from media_file_dialog import MediaFileDialog
from effects_manager import EffectsManager
from graphics_output_widget import GraphicsOutputManager, preanalyze_effects_folder
from gstreamer.gst_stream_manager import NewStreamManager, NewStreamControlWidget
from gstreamer.audio_compositor import AudioCompositor



class VideoInputManager:
    def __init__(self, window):
        self.window = window
        self.input_sources = {
            'input1': None,
            'input2': None,
            'input3': None
        }
        self.input_cameras = {
            'input1': None,
            'input2': None,
            'input3': None
        }
        self.input_sessions = {
            'input1': None,
            'input2': None,
            'input3': None
        }
        self.input_widgets = {
            'input1': None,
            'input2': None,
            'input3': None
        }
        # Note: Using QVideoWidget directly (QVideoSink is not available on this build)
        # Media file management
        self.media_files = {
            'media1': None,
            'media2': None,
            'media3': None
        }
        self.media_players = {
            'media1': None,
            'media2': None,
            'media3': None
        }
        # Per-media audio outputs (Qt6 requires QAudioOutput to hear media audio)
        self.media_audio_outputs = {
            'media1': None,
            'media2': None,
            'media3': None
        }
        self.media_widgets = {
            'media1': None,
            'media2': None,
            'media3': None
        }
        # Output preview management
        self.current_output_source = None
        self.output_preview_widget = None  # Will be set to composite widget's internal video widget
        
        # --- Audio mute state ---
        self.muted_inputs = {
            'input1': False,
            'input2': False,
            'input3': False,
            'media1': False,
            'media2': False,
            'media3': False,
        }
        self.master_muted = False

        # Audio compositor reference (set from main)
        self.audio_compositor = None
        # Track which logical sources are currently present inside AudioCompositor
        # to avoid redundant add/remove (which spams pad-added and rebuilds decodebins)
        self._ac_present_sources = set()

        # Icon paths for toggling (fallback when UI doesn't auto-toggle)
        try:
            icons_dir = Path(__file__).resolve().parent / "icons"
            self._icon_volume = QtGui.QIcon(str(icons_dir / "Volume.png"))
            self._icon_mute = QtGui.QIcon(str(icons_dir / "Mute.png"))
        except Exception:
            self._icon_volume = QtGui.QIcon()
            self._icon_mute = QtGui.QIcon()

        self.setup_input_widgets()
        # Connect output panel (monitor) mute button
        self._connect_output_panel_audio_button()
        self.setup_media_widgets()
        # setup_output_preview() is now handled in main function with graphics widget
        self.connect_buttons()
        self.connect_audio_buttons()
        
    def setup_input_widgets(self):
        """Setup video widgets for each input"""
        # Create video widgets and add them to the input frames
        frame_mappings = {
            'input1': 'inputVideoFrame1',
            'input2': 'inputVideoFrame2', 
            'input3': 'inputVideoFrame3'
        }
        
        for input_name, frame_name in frame_mappings.items():
            try:
                if hasattr(self.window, frame_name):
                    frame = getattr(self.window, frame_name)
                    
                    if not frame:
                        print(f"Error: Frame {frame_name} is None")
                        continue
                    
                    # Override frame size policy to allow expansion
                    from PyQt6.QtWidgets import QSizePolicy
                    frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    frame.setMinimumSize(160, 90)  # Minimum 16:9 size
                    
                    # Create video widget
                    video_widget = QVideoWidget()
                    video_widget.setStyleSheet("background-color: black;")
                    # Keep original aspect ratio, show full input without cropping
                    try:
                        video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
                    except Exception:
                        pass
                    
                    # Set size policy to expand and fill available space
                    video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    
                    # Add to frame layout directly
                    if frame.layout() is None:
                        from PyQt6.QtWidgets import QVBoxLayout
                        layout = QVBoxLayout(frame)
                        layout.setContentsMargins(0, 0, 0, 0)
                        layout.setSpacing(0)
                    else:
                        layout = frame.layout()
                    
                    # Add video widget directly to show full input
                    layout.addWidget(video_widget)
                    self.input_widgets[input_name] = video_widget
                    
                    # Create capture session and connect to the widget directly
                    session = QMediaCaptureSession()
                    session.setVideoOutput(video_widget)
                    self.input_sessions[input_name] = session
                else:
                    print(f"Warning: Frame {frame_name} not found in UI")
            except Exception as e:
                print(f"Error setting up input widget {input_name}: {e}")
    
    def setup_media_widgets(self):
        """Setup video widgets for each media input"""
        frame_mappings = {
            'media1': 'mediaVideoFrame1',
            'media2': 'mediaVideoFrame2', 
            'media3': 'mediaVideoFrame3'
        }
        
        for media_name, frame_name in frame_mappings.items():
            try:
                if hasattr(self.window, frame_name):
                    frame = getattr(self.window, frame_name)
                    
                    if not frame:
                        print(f"Error: Frame {frame_name} is None")
                        continue
                    
                    # Create video widget
                    video_widget = QVideoWidget()
                    video_widget.setStyleSheet("background-color: black;")
                    
                    # Add to frame layout
                    if frame.layout() is None:
                        from PyQt6.QtWidgets import QVBoxLayout
                        layout = QVBoxLayout(frame)
                        layout.setContentsMargins(2, 2, 2, 2)
                    else:
                        layout = frame.layout()
                    
                    layout.addWidget(video_widget)
                    self.media_widgets[media_name] = video_widget
                    
                    # Create media player and connect to video widget
                    player = QMediaPlayer()
                    player.setVideoOutput(video_widget)
                    self.media_players[media_name] = player
                    
                    print(f"Media widget {media_name} setup complete")
                else:
                    print(f"Warning: Frame {frame_name} not found in UI")
            except Exception as e:
                print(f"Error setting up media widget {media_name}: {e}")
    
    def setup_output_preview(self):
        """Setup the main output preview widget"""
        if hasattr(self.window, 'outputPreview'):
            output_frame = self.window.outputPreview
            
            # Create video widget for output preview
            self.output_preview_widget = QVideoWidget()
            self.output_preview_widget.setStyleSheet("background-color: black;")
            
            # Add to output frame layout
            if output_frame.layout() is None:
                from PyQt6.QtWidgets import QVBoxLayout
                layout = QVBoxLayout(output_frame)
                layout.setContentsMargins(0, 0, 0, 0)
            else:
                layout = output_frame.layout()
            
            layout.addWidget(self.output_preview_widget)
        else:
            print("Warning: outputPreview frame not found in UI")
        
    def connect_buttons(self):
        """Connect settings buttons to open dialogs"""
        # Input video source buttons
        input_button_mappings = {
            'input1SettingsButton': 'input1',
            'input2SettingsButton': 'input2', 
            'input3SettingsButton': 'input3'
        }
        
        for button_name, input_name in input_button_mappings.items():
            try:
                if hasattr(self.window, button_name):
                    button = getattr(self.window, button_name)
                    if button:
                        button.clicked.connect(lambda checked, inp=input_name: self.open_source_dialog(inp))
                    else:
                        print(f"Warning: Button {button_name} is None")
                else:
                    print(f"Warning: Button {button_name} not found in UI")
            except Exception as e:
                print(f"Error connecting button {button_name}: {e}")
        
        # Media file buttons
        media_button_mappings = {
            'media1SettingsButton': 'media1',
            'media2SettingsButton': 'media2', 
            'media3SettingsButton': 'media3'
        }
        
        for button_name, media_name in media_button_mappings.items():
            try:
                if hasattr(self.window, button_name):
                    button = getattr(self.window, button_name)
                    if button:
                        button.clicked.connect(lambda checked, med=media_name: self.open_media_dialog(med))
                    else:
                        print(f"Warning: Button {button_name} is None")
                else:
                    print(f"Warning: Button {button_name} not found in UI")
            except Exception as e:
                print(f"Error connecting button {button_name}: {e}")
        
        # 1A switching buttons
        switching_button_mappings = {
            'input1_1A_btn': ('input', 'input1'),
            'input2_1A_btn': ('input', 'input2'),
            'input3_1A_btn': ('input', 'input3'),
            'media1_1A_btn': ('media', 'media1'),
            'media2_1A_btn': ('media', 'media2'),
            'media3_1A_btn': ('media', 'media3')
        }
        
        for button_name, (source_type, source_name) in switching_button_mappings.items():
            try:
                if hasattr(self.window, button_name):
                    button = getattr(self.window, button_name)
                    if button:
                        button.clicked.connect(lambda checked, st=source_type, sn=source_name: self.switch_to_output(st, sn))
                    else:
                        print(f"Warning: Button {button_name} is None")
                else:
                    print(f"Warning: Button {button_name} not found in UI")
            except Exception as e:
                print(f"Error connecting switching button {button_name}: {e}")

    def _toggle_button_icon(self, button, muted: bool):
        """Ensure the icon reflects mute state even if the .ui iconset doesn't auto-toggle."""
        try:
            if not isinstance(button, QWidget):
                return
            # If button is checkable, keep its checked state in sync
            if hasattr(button, 'setChecked'):
                button.setChecked(muted)
            # Explicitly set icon to be safe
            button.setIcon(self._icon_mute if muted else self._icon_volume)
        except Exception:
            pass

    def connect_audio_buttons(self):
        """Connect per-input and media audio buttons, plus optional master mute."""
        audio_btn_map = {
            'input1AudioButton': ('input', 'input1'),
            'input2AudioButton': ('input', 'input2'),
            'input3AudioButton': ('input', 'input3'),
            'media1AudioButton': ('media', 'media1'),
            'media2AudioButton': ('media', 'media2'),
            'media3AudioButton': ('media', 'media3'),
        }

        for btn_name, (stype, sname) in audio_btn_map.items():
            try:
                if hasattr(self.window, btn_name):
                    btn = getattr(self.window, btn_name)
                    if btn:
                        # Initialize icon to unmuted
                        self._toggle_button_icon(btn, self.muted_inputs.get(sname, False))
                        btn.clicked.connect(lambda checked=False, t=stype, n=sname: self.on_per_input_mute_toggle(t, n))
                    else:
                        print(f"Warning: Button {btn_name} is None")
                else:
                    print(f"Warning: Button {btn_name} not found in UI")
            except Exception as e:
                print(f"Error connecting audio button {btn_name}: {e}")

        # Optional master mute button if present in UI later
        for master_name in ("audioTopButton", "masterMuteButton", "master_mute_btn", "outputMasterMuteButton"):
            try:
                if hasattr(self.window, master_name):
                    mbtn = getattr(self.window, master_name)
                    if mbtn:
                        self._toggle_button_icon(mbtn, self.master_muted)
                        mbtn.clicked.connect(self.on_master_mute_toggle)
                        break
            except Exception:
                pass

    def on_per_input_mute_toggle(self, source_type: str, source_name: str):
        """Toggle mute for a specific input/media and update UI + integration hooks."""
        try:
            new_state = not self.muted_inputs.get(source_name, False)
            self.muted_inputs[source_name] = new_state

            # Update button icon
            btn_lookup = {
                'input1': 'input1AudioButton',
                'input2': 'input2AudioButton',
                'input3': 'input3AudioButton',
                'media1': 'media1AudioButton',
                'media2': 'media2AudioButton',
                'media3': 'media3AudioButton',
            }
            bname = btn_lookup.get(source_name)
            if bname and hasattr(self.window, bname):
                self._toggle_button_icon(getattr(self.window, bname), new_state)

            # Apply immediately only if the toggled source is currently active in output
            if self.current_output_source == (source_type, source_name):
                if source_type == 'media':
                    # Control media volume via AudioCompositor for active media
                    if getattr(self, 'audio_compositor', None):
                        vol = 0.0 if (new_state or self.master_muted) else 1.0
                        try:
                            # Ensure source exists in AC
                            if self.media_files.get(source_name) and source_name not in self._ac_present_sources:
                                self.audio_compositor.add_media_file_source(source_name, self.media_files[source_name])
                                self._ac_present_sources.add(source_name)
                        except Exception:
                            pass
                        self.audio_compositor.set_input_volume(source_name, vol)
                else:
                    # Control mic volume via audio compositor for active input
                    self._apply_per_input_mute(source_type, source_name, new_state)
            print(f"{'Muted' if new_state else 'Unmuted'} {source_name}")
        except Exception as e:
            print(f"Error toggling mute for {source_name}: {e}")

    def on_master_mute_toggle(self):
        """Toggle master mute for final mixed output."""
        try:
            self.master_muted = not self.master_muted
            # Update icon if button exists
            for master_name in ("masterMuteButton", "master_mute_btn", "outputMasterMuteButton"):
                btn = getattr(self.window, master_name, None)
                if btn:
                    self._toggle_button_icon(btn, self.master_muted)
                    break

            # Integration hook: adjust master volume when available
            self._apply_master_mute(self.master_muted)
            print(f"Master {'muted' if self.master_muted else 'unmuted'}")
        except Exception as e:
            print(f"Error toggling master mute: {e}")

    def _connect_output_panel_audio_button(self):
        """Connect the output panel (monitor) audio mute button to monitor-only mute.
        This only affects local preview audio, not the stream audio.
        """
        try:
            btn = getattr(self.window, 'audioTopButton', None)
            if not btn:
                return
            # Ensure unchecked (unmuted) by default
            try:
                btn.setChecked(False)
                self._toggle_button_icon(btn, False)
            except Exception:
                pass
            btn.toggled.connect(self.on_output_panel_mute_toggle)
        except Exception as e:
            print(f"Error connecting output panel audio button: {e}")

    def on_output_panel_mute_toggle(self, checked: bool):
        """Monitor-only mute toggle handler for output panel button."""
        try:
            # Update icon
            try:
                self._toggle_button_icon(self.window.audioTopButton, checked)
            except Exception:
                pass
            # Apply to AudioCompositor monitor branch only
            if getattr(self, 'audio_compositor', None):
                self.audio_compositor.set_monitor_muted(bool(checked))
            print(f"Output panel audio {'muted' if checked else 'unmuted'}")
        except Exception as e:
            print(f"Error toggling output panel audio: {e}")

    # --- Integration hooks (no-ops for now; to be wired to GStreamer when ready) ---
    def _apply_per_input_mute(self, source_type: str, source_name: str, muted: bool):
        try:
            # If an audio compositor is available, set volume for the logical input
            if getattr(self, 'audio_compositor', None):
                vol = 0.0 if muted else 1.0
                # Map directly by logical name; compositor is expected to have sources with same names
                self.audio_compositor.set_input_volume(source_name, vol)
        except Exception as e:
            print(f"Warning: Failed applying mute to {source_name}: {e}")

    def _apply_master_mute(self, muted: bool):
        try:
            if getattr(self, 'audio_compositor', None):
                vol = 0.0 if muted else 1.0
                self.audio_compositor.set_master_volume(vol)
        except Exception as e:
            print(f"Warning: Failed applying master mute: {e}")
    
    def open_source_dialog(self, input_name):
        """Open video source selection dialog for specified input"""
        current_source = self.input_sources.get(input_name)
        dialog = VideoSourceDialog(current_source, self.window)
        
        if dialog.exec() == dialog.DialogCode.Accepted:
            selected_source = dialog.get_selected_source()
            if selected_source:
                self.set_input_source(input_name, selected_source)
    
    def set_input_source(self, input_name, camera_device):
        """Set video source for specified input"""
        try:
            # Stop and cleanup existing camera if any
            if self.input_cameras[input_name]:
                old_camera = self.input_cameras[input_name]
                old_camera.stop()
                # Disconnect from session before destroying
                session = self.input_sessions[input_name]
                if session:
                    session.setCamera(None)
                    # Keep sink bound to widget; no need to clear video output here
                # Clean up the old camera
                old_camera.deleteLater()
                self.input_cameras[input_name] = None
                
            # Create new camera
            camera = QCamera(camera_device)
            self.input_cameras[input_name] = camera
            self.input_sources[input_name] = camera_device
            
            # Use camera's default format to preserve original resolution
            try:
                formats = camera_device.videoFormats()
                if formats:
                    # Log available formats for debugging
                    print(f"Available formats for {input_name}:")
                    for fmt in formats[:5]:  # Show first 5 formats
                        sz = fmt.resolution()
                        print(f"  {sz.width()}x{sz.height()}")
            except Exception as e:
                print(f"Could not list camera formats for {input_name}: {e}")

            # Set camera to session and start
            session = self.input_sessions[input_name]
            video_widget = self.input_widgets[input_name]
            
            if session and video_widget:
                # Ensure session is connected to the video widget
                session.setVideoOutput(video_widget)
                print(f"Video output set for {input_name}")
                
                # Then set camera to session
                session.setCamera(camera)
                print(f"Camera set to session for {input_name}")
                
                # Start the camera
                camera.start()
                print(f"Camera started for {input_name}")
                
                # Update input label to show selected source
                self.update_input_label(input_name, camera_device.description())
                print(f"Successfully set {input_name} to {camera_device.description()}")
                print(f"Camera session connected to video widget for {input_name}")
            else:
                print(f"Error: No session or video widget found for {input_name}")
                if not session:
                    print(f"  Session is None for {input_name}")
                    
        except Exception as e:
            print(f"Error setting camera for {input_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def open_media_dialog(self, media_name):
        """Open media file selection dialog for specified media input"""
        current_file = self.media_files.get(media_name)
        dialog = MediaFileDialog(current_file, self.window)
        
        if dialog.exec() == dialog.DialogCode.Accepted:
            selected_file = dialog.get_selected_file()
            if selected_file:
                self.set_media_file(media_name, selected_file)
    
    def set_media_file(self, media_name, file_path):
        """Set media file for specified media input"""
        try:
            # Stop and cleanup existing player if any
            if self.media_players[media_name]:
                old_player = self.media_players[media_name]
                old_player.stop()
                old_player.setVideoOutput(None)
                old_player.deleteLater()
                self.media_players[media_name] = None
            
            # Create new player and connect to video widget
            player = QMediaPlayer()
            video_widget = self.media_widgets[media_name]
            if video_widget:
                # Connect video output FIRST
                player.setVideoOutput(video_widget)
                print(f"Connected media player to video widget for {media_name}")
            else:
                print(f"Warning: No video widget found for {media_name}")
            
            self.media_players[media_name] = player
                
            # Set new media file
            if player:
                from PyQt6.QtCore import QUrl
                player.setSource(QUrl.fromLocalFile(file_path))
                self.media_files[media_name] = file_path
                # Do NOT route media audio into AudioCompositor here.
                # We will attach only the currently active media (1-A) during source switch
                # to guarantee that non-active media are silent in both monitor and stream.
                
                # Update media label to show selected file
                file_name = Path(file_path).name
                self.update_media_label(media_name, file_name)
                print(f"Successfully set {media_name} to {file_name}")
                
                # Auto-play the media
                player.play()
                print(f"Started playing media file for {media_name}")
            else:
                print(f"Error: No player found for {media_name}")
                
        except Exception as e:
            print(f"Error setting media file for {media_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def update_input_label(self, input_name, source_name):
        """Update input label to show selected source name"""
        # Map input names to actual label names in UI
        label_mappings = {
            'input1': 'label_input1',
            'input2': 'label_input2', 
            'input3': 'label_input3'
        }
        
        label_name = label_mappings.get(input_name)
        if label_name and hasattr(self.window, label_name):
            label = getattr(self.window, label_name)
            # Truncate long names
            display_name = source_name[:15] + "..." if len(source_name) > 15 else source_name
            label.setText(display_name)
        else:
            print(f"Warning: Label {label_name} not found for {input_name}")
    
    def update_media_label(self, media_name, file_name):
        """Update media label to show selected file name"""
        # Map media names to actual label names in UI
        label_mappings = {
            'media1': 'label_media1',
            'media2': 'label_media2', 
            'media3': 'label_media3'
        }
        
        label_name = label_mappings.get(media_name)
        if label_name and hasattr(self.window, label_name):
            label = getattr(self.window, label_name)
            # Truncate long names
            display_name = file_name[:15] + "..." if len(file_name) > 15 else file_name
            label.setText(display_name)
        else:
            print(f"Warning: Label {label_name} not found for {media_name}")
    
    def switch_to_output(self, source_type, source_name):
        """Switch the specified input or media to the main output preview"""
        try:
            # Clear previous output connections first
            self._clear_current_output()
            
            if source_type == 'input':
                # Switch camera input to output
                if source_name in self.input_cameras and self.input_cameras[source_name]:
                    camera = self.input_cameras[source_name]
                    session = self.input_sessions[source_name]
                    
                    if not session or not self.output_preview_widget:
                        print(f"Error: Invalid session or output widget for {source_name}")
                        return
                    
                    # Set camera output to main preview
                    session.setVideoOutput(self.output_preview_widget)
                    
                    # Ensure camera is running
                    if not camera.isActive():
                        camera.start()
                    
                    self.current_output_source = (source_type, source_name)
                    print(f"Switched output to {source_name} camera")
                    # Update audio routing: enable only this input's mic; disable others and all media audio
                    self._apply_audio_for_active_source('input', source_name)
                else:
                    print(f"No camera assigned to {source_name}. Please select a camera first.")
                    
            elif source_type == 'media':
                # Switch media file to output
                if source_name in self.media_players and self.media_players[source_name]:
                    player = self.media_players[source_name]

                    if not self.output_preview_widget:
                        print(f"Error: Invalid output widget for {source_name}")
                        return

                    # Set media player output to main preview
                    player.setVideoOutput(self.output_preview_widget)
                    # Do not attach a QAudioOutput; audio will be handled by AudioCompositor

                    # Play the media if it has a source
                    if self.media_files[source_name]:
                        player.play()

                    self.current_output_source = (source_type, source_name)
                    print(f"Switched output to {source_name} media")
                    # Update audio routing: enable only this media's audio in AudioCompositor; disable all mics and other media
                    self._apply_audio_for_active_source('media', source_name)
                else:
                    print(f"No media file assigned to {source_name}. Please select a media file first.")
                    
        except Exception as e:
            print(f"Error switching to {source_type} {source_name}: {e}")

    def _apply_audio_for_active_source(self, source_type: str, source_name: str):
        """Ensure only the active source has audible audio.
        - If active is input: activate that input's mic via AudioCompositor, mute/remove others; mute all media players.
        - If active is media: mute/disable all mics; unmute only the active media source inside AudioCompositor; mute other media sources.
        """
        try:
            # Handle inputs (mics) via AudioCompositor
            ac = getattr(self, 'audio_compositor', None)
            input_names = ('input1', 'input2', 'input3')
            media_names = ('media1', 'media2', 'media3')

            if ac:
                if source_type == 'input':
                    # Inputs: ensure only the selected mic is present and audible; remove all media sources entirely
                    for name in input_names:
                        if name == source_name:
                            try:
                                ac.add_auto_source(name)
                            except Exception:
                                pass
                            vol = 0.0 if self.muted_inputs.get(name, False) or self.master_muted else 1.0
                            ac.set_input_volume(name, vol)
                        else:
                            # Keep other inputs at 0 volume (or they may not exist yet)
                            ac.set_input_volume(name, 0.0)
                    # Remove all media sources to guarantee silence
                    for m in media_names:
                        try:
                            if m in self._ac_present_sources:
                                ac.remove_source(m)
                                self._ac_present_sources.discard(m)
                        except Exception:
                            pass
                else:
                    # Media active: remove all mic inputs from mix, and keep only the active media in the pipeline
                    for name in input_names:
                        try:
                            # Keep mics at 0 volume (or remove in future if added as sources)
                            ac.set_input_volume(name, 0.0)
                        except Exception:
                            pass
                    for m in media_names:
                        if m == source_name and self.media_files.get(m):
                            try:
                                # Re-add/ensure only the active media exists in the mixer
                                if m not in self._ac_present_sources:
                                    ac.add_media_file_source(m, self.media_files[m])
                                    self._ac_present_sources.add(m)
                            except Exception:
                                pass
                            vol = 0.0 if self.muted_inputs.get(m, False) or self.master_muted else 1.0
                            ac.set_input_volume(m, vol)
                        else:
                            try:
                                if m in self._ac_present_sources:
                                    ac.remove_source(m)
                                    self._ac_present_sources.discard(m)
                            except Exception:
                                pass
        except Exception as e:
            print(f"Error applying audio state for active source {source_type}:{source_name}: {e}")

    def _ensure_media_audio_output(self, media_name: str):
        """Create and attach QAudioOutput for a media player if missing."""
        try:
            if media_name not in self.media_players:
                return
            player = self.media_players.get(media_name)
            if not player:
                return
            if self.media_audio_outputs.get(media_name) is None:
                ao = QAudioOutput()
                try:
                    ao.setVolume(1.0)
                except Exception:
                    pass
                self.media_audio_outputs[media_name] = ao
                try:
                    player.setAudioOutput(ao)
                except Exception:
                    pass
        except Exception as e:
            print(f"Error creating audio output for {media_name}: {e}")
    
    def _clear_current_output(self):
        """Clear current output connections to prevent conflicts"""
        try:
            # Clear all camera sessions from output
            for session in self.input_sessions.values():
                if session and hasattr(session, 'videoOutput') and session.videoOutput() == self.output_preview_widget:
                    session.setVideoOutput(None)
            
            # Clear all media players from output
            for player in self.media_players.values():
                if player and hasattr(player, 'videoOutput') and player.videoOutput() == self.output_preview_widget:
                    player.setVideoOutput(None)
        except Exception as e:
            print(f"Error clearing output connections: {e}")
    
    def cleanup_resources(self):
        """Clean up all resources to prevent memory leaks"""
        try:
            # Clear output connections first
            self._clear_current_output()
            
            # Stop and cleanup all cameras
            for input_name, camera in list(self.input_cameras.items()):
                if camera:
                    try:
                        camera.stop()
                        # Disconnect from session
                        session = self.input_sessions.get(input_name)
                        if session:
                            session.setCamera(None)
                            session.setVideoOutput(None)
                        camera.deleteLater()
                    except Exception as e:
                        print(f"Error cleaning up camera {input_name}: {e}")
                    finally:
                        self.input_cameras[input_name] = None
            
            # Stop and cleanup all media players
            for media_name, player in list(self.media_players.items()):
                if player:
                    try:
                        player.stop()
                        player.setVideoOutput(None)
                        player.deleteLater()
                    except Exception as e:
                        print(f"Error cleaning up player {media_name}: {e}")
                    finally:
                        self.media_players[media_name] = None
            
            # Clear sessions
            for input_name, session in list(self.input_sessions.items()):
                if session:
                    try:
                        session.setCamera(None)
                        session.setVideoOutput(None)
                        session.deleteLater()
                    except Exception as e:
                        print(f"Error cleaning up session {input_name}: {e}")
                    finally:
                        self.input_sessions[input_name] = None
            
            # Clear widgets references
            for input_name in self.input_widgets:
                self.input_widgets[input_name] = None
            for media_name in self.media_widgets:
                self.media_widgets[media_name] = None
            
            self.output_preview_widget = None
            self.current_output_source = None
            
            print("Resources cleaned up successfully")
            
        except Exception as e:
            print(f"Error during resource cleanup: {e}")


def main():
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("GoLive Studio (UI Only)")
    app.setApplicationVersion("1.0")

    # Resolve path to the original UI file (located one directory above this script)
    ui_path = Path(__file__).resolve().parents[1] / "mainwindow.ui"

    # Load and show the UI as-is
    window = uic.loadUi(str(ui_path))

    # --- Apply Icons ---
    icon_path = Path(__file__).resolve().parent / "icons"
    window.settingsTopButton.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))
    window.audioTopButton.setIcon(QtGui.QIcon(str(icon_path / "Volume.png")))
    window.recordRedCircle.setIcon(QtGui.QIcon(str(icon_path / "Record.png")))
    window.playButton.setIcon(QtGui.QIcon(str(icon_path / "Play.png")))
    window.stream1SettingsBtn.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))
    window.stream1AudioBtn.setIcon(QtGui.QIcon(str(icon_path / "Stream.png")))
    window.stream2SettingsBtn.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))
    window.stream2AudioBtn.setIcon(QtGui.QIcon(str(icon_path / "Stream.png")))

    # Input and Media Panel Settings Icons
    window.input1SettingsButton.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))
    window.input2SettingsButton.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))
    window.input3SettingsButton.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))
    window.media1SettingsButton.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))
    window.media2SettingsButton.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))
    window.media3SettingsButton.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))

    # Initialize graphics output manager
    graphics_manager = GraphicsOutputManager(window)
    
    # Replace the output preview with graphics output widget if it exists
    if hasattr(window, 'outputPreview'):
        # Create graphics output widget to replace any existing video widget
        graphics_widget = graphics_manager.create_output_widget("main_output", window.outputPreview)
        
        # Clear existing layout and add graphics widget
        if window.outputPreview.layout():
            # Clear existing widgets
            while window.outputPreview.layout().count():
                child = window.outputPreview.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        else:
            # Create layout if it doesn't exist
            from PyQt6.QtWidgets import QVBoxLayout
            layout = QVBoxLayout(window.outputPreview)
            layout.setContentsMargins(0, 0, 0, 0)
        
        # Add graphics widget to output preview
        window.outputPreview.layout().addWidget(graphics_widget)
        print("Graphics output widget created and integrated")
    
    # Initialize audio compositor (GStreamer) and start it
    audio_compositor = AudioCompositor()
    audio_compositor.start()

    # Initialize video input manager
    video_manager = VideoInputManager(window)
    # Provide audio compositor to video manager for mute hooks
    video_manager.audio_compositor = audio_compositor
    
    # Connect video manager to graphics widget's video item
    video_item = graphics_manager.get_video_item_for_output("main_output")
    if video_item:
        video_manager.output_preview_widget = video_item
        print("Video manager connected to graphics video item")
    else:
        print("Warning: Could not connect video manager to graphics video item")
    
    # Do not pre-attach audio inputs. Mic/audio activates only when a source is switched to output.

    # Initialize effects manager
    effects_manager = EffectsManager(window)
    
    # Pre-analyze all PNG effects for faster loading
    effects_folder = Path(__file__).parent / "effects"
    preanalyze_effects_folder(str(effects_folder))
    
    # Set up effects tabs with their corresponding widgets and layouts
    tab_widgets_dict = {
        "Web01": (window.scrollAreaWidgetContents_web01, window.gridLayout_8),
        "Web02": (window.scrollAreaWidgetContents_web02, window.gridLayout_2),
        "Web03": (window.scrollAreaWidgetContents_web03, window.gridLayout_3),
        "God01": (window.scrollAreaWidgetContents_god01, window.gridLayout_4),
        "Muslim": (window.scrollAreaWidgetContents_muslim, window.gridLayout_5),
        "Stage": (window.scrollAreaWidgetContents_stage, window.gridLayout_6),
        "Telugu": (window.scrollAreaWidgetContents_telugu, window.gridLayout_7)
    }
    
    # Populate all effects tabs
    effects_manager.refresh_all_tabs(tab_widgets_dict)
    
    # Connect effects selection signal
    def on_effect_selected(tab_name, effect_path):
        print(f"Effect selected in {tab_name}: {effect_path}")
        # Apply frame effect to graphics output
        graphics_manager.set_frame_for_widget("main_output", effect_path)
    
    effects_manager.effect_selected.connect(on_effect_selected)
    
    # Initialize new streaming system (GStreamer) using AudioCompositor's interaudio channel
    stream_manager = NewStreamManager(audio_channel=audio_compositor.channel_name)
    
    # Register the graphics output widget for streaming
    graphics_widget = graphics_manager.get_output_widget("main_output")
    if graphics_widget:
        stream_manager.register_graphics_view("Stream1", graphics_widget)
        stream_manager.register_graphics_view("Stream2", graphics_widget)
        
    # Create stream control widgets
    stream1_control = NewStreamControlWidget("Stream1", stream_manager, window)
    stream2_control = NewStreamControlWidget("Stream2", stream_manager, window)
        
    # Connect both settings and audio buttons to open settings dialog
    window.stream1SettingsBtn.clicked.connect(stream1_control.open_settings_dialog)
    window.stream2SettingsBtn.clicked.connect(stream2_control.open_settings_dialog)
    window.stream1AudioBtn.clicked.connect(stream1_control.open_settings_dialog)
    window.stream2AudioBtn.clicked.connect(stream2_control.open_settings_dialog)

    # Setup cleanup on application exit
    def cleanup_on_exit():
        print("Application shutting down, cleaning up resources...")
        try:
            # Stop all streams first
            stream_manager.stop_all_streams()
            
            # Clean up video resources
            video_manager.cleanup_resources()
            
            # Clear graphics effects
            graphics_manager.clear_all_frames()

            # Stop audio compositor
            try:
                audio_compositor.stop()
            except Exception:
                pass

            print("Cleanup completed successfully")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    app.aboutToQuit.connect(cleanup_on_exit)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

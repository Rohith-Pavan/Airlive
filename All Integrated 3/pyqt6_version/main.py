#!/usr/bin/env python3
"""
GoLive Studio - UI-only launcher
Loads and displays the original Qt Designer UI with video source selection functionality.
"""
    
import sys
import os
from pathlib import Path
from PyQt6 import uic, QtGui
from PyQt6.QtCore import (QCoreApplication, QDateTime, QEvent, QObject, QPoint, QPointF, QRectF, QSize, QSettings, Qt, QTimer, pyqtSignal)
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QMessageBox, QSizePolicy
from PyQt6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaPlayer, QAudioOutput, QVideoSink, QVideoFrame
from PyQt6.QtMultimediaWidgets import QVideoWidget
from video_source_dialog import VideoSourceDialog
from media_file_dialog import MediaFileDialog
from effects_manager import EffectsManager
from graphics_output_widget import GraphicsOutputManager, preanalyze_effects_folder
from hdmi_stream_manager import get_hdmi_stream_manager
# Try GStreamer first, fall back to our working stream manager
try:
    from gstreamer.gst_stream_manager import (
        NewStreamManager,
        NewStreamControlWidget,
        GstMediaRtmpStreamer,
        build_media_rtmp_pipeline,
        build_media_preview_pipeline,
    )
    USING_GSTREAMER = True
except ImportError as e:
    print(f"GStreamer not available ({e}), using fallback stream manager")
    from new_stream_manager import NewStreamManager, NewStreamControlWidget
    USING_GSTREAMER = False

# Conditional GStreamer imports
if USING_GSTREAMER:
    from gstreamer.audio_compositor import AudioCompositor
    from gstreamer.recording_manager import RecordingManager
else:
    # Fallback classes for when GStreamer is not available
    class AudioCompositor:
        def __init__(self):
            self.channel_name = "fallback_audio_channel"
        def start(self):
            pass
        def stop(self):
            pass
        def cleanup(self):
            pass
        def set_input_muted(self, name, muted):
            pass
        def set_monitor_muted(self, muted):
            pass
        def set_master_volume(self, volume):
            pass
        def add_auto_source(self, name):
            pass
        def add_media_file_source(self, name, filepath):
            pass
        def remove_source(self, name):
            pass
    
    class RecordingManager:
        def __init__(self, audio_channel=None):
            from PyQt6.QtCore import QObject, pyqtSignal
            # Create a dummy QObject for signals
            self._signal_obj = type('SignalObj', (QObject,), {
                'recording_started': pyqtSignal(),
                'recording_stopped': pyqtSignal(),
                'recording_error': pyqtSignal(str)
            })()
            self.recording_started = self._signal_obj.recording_started
            self.recording_stopped = self._signal_obj.recording_stopped
            self.recording_error = self._signal_obj.recording_error
            
        def start_recording(self, *args, **kwargs):
            return False
        def stop_recording(self):
            pass
        def cleanup(self):
            pass
        def configure_recording(self, config):
            return True
        def is_recording(self):
            return False
        def is_paused(self):
            return False
        def pause_recording(self):
            return False
        def resume_recording(self):
            return False
        def register_graphics_view(self, widget):
            pass

from recording_settings_dialog import RecordingSettingsDialog



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
        # Shared QVideoSink for routing camera frames into the graphics scene
        self._qvideosink = None
        
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
        # Track currently active audible logical source to avoid touching all sources on switch
        self._active_audio_name = None

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
        # Initialize QVideoSink if available and connect frame signal
        try:
            self._qvideosink = QVideoSink()
            # Forward frames from sink to the graphics video item as QImage
            self._qvideosink.videoFrameChanged.connect(self._on_sink_frame)
        except Exception as e:
            print(f"Warning: QVideoSink not available or failed to initialize: {e}")
            self._qvideosink = None
        # Streaming handoff state
        self.stream_manager = None  # type: ignore
        self._media_streamers = {}  # stream_name -> GstMediaRtmpStreamer
        self._last_active_streams = []  # preserve to restart scene streams on input switch
        # Preview-only pipeline when not streaming
        self._preview_streamer = None  # type: ignore
        # Remember last playback position per media in nanoseconds
        self._media_positions_ns = {
            'media1': 0,
            'media2': 0,
            'media3': 0,
        }
        
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
                    
                    # Create media player with ENHANCED QUALITY settings
                    player = QMediaPlayer()
                    
                    # QUALITY ENHANCEMENT: Set high-quality audio output
                    audio_output = QAudioOutput()
                    # Set high-quality audio settings
                    try:
                        # Enable high-quality audio processing
                        audio_output.setVolume(1.0)  # Full volume for quality
                        player.setAudioOutput(audio_output)
                        self.media_audio_outputs[media_name] = audio_output
                        print(f"✅ High-quality audio output configured for {media_name}")
                    except Exception as e:
                        print(f"Could not configure audio output for {media_name}: {e}")
                    
                    # Connect to video widget with quality settings
                    player.setVideoOutput(video_widget)
                    
                    # QUALITY ENHANCEMENT: Configure video widget for maximum quality
                    try:
                        video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
                        # Enable high-quality scaling
                        video_widget.setSizePolicy(
                            QSizePolicy.Policy.Expanding, 
                            QSizePolicy.Policy.Expanding
                        )
                        print(f"✅ High-quality video settings applied to {media_name}")
                    except Exception as e:
                        print(f"Could not apply video quality settings to {media_name}: {e}")
                    
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

        # Media control buttons (play/pause)
        media_control_mappings = {
            'pushButton_19': 'media1',
            'pushButton_20': 'media2',
            'pushButton_21': 'media3'
        }
        
        # Load play/pause icons
        icon_path = Path(__file__).resolve().parent / "icons"
        play_icon = QtGui.QIcon(str(icon_path / "Play.png"))
        pause_icon = QtGui.QIcon(str(icon_path / "Pause.png"))
        
        for button_name, media_name in media_control_mappings.items():
            try:
                if hasattr(self.window, button_name):
                    button = getattr(self.window, button_name)
                    if button:
                        # Make button square and set styling
                        button.setMinimumSize(24, 24)
                        button.setMaximumSize(24, 24)
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #404040;
                                border: 1px solid #555555;
                                border-radius: 4px;
                                padding: 2px;
                            }
                            QPushButton:hover {
                                background-color: #505050;
                                border: 1px solid #666666;
                            }
                            QPushButton:pressed {
                                background-color: #353535;
                                border: 1px solid #444444;
                            }
                            QPushButton:checked {
                                background-color: #0078d4;
                                border: 1px solid #106ebe;
                            }
                        """)
                        
                        # Set initial play icon
                        button.setIcon(play_icon)
                        button.setIconSize(button.size() * 0.7)  # Icon slightly smaller than button
                        
                        # Make it a toggle button
                        button.setCheckable(True)
                        button.setChecked(False)  # Start in paused state
                        
                        # Store icons for later use
                        button.play_icon = play_icon
                        button.pause_icon = pause_icon
                        
                        button.clicked.connect(lambda checked, med=media_name: self.toggle_media_playback(med))
                    else:
                        print(f"Warning: Media control button {button_name} is None")
                else:
                    print(f"Warning: Media control button {button_name} not found in UI")
            except Exception as e:
                print(f"Error connecting media control button {button_name}: {e}")

        # Media progress sliders
        media_slider_mappings = {
            'horizontalSlider': 'media1',
            'horizontalSlider_2': 'media2',
            'horizontalSlider_3': 'media3'
        }
        
        for slider_name, media_name in media_slider_mappings.items():
            try:
                if hasattr(self.window, slider_name):
                    slider = getattr(self.window, slider_name)
                    if slider:
                        slider.setMinimum(0)
                        slider.setMaximum(1000)  # Use 1000 for smooth progress
                        slider.setValue(0)
                        slider.sliderPressed.connect(lambda med=media_name: self.on_slider_pressed(med))
                        slider.sliderReleased.connect(lambda med=media_name: self.on_slider_released(med))
                        slider.valueChanged.connect(lambda value, med=media_name: self.on_slider_value_changed(med, value))
                    else:
                        print(f"Warning: Media slider {slider_name} is None")
                else:
                    print(f"Warning: Media slider {slider_name} not found in UI")
            except Exception as e:
                print(f"Error connecting media slider {slider_name}: {e}")

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
                    # Control media mute via AudioCompositor for active media
                    if getattr(self, 'audio_compositor', None):
                        try:
                            # Ensure source exists in AC
                            if self.media_files.get(source_name) and source_name not in self._ac_present_sources:
                                self.audio_compositor.add_media_file_source(source_name, self.media_files[source_name])
                                self._ac_present_sources.add(source_name)
                        except Exception:
                            pass
                        # Mute immediately if per-source or master is muted
                        self.audio_compositor.set_input_muted(source_name, bool(new_state or self.master_muted))
                else:
                    # Control mic mute via audio compositor for active input
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
            # If an audio compositor is available, toggle mute for the logical input
            if getattr(self, 'audio_compositor', None):
                # Map directly by logical name; compositor is expected to have sources with same names
                self.audio_compositor.set_input_muted(source_name, bool(muted))
        except Exception as e:
            print(f"Warning: Failed applying mute to {source_name}: {e}")

    def _apply_audio_for_active_source(self, source_type: str, source_name: str) -> None:
        """Route audio in AudioCompositor so only the active source is audible.

        - Ensures the active logical source exists in `AudioCompositor`.
        - Keeps only the active logical source's audio path present; removes others to avoid bleed.
        - Sets the active source unmuted (unless per-source or master mute applies).
        """
        try:
            ac = getattr(self, 'audio_compositor', None)
            if not ac:
                return

            # Helper to ensure presence in AC
            def ensure_ac_source(name: str, stype: str):
                try:
                    if name in self._ac_present_sources:
                        return
                    if stype == 'input':
                        ac.add_auto_source(name)
                        self._ac_present_sources.add(name)
                    elif stype == 'media':
                        fpath = self.media_files.get(name)
                        if fpath:
                            ac.add_media_file_source(name, fpath)
                            self._ac_present_sources.add(name)
                except Exception as e:
                    print(f"Warning: ensure_ac_source failed for {name}: {e}")

            # Before adding/activating, remove conflicting categories to prevent background audio
            try:
                # If switching to media, remove all other media sources from AC
                if source_type == 'media':
                    for n in list(self._ac_present_sources):
                        if n.startswith('media') and n != source_name:
                            try:
                                ac.remove_source(n)
                            except Exception:
                                pass
                            self._ac_present_sources.discard(n)
                # If switching to input, remove all media sources from AC
                else:
                    for n in list(self._ac_present_sources):
                        if n.startswith('media'):
                            try:
                                ac.remove_source(n)
                            except Exception:
                                pass
                            self._ac_present_sources.discard(n)
            except Exception as e:
                print(f"Warning: failed pruning AC sources: {e}")

            # Ensure active source exists in AC (after pruning)
            ensure_ac_source(source_name, source_type)

            # Calculate target mute states
            def target_muted(name: str) -> bool:
                # Respect master mute and per-source mute
                if self.master_muted:
                    return True
                if self.muted_inputs.get(name, False):
                    return True
                return False

            # Quickly switch by only touching previous active and new active
            prev = getattr(self, '_active_audio_name', None)
            if prev and prev != source_name:
                try:
                    # Remove previous media audio entirely to ensure no residual playback
                    if prev.startswith('media') and source_type == 'media':
                        try:
                            ac.remove_source(prev)
                        except Exception:
                            pass
                        self._ac_present_sources.discard(prev)
                    else:
                        ac.set_input_muted(prev, True)
                except Exception:
                    pass
            # Set current active mute state
            try:
                ac.set_input_muted(source_name, target_muted(source_name))
            except Exception as e:
                print(f"Warning: failed to set mute for active {source_name}: {e}")
            self._active_audio_name = source_name

        except Exception as e:
            print(f"Warning: _apply_audio_for_active_source error: {e}")

    def _silence_audio_compositor_for_media_monitor(self):
        """Mute all AudioCompositor inputs so only media pipeline monitor audio is heard."""
        ac = getattr(self, 'audio_compositor', None)
        if not ac:
            return
        try:
            for nm in ['input1','input2','input3','media1','media2','media3']:
                try:
                    ac.set_input_muted(nm, True)
                except Exception:
                    pass
        except Exception as e:
            print(f"Warning: failed to mute AudioCompositor inputs: {e}")

    def _snapshot_media_position(self, media_name: str):
        """Capture current playback position (ns) for the given media from active pipelines."""
        pos = None
        try:
            if getattr(self, '_preview_streamer', None):
                pos = self._preview_streamer.get_position_ns()
            elif getattr(self, '_media_streamers', None):
                # any one of the streamers carries the same media position
                try:
                    any_streamer = next(iter(self._media_streamers.values()))
                    pos = any_streamer.get_position_ns()
                except Exception:
                    pos = None
        except Exception:
            pos = None
        if isinstance(pos, int) and pos > 0:
            try:
                self._media_positions_ns[media_name] = int(pos)
            except Exception:
                pass

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
            
            # ENHANCED: Select highest quality format available
            try:
                formats = camera_device.videoFormats()
                if formats:
                    # Log available formats for debugging
                    print(f"Available formats for {input_name}:")
                    for fmt in formats[:5]:  # Show first 5 formats
                        sz = fmt.resolution()
                        print(f"  {sz.width()}x{sz.height()}")
                    
                    # QUALITY ENHANCEMENT: Select best format
                    best_format = None
                    best_score = 0
                    
                    for fmt in formats:
                        sz = fmt.resolution()
                        width, height = sz.width(), sz.height()
                        
                        # Calculate quality score (resolution * frame rate)
                        fps = fmt.maxFrameRate()
                        score = width * height * fps
                        
                        # Prefer common high-quality resolutions
                        if width >= 1280 and height >= 720:  # HD or better
                            score *= 2  # Bonus for HD+
                        if width >= 1920 and height >= 1080:  # Full HD
                            score *= 1.5  # Extra bonus for Full HD
                        
                        if score > best_score:
                            best_score = score
                            best_format = fmt
                    
                    # Apply best format if found
                    if best_format:
                        try:
                            camera.setCameraFormat(best_format)
                            sz = best_format.resolution()
                            fps = best_format.maxFrameRate()
                            print(f"✅ Set {input_name} to MAXIMUM QUALITY: {sz.width()}x{sz.height()} @ {fps}fps")
                        except Exception as e:
                            print(f"Could not set camera format for {input_name}: {e}")
                    
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
            
            # AUDIO SYNC ENHANCEMENT: Create audio output with 0 volume for preview
            audio_output = QAudioOutput()
            audio_output.setVolume(0.0)  # Start with 0 volume for synchronized preview
            player.setAudioOutput(audio_output)
            self.media_audio_outputs[media_name] = audio_output
            print(f"✅ Audio sync setup: {media_name} starts with 0 volume for preview")
            
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
                
                # Update button state to reflect playing state
                self.update_media_button_state(media_name)
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
                # Clear any media streamers if they exist
                try:
                    if hasattr(self, '_media_streamers'):
                        self._media_streamers.clear()
                    if hasattr(self, '_preview_streamer'):
                        self._preview_streamer = None
                except Exception as _e:
                    print(f"Warning: failed clearing media streamers on input switch: {_e}")
                # Switch camera input to output
                if source_name in self.input_cameras and self.input_cameras[source_name]:
                    camera = self.input_cameras[source_name]
                    session = self.input_sessions[source_name]

                    if not session or not self.output_preview_widget:
                        print(f"Error: Invalid session or output widget for {source_name}")
                        return

                    # CRITICAL FIX: Add small delay to ensure clearing is complete
                    from PyQt6.QtCore import QTimer
                    def _assign_camera_output():
                        try:
                            # Route camera frames to QVideoSink, which will feed the graphics item
                            if self._qvideosink is not None:
                                session.setVideoOutput(self._qvideosink)
                                print(f"✅ Assigned {source_name} to QVideoSink")
                            else:
                                print("Error: QVideoSink unavailable; cannot display camera on output")
                                return

                            # Ensure camera is running
                            if not camera.isActive():
                                camera.start()
                                print(f"✅ Started camera {source_name}")
                                
                        except Exception as e:
                            print(f"Error assigning camera output: {e}")
                    
                    # Use QTimer to delay the assignment slightly
                    QTimer.singleShot(50, _assign_camera_output)

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

                    # CRITICAL FIX: Add small delay to ensure clearing is complete
                    from PyQt6.QtCore import QTimer
                    def _assign_media_output():
                        try:
                            # Assign video output to media player
                            player.setVideoOutput(self.output_preview_widget)
                            print(f"✅ Assigned {source_name} to output widget")
                            
                            # Ensure media is playing
                            from PyQt6.QtMultimedia import QMediaPlayer
                            if player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                                player.play()
                                print(f"✅ Started playing {source_name}")
                            
                        except Exception as e:
                            print(f"Error assigning media output: {e}")
                    
                    # Use QTimer to delay the assignment slightly
                    QTimer.singleShot(50, _assign_media_output)
                    
                    # AUDIO SYNC ENHANCEMENT: Increase volume when media is selected for output
                    self._set_media_audio_volume(source_name, 1.0)  # Full volume for output

                    self.current_output_source = (source_type, source_name)
                    print(f"Switched output to {source_name} media")
                    
                    # AUDIO SYNC FIX: Use direct QAudioOutput control for reliable audio
                    # Remove all media from AudioCompositor to prevent duplicate audio
                    self._remove_all_media_from_audio_compositor()
                    # Ensure all other media is muted
                    self._mute_all_media_audio()
                    # Then unmute only the active media
                    self._set_media_audio_volume(source_name, 1.0)
                    print(f"✅ Audio sync: Using direct audio control, AudioCompositor bypassed")
                else:
                    print(f"No media file assigned to {source_name}. Please select a media file first.")

        except Exception as e:
            print(f"Error switching to {source_type} {source_name}: {e}")

    def _clear_current_output(self):
        """Clear current output connections to prevent conflicts"""
        try:
            print(f"Clearing current output: {self.current_output_source}")
            
            # Snapshot position for current media before tearing down
            try:
                if self.current_output_source and self.current_output_source[0] == 'media':
                    self._snapshot_media_position(self.current_output_source[1])
                    
                    # AUDIO SYNC FIX: Remove media from AudioCompositor to prevent duplicate audio
                    media_name = self.current_output_source[1]
                    if hasattr(self, 'audio_compositor') and self.audio_compositor:
                        try:
                            if media_name in self._ac_present_sources:
                                self.audio_compositor.remove_source(media_name)
                                self._ac_present_sources.discard(media_name)
                                print(f"✅ Removed {media_name} from AudioCompositor to prevent duplicate audio")
                        except Exception as e:
                            print(f"Warning: Could not remove {media_name} from AudioCompositor: {e}")
            except Exception:
                pass
                
            # CRITICAL FIX: Clear ALL video output connections completely
            
            # 1. Clear all camera sessions from ALL possible outputs
            for input_name, session in self.input_sessions.items():
                if session:
                    try:
                        # Clear from QVideoSink
                        if self._qvideosink and session.videoOutput() == self._qvideosink:
                            session.setVideoOutput(None)
                            print(f"✅ Cleared {input_name} from QVideoSink")
                        
                        # Clear from direct output widget
                        if hasattr(session, 'videoOutput') and session.videoOutput() == self.output_preview_widget:
                            session.setVideoOutput(None)
                            print(f"✅ Cleared {input_name} from output widget")
                            
                    except Exception as e:
                        print(f"Warning: Error clearing {input_name} session: {e}")

            # 2. Clear all media players from output and mute their audio
            for media_name, player in self.media_players.items():
                if player:
                    try:
                        # Clear video output if connected
                        if hasattr(player, 'videoOutput') and player.videoOutput() == self.output_preview_widget:
                            player.setVideoOutput(None)
                            print(f"✅ Cleared {media_name} from output widget")
                        
                        # Mute audio when media is no longer active
                        self._set_media_audio_volume(media_name, 0.0)
                        
                    except Exception as e:
                        print(f"Warning: Error clearing {media_name} player: {e}")
            
            # 3. CRITICAL: Clear the graphics video item if it exists
            try:
                if hasattr(self.output_preview_widget, 'clear_video_frame'):
                    self.output_preview_widget.clear_video_frame()
                    print("✅ Cleared graphics video frame")
                elif hasattr(self.output_preview_widget, 'set_qimage_frame'):
                    self.output_preview_widget.set_qimage_frame(None)
                    print("✅ Cleared graphics QImage frame")
            except Exception as e:
                print(f"Warning: Could not clear graphics frame: {e}")
            
            # 4. Force a visual update
            try:
                if hasattr(self.output_preview_widget, 'update'):
                    self.output_preview_widget.update()
                if hasattr(self.output_preview_widget, 'repaint'):
                    self.output_preview_widget.repaint()
            except Exception as e:
                print(f"Warning: Could not force visual update: {e}")
                
            print("✅ Output cleared successfully")
            
        except Exception as e:
            print(f"Error clearing output: {e}")
            import traceback
            traceback.print_exc()
    
    def _set_media_audio_volume(self, media_name, volume):
        """Set audio volume for a specific media player (0.0 = muted, 1.0 = full)"""
        try:
            if media_name in self.media_audio_outputs:
                audio_output = self.media_audio_outputs[media_name]
                audio_output.setVolume(volume)
                status = "muted" if volume == 0.0 else f"{int(volume * 100)}%"
                print(f"✅ Audio sync: {media_name} volume set to {status}")
                return True
            else:
                print(f"⚠️ No audio output found for {media_name}")
                return False
        except Exception as e:
            print(f"❌ Error setting audio volume for {media_name}: {e}")
            return False
    
    def _mute_all_media_audio(self):
        """Mute all media audio for synchronized preview"""
        try:
            for media_name in self.media_audio_outputs.keys():
                self._set_media_audio_volume(media_name, 0.0)
            print("✅ All media audio muted for synchronized preview")
        except Exception as e:
            print(f"❌ Error muting all media audio: {e}")
    
    def _remove_all_media_from_audio_compositor(self):
        """Remove all media sources from AudioCompositor to prevent duplicate audio"""
        try:
            if hasattr(self, 'audio_compositor') and self.audio_compositor:
                media_sources_to_remove = [name for name in self._ac_present_sources if name.startswith('media')]
                for media_name in media_sources_to_remove:
                    try:
                        self.audio_compositor.remove_source(media_name)
                        self._ac_present_sources.discard(media_name)
                        print(f"✅ Removed {media_name} from AudioCompositor")
                    except Exception as e:
                        print(f"Warning: Could not remove {media_name} from AudioCompositor: {e}")
                
                if media_sources_to_remove:
                    print("✅ All media sources removed from AudioCompositor - using direct audio control")
        except Exception as e:
            print(f"❌ Error removing media from AudioCompositor: {e}")
    
    def _on_sink_frame(self, frame):
        """Handle video frames from QVideoSink"""
        try:
            if not frame.isValid():
                return
            
            # Convert QVideoFrame to QImage
            image = frame.toImage()
            if image.isNull():
                return
            
            # Send frame to graphics output widget if available
            if self.output_preview_widget and hasattr(self.output_preview_widget, 'set_qimage_frame'):
                self.output_preview_widget.set_qimage_frame(image)
                
        except Exception as e:
            print(f"Error processing video frame: {e}")
    
    def _stop_media_streamers(self, restart_scene_streams=True):
        """Stop all media streamers and optionally restart scene streams"""
        try:
            # Stop all media players
            for player_name, player in self.media_players.items():
                if player:
                    try:
                        player.stop()
                        print(f"Stopped media player: {player_name}")
                    except Exception as e:
                        print(f"Error stopping media player {player_name}: {e}")
            
            # Stop preview streamer if active
            if hasattr(self, '_preview_streamer') and self._preview_streamer:
                try:
                    self._preview_streamer.stop()
                    self._preview_streamer = None
                    print("Stopped preview streamer")
                except Exception as e:
                    print(f"Error stopping preview streamer: {e}")
            
            # Clear audio compositor sources if needed
            if self.audio_compositor and hasattr(self.audio_compositor, 'remove_source'):
                for source_name in list(self._ac_present_sources):
                    try:
                        self.audio_compositor.remove_source(source_name)
                        self._ac_present_sources.discard(source_name)
                    except Exception as e:
                        print(f"Error removing audio source {source_name}: {e}")
            
            print("Media streamers stopped successfully")
            
        except Exception as e:
            print(f"Error stopping media streamers: {e}")
    
    def cleanup_resources(self):
        """Clean up all video input manager resources"""
        try:
            print("Cleaning up VideoInputManager resources...")
            
            # Stop all media streamers
            self._stop_media_streamers(restart_scene_streams=False)
            
            # Stop and cleanup all cameras
            for input_name, camera in self.input_cameras.items():
                if camera:
                    try:
                        camera.stop()
                        print(f"Stopped camera: {input_name}")
                    except Exception as e:
                        print(f"Error stopping camera {input_name}: {e}")
            
            # Cleanup all camera sessions
            for input_name, session in self.input_sessions.items():
                if session:
                    try:
                        session.setCamera(None)
                        session.setVideoOutput(None)
                        print(f"Cleaned up camera session: {input_name}")
                    except Exception as e:
                        print(f"Error cleaning up camera session {input_name}: {e}")
            
            # Cleanup all media players
            for player_name, player in self.media_players.items():
                if player:
                    try:
                        player.stop()
                        player.setVideoOutput(None)
                        player.setAudioOutput(None)
                        print(f"Cleaned up media player: {player_name}")
                    except Exception as e:
                        print(f"Error cleaning up media player {player_name}: {e}")
            
            # Clear all references
            self.input_cameras.clear()
            self.input_sessions.clear()
            self.input_widgets.clear()
            self.media_players.clear()
            self.media_audio_outputs.clear()
            self.media_widgets.clear()
            
            # Clear video sink
            if self._qvideosink:
                try:
                    self._qvideosink.deleteLater()
                    self._qvideosink = None
                except Exception as e:
                    print(f"Error cleaning up video sink: {e}")
            
            print("VideoInputManager resources cleaned up successfully")
            
        except Exception as e:
            print(f"Error during VideoInputManager cleanup: {e}")

    # Media Control Methods
    def toggle_media_playback(self, media_name):
        """Toggle play/pause for a media player"""
        try:
            player = self.media_players.get(media_name)
            if not player:
                print(f"No media player found for {media_name}")
                return
            
            # Get the corresponding button to update its state
            button_mapping = {
                'media1': 'pushButton_19',
                'media2': 'pushButton_20', 
                'media3': 'pushButton_21'
            }
            
            button_name = button_mapping.get(media_name)
            button = getattr(self.window, button_name, None) if button_name else None
            
            # Check current state and toggle
            from PyQt6.QtMultimedia import QMediaPlayer
            if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                # Currently playing, so pause
                player.pause()
                if button:
                    button.setChecked(False)
                    # Update icon to play (since we're now paused)
                    if hasattr(button, 'play_icon'):
                        button.setIcon(button.play_icon)
                print(f"Paused {media_name}")
            else:
                # Currently paused or stopped, so play
                player.play()
                if button:
                    button.setChecked(True)
                    # Update icon to pause (since we're now playing)
                    if hasattr(button, 'pause_icon'):
                        button.setIcon(button.pause_icon)
                print(f"Playing {media_name}")
                
        except Exception as e:
            print(f"Error toggling playback for {media_name}: {e}")
    
    def on_slider_pressed(self, media_name):
        """Handle when user starts dragging the progress slider"""
        try:
            # Store that user is dragging to prevent automatic updates
            if not hasattr(self, '_slider_dragging'):
                self._slider_dragging = {}
            self._slider_dragging[media_name] = True
        except Exception as e:
            print(f"Error on slider pressed for {media_name}: {e}")
    
    def on_slider_released(self, media_name):
        """Handle when user releases the progress slider"""
        try:
            # Clear dragging state
            if hasattr(self, '_slider_dragging'):
                self._slider_dragging[media_name] = False
        except Exception as e:
            print(f"Error on slider released for {media_name}: {e}")
    
    def on_slider_value_changed(self, media_name, value):
        """Handle progress slider value changes"""
        try:
            # Only seek if user is dragging (not automatic updates)
            if hasattr(self, '_slider_dragging') and self._slider_dragging.get(media_name, False):
                player = self.media_players.get(media_name)
                if player and player.duration() > 0:
                    # Convert slider value (0-1000) to position in milliseconds
                    position = int((value / 1000.0) * player.duration())
                    player.setPosition(position)
                    print(f"Seeking {media_name} to {position}ms")
        except Exception as e:
            print(f"Error on slider value changed for {media_name}: {e}")
    
    def setup_media_progress_updates(self):
        """Set up automatic progress updates for media sliders"""
        try:
            # Create timers for updating progress sliders
            if not hasattr(self, '_progress_timers'):
                self._progress_timers = {}
                self._slider_dragging = {}
            
            from PyQt6.QtCore import QTimer
            
            for media_name in ['media1', 'media2', 'media3']:
                # Create timer for this media
                timer = QTimer()
                timer.timeout.connect(lambda mn=media_name: self.update_media_progress(mn))
                timer.start(100)  # Update every 100ms for smooth progress
                self._progress_timers[media_name] = timer
                self._slider_dragging[media_name] = False
                
        except Exception as e:
            print(f"Error setting up media progress updates: {e}")
    
    def update_media_progress(self, media_name):
        """Update progress slider for a media player"""
        try:
            # Don't update if user is dragging
            if self._slider_dragging.get(media_name, False):
                return
                
            player = self.media_players.get(media_name)
            if not player or player.duration() <= 0:
                return
            
            # Get the corresponding slider
            slider_mapping = {
                'media1': 'horizontalSlider',
                'media2': 'horizontalSlider_2',
                'media3': 'horizontalSlider_3'
            }
            
            slider_name = slider_mapping.get(media_name)
            slider = getattr(self.window, slider_name, None) if slider_name else None
            
            if slider:
                # Calculate progress (0-1000)
                progress = int((player.position() / player.duration()) * 1000)
                slider.setValue(progress)
                
        except Exception as e:
            print(f"Error updating progress for {media_name}: {e}")
    
    def update_media_button_state(self, media_name):
        """Update the media control button state based on player state"""
        try:
            player = self.media_players.get(media_name)
            if not player:
                return
                
            # Get the corresponding button
            button_mapping = {
                'media1': 'pushButton_19',
                'media2': 'pushButton_20', 
                'media3': 'pushButton_21'
            }
            
            button_name = button_mapping.get(media_name)
            button = getattr(self.window, button_name, None) if button_name else None
            
            if button:
                from PyQt6.QtMultimedia import QMediaPlayer
                is_playing = player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                
                button.setChecked(is_playing)
                
                # Update icon based on state
                if is_playing and hasattr(button, 'pause_icon'):
                    button.setIcon(button.pause_icon)
                elif not is_playing and hasattr(button, 'play_icon'):
                    button.setIcon(button.play_icon)
                    
        except Exception as e:
            print(f"Error updating button state for {media_name}: {e}")


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
    if hasattr(window, 'audioTopButton') and window.audioTopButton:
        window.audioTopButton.setIcon(QtGui.QIcon(str(icon_path / "Volume.png")))
    # Record panel icons
    if hasattr(window, 'settingsRecordButton') and window.settingsRecordButton:
        window.settingsRecordButton.setIcon(QtGui.QIcon(str(icon_path / "Settings.png")))
    if hasattr(window, 'recordRedCircle') and window.recordRedCircle:
        window.recordRedCircle.setIcon(QtGui.QIcon(str(icon_path / "Record.png")))
    if hasattr(window, 'playButton') and window.playButton:
        window.playButton.setIcon(QtGui.QIcon(str(icon_path / "Play.png")))
    if hasattr(window, 'captureButton') and window.captureButton:
        window.captureButton.setIcon(QtGui.QIcon(str(icon_path / "capture.png")))
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
    
    # Initialize HDMI stream manager
    hdmi_manager = get_hdmi_stream_manager()
    
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
    video_input_manager = VideoInputManager(window)
    # Provide audio compositor to video manager for mute hooks
    video_input_manager.audio_compositor = audio_compositor
    
    # Set up media progress updates
    video_input_manager.setup_media_progress_updates()
    
    # Connect video manager to graphics widget's video item
    video_item = graphics_manager.get_video_item_for_output("main_output")
    if video_item:
        video_input_manager.output_preview_widget = video_item
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
    
    # Connect effects removal signal
    def on_effect_removed(tab_name, effect_path):
        print(f"Effect removed from {tab_name}: {effect_path}")
        # Clear frame effect from graphics output
        graphics_manager.clear_frame_for_widget("main_output")
    
    effects_manager.effect_selected.connect(on_effect_selected)
    effects_manager.effect_removed.connect(on_effect_removed)
    
    # Initialize new streaming system (fallback) 
    stream_manager = NewStreamManager()
    
    # Register the graphics output widget for streaming
    graphics_widget = graphics_manager.get_output_widget("main_output")
    if graphics_widget:
        stream_manager.register_graphics_view("Stream1", graphics_widget)
        stream_manager.register_graphics_view("Stream2", graphics_widget)
    # Provide stream manager reference for media handoff (after creation)
    video_input_manager.stream_manager = stream_manager
        
    # Create stream control widgets with HDMI support
    stream1_control = NewStreamControlWidget("Stream1", stream_manager, window)
    stream2_control = NewStreamControlWidget("Stream2", stream_manager, window)
    
    # Connect HDMI manager to stream controls for integrated HDMI streaming
    stream1_control.hdmi_manager = hdmi_manager
    stream2_control.hdmi_manager = hdmi_manager
        
    # Connect both settings and audio buttons to open settings dialog
    window.stream1SettingsBtn.clicked.connect(stream1_control.open_settings_dialog)
    window.stream2SettingsBtn.clicked.connect(stream2_control.open_settings_dialog)
    window.stream1AudioBtn.clicked.connect(stream1_control.open_settings_dialog)
    window.stream2AudioBtn.clicked.connect(stream2_control.open_settings_dialog)

    # Setup cleanup on application exit
    def cleanup_on_exit():
        """Ensure all resources are released when the app closes."""
        print("Cleaning up resources...")
        try:
            # Stop all streams
            stream_manager.stop_all_streams()

            # Stop recording
            recording_manager.stop_recording()

            # Cleanup video inputs
            video_input_manager.cleanup_resources()

            # Clear graphics effects
            graphics_manager.clear_all_frames()

            # Stop audio compositor
            audio_compositor.stop()

            print("Cleanup completed successfully")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    app.aboutToQuit.connect(cleanup_on_exit)

    # Recording Manager Setup
    ac_channel = audio_compositor.channel_name
    recording_manager = RecordingManager(audio_channel=ac_channel)
    recording_manager.register_graphics_view(graphics_manager.get_output_widget("main_output"))

    def get_recording_settings():
        """Helper to load raw settings for the dialog."""
        settings = QSettings("GoLive", "GoLiveApp")
        return {
            'destination_folder': settings.value('recording/destination_folder', os.path.join(os.path.expanduser('~'), 'Videos')),
            'file_name_pattern': settings.value('recording/file_name_pattern', 'GoLive_Recording'),
            'video_format': settings.value('recording/video_format', 'MP4'),
            'quality_preset': settings.value('recording/quality_preset', 'High'),
            'bitrate': settings.value('recording/bitrate', '8000'),
            'resolution': settings.value('recording/resolution', '1080p'),
            'frame_rate': settings.value('recording/frame_rate', '30'),
            'screenshot_format': settings.value('recording/screenshot_format', 'PNG'),
            'screenshot_location': settings.value('recording/screenshot_location', 'Same as video'),
            'custom_screenshot_path': settings.value('recording/custom_screenshot_path', '')
        }

    def get_recording_config_from_settings():
        """Helper to load and translate recording settings for the manager."""
        config = get_recording_settings()
        resolution_map = {'720p': '1280x720', '1080p': '1920x1080', '2K': '2560x1440', '4K': '3840x2160'}
        quality_map = {'Low': '2000', 'Medium': '4000', 'High': '8000'}

        manager_config = {}
        manager_config['resolution'] = resolution_map.get(config['resolution'], '1920x1080')
        manager_config['fps'] = int(config['frame_rate'])
        
        if config['quality_preset'] == 'Custom':
            bitrate_str = config['bitrate'] if config['bitrate'] else '8000' # Default to 8000 if empty
            manager_config['video_bitrate'] = int(bitrate_str)
        else:
            manager_config['video_bitrate'] = int(quality_map.get(config['quality_preset'], '4000'))

        manager_config['audio_bitrate'] = 128 # Hardcoded for now
        manager_config['video_format'] = config['video_format'].lower()

        now = QDateTime.currentDateTime()
        date_str = now.toString('yyyy-MM-dd')
        time_str = now.toString('HH-mm-ss')
        
        # Always include timestamp even if pattern doesn't have placeholders
        pattern = config['file_name_pattern']
        if '{date}' not in pattern and '{time}' not in pattern:
            # Add timestamp to prevent overwrites
            filename = f"{pattern}_{date_str}_{time_str}"
        else:
            filename = pattern.replace('{date}', date_str).replace('{time}', time_str)
        
        filename += f".{manager_config['video_format']}"
        manager_config['output_path'] = os.path.join(config['destination_folder'], filename)

        return manager_config

    # Initial configuration
    recording_manager.configure_recording(get_recording_config_from_settings())

    # --- Record Panel UI State & Logic ---
    # Elements
    record_btn = getattr(window, 'recordRedCircle', None)
    pause_btn = getattr(window, 'playButton', None)
    screenshot_btn = getattr(window, 'captureButton', None)
    status_icon = getattr(window, 'recordStatusIcon', None)
    status_text = getattr(window, 'recordStatusText', None)
    settings_btn = getattr(window, 'settingsRecordButton', None)

    def open_recording_settings():
        dialog = RecordingSettingsDialog(window)
        current_settings = get_recording_settings() # Use the other helper to load current settings
        dialog.set_settings(current_settings)

        if dialog.exec():
            new_settings = dialog.get_settings()
            settings = QSettings("GoLive", "GoLiveApp")
            for key, value in new_settings.items():
                if value is not None:
                    settings.setValue(f'recording/{key}', value)
            
            settings.sync()
            print(f"Recording settings saved and applied: {new_settings}")

            # Immediately re-configure the recording manager if not actively recording
            if not recording_manager.is_recording():
                new_manager_config = get_recording_config_from_settings()
                recording_manager.configure_recording(new_manager_config)

    if settings_btn:
        settings_btn.clicked.connect(open_recording_settings)

    # Access graphics output widget for screenshots
    graphics_widget = graphics_manager.get_output_widget("main_output")

    def take_screenshot():
        if not graphics_widget:
            return

        settings = QSettings("GoLive", "GoLiveApp")
        custom_dir = settings.value("recording/custom_screenshot_path", "")
        video_dir = settings.value("recording/destination_folder", os.path.join(os.path.expanduser('~'), 'Videos'))
        ss_format = settings.value("recording/screenshot_format", "PNG").lower()

        # Prefer explicit screenshot folder if provided; otherwise use recording destination
        save_dir = custom_dir if (custom_dir and os.path.isdir(custom_dir)) else video_dir
        if not save_dir or not os.path.isdir(save_dir):
            save_dir = os.path.join(os.path.expanduser('~'), 'Pictures')
            print(f"Screenshot path not set or invalid, falling back to: {save_dir}")

        try:
            os.makedirs(save_dir, exist_ok=True)
            timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
            filename = f"Screenshot_{timestamp}.{ss_format}"
            filepath = os.path.join(save_dir, filename)

            pixmap = graphics_widget.grab()
            if pixmap.save(filepath):
                print(f"Screenshot saved to {filepath}")
            else:
                print(f"Failed to save screenshot to {filepath}.")
        except Exception as e:
            print(f"Error taking screenshot: {e}")

    if screenshot_btn:
        screenshot_btn.clicked.connect(take_screenshot)

    # Initial state
    state = {
        'is_recording': False, # True when recording or paused
        'is_paused': False,
        'elapsed': 0,
        'blink_on': False
    }

    # Default recording settings
    try:
        from PyQt6.QtCore import QStandardPaths
        videos_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation)
        default_rec_path = Path(videos_path) / "GoLive_Recording.mp4"
        rec_settings = {
            'resolution': '1280x720',
            'fps': 30,
            'video_bitrate': 4000, # kbps
            'audio_bitrate': 128, # kbps
            'output_path': str(default_rec_path)
        }
        recording_manager.configure_recording(rec_settings)
    except Exception as e:
        print(f"[Main] Error setting default recording config: {e}")

    # Timers
    elapsed_timer = QTimer(window)
    elapsed_timer.setInterval(1000)
    blink_timer = QTimer(window)
    blink_timer.setInterval(500)

    def _format_time(sec: int) -> str:
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _set_status_ready():
        if status_icon:
            status_icon.setStyleSheet("background-color: #777777; border-radius: 6px;")
        if status_text:
            status_text.setText("Ready")

    def _set_status_recording(is_resuming=False):
        # blinking red dot
        if status_icon:
            color = "#ff3b30" if state['blink_on'] else "#551111"
            status_icon.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        if status_text:
            elapsed_str = _format_time(state['elapsed'])
            if is_resuming:
                status_text.setText("Resuming...")
            else:
                status_text.setText(f"REC {elapsed_str}")

    def _set_status_paused():
        if status_icon:
            status_icon.setStyleSheet("background-color: #ffcc00; border-radius: 2px;")
        if status_text:
            status_text.setText(f"Paused {_format_time(state['elapsed'])}")

    def _set_status_saving():
        if status_icon:
            status_icon.setStyleSheet("background-color: #888888; border-radius: 6px;")
        if status_text:
            status_text.setText("Saving…")

    def _set_status_stopped():
        if status_icon:
            status_icon.setStyleSheet("background-color: #777777; border-radius: 6px;")
        if status_text:
            status_text.setText("Ready")

    def _on_elapsed_tick():
        state['elapsed'] += 1
        if state['is_recording'] and not state['is_paused']:
            _set_status_recording()

    def _on_blink_tick():
        state['blink_on'] = not state['blink_on']
        if state['is_recording'] and not state['is_paused']:
            _set_status_recording()

    elapsed_timer.timeout.connect(_on_elapsed_tick)
    blink_timer.timeout.connect(_on_blink_tick)

    def start_recording():
        manager_config = get_recording_config_from_settings()
        if recording_manager.configure_recording(manager_config):
            if not recording_manager.start_recording():
                print("[Main] Failed to start recording via manager.")
        else:
            print("[Main] Failed to configure recording manager.")

    def stop_recording():
        recording_manager.stop_recording()
        print("[Main] Recording stopped via manager.")

    def on_record_button_clicked():
        try:
            if recording_manager.is_recording():
                stop_recording()
            else:
                start_recording()
        except Exception as e:
            print(f"Record toggle error: {e}")

    def on_play_pause_button_clicked():
        if not recording_manager.is_recording():
            return

        if recording_manager.is_paused():
            if recording_manager.resume_recording():
                state['is_paused'] = False
                _set_status_recording(is_resuming=True)
        else:
            if recording_manager.pause_recording():
                state['is_paused'] = True
                _set_status_paused()

    def on_screenshot_clicked():
        try:
            if not graphics_widget:
                print("No graphics widget available for screenshot")
                return
            pixmap = graphics_widget.grab()
            if pixmap.isNull():
                print("Failed to grab screenshot")
                return

            # Get screenshot settings
            settings = QSettings()
            ss_location = settings.value('recording/screenshot_location', 'Same as video')
            ss_format = settings.value('recording/screenshot_format', 'PNG').lower()
            
            save_dir = ''
            if ss_location == 'Custom':
                save_dir = settings.value('recording/custom_screenshot_path', '')
            else:  # 'Same as video'
                save_dir = settings.value('recording/destination_folder', '')

            if not save_dir or not os.path.isdir(save_dir):
                from PyQt6.QtCore import QStandardPaths
                save_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
                print(f"Screenshot path not set or invalid, falling back to: {save_dir}")

            # Create filename
            ts = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
            file_name = f"Screenshot_{ts}.{ss_format}"
            
            # Ensure directory exists and save
            out_dir = Path(save_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / file_name
            
            ok = pixmap.save(str(out_path), ss_format)
            print(f"Screenshot {'saved to' if ok else 'failed saving to'} {out_path}")

        except Exception as e:
            print(f"Screenshot error: {e}")

    # Initialize default states
    if status_text and status_icon:
        _set_status_ready()
    if pause_btn:
        pause_btn.setEnabled(False)
        try:
            pause_btn.setChecked(False)
        except Exception:
            pass

    # Hook up buttons
    if record_btn:
        record_btn.setCheckable(True)
        record_btn.setChecked(False)
        record_btn.clicked.connect(on_record_button_clicked)
    if pause_btn:
        pause_btn.setEnabled(False) # Disabled by default
        pause_btn.clicked.connect(on_play_pause_button_clicked)
    if screenshot_btn:
        screenshot_btn.clicked.connect(on_screenshot_clicked)

    # Connect recording manager signals to UI update functions
    def on_recording_started():
        state['is_recording'] = True
        state['is_paused'] = False
        state['elapsed'] = 0
        elapsed_timer.start(1000)
        blink_timer.start(500)
        _set_status_recording()
        if record_btn:
            record_btn.setChecked(True)
        if pause_btn:
            pause_btn.setEnabled(True)

    def on_recording_stopped():
        state['is_recording'] = False
        state['is_paused'] = False
        elapsed_timer.stop()
        blink_timer.stop()
        _set_status_stopped()
        if record_btn:
            record_btn.setChecked(False)
        if pause_btn:
            pause_btn.setEnabled(False)
            pause_btn.setChecked(False)

    def on_recording_error(message):
        print(f"[Main] Recording Error: {message}")
        # Ensure UI resets to a non-recording state
        on_recording_stopped()

        msg_box = QMessageBox(window)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText("Recording Error")
        msg_box.setInformativeText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    recording_manager.recording_started.connect(on_recording_started)
    recording_manager.recording_stopped.connect(on_recording_stopped)
    recording_manager.recording_error.connect(on_recording_error)

    # Setup cleanup on application exit
    def cleanup_on_exit():
        """Ensure all resources are released when the app closes."""
        print("Cleaning up resources...")
        try:
            # Stop all streams
            stream_manager.stop_all_streams()

            # Stop recording
            recording_manager.stop_recording()

            # Cleanup video inputs
            video_input_manager.cleanup_resources()

            # Clear graphics effects
            graphics_manager.clear_all_frames()

            # Cleanup HDMI streams
            hdmi_manager.cleanup()

            # Stop audio compositor
            audio_compositor.stop()

            print("Cleanup completed successfully")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    app.aboutToQuit.connect(cleanup_on_exit)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

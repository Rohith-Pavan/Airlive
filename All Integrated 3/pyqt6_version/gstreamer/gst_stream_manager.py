#!/usr/bin/env python3
"""
GStreamer-based Stream Manager for GoLive Studio (replacing FFmpeg)

- Pushes video frames from a Qt scene/widget via appsrc
- Pulls mixed audio from AudioCompositor via interaudiosrc (shared channel)
- Muxes A/V to RTMP using flvmux -> rtmpsink

Requires:
  - PyGObject (GStreamer 1.0)

Public API mirrors the previous FFmpeg manager where practical:
  class NewStreamManager
    - register_graphics_view(stream_name, graphics_view)
    - configure_stream(stream_name, settings)
    - start_stream(stream_name)
    - stop_stream(stream_name)
    - stop_all_streams()
    - is_streaming(stream_name)
    - get_stream_state(stream_name)

Signals:
  - stream_started(str)
  - stream_stopped(str)
  - stream_error(str, str)
  - status_update(str, str)
  - frame_count_updated(str, int)

Notes:
  - This module depends on an AudioCompositor instance to already be running and
    writing to an interaudiosink with a known channel name.
"""
from __future__ import annotations

from typing import Dict, Any, Optional

import gi  # type: ignore
try:
    gi.require_version('Gst', '1.0')
    gi.require_version('GObject', '2.0')
    from gi.repository import Gst, GObject  # type: ignore
except Exception as e:
    raise RuntimeError(
        "PyGObject / GStreamer (gi) is not available.\n"
        "Install GStreamer + PyGObject: macOS (Homebrew), Linux (apt/yum), or Windows (MSYS2 MinGW64 or prebuilt PyGObject wheel)."
    ) from e

from PyQt6.QtCore import QObject, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QImage

from .qt_gst import QtSceneToGstStreamer

# Initialize GStreamer once
if not Gst.is_initialized():
    Gst.init(None)


class StreamState:
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


def build_rtmp_av_pipeline(width: int, height: int, fps: int, rtmp_url: str, audio_channel: str, video_kbps: int, audio_kbps: int) -> str:
    """Build a GStreamer pipeline description string with video appsrc and interaudiosrc.
    Auto-select an available AAC encoder for better cross-platform support.
    """
    # Ensure GStreamer is initialized before querying factories
    if not Gst.is_initialized():
        Gst.init(None)

    # Choose an available AAC encoder (order of preference)
    aac_candidates = ["avenc_aac", "voaacenc", "fdkaacenc", "faac"]
    aac_enc = None
    for name in aac_candidates:
        try:
            if Gst.ElementFactory.find(name) is not None:
                aac_enc = name
                break
        except Exception:
            pass
    if aac_enc is None:
        raise RuntimeError(
            "No AAC encoder found (tried: avenc_aac, voaacenc, fdkaacenc, faac). "
            "Install gst-libav or gst-plugins-bad/ugly."
        )

    # Common queues
    vq = "queue max-size-buffers=0 max-size-bytes=0 max-size-time=0"
    aq = "queue max-size-buffers=0 max-size-bytes=0 max-size-time=0"
    # AAC bitrate in bits/s
    a_bps = max(16, int(audio_kbps)) * 1000

    desc = (
        "appsrc name=qtappsrc is-live=true format=time do-timestamp=true ! "
        f"video/x-raw,format=BGRA,width={width},height={height},framerate={fps}/1 ! "
        "videoconvert ! x264enc tune=zerolatency bitrate={vkbps} speed-preset=veryfast key-int-max={gop} ! "
        f"{vq} ! mux. "
        f"interaudiosrc channel={audio_channel} ! audioconvert ! audioresample ! {{aac}} bitrate={{a_bps}} ! "
        f"{aq} ! mux. "
        "flvmux name=mux streamable=true ! rtmpsink location={rtmp}"
    )
    # Fill format values
    return desc.format(vkbps=max(100, int(video_kbps)), gop=max(1, int(fps)), a_bps=a_bps, rtmp=rtmp_url, aac=aac_enc)


class _StreamRecord:
    def __init__(self, scene_streamer: QtSceneToGstStreamer):
        self.scene_streamer = scene_streamer
        self.frame_count = 0


class NewStreamManager(QObject):
    # Signals (matching previous manager)
    stream_started = pyqtSignal(str)
    stream_stopped = pyqtSignal(str)
    stream_error = pyqtSignal(str, str)
    status_update = pyqtSignal(str, str)
    frame_count_updated = pyqtSignal(str, int)

    def __init__(self, audio_channel: str = "ac_audio_bus", parent: Optional[QObject] = None):
        super().__init__(parent)
        self._streams: Dict[str, Dict[str, Any]] = {}
        self._records: Dict[str, _StreamRecord] = {}
        self._graphics_views: Dict[str, Any] = {}
        self._stream_states: Dict[str, str] = {}
        self._audio_channel = audio_channel

        # Health check timer
        self._health_timer = QTimer(self)
        self._health_timer.timeout.connect(self._check_stream_health)
        self._health_timer.start(5000)

    def register_graphics_view(self, stream_name: str, graphics_view) -> None:
        self._graphics_views[stream_name] = graphics_view
        self._stream_states[stream_name] = StreamState.STOPPED
        print(f"[Gst] Registered graphics view for {stream_name}")

    def configure_stream(self, stream_name: str, settings: Dict[str, Any]) -> bool:
        try:
            # Validate inputs
            for key in ['url', 'key', 'resolution', 'fps', 'video_bitrate']:
                if key not in settings or not settings[key]:
                    self.stream_error.emit(stream_name, f"Missing required setting: {key}")
                    return False
            # Store
            self._streams[stream_name] = settings.copy()
            print(f"[Gst] Configured {stream_name}: {settings.get('resolution')} @ {settings.get('fps')}fps")
            return True
        except Exception as e:
            self.stream_error.emit(stream_name, f"Configuration error: {e}")
            return False

    def start_stream(self, stream_name: str) -> bool:
        try:
            if self.is_streaming(stream_name):
                return True
            if stream_name not in self._streams:
                self.stream_error.emit(stream_name, "Stream not configured")
                return False
            if stream_name not in self._graphics_views:
                self.stream_error.emit(stream_name, "Graphics view not registered")
                return False

            self.stop_stream(stream_name)  # ensure clean state

            settings = self._streams[stream_name]
            width, height = map(int, settings['resolution'].split('x'))
            fps = int(settings['fps'])
            v_kbps = int(settings['video_bitrate'])
            a_kbps = int(settings.get('audio_bitrate', 128))
            url = settings['url'].rstrip('/')
            key = settings.get('key', '')
            target = f"{url}/{key}" if key else url

            pipeline_desc = build_rtmp_av_pipeline(width, height, fps, target, self._audio_channel, v_kbps, a_kbps)
            gv = self._graphics_views[stream_name]

            # Prepare scene streamer
            if hasattr(gv, 'scene') and gv.scene():
                scene = gv.scene()
            else:
                scene = gv  # QWidget with render()
            size = QSize(width, height)
            scene_streamer = QtSceneToGstStreamer(scene, size, fps, pipeline_desc, self)

            # Start
            scene_streamer.start()
            self._records[stream_name] = _StreamRecord(scene_streamer)
            self._stream_states[stream_name] = StreamState.RUNNING
            self.stream_started.emit(stream_name)
            self.status_update.emit(stream_name, "GStreamer pipeline started")
            return True
        except Exception as e:
            self._stream_states[stream_name] = StreamState.ERROR
            self.stream_error.emit(stream_name, f"Failed to start stream: {e}")
            return False

    def stop_stream(self, stream_name: str) -> bool:
        try:
            rec = self._records.pop(stream_name, None)
            if rec:
                rec.scene_streamer.stop()
            self._stream_states[stream_name] = StreamState.STOPPED
            self.stream_stopped.emit(stream_name)
            return True
        except Exception as e:
            self.stream_error.emit(stream_name, f"Error stopping stream: {e}")
            return False

    def is_streaming(self, stream_name: str) -> bool:
        state = self._stream_states.get(stream_name, StreamState.STOPPED)
        return state in (StreamState.STARTING, StreamState.RUNNING)

    def get_stream_state(self, stream_name: str) -> str:
        return self._stream_states.get(stream_name, StreamState.STOPPED)

    def stop_all_streams(self) -> None:
        for name in list(self._records.keys()):
            self.stop_stream(name)

    def _check_stream_health(self) -> None:
        # QtSceneToGstStreamer drives via QTimer; basic liveness check can be added if needed
        pass


class NewStreamControlWidget(QObject):
    """Control widget for settings and basic button state updates, compatible with main.py wiring."""

    def __init__(self, stream_name: str, stream_manager: NewStreamManager, parent_window=None):
        super().__init__(parent_window)
        self.stream_name = stream_name
        self.stream_manager = stream_manager
        self.parent_window = parent_window

        # Hook up no UI elements directly here; main.py connects button signals.
        # We only handle settings dialog opening and status-driven icon changes similar to prior implementation.
        self.stream_manager.stream_started.connect(self._on_stream_started)
        self.stream_manager.stream_stopped.connect(self._on_stream_stopped)
        self.stream_manager.stream_error.connect(self._on_stream_error)
        self.stream_manager.status_update.connect(self._on_status_update)

    def open_settings_dialog(self) -> None:
        try:
            from new_stream_settings_dialog import NewStreamSettingsDialog
            dialog = NewStreamSettingsDialog(self.stream_name, self.parent_window, self.stream_manager)
            dialog.settings_saved.connect(self._on_settings_saved)
            dialog.exec()
        except Exception as e:
            print(f"[Gst] Error opening settings dialog: {e}")

    def _on_settings_saved(self, settings: Dict[str, Any]) -> None:
        self.stream_manager.configure_stream(self.stream_name, settings)

    def _on_stream_started(self, name: str) -> None:
        if name == self.stream_name:
            self._update_ui_state("streaming")

    def _on_stream_stopped(self, name: str) -> None:
        if name == self.stream_name:
            self._update_ui_state("stopped")

    def _on_stream_error(self, name: str, error_msg: str) -> None:
        if name == self.stream_name:
            self._update_ui_state("error")
            print(f"[Gst] {self.stream_name} error: {error_msg}")

    def _on_status_update(self, name: str, status: str) -> None:
        if name == self.stream_name:
            print(f"[Gst] {self.stream_name} status: {status}")

    def _update_ui_state(self, state: str) -> None:
        try:
            if not self.parent_window:
                return
            # Get the appropriate button, mirroring names used in main.ui
            from PyQt6.QtGui import QIcon
            from pathlib import Path
            icon_path = Path(__file__).resolve().parents[1] / "icons"
            if self.stream_name == "Stream1":
                button = getattr(self.parent_window, 'stream1AudioBtn', None)
            elif self.stream_name == "Stream2":
                button = getattr(self.parent_window, 'stream2AudioBtn', None)
            else:
                return
            if not button:
                return
            if state == "streaming":
                button.setIcon(QIcon(str(icon_path / "Pause.png")))
                button.setStyleSheet("border-radius: 5px; background-color: #ff4444;")
                button.setToolTip(f"Stop {self.stream_name}")
            elif state == "error":
                button.setIcon(QIcon(str(icon_path / "Stream.png")))
                button.setStyleSheet("border-radius: 5px; background-color: #ff8800;")
                button.setToolTip(f"{self.stream_name} Error - Click to retry")
            else:
                button.setIcon(QIcon(str(icon_path / "Stream.png")))
                button.setStyleSheet("border-radius: 5px; background-color: #404040;")
                button.setToolTip(f"Start {self.stream_name}")
        except Exception as e:
            print(f"[Gst] Error updating UI state: {e}")

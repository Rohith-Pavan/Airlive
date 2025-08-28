#!/usr/bin/env python3
"""
GStreamer-based Recording Manager for GoLive Studio

- Pushes video frames from a Qt scene/widget via appsrc
- Pulls mixed audio from AudioCompositor via interaudiosrc (shared channel)
- Muxes A/V to a local file (MP4) using mp4mux -> filesink
"""
from __future__ import annotations

import os
from pathlib import Path
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

from .qt_gst import QtSceneToGstStreamer

# Initialize GStreamer once
if not Gst.is_initialized():
    Gst.init(None)


class RecordingState:
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


def build_file_av_pipeline(width: int, height: int, fps: int, out_path: str, audio_channel: str, video_kbps: int, audio_kbps: int) -> str:
    """Build a GStreamer pipeline description string to save to a local MP4 file."""
    # Ensure GStreamer is initialized before querying factories
    if not Gst.is_initialized():
        Gst.init(None)

    # Choose an available AAC encoder
    aac_candidates = ["avenc_aac", "voaacenc", "fdkaacenc", "faac"]
    aac_enc = next((name for name in aac_candidates if Gst.ElementFactory.find(name)), None)
    if aac_enc is None:
        raise RuntimeError(
            "No AAC encoder found (tried: avenc_aac, voaacenc, fdkaacenc, faac). "
            "Install gst-libav or gst-plugins-bad/ugly."
        )

    # Common queues
    vq = "queue max-size-buffers=0 max-size-bytes=0 max-size-time=0"
    aq = "queue max-size-buffers=0 max-size-bytes=0 max-size-time=0"
    a_bps = max(16, int(audio_kbps)) * 1000

    desc = (
        "appsrc name=qtappsrc is-live=true format=time do-timestamp=true ! "
        f"video/x-raw,format=BGRA,width={width},height={height},framerate={fps}/1 ! "
        f"videoconvert ! x264enc tune=zerolatency bitrate={{vkbps}} speed-preset=veryfast key-int-max={{gop}} ! "
        f"{vq} ! mux. "
        f"interaudiosrc channel={audio_channel} ! audioconvert ! audioresample ! {{aac}} bitrate={{a_bps}} ! "
        f"{aq} ! mux. "
        f"mp4mux name=mux ! filesink location=\"{out_path}\""
    )
    return desc.format(vkbps=max(100, int(video_kbps)), gop=max(1, int(fps)), a_bps=a_bps, aac=aac_enc)


class RecordingManager(QObject):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_error = pyqtSignal(str)

    def __init__(self, audio_channel: str = "ac_audio_bus", parent: Optional[QObject] = None):
        super().__init__(parent)
        self._config: Dict[str, Any] = {}
        self._scene_streamer: Optional[QtSceneToGstStreamer] = None
        self._graphics_view: Optional[Any] = None
        self._state: str = RecordingState.STOPPED
        self._audio_channel = audio_channel

    def register_graphics_view(self, graphics_view) -> None:
        self._graphics_view = graphics_view
        print("[RecMan] Registered graphics view for recording")

    def configure_recording(self, settings: Dict[str, Any]) -> bool:
        try:
            required_keys = ['resolution', 'fps', 'video_bitrate', 'output_path']
            if not all(key in settings and settings[key] for key in required_keys):
                self.recording_error.emit(f"Missing required recording settings.")
                return False
            self._config = settings.copy()
            print(f"[RecMan] Configured recording: {self._config}")
            return True
        except Exception as e:
            self.recording_error.emit(f"Configuration error: {e}")
            return False

    def start_recording(self) -> bool:
        if self.is_recording():
            return True
        if not self._config:
            self.recording_error.emit("Recording not configured")
            return False
        if not self._graphics_view:
            self.recording_error.emit("Graphics view not registered")
            return False

        self.stop_recording()  # Ensure clean state

        try:
            width, height = map(int, self._config['resolution'].split('x'))
            fps = int(self._config['fps'])
            v_kbps = int(self._config['video_bitrate'])
            a_kbps = int(self._config.get('audio_bitrate', 128))
            out_path = os.path.abspath(self._config['output_path'])

            # Ensure output directory exists
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)

            pipeline_desc = build_file_av_pipeline(width, height, fps, out_path, self._audio_channel, v_kbps, a_kbps)

            if hasattr(self._graphics_view, 'scene') and self._graphics_view.scene():
                scene = self._graphics_view.scene()
            else:
                scene = self._graphics_view  # QWidget with render()
            
            size = QSize(width, height)
            self._scene_streamer = QtSceneToGstStreamer(scene, size, fps, pipeline_desc, self)
            self._scene_streamer.start()
            
            self._state = RecordingState.RUNNING
            self.recording_started.emit()
            print("[RecMan] Recording started")
            return True
        except Exception as e:
            self._state = RecordingState.ERROR
            self.recording_error.emit(f"Failed to start recording: {e}")
            print(f"[RecMan] Error starting recording: {e}")
            return False

    def stop_recording(self) -> bool:
        if self._scene_streamer:
            self._scene_streamer.stop()
            self._scene_streamer = None
        
        if self._state != RecordingState.STOPPED:
            self._state = RecordingState.STOPPED
            self.recording_stopped.emit()
            print("[RecMan] Recording stopped")
        return True

    def is_recording(self) -> bool:
        return self._state == RecordingState.RUNNING

    def get_state(self) -> str:
        return self._state

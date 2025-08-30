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
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


def build_file_av_pipeline(width: int, height: int, fps: int, out_path: str, audio_channel: str, video_kbps: int, audio_kbps: int, video_format: str = 'mp4') -> str:
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

    muxer_map = {
        'mp4': 'mp4mux',
        'mkv': 'matroskamux',
        'avi': 'avimux',
        'flv': 'flvmux',
    }
    muxer_name = muxer_map.get(video_format.lower(), 'mp4mux')
    muxer = muxer_name
    mux_props = ""
    if muxer_name == 'mp4mux':
        # Write moov at the start so Windows players open it immediately
        mux_props = " faststart=true"

    # Ensure minimum bitrate for x264enc to work properly (based on resolution)
    req_min = 500
    if height >= 1080:
        req_min = 4000
    elif height >= 720:
        req_min = 2500
    v_kbps = max(req_min, int(video_kbps))
    
    # Select best available H.264 encoder by priority (hardware > software)
    enc_priority = [
        # NVIDIA (Windows/Linux)
        'nvh264enc',
        # macOS VideoToolbox
        'vtenc_h264',
        # Windows D3D11 (AMD/Intel via MF or AMF)
        'd3d11h264enc',
        # Intel VAAPI (Linux)
        'vaapih264enc',
        # Intel QuickSync (older/newer)
        'qsvh264enc', 'msdkh264enc',
        # AMD AMF
        'amfh264enc',
        # Software encoders
        'x264enc', 'openh264enc', 'avenc_h264',
    ]

    available = [name for name in enc_priority if Gst.ElementFactory.find(name)]
    if not available:
        raise RuntimeError("No H.264 encoder found. Please install GStreamer plugins (bad/ugly/libav).")
    h264_enc = available[0]

    # Bitrate unit differences
    bps_encoders = {'vtenc_h264', 'd3d11h264enc', 'openh264enc', 'avenc_h264'}
    kbps_encoders = {'x264enc', 'nvh264enc', 'vaapih264enc', 'qsvh264enc', 'msdkh264enc', 'amfh264enc'}

    v_bps = max(100_000, int(v_kbps) * 1000)
    v_kbps_final = max(1, int(v_kbps))

    if h264_enc in bps_encoders:
        enc_props = f"bitrate={v_bps}"
    else:
        enc_props = f"bitrate={v_kbps_final}"

    # Add low-latency knobs for specific encoders
    if h264_enc == 'x264enc':
        enc_extra = f" tune=zerolatency speed-preset=ultrafast threads=0 sliced-threads=true bframes=0 key-int-max={max(1, int(fps))} byte-stream=false"
    elif h264_enc == 'vtenc_h264':
        # VideoToolbox: use realtime mode, and avoid frame reordering for latency
        # Props vary by version; these are commonly available.
        enc_extra = f" realtime=true allow-frame-reordering=false max-keyframe-interval={max(1, int(fps))}"
    else:
        enc_extra = ""

    # Use forward slashes for GStreamer on Windows
    gst_path = out_path.replace('\\', '/')

    desc = (
        "appsrc name=qtappsrc is-live=true format=time do-timestamp=true block=false ! "
        # Keep this queue minimal to avoid latency buildup
        "queue leaky=downstream max-size-buffers=0 max-size-bytes=0 max-size-time=0 ! "
        f"video/x-raw,format=BGRx,width={width},height={height},framerate={fps}/1 ! "
        "videoconvert ! queue ! "
        f"{h264_enc} {enc_props}{enc_extra} ! "
        # Ensure proper format for MP4; set caps after parser
        "h264parse config-interval=-1 ! video/x-h264,stream-format=avc,alignment=au ! "
        f"{vq} ! mux. "
        f"interaudiosrc channel={audio_channel} ! audioconvert ! audioresample ! {aac_enc} bitrate={a_bps} ! "
        f"{aq} ! mux. "
        f"{muxer}{mux_props} name=mux ! filesink location=\"{gst_path}\""
    )
    return desc


class RecordingManager(QObject):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_paused = pyqtSignal()
    recording_resumed = pyqtSignal()
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
        if self._state != RecordingState.STOPPED:
            print(f"[RecMan] Cannot start, current state is {self._state}")
            return False
        if not self._config:
            self.recording_error.emit("Recording not configured")
            return False
        if not self._graphics_view:
            self.recording_error.emit("Graphics view not registered")
            return False

        self._state = RecordingState.STARTING
        try:
            width, height = map(int, self._config['resolution'].split('x'))
            fps = int(self._config['fps'])
            v_kbps = int(self._config['video_bitrate'])
            a_kbps = int(self._config.get('audio_bitrate', 128))
            out_path = os.path.abspath(self._config['output_path'])

            # Ensure output directory exists
            out_dir = Path(out_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"[RecMan] Output directory: {out_dir}")
            print(f"[RecMan] Output file path: {out_path}")

            video_format = self._config.get('video_format', 'mp4')
            pipeline_desc = build_file_av_pipeline(width, height, fps, out_path, self._audio_channel, v_kbps, a_kbps, video_format)
            print(f"[RecMan] Pipeline: {pipeline_desc}")

            # Always pass the view/widget; streamer will grab from viewport when available
            scene = self._graphics_view
            print(f"[RecMan] Using widget for capture: {type(scene).__name__}")
            
            size = QSize(width, height)
            print(f"[RecMan] Recording size: {width}x{height} at {fps}fps")
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

    def pause_recording(self) -> bool:
        if self._state == RecordingState.RUNNING and self._scene_streamer:
            # Assuming the streamer has a pause method
            if hasattr(self._scene_streamer, 'pause') and self._scene_streamer.pause():
                self._state = RecordingState.PAUSED
                self.recording_paused.emit()
                print("[RecMan] Recording paused")
                return True
        return False

    def resume_recording(self) -> bool:
        if self._state == RecordingState.PAUSED and self._scene_streamer:
            # Assuming the streamer has a resume method
            if hasattr(self._scene_streamer, 'resume') and self._scene_streamer.resume():
                self._state = RecordingState.RUNNING
                self.recording_resumed.emit()
                print("[RecMan] Recording resumed")
                return True
        return False

    def stop_recording(self) -> bool:
        if self._state in [RecordingState.STOPPED, RecordingState.STOPPING]:
            return True

        self._state = RecordingState.STOPPING
        if self._scene_streamer:
            self._scene_streamer.stop()
            self._scene_streamer = None
        
        self._state = RecordingState.STOPPED
        self.recording_stopped.emit()
        print("[RecMan] Recording stopped")
        
        # Check if file was created
        if self._config and 'output_path' in self._config:
            out_path = os.path.abspath(self._config['output_path'])
            if os.path.exists(out_path):
                file_size = os.path.getsize(out_path)
                print(f"[RecMan] Recording file created: {out_path} ({file_size} bytes)")
            else:
                print(f"[RecMan] WARNING: Recording file not found: {out_path}")
        
        return True

    def is_recording(self) -> bool:
        return self._state in [RecordingState.RUNNING, RecordingState.PAUSED, RecordingState.STARTING]

    def is_paused(self) -> bool:
        return self._state == RecordingState.PAUSED

    def get_state(self) -> str:
        return self._state

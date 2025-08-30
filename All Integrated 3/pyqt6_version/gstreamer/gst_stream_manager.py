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

from .qt_gst import QtSceneToGstStreamer, gst_sample_to_qimage

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

    # Common queues: keep small time window and drop oldest on congestion to minimize latency
    # Ultra-low latency queues; keep both branches symmetrical (10 ms)
    vq = "queue leaky=2 max-size-buffers=0 max-size-bytes=0 max-size-time=10000000"  # 10ms
    aq = "queue leaky=2 max-size-buffers=0 max-size-bytes=0 max-size-time=10000000"  # 10ms
    # AAC bitrate in bits/s
    a_bps = max(16, int(audio_kbps)) * 1000

    # Note: caps for appsrc (BGRx, WxH, FPS) are set programmatically in GstQtStreamer;
    # do not insert a conflicting capsfilter here.
    desc = (
        "appsrc name=qtappsrc is-live=true format=time do-timestamp=true ! "
        "videoconvert ! x264enc tune=zerolatency bitrate={vkbps} speed-preset=veryfast key-int-max={gop} ! "
        f"{vq} ! mux. "
        # Make audio explicitly live and timestamped; convert to standard 48k stereo before encoding
        f"interaudiosrc channel={audio_channel} is-live=true do-timestamp=true ! "
        "audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! "
        "{aac} bitrate={a_bps} ! "
        f"{aq} ! mux. "
        "flvmux name=mux streamable=true ! rtmpsink location={rtmp}"
    )
    # Fill format values
    return desc.format(vkbps=max(100, int(video_kbps)), gop=max(1, int(fps)), a_bps=a_bps, rtmp=rtmp_url, aac=aac_enc)


def build_media_rtmp_pipeline(uri: str, width: int, height: int, fps: int, rtmp_url: str, video_kbps: int, audio_kbps: int) -> str:
    """Build a pipeline that decodes media (audio+video) together and streams to RTMP.

    It also exposes a BGRA branch via appsink (qtappsink) for local preview, guaranteeing
    that preview frames are from the same decoded video path as the streamed video.
    """
    if not Gst.is_initialized():
        Gst.init(None)

    # Choose an available AAC encoder
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

    # Ultra-low latency queues for symmetry (10 ms)
    vq = "queue leaky=2 max-size-buffers=0 max-size-bytes=0 max-size-time=10000000"  # 10ms
    aq = "queue leaky=2 max-size-buffers=0 max-size-bytes=0 max-size-time=10000000"  # 10ms
    a_bps = max(16, int(audio_kbps)) * 1000

    # Use uridecodebin to decode both A and V, split via two links from dec.
    # Video branch tees to preview (appsink) and encoder.
    desc = (
        f"uridecodebin uri={uri} name=dec use-buffering=false "
        # Video branch -> scale/rate -> tee
        "dec. ! queue ! videoconvert ! videoscale ! videorate ! "
        f"video/x-raw,width={int(width)},height={int(height)},framerate={int(fps)}/1 ! tee name=vt "
        # Preview branch (Qt appsink expects BGRA)
        "vt. ! queue ! videoconvert ! video/x-raw,format=BGRA,width=" + str(int(width)) + ",height=" + str(int(height)) + ",framerate=" + str(int(fps)) + "/1 ! "
        # Time-sync preview to pipeline clock (aligns with monitor audio), but keep very low latency
        "appsink name=qtappsink emit-signals=true drop=true max-buffers=1 sync=true async=false max-lateness=20000000 enable-last-sample=false "
        # Encoded video branch to mux
        # Keep only one small queue after encoder to avoid extra video delay vs audio
        f"vt. ! x264enc tune=zerolatency bitrate={max(100, int(video_kbps))} speed-preset=veryfast key-int-max={max(1, int(fps))} ! {vq} ! mux. "
        # Audio branch -> convert/resample -> tee -> (encode->mux) + (monitor sink)
        f"dec. ! {aq} ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! tee name=at "
        # Encoded path to mux
        f"at. ! {aq} ! {aac_enc} bitrate={a_bps} ! {aq} ! mux. "
        # Local monitor path (keep in same pipeline/clock for A/V sync in preview)
        f"at. ! {aq} ! autoaudiosink sync=true "
        # Mux and sink
        f"flvmux name=mux streamable=true ! rtmpsink location={rtmp_url} sync=true"
    )
    return desc


def build_media_preview_pipeline(uri: str, width: int, height: int, fps: int) -> str:
    """Build a low-latency preview-only pipeline with audio and video from the same clock.

    - Video: BGRA frames to qtappsink for preview
    - Audio: autoaudiosink for monitor
    - No encoder or network sink
    """
    if not Gst.is_initialized():
        Gst.init(None)

    # 10ms symmetric queues
    vq = "queue leaky=2 max-size-buffers=0 max-size-bytes=0 max-size-time=10000000"
    aq = "queue leaky=2 max-size-buffers=0 max-size-bytes=0 max-size-time=10000000"

    desc = (
        f"uridecodebin uri={uri} name=dec use-buffering=false "
        # Video branch -> scale/rate -> appsink
        "dec. ! videoconvert ! videoscale ! videorate ! "
        f"video/x-raw,width={int(width)},height={int(height)},framerate={int(fps)}/1 ! {vq} ! "
        "videoconvert ! video/x-raw,format=BGRA ! appsink name=qtappsink emit-signals=true drop=true max-buffers=1 sync=true max-lateness=20000000 enable-last-sample=false "
        # Audio branch -> convert/resample -> monitor sink
        f"dec. ! {aq} ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! autoaudiosink sync=true "
    )
    return desc

class GstMediaRtmpStreamer(QObject):
    """Runs a media RTMP pipeline built by build_media_rtmp_pipeline and provides preview frames via a callback.

    The provided pipeline must contain an appsink named 'qtappsink' producing BGRA frames for preview.
    """
    def __init__(self, pipeline_desc: str, on_qimage, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._pipeline_desc = pipeline_desc
        self._on_qimage = on_qimage
        self._pipeline: Optional[Gst.Pipeline] = None
        self._appsink: Optional[Gst.Element] = None
        self._pending_seek_ns: Optional[int] = None

    def start(self) -> None:
        if self._pipeline:
            return
        self._pipeline = Gst.parse_launch(self._pipeline_desc)
        if not isinstance(self._pipeline, Gst.Pipeline):
            raise RuntimeError("Pipeline description did not create a Gst.Pipeline")

        self._appsink = self._pipeline.get_by_name('qtappsink')
        if self._appsink is None:
            raise RuntimeError("appsink named 'qtappsink' not found in pipeline")
        # Configure appsink
        try:
            self._appsink.set_property('emit-signals', True)
            # Sync to pipeline clock so preview video timing matches monitor audio
            self._appsink.set_property('sync', True)
            try:
                # Keep lateness small but tolerant of occasional jitter (~20ms)
                self._appsink.set_property('max-lateness', 20_000_000)
                self._appsink.set_property('async', False)
            except Exception:
                pass
        except Exception:
            pass
        self._appsink.connect('new-sample', self._on_new_sample)

        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._on_bus_message)

        self._pipeline.set_state(Gst.State.PLAYING)

    def stop(self) -> None:
        if not self._pipeline:
            return
        try:
            self._pipeline.set_state(Gst.State.NULL)
        finally:
            self._pipeline = None
            self._appsink = None
            self._pending_seek_ns = None

    def pause(self) -> None:
        if self._pipeline:
            self._pipeline.set_state(Gst.State.PAUSED)

    def play(self) -> None:
        if self._pipeline:
            self._pipeline.set_state(Gst.State.PLAYING)

    def get_position_ns(self) -> Optional[int]:
        if not self._pipeline:
            return None
        try:
            success, pos = self._pipeline.query_position(Gst.Format.TIME)
            if success:
                return int(pos)
        except Exception:
            pass
        return None

    def seek_ns(self, position_ns: int) -> bool:
        """Attempt to seek; if pipeline is not ready, remember and retry on ASYNC_DONE."""
        if not self._pipeline:
            return False
        try:
            ok = self._pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, int(position_ns))
            if not ok:
                # Queue for later when preroll completes
                self._pending_seek_ns = int(position_ns)
            return ok
        except Exception:
            self._pending_seek_ns = int(position_ns)
            return False

    # GI callback on Gst thread
    def _on_new_sample(self, sink: Gst.Element):
        sample = sink.emit('pull-sample')
        if sample is None:
            return Gst.FlowReturn.EOS
        try:
            qimg: QImage = gst_sample_to_qimage(sample)
            # Deliver to UI (caller should ensure thread marshalling if needed)
            try:
                self._on_qimage(qimg)
            except Exception as e:
                print(f"[GstMediaRtmpStreamer] on_qimage error: {e}")
            return Gst.FlowReturn.OK
        except Exception as e:
            print(f"[GstMediaRtmpStreamer] Error converting sample: {e}")
            return Gst.FlowReturn.ERROR

    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"[Gst] Error: {err} debug={debug}")
        elif t == Gst.MessageType.EOS:
            print("[Gst] EOS")
        elif t == Gst.MessageType.ASYNC_DONE:
            # Perform pending seek after preroll
            if self._pending_seek_ns is not None and self._pipeline is not None:
                try:
                    self._pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, int(self._pending_seek_ns))
                except Exception:
                    pass
                finally:
                    self._pending_seek_ns = None


class _StreamRecord:
    def __init__(self, scene_streamer: QtSceneToGstStreamer):
        self.scene_streamer = scene_streamer
        self.frame_count = 0

class _HDMIStreamRecord:
    def __init__(self, hdmi_manager, hdmi_stream_name: str):
        self.hdmi_manager = hdmi_manager
        self.hdmi_stream_name = hdmi_stream_name
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
            # Check if this is HDMI streaming
            if settings.get('is_hdmi', False):
                # Validate HDMI settings
                if settings.get('hdmi_display_index', -1) == -1:
                    self.stream_error.emit(stream_name, "Invalid HDMI display selection")
                    return False
                
                # HDMI streams don't need URL/key validation
                required_keys = ['resolution', 'fps', 'video_bitrate']
            else:
                # Validate regular streaming settings
                required_keys = ['url', 'key', 'resolution', 'fps', 'video_bitrate']
            
            # Validate inputs
            for key in required_keys:
                if key not in settings or not settings[key]:
                    self.stream_error.emit(stream_name, f"Missing required setting: {key}")
                    return False
            
            # Store
            self._streams[stream_name] = settings.copy()
            
            if settings.get('is_hdmi', False):
                print(f"[Gst] Configured HDMI {stream_name}: Display {settings.get('hdmi_display_index')} - {settings.get('resolution')} @ {settings.get('fps')}fps")
            else:
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
            
            # Handle HDMI streaming
            if settings.get('is_hdmi', False):
                return self._start_hdmi_stream(stream_name, settings)
            else:
                return self._start_regular_stream(stream_name, settings)
                
        except Exception as e:
            self._stream_states[stream_name] = StreamState.ERROR
            self.stream_error.emit(stream_name, f"Failed to start stream: {e}")
            return False
    
    def _start_regular_stream(self, stream_name: str, settings: Dict[str, Any]) -> bool:
        """Start regular RTMP streaming"""
        try:
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
            self.stream_error.emit(stream_name, f"Failed to start regular stream: {e}")
            return False
    
    def _start_hdmi_stream(self, stream_name: str, settings: Dict[str, Any]) -> bool:
        """Start HDMI streaming"""
        try:
            from hdmi_stream_manager import HDMIStreamManager
            
            gv = self._graphics_views[stream_name]
            
            # Create HDMI stream manager
            hdmi_manager = HDMIStreamManager()
            
            # Configure HDMI stream
            hdmi_stream_name = f"hdmi_{stream_name}"
            if not hdmi_manager.configure_hdmi_stream(hdmi_stream_name, settings):
                self.stream_error.emit(stream_name, "Failed to configure HDMI stream")
                return False
            
            # Start HDMI streaming
            success = hdmi_manager.start_hdmi_stream(hdmi_stream_name, gv)
            
            if success:
                # Store HDMI manager for cleanup (using a special record type)
                self._records[stream_name] = _HDMIStreamRecord(hdmi_manager, hdmi_stream_name)
                self._stream_states[stream_name] = StreamState.RUNNING
                self.stream_started.emit(stream_name)
                self.status_update.emit(stream_name, "HDMI stream started")
                return True
            else:
                self.stream_error.emit(stream_name, "Failed to start HDMI stream")
                return False
                
        except Exception as e:
            self.stream_error.emit(stream_name, f"Failed to start HDMI stream: {e}")
            return False

    def stop_stream(self, stream_name: str) -> bool:
        try:
            rec = self._records.pop(stream_name, None)
            if rec:
                if isinstance(rec, _HDMIStreamRecord):
                    # HDMI stream
                    rec.hdmi_manager.stop_hdmi_stream(rec.hdmi_stream_name)
                else:
                    # Regular GStreamer stream
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

    # --- Exposed getters for integration with media pipeline handoff ---
    def get_stream_config(self, stream_name: str) -> Optional[Dict[str, Any]]:
        """Return a copy of the stored stream configuration for the given stream name, if any."""
        cfg = self._streams.get(stream_name)
        return cfg.copy() if isinstance(cfg, dict) else None

    def get_active_streams(self) -> list:
        """Return a list of stream names currently in STARTING/RUNNING state."""
        active_states = {StreamState.STARTING, StreamState.RUNNING}
        return [name for name, st in self._stream_states.items() if st in active_states]


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

#!/usr/bin/env python3
"""
Qt + GStreamer bridge utilities

- Ingest (camera/screen -> Qt): appsink -> GstSample -> QImage
- Output (Qt composited frame -> GStreamer): QImage -> appsrc -> encoder -> flvmux -> rtmpsink

Requirements:
  pip install PyGObject

Example ingest pipelines:
  Linux camera:   v4l2src ! videoconvert ! video/x-raw,format=BGRA,framerate=30/1 ! appsink name=qtappsink emit-signals=true max-buffers=1 drop=true
  Windows camera: ksvideosrc ! videoconvert ! video/x-raw,format=BGRA,framerate=30/1 ! appsink name=qtappsink emit-signals=true max-buffers=1 drop=true

Example streaming pipeline (RTMP):
  appsrc name=qtappsrc is-live=true format=time do-timestamp=true caps=video/x-raw,format=BGRA,width=1280,height=720,framerate=30/1 ! \
  videoconvert ! x264enc tune=zerolatency bitrate=4000 speed-preset=veryfast key-int-max=30 ! flvmux streamable=true ! \
  rtmpsink location=rtmp://a.rtmp.youtube.com/live2/STREAM_KEY
"""

from __future__ import annotations
import sys
import typing as _t

# GStreamer / GI
import gi  # type: ignore
try:
    gi.require_version('Gst', '1.0')
    gi.require_version('GObject', '2.0')
except Exception:
    # If version requirements fail, continue; import may still succeed in some envs
    pass
from gi.repository import Gst, GObject  # type: ignore

# Qt
from PyQt6.QtCore import QObject, QTimer, QSize, QRectF, Qt
from PyQt6.QtGui import QImage

# Initialize GStreamer once
if not Gst.is_initialized():
    Gst.init(None)


# ----------------------------
# Conversions
# ----------------------------

def gst_sample_to_qimage(sample: Gst.Sample) -> QImage:
    """Convert a GstSample (BGRA) to a deep-copied QImage.
    Expects caps video/x-raw,format=BGRA. We map to QImage.Format_ARGB32 which
    shares the same byte layout on little-endian platforms.
    """
    caps = sample.get_caps()
    s = caps.get_structure(0)
    fmt = s.get_string('format')
    width = s.get_value('width')
    height = s.get_value('height')
    if fmt != 'BGRA':
        raise ValueError(f"Unsupported format: {fmt}; expected BGRA")

    buf = sample.get_buffer()
    success, mapinfo = buf.map(Gst.MapFlags.READ)
    if not success:
        raise RuntimeError("Failed to map GstBuffer")
    try:
        stride = int(mapinfo.size // height) if height > 0 else width * 4
        qimg = QImage(mapinfo.data, width, height, stride, QImage.Format.Format_ARGB32)
        return qimg.copy()  # deep copy to detach from buffer lifetime
    finally:
        buf.unmap(mapinfo)


def qimage_to_gst_buffer(img: QImage) -> Gst.Buffer:
    """Convert a QImage to a Gst.Buffer (ARGB). Converts format when necessary."""
    if img.isNull():
        raise ValueError("QImage is null")

    # Ensure ARGB32
    if img.format() != QImage.Format.Format_ARGB32:
        img = img.convertToFormat(QImage.Format.Format_ARGB32)

    width = img.width()
    height = img.height()
    stride = img.bytesPerLine()

    # Make a deep copy of the pixel data
    ptr = img.bits()
    ptr.setsize(stride * height)
    data = bytes(ptr)

    buffer = Gst.Buffer.new_allocate(None, len(data), None)
    # Write bytes into buffer using fill to avoid immutable mapinfo.data issues
    buffer.fill(0, data)

    # Set timestamps downstream if needed at appsrc
    return buffer


# ----------------------------
# Ingest: appsink -> QImage callback
# ----------------------------

class GstQtIngest(QObject):
    """Runs a GStreamer ingest pipeline ending with an appsink named 'qtappsink'.

    - Pipeline must output BGRA to appsink
    - Emits frames via a provided Python callable on the Qt thread
    """

    def __init__(self, pipeline_desc: str, on_qimage: _t.Callable[[QImage], None], parent: QObject | None = None):
        super().__init__(parent)
        self._pipeline_desc = pipeline_desc
        self._on_qimage = on_qimage
        self._pipeline: Gst.Pipeline | None = None
        self._appsink: Gst.Element | None = None

    def start(self) -> None:
        if self._pipeline:
            return
        self._pipeline = Gst.parse_launch(self._pipeline_desc)
        if not isinstance(self._pipeline, Gst.Pipeline):
            raise RuntimeError("Pipeline description did not create a Gst.Pipeline")

        self._appsink = self._pipeline.get_by_name('qtappsink')
        if self._appsink is None:
            raise RuntimeError("appsink named 'qtappsink' not found in pipeline")

        # Configure appsink for signal-based new-sample callback
        self._appsink.set_property('emit-signals', True)
        self._appsink.set_property('sync', False)

        # Connect callback
        self._appsink.connect('new-sample', self._on_new_sample)

        # Bus error handling
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._on_bus_message)

        self._pipeline.set_state(Gst.State.PLAYING)

    def stop(self) -> None:
        if not self._pipeline:
            return
        self._pipeline.set_state(Gst.State.NULL)
        self._pipeline = None
        self._appsink = None

    # GI callback: runs on GStreamer thread
    def _on_new_sample(self, sink: Gst.Element) -> int:
        sample = sink.emit('pull-sample')
        if sample is None:
            return Gst.FlowReturn.EOS
        try:
            qimg = gst_sample_to_qimage(sample)
            # Marshal to Qt thread
            QTimer.singleShot(0, lambda img=qimg: self._on_qimage(img))
            return Gst.FlowReturn.OK
        except Exception as e:
            print(f"[GstQtIngest] Error converting sample: {e}")
            return Gst.FlowReturn.ERROR

    def _on_bus_message(self, bus: Gst.Bus, msg: Gst.Message):
        if msg.type == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print(f"[GstQtIngest] ERROR: {err} | debug: {dbg}")
        elif msg.type == Gst.MessageType.WARNING:
            err, dbg = msg.parse_warning()
            print(f"[GstQtIngest] WARNING: {err} | debug: {dbg}")
        elif msg.type == Gst.MessageType.EOS:
            print("[GstQtIngest] EOS")


# ----------------------------
# Streaming: appsrc push QImage -> RTMP (or file)
# ----------------------------

class GstQtStreamer(QObject):
    """Owns a GStreamer pipeline with an appsrc named 'qtappsrc'.

    Use push_qimage() to push frames. Set width/height/fps via caps on appsrc.
    """

    def __init__(self, pipeline_desc: str, width: int, height: int, fps: int = 30, parent: QObject | None = None):
        super().__init__(parent)
        self._pipeline_desc = pipeline_desc
        self._pipeline: Gst.Pipeline | None = None
        self._appsrc: Gst.Element | None = None
        self._width = int(width)
        self._height = int(height)
        self._fps = int(fps)
        self._timestamp_ns = 0

    def start(self) -> None:
        if self._pipeline:
            return
        self._pipeline = Gst.parse_launch(self._pipeline_desc)
        if not isinstance(self._pipeline, Gst.Pipeline):
            raise RuntimeError("Pipeline description did not create a Gst.Pipeline")

        self._appsrc = self._pipeline.get_by_name('qtappsrc')
        if self._appsrc is None:
            raise RuntimeError("appsrc named 'qtappsrc' not found in pipeline")

        # caps on appsrc
        caps = Gst.Caps.from_string(
            f"video/x-raw,format=BGRA,width={self._width},height={self._height},framerate={self._fps}/1"
        )
        self._appsrc.set_property('caps', caps)
        self._appsrc.set_property('is-live', True)
        self._appsrc.set_property('format', Gst.Format.TIME)
        self._appsrc.set_property('do-timestamp', True)
        self._appsrc.set_property('block', False)

        # Bus handling
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._on_bus_message)

        self._pipeline.set_state(Gst.State.PLAYING)
        self._timestamp_ns = 0

    def stop(self) -> None:
        if not self._pipeline:
            return
        self._pipeline.set_state(Gst.State.NULL)
        self._pipeline = None
        self._appsrc = None

    def push_qimage(self, img: QImage) -> None:
        if self._appsrc is None:
            return
        if img.width() != self._width or img.height() != self._height:
            img = img.scaled(self._width, self._height, Qt.AspectRatioMode.IgnoreAspectRatio)
        buf = qimage_to_gst_buffer(img)
        # Optionally set PTS/DTS manually for constant framerate pacing
        dur = int(1e9 / max(1, self._fps))
        buf.pts = self._timestamp_ns
        buf.duration = dur
        self._timestamp_ns += dur
        # Push
        flow = self._appsrc.emit('push-buffer', buf)
        if flow != Gst.FlowReturn.OK:
            print(f"[GstQtStreamer] push-buffer flow: {flow}")

    def _on_bus_message(self, bus: Gst.Bus, msg: Gst.Message):
        if msg.type == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print(f"[GstQtStreamer] ERROR: {err} | debug: {dbg}")
        elif msg.type == Gst.MessageType.WARNING:
            err, dbg = msg.parse_warning()
            print(f"[GstQtStreamer] WARNING: {err} | debug: {dbg}")
        elif msg.type == Gst.MessageType.EOS:
            print("[GstQtStreamer] EOS")


# ----------------------------
# Scene -> Stream helper
# ----------------------------

class QtSceneToGstStreamer(QObject):
    """Periodically renders a QGraphicsScene (or any QWidget paintable) to QImage and pushes to GstQtStreamer."""
    def __init__(self, scene, size: QSize, fps: int, pipeline_desc: str, parent: QObject | None = None):
        super().__init__(parent)
        self.scene = scene  # expects QGraphicsScene or has render(QPainter, ...)
        self.size = size
        self.fps = int(fps)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.streamer = GstQtStreamer(pipeline_desc, size.width(), size.height(), fps, self)

    def start(self):
        self.streamer.start()
        interval_ms = int(1000 / max(1, self.fps))
        self.timer.start(interval_ms)

    def stop(self):
        self.timer.stop()
        self.streamer.stop()

    def _on_tick(self):
        # Render scene to QImage (BGRA)
        img = QImage(self.size, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.black)
        from PyQt6.QtGui import QPainter
        p = QPainter(img)
        # If scene has sceneRect, render QGraphicsScene
        if hasattr(self.scene, 'render'):
            target = QRectF(0, 0, self.size.width(), self.size.height())
            self.scene.render(p, target)  # source rect auto
        p.end()
        self.streamer.push_qimage(img)


# ----------------------------
# Convenience pipeline builders
# ----------------------------

def build_rtmp_pipeline(width: int, height: int, fps: int, rtmp_url: str) -> str:
    return (
        "appsrc name=qtappsrc is-live=true format=time do-timestamp=true ! "
        "videoconvert ! x264enc tune=zerolatency bitrate=4000 speed-preset=veryfast key-int-max=30 ! "
        "flvmux streamable=true ! rtmpsink location=" + rtmp_url
        + f" caps=video/x-raw,format=BGRA,width={width},height={height},framerate={fps}/1"
    )


def build_file_pipeline(width: int, height: int, fps: int, out_path: str) -> str:
    # MPEG-TS H264 as an example
    return (
        "appsrc name=qtappsrc is-live=true format=time do-timestamp=true ! "
        "videoconvert ! x264enc tune=zerolatency bitrate=4000 speed-preset=veryfast key-int-max=30 ! "
        "h264parse ! mpegtsmux ! filesink location=" + out_path
        + f" caps=video/x-raw,format=BGRA,width={width},height={height},framerate={fps}/1"
    )


__all__ = [
    'gst_sample_to_qimage',
    'qimage_to_gst_buffer',
    'GstQtIngest',
    'GstQtStreamer',
    'QtSceneToGstStreamer',
    'build_rtmp_pipeline',
    'build_file_pipeline',
]

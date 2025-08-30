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


def qimage_to_gst_buffer(img: QImage, prealloc: bytearray | None = None) -> Gst.Buffer:
    """Convert a QImage to a Gst.Buffer (BGRx).
    Optionally reuse a provided preallocated bytearray to reduce allocations.
    """
    if img.isNull():
        raise ValueError("QImage is null")

    # Ensure RGB32 (opaque); memory layout is B,G,R,0xFF on little-endian
    if img.format() != QImage.Format.Format_RGB32:
        img = img.convertToFormat(QImage.Format.Format_RGB32)

    width = img.width()
    height = img.height()
    stride = img.bytesPerLine()

    # Pack to tight rows (width*4) to avoid padding issues in appsrc; matches BGRx stride
    tight_row = width * 4
    total = tight_row * height
    if prealloc is not None and len(prealloc) == total:
        packed = prealloc
    else:
        packed = bytearray(total)
    ptr = img.constBits()
    ptr.setsize(stride * height)
    mv = memoryview(ptr)
    if stride == tight_row:
        # Already tight
        packed[:] = mv
    else:
        # Copy row by row excluding padding
        for y in range(height):
            src_off = y * stride
            dst_off = y * tight_row
            packed[dst_off:dst_off + tight_row] = mv[src_off:src_off + tight_row]

    buffer = Gst.Buffer.new_allocate(None, len(packed), None)
    buffer.fill(0, packed)

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
        # Async push worker to avoid blocking UI on conversion/encode
        self._q: 'queue.Queue[QImage]' | None = None
        self._worker_thread: 'threading.Thread' | None = None
        self._stop_flag: bool = False
        # Reusable packing buffer to reduce allocations
        self._pack_buf: bytearray | None = None

    def start(self) -> None:
        if self._pipeline:
            return
        self._pipeline = Gst.parse_launch(self._pipeline_desc)
        if not isinstance(self._pipeline, Gst.Pipeline):
            raise RuntimeError("Pipeline description did not create a Gst.Pipeline")

        self._appsrc = self._pipeline.get_by_name('qtappsrc')
        if self._appsrc is None:
            raise RuntimeError("appsrc named 'qtappsrc' not found in pipeline")

        # caps on appsrc (BGRx, opaque)
        caps = Gst.Caps.from_string(
            f"video/x-raw,format=BGRx,width={self._width},height={self._height},framerate={self._fps}/1"
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
        # Start async worker
        self._start_worker()

    def pause(self) -> bool:
        if not self._pipeline:
            return False
        ret = self._pipeline.set_state(Gst.State.PAUSED)
        is_success = ret != Gst.StateChangeReturn.FAILURE
        if is_success:
            print("[GstQtStreamer] Pipeline paused")
        return is_success

    def resume(self) -> bool:
        if not self._pipeline:
            return False
        ret = self._pipeline.set_state(Gst.State.PLAYING)
        is_success = ret != Gst.StateChangeReturn.FAILURE
        if is_success:
            print("[GstQtStreamer] Pipeline resumed")
        return is_success

    def stop(self) -> None:
        if not self._pipeline:
            return
        # Stop async worker first
        self._stop_worker()
        try:
            # Signal EOS so muxers can finalize indexes (e.g., mp4)
            if self._appsrc is not None:
                try:
                    self._appsrc.emit('end-of-stream')
                except Exception:
                    pass
            # Wait up to 3s for EOS or ERROR
            bus = self._pipeline.get_bus()
            if bus is not None:
                bus.timed_pop_filtered(3 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
        except Exception:
            pass
        self._pipeline.set_state(Gst.State.NULL)
        self._pipeline = None
        self._appsrc = None
        self._pack_buf = None

    def push_qimage(self, img: QImage) -> None:
        # Enqueue frame for async processing; drop if queue full
        if self._q is None:
            return
        try:
            # Prefer latest frames: if full, get_nowait() oldest and discard
            if self._q.full():
                try:
                    _ = self._q.get_nowait()
                except Exception:
                    pass
            self._q.put_nowait(img)
        except Exception:
            pass

    def _on_bus_message(self, bus: Gst.Bus, msg: Gst.Message):
        if msg.type == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print(f"[GstQtStreamer] ERROR: {err} | debug: {dbg}")
        elif msg.type == Gst.MessageType.WARNING:
            err, dbg = msg.parse_warning()
            print(f"[GstQtStreamer] WARNING: {err} | debug: {dbg}")
        elif msg.type == Gst.MessageType.EOS:
            print("[GstQtStreamer] EOS")
        elif msg.type == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = msg.parse_state_changed()
            if msg.src == self._pipeline:
                print(f"[GstQtStreamer] Pipeline state: {old_state.value_nick} -> {new_state.value_nick}")
        elif msg.type == Gst.MessageType.STREAM_START:
            print("[GstQtStreamer] Stream started")
        elif msg.type == Gst.MessageType.ASYNC_DONE:
            print("[GstQtStreamer] Async done")

    # -------------- Worker --------------
    def _start_worker(self) -> None:
        try:
            import threading, queue
            self._stop_flag = False
            self._q = queue.Queue(maxsize=1)
            # Initialize reusable pack buffer sized for current WxH
            try:
                self._pack_buf = bytearray(self._width * self._height * 4)
            except Exception:
                self._pack_buf = None

            def _run():
                while not self._stop_flag:
                    try:
                        img: QImage = self._q.get(timeout=0.1)  # wait for frame
                    except Exception:
                        continue
                    try:
                        if self._appsrc is None or img is None or img.isNull():
                            continue
                        # Scale-to-fill and crop if needed
                        if img.width() != self._width or img.height() != self._height:
                            scaled = img.scaled(self._width, self._height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.FastTransformation)
                            x = max(0, (scaled.width() - self._width) // 2)
                            y = max(0, (scaled.height() - self._height) // 2)
                            img = scaled.copy(x, y, self._width, self._height)
                        buf = qimage_to_gst_buffer(img, self._pack_buf)
                        flow = self._appsrc.emit('push-buffer', buf)
                        if flow != Gst.FlowReturn.OK:
                            print(f"[GstQtStreamer] push-buffer flow: {flow}")
                    except Exception as e:
                        print(f"[GstQtStreamer] Worker error: {e}")

            self._worker_thread = threading.Thread(target=_run, name="GstQtStreamerWorker", daemon=True)
            self._worker_thread.start()
        except Exception as e:
            print(f"[GstQtStreamer] Failed to start worker: {e}")

    def _stop_worker(self) -> None:
        try:
            self._stop_flag = True
            if self._worker_thread:
                self._worker_thread.join(timeout=1.0)
        except Exception:
            pass
        finally:
            self._worker_thread = None
            self._q = None


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
        try:
            # More accurate pacing to reduce jitter
            self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        except Exception:
            pass
        self.timer.timeout.connect(self._on_tick)
        self.streamer = GstQtStreamer(pipeline_desc, size.width(), size.height(), fps, self)

    def start(self):
        self.streamer.start()
        interval_ms = int(1000 / max(1, self.fps))
        self.timer.start(interval_ms)

    def pause(self) -> bool:
        self.timer.stop()
        return self.streamer.pause()

    def resume(self) -> bool:
        if self.streamer.resume():
            interval_ms = int(1000 / max(1, self.fps))
            self.timer.start(interval_ms)
            return True
        return False

    def stop(self):
        self.timer.stop()
        self.streamer.stop()

    def _on_tick(self):
        # Prefer viewport grab first (fast, captures HW video), then fallback to render()
        img = None
        try:
            if hasattr(self.scene, 'viewport') and callable(getattr(self.scene, 'viewport')):
                vp = self.scene.viewport()
                if vp is not None:
                    pm = vp.grab()
                    img = pm.toImage()
            if (img is None or img.isNull()) and hasattr(self.scene, 'grab'):
                pm = self.scene.grab()
                img = pm.toImage()
        except Exception as e:
            print(f"[QtSceneToGstStreamer] QWidget grab failed: {e}")

        if img is None or img.isNull():
            # Fallback to render (slower, but always available)
            img = QImage(self.size, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.black)
            from PyQt6.QtGui import QPainter
            try:
                if hasattr(self.scene, 'render'):
                    p = QPainter(img)
                    target = QRectF(0, 0, self.size.width(), self.size.height())
                    self.scene.render(p, target)
                    p.end()
            except Exception as e:
                print(f"[QtSceneToGstStreamer] view.render failed: {e}")

        # Save first frame for debugging
        if not hasattr(self, '_debug_saved'):
            try:
                img.save("debug_frame.png")
                self._debug_saved = True
                print("[QtSceneToGstStreamer] Debug frame saved")
            except Exception as e:
                print(f"[QtSceneToGstStreamer] Failed to save debug frame: {e}")

        if not img.isNull():
            self.streamer.push_qimage(img)
        else:
            print("[QtSceneToGstStreamer] Warning: Rendered image is null")


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

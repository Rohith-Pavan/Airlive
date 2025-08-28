#!/usr/bin/env python3
"""
AudioCompositor - GStreamer-based audio mixer with per-input and master volume control

Dependencies:
  - PyGObject (GStreamer 1.0)

Design:
  Pipeline (created on start):
    audiomixer name=mix ! volume name=vol_master volume=1.0 ! autoaudiosink sync=false

  Per input:
    autoaudiosrc (or external supplied element) ! audioconvert ! audioresample ! volume name=vol_<name> volume=1.0 ! queue ! mix.

Public API:
  - start()
  - stop()
  - add_auto_source(name: str) -> None
  - remove_source(name: str) -> None
  - set_input_volume(name: str, vol: float) -> None
  - set_master_volume(vol: float) -> None

Notes:
  - This module focuses on live volume control. Integrating real media/player audio
    may require custom sources (e.g., appsrc) or platform-specific capture.
"""
from __future__ import annotations

from typing import Dict, Optional

import gi  # type: ignore
try:
    gi.require_version('Gst', '1.0')
    gi.require_version('GObject', '2.0')
except Exception:
    pass
from gi.repository import Gst, GObject, GLib  # type: ignore

# Initialize GStreamer once
if not Gst.is_initialized():
    Gst.init(None)


class AudioCompositor:
    def __init__(self) -> None:
        self._pipeline: Optional[Gst.Pipeline] = None
        self._mixer: Optional[Gst.Element] = None
        self._master_volume: Optional[Gst.Element] = None
        self._tee: Optional[Gst.Element] = None
        self._monitor_sink: Optional[Gst.Element] = None
        self._inter_sink: Optional[Gst.Element] = None
        self._monitor_volume: Optional[Gst.Element] = None
        # Track per-input elements: { name: { 'source': el, 'convert': el, 'resample': el, 'volume': el, 'queue': el } }
        self._inputs: Dict[str, Dict[str, Gst.Element]] = {}
        # Inter-audio channel name for external pipelines
        self.channel_name: str = "ac_audio_bus"

    def start(self) -> None:
        if self._pipeline:
            return
        self._pipeline = Gst.Pipeline.new("audio_compositor")
        if self._pipeline is None:
            raise RuntimeError("Failed to create audio pipeline")

        # Elements
        self._mixer = Gst.ElementFactory.make("audiomixer", "mix")
        self._master_volume = Gst.ElementFactory.make("volume", "vol_master")
        self._tee = Gst.ElementFactory.make("tee", "tee_master")
        self._monitor_sink = Gst.ElementFactory.make("autoaudiosink", "audiosink")
        self._monitor_volume = Gst.ElementFactory.make("volume", "vol_monitor")
        self._inter_sink = Gst.ElementFactory.make("interaudiosink", "ac_inter_sink")

        if not all([self._mixer, self._master_volume, self._tee, self._monitor_sink, self._inter_sink, self._monitor_volume]):
            raise RuntimeError("Failed to create one or more GStreamer elements for audio")

        # Configure
        self._master_volume.set_property("volume", 1.0)
        try:
            self._monitor_sink.set_property("sync", False)
        except Exception:
            pass
        # Configure inter-audio channel so other pipelines can read from it
        try:
            self._inter_sink.set_property("channel", self.channel_name)
        except Exception:
            pass
        
        # Debug: confirm channel in use
        print(f"[AudioCompositor] Started with interaudio channel: {self.channel_name}")

        # Assemble base pipeline: mix -> vol_master -> tee
        self._pipeline.add(self._mixer)
        self._pipeline.add(self._master_volume)
        self._pipeline.add(self._tee)
        self._pipeline.add(self._monitor_sink)
        self._pipeline.add(self._monitor_volume)
        self._pipeline.add(self._inter_sink)

        if not self._mixer.link(self._master_volume):
            raise RuntimeError("Failed to link mixer -> master volume")
        if not self._master_volume.link(self._tee):
            raise RuntimeError("Failed to link master volume -> tee")

        # Tee branches: to monitor sink and to interaudiosink (with queues for safety)
        q_monitor = Gst.ElementFactory.make("queue", "q_monitor")
        q_inter = Gst.ElementFactory.make("queue", "q_inter")
        if not all([q_monitor, q_inter]):
            raise RuntimeError("Failed to create tee branch queues")
        self._pipeline.add(q_monitor)
        self._pipeline.add(q_inter)

        # Link tee src pads to queues
        if not self._tee.link(q_monitor):
            raise RuntimeError("Failed to link tee -> q_monitor")
        if not self._tee.link(q_inter):
            raise RuntimeError("Failed to link tee -> q_inter")
        # Link queues to sinks
        if not q_monitor.link(self._monitor_volume):
            raise RuntimeError("Failed to link q_monitor -> monitor volume")
        if not self._monitor_volume.link(self._monitor_sink):
            raise RuntimeError("Failed to link monitor volume -> monitor sink")
        if not q_inter.link(self._inter_sink):
            raise RuntimeError("Failed to link q_inter -> interaudiosink")

        # Bus logging (warnings/errors)
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._on_bus_message)

        self._pipeline.set_state(Gst.State.PLAYING)

    def stop(self) -> None:
        if not self._pipeline:
            return
        self._pipeline.set_state(Gst.State.NULL)
        self._pipeline = None
        self._inputs.clear()
        self._mixer = None
        self._master_volume = None

    # ------------- Inputs -------------
    def add_auto_source(self, name: str) -> None:
        """Create and add a platform auto audio source into the mixer under the given logical name.
        If an input with the name exists, it is first removed.
        """
        if not self._pipeline or not self._mixer:
            raise RuntimeError("AudioCompositor not started")

        if name in self._inputs:
            self.remove_source(name)

        src = Gst.ElementFactory.make("autoaudiosrc", f"src_{name}")
        conv = Gst.ElementFactory.make("audioconvert", f"conv_{name}")
        res = Gst.ElementFactory.make("audioresample", f"res_{name}")
        vol = Gst.ElementFactory.make("volume", f"vol_{name}")
        q = Gst.ElementFactory.make("queue", f"queue_{name}")
        if not all([src, conv, res, vol, q]):
            raise RuntimeError(f"Failed to create input elements for {name}")

        vol.set_property("volume", 1.0)

        for el in (src, conv, res, vol, q):
            self._pipeline.add(el)

        # Link branch: src -> conv -> res -> vol -> queue -> mixer sink pad
        if not src.link(conv):
            raise RuntimeError(f"Failed to link src->conv for {name}")
        if not conv.link(res):
            raise RuntimeError(f"Failed to link conv->res for {name}")
        if not res.link(vol):
            raise RuntimeError(f"Failed to link res->vol for {name}")
        if not vol.link(q):
            raise RuntimeError(f"Failed to link vol->queue for {name}")

        # Link queue to an available mixer sink pad
        if not q.link(self._mixer):
            raise RuntimeError(f"Failed to link queue->audiomixer for {name}")

        self._inputs[name] = {
            'source': src,
            'convert': conv,
            'resample': res,
            'volume': vol,
            'queue': q,
        }

        # Ensure playing state for newly added elements
        for el in (src, conv, res, vol, q):
            el.sync_state_with_parent()

    def add_media_file_source(self, name: str, file_path: str) -> None:
        """Create and add a media file audio source into the mixer under the given logical name.
        Uses uridecodebin to decode the file and links only the audio pad into the mixer path.
        If an input with the name exists, it is first removed.
        """
        if not self._pipeline or not self._mixer:
            raise RuntimeError("AudioCompositor not started")

        if name in self._inputs:
            self.remove_source(name)

        # Build decode branch
        decode = Gst.ElementFactory.make("uridecodebin", f"decode_{name}")
        conv = Gst.ElementFactory.make("audioconvert", f"conv_{name}")
        res = Gst.ElementFactory.make("audioresample", f"res_{name}")
        vol = Gst.ElementFactory.make("volume", f"vol_{name}")
        q = Gst.ElementFactory.make("queue", f"queue_{name}")
        if not all([decode, conv, res, vol, q]):
            raise RuntimeError(f"Failed to create media input elements for {name}")

        # Set file URI
        try:
            uri = GLib.filename_to_uri(file_path, None)
        except Exception:
            # Fallback: naive file URI
            uri = f"file://{file_path}"
        decode.set_property("uri", uri)

        # Default volume
        vol.set_property("volume", 1.0)

        for el in (decode, conv, res, vol, q):
            self._pipeline.add(el)

        # Static links (except decode -> conv which is dynamic)
        if not conv.link(res):
            raise RuntimeError(f"Failed to link conv->res for {name}")
        if not res.link(vol):
            raise RuntimeError(f"Failed to link res->vol for {name}")
        if not vol.link(q):
            raise RuntimeError(f"Failed to link vol->queue for {name}")
        if not q.link(self._mixer):
            raise RuntimeError(f"Failed to link queue->audiomixer for {name}")

        # Dynamic pad linking for decodebin
        def _on_pad_added(db, pad: Gst.Pad, user_data=None):
            try:
                caps = pad.get_current_caps()
                if not caps:
                    caps = pad.get_allowed_caps()
                s = caps.to_string() if caps else "<no caps>"
                is_audio = False
                if caps:
                    is_audio = s.startswith("audio/") or ("audio/" in s)
                print(f"[AudioCompositor] {name}: pad-added with caps={s}")
                if is_audio:
                    sinkpad = conv.get_static_pad("sink")
                    if sinkpad and not sinkpad.is_linked():
                        res = pad.link(sinkpad)
                        print(f"[AudioCompositor] {name}: linked decodebin->audioconvert result={res}")
                    else:
                        print(f"[AudioCompositor] {name}: sink pad already linked or missing")
                else:
                    print(f"[AudioCompositor] {name}: non-audio pad ignored")
            except Exception as e:
                print(f"[AudioCompositor] pad-added link failed for {name}: {e}")

        decode.connect("pad-added", _on_pad_added)

        # Track elements
        self._inputs[name] = {
            'source': decode,
            'convert': conv,
            'resample': res,
            'volume': vol,
            'queue': q,
        }

        # Ensure playing state for newly added elements
        for el in (decode, conv, res, vol, q):
            el.sync_state_with_parent()

    def remove_source(self, name: str) -> None:
        if not self._pipeline:
            return
        info = self._inputs.pop(name, None)
        if not info:
            return
        # Set elements to NULL and remove from pipeline
        for key in ['source', 'convert', 'resample', 'volume', 'queue']:
            el = info.get(key)
            if el:
                el.set_state(Gst.State.NULL)
                try:
                    self._pipeline.remove(el)
                except Exception:
                    pass

    # ------------- Volumes -------------
    def set_input_volume(self, name: str, vol: float) -> None:
        vol = max(0.0, min(1.0, float(vol)))
        info = self._inputs.get(name)
        if not info:
            # Input not present; ignore silently (or raise if strict desired)
            return
        volume_el: Optional[Gst.Element] = info.get('volume')
        if volume_el is not None:
            volume_el.set_property('volume', vol)

    def set_master_volume(self, volume: float) -> None:
        """Set master volume [0.0 - 1.0]"""
        if not self._master_volume:
            return
        try:
            self._master_volume.set_property("volume", max(0.0, min(1.0, float(volume))))
        except Exception:
            pass

    def set_monitor_muted(self, muted: bool) -> None:
        """Mute/unmute only the monitor branch (does not affect stream)."""
        if not self._monitor_volume:
            return
        try:
            self._monitor_volume.set_property("mute", bool(muted))
        except Exception:
            pass

    # ------------- Bus -------------
    def _on_bus_message(self, bus: Gst.Bus, msg: Gst.Message):
        if msg.type == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print(f"[AudioCompositor] ERROR: {err} | debug: {dbg}")
        elif msg.type == Gst.MessageType.WARNING:
            err, dbg = msg.parse_warning()
            print(f"[AudioCompositor] WARNING: {err} | debug: {dbg}")
        elif msg.type == Gst.MessageType.EOS:
            print("[AudioCompositor] EOS")

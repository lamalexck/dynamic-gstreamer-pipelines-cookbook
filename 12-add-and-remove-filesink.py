#!/usr/bin/env python
import sys
import time
import datetime
import logging
from threading import Thread, Event

from tools.application_init import application_init

from gstgva import VideoFrame

application_init()

from gi.repository import Gst, GLib
from tools.logging_pad_probe import logging_pad_probe
from tools.runner import Runner

from roi_tracking import ROI_RecordTracking

VIDEO1='person-bicycle-car-detection.mp4'
log = logging.getLogger("main")

detection_model='models/intel/person-vehicle-bike-detection-2004/FP16/person-vehicle-bike-detection-2004.xml'
detection_proc='models/intel/person-vehicle-bike-detection-2004/person-vehicle-bike-detection-2004.json'

video_recording = Event()
video_recording.clear()

def start_recording():
    now_str = time.strftime("%H%M%S", time.localtime())
    log.info(f'Saving video clip in video_out.{now_str}.mp4')
    GLib.idle_add(add_sinkbin, f'video_out.{now_str}.mp4')

def end_recording():
    log.info(f'Stopping video clip')
    GLib.idle_add(stop_sinkbin)

vehicle_roi = ROI_RecordTracking(start_recording, end_recording)

def inspect_buffer(pad, probeinfo, location):
    buffer = probeinfo.get_buffer()
    frame = VideoFrame(buffer)
    roi_labels = [ roi.label() for roi in frame.regions() ]
    if "vehicle" in roi_labels:
        vehicle_roi.observed()
    else:
        vehicle_roi.not_observed()
    return Gst.PadProbeReturn.OK    

log.info("building pipeline")
pipeline_str = f'filesrc location={VIDEO1} ! decodebin ! tee name=tee ! queue ! '
pipeline_str += f'gvadetect model={detection_model} model-proc={detection_proc} device=CPU !' 
pipeline_str += f'gvatrack ! identity !'
pipeline_str += f'gvafpscounter ! fakesink sync=true' 

pipeline = Gst.parse_launch(pipeline_str)

pipeline.get_by_name("identity0").get_static_pad("src").add_probe(
    Gst.PadProbeType.BUFFER, inspect_buffer, "identity")

tee = pipeline.get_by_name("tee")

def filesink_eos_cb(pad, probeinfo, sinkbin):
    type = probeinfo.get_event().type
    if type == Gst.EventType.EOS:
        log.info(f"filesink received EOS. Schedule to remove sinkbin.")
        GLib.idle_add(remove_sinkbin, sinkbin)
    return Gst.PadProbeReturn.OK
    
def create_sinkbin(filename):
    log.info(f"Creating filesink bin for file {filename}")
    sinkbin = Gst.Bin.new("filesink-bin")
    #log.debug(sinkbin)

    log.info("Creating queue")
    queue = Gst.ElementFactory.make("queue", "queue")  # (3)
    #log.debug(queue)
    log.info("Adding queue to bin")
    log.debug(sinkbin.add(queue))

    log.info("Creating vaapih264enc")
    h264enc = Gst.ElementFactory.make("vaapih264enc", "h264enc")
    #log.debug(h264enc)
    log.info("Adding h264enc to bin")
    log.debug(sinkbin.add(h264enc))
    log.info("Linking queue to h264enc")
    log.debug(queue.link(h264enc))

    log.info("Creating h264parse")
    h264parse = Gst.ElementFactory.make("h264parse", "h264parse")
    #log.debug(h264parse)
    log.info("Adding h264parse to bin")
    log.debug(sinkbin.add(h264parse))
    log.info("Linking h264enc to h264parse")
    log.debug(h264enc.link(h264parse))

    log.info("Creating mp4mux")
    mp4mux = Gst.ElementFactory.make("mp4mux", "mp4mux")
    #log.debug(mp4mux)
    log.info("Adding mp4mux to bin")
    log.debug(sinkbin.add(mp4mux))
    log.info("Linking h264parse to mp4mux")
    log.debug(h264parse.link(mp4mux))

    log.info("Creating filesink")
    filesink = Gst.ElementFactory.make("filesink", "filesink")
    filesink.set_property("location", filename)
    filesink.get_static_pad("sink").add_probe(
        Gst.PadProbeType.EVENT_DOWNSTREAM, filesink_eos_cb, sinkbin)

    log.info("Adding filesink to bin")
    log.debug(sinkbin.add(filesink))
    log.info("Linking mp4mux to filesink")
    log.debug(mp4mux.link(filesink))

    log.info("Selecting Input-Pad")
    sink_pad = queue.get_static_pad("sink")
    #log.debug(sink_pad)
    log.info("Creating Ghost-Pad")
    ghost_pad = Gst.GhostPad.new("sink", sink_pad)
    #log.debug(ghost_pad)
    log.info("Adding Ghost-Pad to Bin")
    log.debug(sinkbin.add_pad(ghost_pad))

    sinkbin.set_property("message-forward", True)
    return sinkbin

def add_sinkbin(filename):
    log.info(f"Adding filesink-bin for {filename} to the Pipeline")
    Gst.debug_bin_to_dot_file_with_ts(pipeline, Gst.DebugGraphDetails.ALL, "add_sinkbin_before")

    log.info("Creating filesink-bin")
    sinkbin = create_sinkbin(filename)
    log.info("Created filesink-bin")
    log.debug(sinkbin)

    log.info("Adding sinkbin to pipeline")
    log.debug(pipeline.add(sinkbin))

    log.info("Syncing filesink-bin-State with Parent")
    log.debug(sinkbin.sync_state_with_parent())

    log.info("Linking filesink-bin to tee")
    tee.link(sinkbin)

    Gst.debug_bin_to_dot_file_with_ts(pipeline, Gst.DebugGraphDetails.ALL, "add_sinkbin_after")
    log.info(f"Added filesink-bin for {filename} to the Pipeline")
    log.info("Adding filesink-bin done")

def stop_sinkbin():
    log.info("Stopping filesink-bin")
    Gst.debug_bin_to_dot_file_with_ts(pipeline, Gst.DebugGraphDetails.ALL, "stopping_sinkbin_before")

    log.info("Selecting Bin")
    sinkbin = pipeline.get_by_name("filesink-bin")
    #log.debug(sinkbin)

    log.info("Selecting Ghost-Pad")
    ghostpad = sinkbin.get_static_pad("sink")
    #log.debug(ghostpad)

    log.info("Selecting Tee-Pad (Peer of Ghost-Pad)")
    teepad = ghostpad.get_peer()
    #log.debug(teepad)

    def blocking_pad_probe(pad, info):
        log.info("Unlinking ghostpad")
        log.debug(pad.unlink(ghostpad))
        log.info('Sending EOS to ghostpad')
        log.debug(ghostpad.send_event(Gst.Event.new_eos()))
        return Gst.PadProbeReturn.REMOVE

    log.info("Configuring Blocking Probe on teepad")
    teepad.add_probe(Gst.PadProbeType.BLOCK, blocking_pad_probe)  # (5)

def remove_sinkbin(sinkbin):
    log.info("Chaning sinkbin to NULL state.")
    log.debug(sinkbin.set_state(Gst.State.NULL))
    log.info("Removing sinkbin from Pipeline")
    log.debug(pipeline.remove(sinkbin))

    Gst.debug_bin_to_dot_file_with_ts(pipeline, Gst.DebugGraphDetails.ALL, "remove_sinkbin")
    log.info("Removed sink-bin from Pipeline")

stop_event = Event()

def timed_sequence():
    log.info("Scheduling add_sinkbin")
    if stop_event.wait(5): return
    GLib.idle_add(add_sinkbin, "video_out.mp4") 

    log.info("Scheduling remove_sinkbin")
    if stop_event.wait(5): return
    GLib.idle_add(stop_sinkbin) 

    log.info("Scheduling add_sinkbin")
    if stop_event.wait(5): return
    GLib.idle_add(add_sinkbin, "video_out2.mp4") 

    log.info("Scheduling remove_sinkbin")
    if stop_event.wait(5): return
    GLib.idle_add(stop_sinkbin) 

#t = Thread(target=timed_sequence, name="Sequence")
#t.start()

runner = Runner(pipeline)
runner.run_blocking()

stop_event.set()
#t.join()

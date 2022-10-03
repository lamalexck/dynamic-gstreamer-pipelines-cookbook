#!/usr/bin/env python
import sys
import datetime
import logging
from threading import Thread, Event

from tools.application_init import application_init

from gstgva import VideoFrame

application_init()

from gi.repository import Gst, GLib
from tools.logging_pad_probe import logging_pad_probe
from tools.runner import Runner

VIDEO1='person-bicycle-car-detection.mp4'
log = logging.getLogger("main")

detection_model='models/intel/person-vehicle-bike-detection-2004/FP16/person-vehicle-bike-detection-2004.xml'
detection_proc='models/intel/person-vehicle-bike-detection-2004/person-vehicle-bike-detection-2004.json'

def inspect_buffer(pad, probeinfo, location):
    pts_nanpseconds = probeinfo.get_buffer().pts
    pts_timedelta = datetime.timedelta(microseconds=pts_nanpseconds / 1000)
    buffer = probeinfo.get_buffer()
    frame = VideoFrame(buffer)
    for roi in frame.regions():
        if roi.label() == "vehicle":
            log.debug(f'{roi.label()} detected at {location} PTS = {pts_timedelta}')
        break
    return Gst.PadProbeReturn.OK

log.info("building pipeline")
pipeline_str = f'filesrc location={VIDEO1} ! decodebin ! tee name=tee ! queue ! '
pipeline_str += f'gvadetect model={detection_model} model-proc={detection_proc} device=CPU !' 
pipeline_str += f'identity !'
pipeline_str += f'gvafpscounter ! fakesink sync=false' 

pipeline = Gst.parse_launch(pipeline_str)

pipeline.get_by_name("identity0").get_static_pad("src").add_probe(
    Gst.PadProbeType.BUFFER, inspect_buffer, "identity")

tee = pipeline.get_by_name("tee")

def create_sinkbin(filename):
    log.info(f"Creating filesink bin for file {filename}")
    sinkbin = Gst.Bin.new("filesink-bin")
    #log.debug(sinkbin)

    log.info("Creating queue")
    queue = Gst.ElementFactory.make("queue")  # (3)
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
    #log.debug(filesink)
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

    return sinkbin

def add_filesink(filename):
    log.info("Adding filesink-bin for {filename} to the Pipeline")
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
    log.info("Added filesink-bin for {filename} to the Pipeline")
    log.info("Adding filesink-bin done")

stop_event = Event()

def timed_sequence():
    log.info("Starting Sequence")
    if stop_event.wait(2): return
    GLib.idle_add(add_filesink, "video_out.mp4") 
    log.info("Sequence ended")

t = Thread(target=timed_sequence, name="Sequence")
t.start()

print(f'sys.path = {sys.path}')
runner = Runner(pipeline)
runner.run_blocking()

stop_event.set()
t.join()

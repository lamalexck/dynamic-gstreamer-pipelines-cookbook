#!/usr/bin/env python
import logging

from threading import Thread, Event

from tools.application_init import application_init

application_init()

from gi.repository import Gst, GLib, GObject
from tools.logging_pad_probe import logging_pad_probe
from tools.runner2 import Runner2

log = logging.getLogger("main")

log.info("building pipeline")

caps = Gst.Caps.from_string("video/x-raw")

def create_pipeline(name):
    pipeline = Gst.Pipeline.new()
    src = Gst.ElementFactory.make("videotestsrc", f"src-{name}")
    src.set_property("is-live", True)  
    src.set_property("pattern", "smpte100")
    pipeline.add(src)

    sink = Gst.ElementFactory.make("fpsdisplaysink", f"sink-{name}")
    sink.set_property("text-overlay", False) 
    pipeline.add(sink)
    src.link_filtered(sink, caps)

    src.get_static_pad("src").add_probe(
        Gst.PadProbeType.BUFFER, logging_pad_probe, f"src-{name}-output")

    runner = Runner2(pipeline, name)
    return runner

def main():

    mainloop = GObject.MainLoop()
    pipeline_runner1 = create_pipeline("Pipe1")
    pipeline_runner2 = create_pipeline("Pipe2")
    pipeline_runner1.configure()
    pipeline_runner2.configure()
    pipeline_runner1.set_playing()
    pipeline_runner2.set_playing()

    try:
        mainloop.run()
    except KeyboardInterrupt:
        print('Terminated via Ctrl-C')

    pipeline_runner1.set_null()
    pipeline_runner2.set_null()
    

if __name__ == "__main__":
    main()
    
#stop_event = Event()

"""
def timed_sequence():
    log.info("Starting Sequence")
    if stop_event.wait(2): return
    GLib.idle_add(add_new_src)  # (1)
    log.info("Sequence ended")


t = Thread(target=timed_sequence, name="Sequence")
t.start()
"""
#stop_event.set()
#t.join()

import logging

from gi.repository import Gst#, GObject

log = logging.getLogger('Runner')

class Runner2(object):
    def __init__(self, pipeline, pipeline_name, error_callback=None):
        #self.mainloop = GObject.MainLoop()
        self.pipeline_name = pipeline_name
        self.pipeline = pipeline
        self.error_callback = error_callback or self.quit

        """
    def run_blocking(self):
        self.configure()
        self.set_playing()

        try:
            self.mainloop.run()
        except KeyboardInterrupt:
            print('Terminated via Ctrl-C')
        self.set_null()
        """

    def configure(self):
        log.debug(f'configuring pipeline {self.pipeline_name}')
        bus = self.pipeline.bus

        bus.add_signal_watch()
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::error", self.on_error)
        bus.connect("message::state-changed", self.on_state_change)

    def on_eos(self, _bus, message):
        log.error("EOS from %s %s (at %s)",
                  self.pipeline_name, message.src.name, message.src.get_path_string())
        self.error_callback()

    def on_error(self, _bus, message):
        (error, debug) = message.parse_error()
        log.error("Error from %s %s (at %s)\n%s (%s)",
                  self.pipeline_name, message.src.name, message.src.get_path_string(), error, debug)
        self.error_callback()

    def quit(self):
        """
        log.warning('quitting mainloop')
        self.mainloop.quit()
        """
        self.set_null()
        
    def on_state_change(self, _bus, message):
        old_state, new_state, pending = message.parse_state_changed()
        if message.src == self.pipeline:
            log.info("Pipeline %s: State-Change from %s to %s; pending %s",
                     self.pipeline_name, old_state.value_name, new_state.value_name, pending.value_name)
        else:
            log.debug("Pipeline %s %s: State-Change from %s to %s; pending %s",
                      self.pipeline_name, message.src.name, old_state.value_name, new_state.value_name, pending.value_name)

    def set_playing(self):
        log.info(f'Pipeline {self.pipeline_name} requesting state-change to PLAYING')
        self.pipeline.set_state(Gst.State.PLAYING)

    def set_null(self):
        log.info(f'Piepline {self.pipeline_name} requesting state-change to NULL')
        self.pipeline.set_state(Gst.State.NULL)

#!/usr/bin/env python3
"""
gst_pipeline.py

A standalone GStreamer pipeline launcher with a watchdog for failures.
It is necessary to run this in a separate process to avoid
resource leaks when restarting gst-parse-launch pipelines

To run:
  python gst_pipeline.py <pipeline_string>

To stop from another script, call subprocess.Popen(...), then .terminate().
"""

import sys
import time

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst

GST_WATCHDOG_TIMER_MAX_s = 1.5
GST_WATCHDOG_CHECK_PERIOD_ms = 250


class GstPipeline:
    """
    Run GStreamer pipeline in a dedicated process.
    (In this file, we actually run in 'main'; but conceptually,
    we isolate all pipeline code here.)
    """

    def __init__(self, gst_command):
        self.gst_command = gst_command
        self.enabled = False
        self.last_buffer_time = None

        self.loop = None
        self.pipeline = None
        self.bus = None

    def run(self):
        """
        Set up GStreamer and the main loop, then block until loop.quit() is called
        or the process is terminated.
        """

        Gst.init(None)

        # Primarily for watchdog
        self.loop = GLib.MainLoop()

        self._launch_pipeline()
        try:
            self.loop.run()
        except KeyboardInterrupt:
            pass
        finally:
            self._teardown()

    def _launch_pipeline(self):
        """
        Setup and start the GStreamer pipeline. Equivalent to your old 'camPreview'.
        """
        self.enabled = True

        self.pipeline = Gst.parse_launch(self.gst_command)

        identity_element = self.pipeline.get_by_name("id")
        if identity_element:
            identity_element.connect("handoff", self._on_buffer_handoff)

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._on_message)

        self.pipeline.set_state(Gst.State.PLAYING)

        GLib.timeout_add(
            int(GST_WATCHDOG_TIMER_MAX_s * 1000), self._watchdog_timer_check
        )

    def _on_buffer_handoff(self, _element, _buffer):
        """Called each time a buffer passes through the named 'identity'."""
        self.last_buffer_time = time.monotonic()
        return Gst.FlowReturn.OK

    def _pipeline_teardown(self):
        """Stop the pipeline and free resources."""
        # Perform valid state transitions:
        # https://gstreamer.freedesktop.org/documentation/additional/design/states.html?gi-language=python
        if self.pipeline is not None:
            self.pipeline.set_state(Gst.State.PAUSED)
            self.pipeline.set_state(Gst.State.READY)
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None

    def _watchdog_timer_check(self):
        """
        Periodically checks if the pipeline has 'frozen' by not producing buffers.
        If stuck, restarts the pipeline.
        """
        if not self.enabled:
            return False  # Stop scheduling

        if self.last_buffer_time is None:
            # Haven't received a buffer yet, keep waiting
            return True

        elapsed = time.monotonic() - self.last_buffer_time
        if elapsed > GST_WATCHDOG_TIMER_MAX_s:
            print("[GstPipeline] Watchdog triggered, restarting pipeline.")
            self.last_buffer_time = None
            self._pipeline_teardown()
            self._launch_pipeline()
            return False  # We'll re-add the timeout in _cam_preview
        return True

    def _on_message(self, bus, message):
        """
        Handles GStreamer bus messages (ERROR, EOS, etc.).
        If an error/EOS occurs, we stop the loop.
        """
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"[GstPipeline] ERROR: {err}, debug={debug}")
            self._stop_loop()
        elif message.type == Gst.MessageType.EOS:
            print("[GstPipeline] EOS reached, stopping loop.")
            self._stop_loop()

    def _stop_loop(self):
        """Quit the GLib main loop"""
        if self.loop is not None:
            self.loop.quit()

    def _teardown(self):
        """Stop the gst pipeline and free resources."""
        self._pipeline_teardown()
        self.enabled = False
        self.last_buffer_time = None
        self._stop_loop()
        print("[GstPipeline] Pipeline set to NULL (child).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gst_pipeline.py <pipeline_string>")
        sys.exit(1)
    pipeline_cmd = sys.argv[1]

    pipeline = GstPipeline(pipeline_cmd)
    pipeline.run()

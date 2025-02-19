#!/usr/bin/env python3

import math
import os
import re
import subprocess
import threading
import time

import gi

from vai.common import (
    APP_HEADER,
    TRIA,
    TRIA_BLUE_RGBH,
    TRIA_PINK_RGBH,
    TRIA_YELLOW_RGBH,
)
from vai.handler import Handler

# os.environ["XDG_RUNTIME_DIR"] = "/dev/socket/weston"
# os.environ["WAYLAND_DISPLAY"] = "wayland-1"
# os.environ["GDK_BACKEND"] = "wayland"
# os.environ["LC_ALL"] = "en.utf-8"

# os.environ["QMONITOR_BACKEND_LIB_PATH"] = "/var/QualcommProfiler/libs/backends/"
# os.environ["LD_LIBRARY_PATH"] = "$LD_LIBRARY_PATH:/var/QualcommProfiler/libs/"
# os.environ["PATH"] = "$PATH:/data/shared/QualcommProfiler/bins"

# Locks app version, prevents warnings
gi.require_version("Gdk", "3.0")
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gst, Gtk

GRAPH_COLORS_RGBF = [
    tuple(c / 255.0 for c in TRIA_PINK_RGBH),
    tuple(c / 255.0 for c in TRIA_BLUE_RGBH),
    tuple(c / 255.0 for c in TRIA_YELLOW_RGBH),
]

GladeBuilder = Gtk.Builder()
APP_FOLDER = os.path.dirname(__file__)
RESOURCE_FOLDER = os.path.join(APP_FOLDER, "resources")
LAYOUT_PATH = os.path.join(RESOURCE_FOLDER, "GSTLauncher.glade")


def index_containing_substring(the_list, substring):
    for i, s in enumerate(the_list):
        if substring in s:
            return i
    return -1


class QProfProcess(threading.Thread):
    def __init__(self):
        self.enabled = True
        self.CPU = 0
        self.GPU = 0
        self.MEM = 0
        threading.Thread.__init__(self)

    def run(self):
        ansi_escape_8bit = re.compile(
            rb"(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])"
        )
        while self.enabled:
            try:
                p = subprocess.Popen(
                    "qprof \
                                        --profile \
                                        --profile-type async \
                                        --result-format CSV \
                                        --capabilities-list profiler:apps-proc-cpu-metrics profiler:proc-gpu-specific-metrics profiler:apps-proc-mem-metrics \
                                        --profile-time 10 \
                                        --sampling-rate 50 \
                                        --streaming-rate 500 \
                                        --live \
                                        --metric-id-list 4648 4616 4865".split(),
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except:
                self.enabled = False
                pass

            while self.enabled:
                # line = p.stdout.readline().decode('utf-8').encode("ascii","ignore")
                line = p.stdout.readline().decode("utf-8").encode("ascii", "ignore")

                line = ansi_escape_8bit.sub(b"", line)
                if not line:
                    break
                # the real code does filtering here

                if line.find(b"CPU Total Load:") > -1:
                    result = re.search(b"CPU Total Load:(.*)%", line)
                    self.CPU = float(result.group(1))
                    # print ('CPU Usage', self.CPU, '%')
                elif line.find(b"GPU Utilization:") > -1:
                    result = re.search(b"GPU Utilization:(.*)%", line)
                    self.GPU = float(result.group(1))
                    # print ('GPU Usage', self.GPU, '%')
                elif line.find(b"Memory Usage %:") > -1:
                    result = re.search(b"Memory Usage %:(.*)%", line)
                    self.MEM = float(result.group(1))
                    # print ('MEM Usage', self.MEM, '%')

            # cleanup output files
            subprocess.call(
                "/bin/rm -rf /data/shared/QualcommProfiler/profilingresults/*",
                shell=True,
            )

    def Close(self):
        self.enabled = False

    def GetCPU(self):
        return round(self.CPU, 2)

    def GetGPU(self):
        return round(self.GPU, 2)

    def GetMEM(self):
        return round(self.MEM, 2)


class Video:
    def __init__(self, port=7001):
        Gst.init(None)

        self.eventHandler = Handler()
        self.running = True

        self.localAppThread = threading.Thread(target=self.localApp)
        self.localAppThread.start()

    def on_graph_draw(self, widget, cr):
        """Draw three out-of-phase sine waves + legend (top-right) using Cairo"""
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # --- Draw graph container ---
        cr.set_source_rgba(0.1, 0.1, 0.1, 0.15)  # Transparent gray container fill
        cr.rectangle(0, 0, width, height)
        cr.fill_preserve()
        cr.set_source_rgb(0.5, 0.5, 0.5)  # Gray border
        cr.set_line_width(2)
        cr.stroke()

        # --- Draw line graph ---
        cr.set_line_width(2)
        for i in range(3):
            cr.set_source_rgb(*GRAPH_COLORS_RGBF[i])
            cr.move_to(0, height // 2 + (self.graph_data[i][0]*height/100))
            for x in range(1, len(self.graph_data[i])):
                cr.line_to(x, height // 2 + (self.graph_data[i][x]*height/100))
            cr.stroke()

        # --- Draw Legend ---
        legend_margin_x = 20  # Distance from the right edge
        legend_margin_y = 10  # Distance from the top edge
        box_size = 20  # Size of the color box
        spacing = 30  # Vertical spacing between entries

        # TODO: Scale by res?
        cr.select_font_face("Sans", 0, 1)  # Bold weight & normal slant
        cr.set_font_size(20)

        wave_labels = ["CPU %", "LPDDR5 %", "GPU %"]  # Labels for each wave
        for i, label in enumerate(wave_labels):
            item_y = legend_margin_y + i * spacing

            # Tuning offset variable
            # TODO: scale with res
            text_guess_width = 90
            legend_x = width - legend_margin_x - (text_guess_width + box_size + 10)

            # Draw color box
            cr.set_source_rgb(*GRAPH_COLORS_RGBF[i])
            cr.rectangle(legend_x, item_y, box_size, box_size)
            cr.fill()

            # Draw label text in white
            cr.set_source_rgb(1, 1, 1)
            text_x = legend_x + box_size + 10
            text_y = (
                item_y + box_size - 5
            )  # Shift text slightly so it's vertically centered
            cr.move_to(text_x, text_y)
            cr.show_text(label)

    def update_graph(self):
        """Update the graph values for real-time rendering"""
        elapsed = time.time()

        # For each wave, pop the oldest sample and append a new one
        for i in range(3):
            self.graph_data[i].pop(0)
            # Eachwave has a different phase
            new_value = int(30 * math.sin(elapsed * 2 + self.phases[i]))
            self.graph_data[i].append(new_value)

        # Request a redraw
        self.eventHandler.GraphDrawArea.queue_draw()
        return True

    def localApp(self):
        global GladeBuilder

        GladeBuilder.add_from_file(LAYOUT_PATH)
        GladeBuilder.connect_signals(self.eventHandler)

        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_path(os.path.join(RESOURCE_FOLDER, "app.css"))
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.eventHandler.MainWindow = GladeBuilder.get_object("mainWindow")
        self.eventHandler.MainWindow.connect("destroy", self.eventHandler.exit)
        self.eventHandler.aboutWindow = GladeBuilder.get_object("aboutWindow")
        self.eventHandler.FPSRate0 = GladeBuilder.get_object("FPS_rate_0")
        self.eventHandler.FPSRate1 = GladeBuilder.get_object("FPS_rate_1")
        self.eventHandler.CPU_load = GladeBuilder.get_object("CPU_load")
        self.eventHandler.GPU_load = GladeBuilder.get_object("GPU_load")
        self.eventHandler.MEM_load = GladeBuilder.get_object("MEM_load")
        self.eventHandler.CPU_temp = GladeBuilder.get_object("CPU_temp")
        self.eventHandler.GPU_temp = GladeBuilder.get_object("GPU_temp")
        self.eventHandler.MEM_temp = GladeBuilder.get_object("MEM_temp")
        self.eventHandler.TopBox = GladeBuilder.get_object("TopBox")
        self.eventHandler.DataGrid = GladeBuilder.get_object("DataGrid")
        self.eventHandler.BottomBox = GladeBuilder.get_object("BottomBox")
        self.eventHandler.DrawArea1 = GladeBuilder.get_object("DrawArea1")
        self.eventHandler.DrawArea2 = GladeBuilder.get_object("DrawArea2")
        self.eventHandler.GraphDrawArea = GladeBuilder.get_object("GraphDrawArea")
        # TODO: Dynamic sizing, positioning
        self.eventHandler.GraphDrawArea.connect("draw", self.on_graph_draw)
        # TODO: replace with real perf data
        # Maybe keep canned generation for situations that perf depends arent available
        # TODO: Remove this tuning variable and determine a good fixed-data size for graphs that scales to reasonable resolutions
        self.graph_data = [[0] * int(1920 * 0.925) for _ in range(3)]
        self.phases = [0, math.pi / 3, 2 * math.pi / 3]
        GLib.timeout_add(16, self.update_graph)  # Calls update_graph() every 16ms

        self.eventHandler.QProf = QProfProcess()

        # TODO: Can just put these in CSS
        self.eventHandler.MainWindow.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(23 / 255, 23 / 255, 23 / 255, 0)
        )
        self.eventHandler.TopBox.override_background_color(
            Gtk.StateType.NORMAL, Gdk.RGBA(23 / 255, 23 / 255, 23 / 255, 0.5)
        )

        self.eventHandler.BottomBox.override_background_color(
            Gtk.StateType.NORMAL, Gdk.RGBA(23 / 255, 23 / 255, 23 / 255, 0.5)
        )

        self.eventHandler.MainWindow.set_decorated(False)
        self.eventHandler.MainWindow.set_keep_below(True)
        self.eventHandler.MainWindow.maximize()
        self.eventHandler.MainWindow.show_all()

        self.eventHandler.QProf.start()

        Gtk.main()


if __name__ == "__main__":
    print(TRIA)
    print(f"\nLaunching {APP_HEADER}")
    # Create the video object
    # Add port= if is necessary to use a different one
    video = Video()

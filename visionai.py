#!/usr/bin/env python3

import os
import re
import subprocess
import threading
from time import sleep

import gi

from vai.cam import camThread
from vai.common import APP_HEADER, TRIA
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
from gi.repository import Gdk, Gst, Gtk

GladeBuilder = Gtk.Builder()
APP_FOLDER = os.path.dirname(__file__)
RESOURCE_FOLDER = os.path.join(APP_FOLDER, "resources")
LAYOUT_PATH = os.path.join(RESOURCE_FOLDER, "GSTLauncher.glade")

# camera = "gst-launch-1.0 qtiqmmfsrc name=camsrc  ! video/x-raw,format=NV12 ! videoconvert ! video/x-raw,format=BGRA ,width=640,height=480,framerate=30/1 ! appsink drop=1"

# pose_detection = "gst-launch-1.0 \
# camera=x ! video/x-raw\(memory:GBM\),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc ! queue ! tee name=split \
# split. ! queue ! qtivcomposer name=mixer ! videoconvert ! video/x-raw,format=BGRA ! appsink drop=1 \
# split. ! queue ! qtimlvconverter ! queue ! qtimltflite delegate=external external-delegate-path=libQnnTFLiteDelegate.so external-delegate-options=QNNExternalDelegate,backend_type=htp; \
# model=/opt/posenet_mobilenet_v1.tflite ! queue ! qtimlvpose threshold=51.0 results=2 module=posenet labels=/opt/posenet_mobilenet_v1.labels \
# constants=Posenet,q-offsets=<128.0,128.0,117.0>,q-scales=<0.0784313753247261,0.0784313753247261,1.3875764608383179>; ! video/x-raw,format=BGRA,width=640,height=360 ! queue ! mixer."


# gst-launch-1.0 qtiqmmfsrc name=camsrc ! "video/x-raw, width=640, height=480, framerate=(fraction)30/1" ! fpsdisplaysink sync=false video-sink="autovideosink" -v


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

        self.eventHandler.demoProcess0 = camThread(self.eventHandler.getCommand(4, 0))
        self.eventHandler.demoProcess1 = camThread(self.eventHandler.getCommand(1, 1))
        self.eventHandler.QProf = QProfProcess()

        self.eventHandler.MainWindow.fullscreen()
        self.eventHandler.MainWindow.show_all()

        self.eventHandler.demoProcess0.start()
        while self.eventHandler.demoProcess0.FrameOk == False:
            sleep(0.1)

        # self.eventHandler.demoProcess1.start()
        # while self.eventHandler.demoProcess1.FrameOk == False:
        #    sleep(0.1)

        # self.eventHandler.QProf.start()

        Gtk.main()


if __name__ == "__main__":
    print(TRIA)
    print(f"\nLaunching {APP_HEADER}")
    # Create the video object
    # Add port= if is necessary to use a different one
    video = Video()

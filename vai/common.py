"""Common utilities and constants for VAI demo"""

import subprocess

GRAPH_SAMPLE_WINDOW_SIZE_s = 16
HW_SAMPLING_PERIOD_ms = 250

CPU_UTIL_KEY = "cpu %"
MEM_UTIL_KEY = "lpddr5 %"
GPU_UTIL_KEY = "gpu %"
CPU_THERMAL_KEY = "cpu temp (°c)"
MEM_THERMAL_KEY = "lpddr5 temp (°c)"
GPU_THERMAL_KEY = "gpu temp (°c)"
TIME_KEY = "time"

TRIA_PINK_RGBH = (0xFE, 0x00, 0xA2)
TRIA_BLUE_RGBH = (0x00, 0x19, 0x4F)
TRIA_WHITE_RGBH = (0xFF, 0xFF, 0xFF)
TRIA_YELLOW_RGBH = (0xFE, 0xDB, 0x00)

# WARN: These commands will be processed by application. Tags like <TAG> are likely placeholder

# Having one default is fine, as we can extrapolate for the other window
DEFAULT_LEFT_WINDOW = "waylandsink async=true sync=false <ONE_WINDOW_XYWH>"
DEFAULT_DUAL_WINDOW = "waylandsink async=true sync=false <DUAL_WINDOW_XYWH>"

# TODO: add FPS support for camera
# TODO: What is the most reasonable res?
CAMERA = f"<DATA_SRC> ! qtivtransform ! video/x-raw(memory:GBM),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc ! {DEFAULT_LEFT_WINDOW}"

POSE_DETECTION = "<DATA_SRC> ! qtivtransform ! video/x-raw(memory:GBM),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc ! tee name=split \
split. ! queue ! qtivcomposer name=mixer ! <SINGLE_DISPLAY> \
split. ! queue ! qtimlvconverter ! qtimltflite delegate=external external-delegate-path=libQnnTFLiteDelegate.so external-delegate-options=QNNExternalDelegate,backend_type=htp; \
model=/opt/posenet_mobilenet_v1.tflite ! qtimlvpose threshold=51.0 results=2 module=posenet labels=/opt/posenet_mobilenet_v1.labels \
constants=Posenet,q-offsets=<128.0,128.0,117.0>,q-scales=<0.0784313753247261,0.0784313753247261,1.3875764608383179>; ! video/x-raw,format=BGRA,width=640,height=480 ! mixer."

SEGMENTATION = "<DATA_SRC> ! qtivtransform ! video/x-raw(memory:GBM),format=NV12,width=640,height=360,framerate=30/1,compression=ubwc ! tee name=split \
split. ! queue ! qtivcomposer name=mixer sink_1::alpha=0.5 ! queue ! <SINGLE_DISPLAY> \
split. ! queue ! qtimlvconverter ! queue ! qtimltflite delegate=external external-delegate-path=libQnnTFLiteDelegate.so external-delegate-options=QNNExternalDelegate,backend_type=htp; \
model=/opt/deeplabv3_resnet50.tflite ! queue ! qtimlvsegmentation module=deeplab-argmax labels=/opt/deeplabv3_resnet50.labels ! video/x-raw,width=256,height=144 ! queue ! mixer."

CLASSIFICATION = '<DATA_SRC> ! qtivtransform ! video/x-raw(memory:GBM),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc !queue ! tee name=split \
split. ! queue ! qtivcomposer name=mixer sink_1::position="<30,30>" sink_1::dimensions="<320, 180>" ! queue ! <SINGLE_DISPLAY> \
split. ! queue ! qtimlvconverter ! queue ! qtimlsnpe delegate=dsp model=/opt/inceptionv3.dlc ! queue ! qtimlvclassification threshold=40.0 results=2 \
module=mobilenet labels=/opt/classification.labels ! video/x-raw,format=BGRA,width=640,height=360 ! queue ! mixer.'

OBJECT_DETECTION = '<DATA_SRC> ! qtivtransform ! video/x-raw(memory:GBM),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc !queue ! tee name=split \
split. ! queue ! qtivcomposer name=mixer1 ! queue ! <SINGLE_DISPLAY> \
split. ! queue ! qtimlvconverter ! queue ! qtimlsnpe delegate=dsp model=/opt/yolonas.dlc layers="</heads/Mul, /heads/Sigmoid>" ! queue ! qtimlvdetection threshold=51.0 results=10 module=yolo-nas labels=/opt/yolonas.labels \
! video/x-raw,format=BGRA,width=640,height=480 ! queue ! mixer1.'

# TODO: find suitable way to dynamically adjust sink dimensions
# Keep in mind, the sink dimensions are relative to the later sink (waylandsink) in some capacity
# If the waylandsink is automated to scale with monitor resolution, we may need to adjust the sink dimensions accordingly
DEPTH_SEGMENTATION = "<DATA_SRC> ! qtivtransform ! \
    video/x-raw(memory:GBM),format=NV12,width=1920,height=1080,framerate=30/1,compression=ubwc ! \
    tee name=split \
    split. ! queue ! qtivcomposer background=0 name=dual \
        sink_0::position=<0,0> sink_0::dimensions=<960,720> \
        sink_1::position=<960,0> sink_1::dimensions=<960,720> \
    ! queue ! <DUAL_DISPLAY> \
    split. ! queue ! qtimlvconverter ! queue ! \
        qtimltflite delegate=external \
            external-delegate-path=libQnnTFLiteDelegate.so \
            external-delegate-options=QNNExternalDelegate,backend_type=htp \
            model=/opt/Midas-V2-Quantized.tflite ! queue ! \
        qtimlvsegmentation module=midas-v2 labels=/opt/monodepth.labels \
            constants=Midas,q-offsets=<0.0>,q-scales=<4.716535568237305>; ! \
        video/x-raw,width=960,height=720 ! queue ! dual.sink_1"


APP_NAME = f"QCS6490 Vision AI"

TRIA = r"""
████████╗██████╗ ██╗ █████╗ 
╚══██╔══╝██╔══██╗██║██╔══██╗
   ██║   ██████╔╝██║███████║
   ██║   ██╔══██╗██║██╔══██║
   ██║   ██║  ██║██║██║  ██║
   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
"""


def app_version():
    """Get the latest tag or commit hash if possible, unknown otherwise"""

    try:
        version = subprocess.check_output(
            ["git", "describe", "--tags", "--always"], text=True
        ).strip()
        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=short"], text=True
        ).strip()

        return f"{version} {date}"
    except subprocess.CalledProcessError:
        # Handle errors, such as not being in a Git repository
        return "unknown"


APP_HEADER = f"{APP_NAME} v({app_version()})"

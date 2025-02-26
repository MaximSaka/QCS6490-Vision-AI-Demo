"""Common utilities and constants for VAI demo"""

import subprocess

GRAPH_SAMPLE_WINDOW_SIZE_s = 15
HW_SAMPLING_PERIOD_ms = 250
GRAPH_DRAW_PERIOD_ms = 30

# TODO: relate this with qprof rate
GRAPH_SAMPLE_SIZE = int(GRAPH_SAMPLE_WINDOW_SIZE_s * 1000 / GRAPH_DRAW_PERIOD_ms)

CPU_UTIL_KEY = "cpu %"
MEM_UTIL_KEY = "lpddr5 %"
GPU_UTIL_KEY = "gpu %"
CPU_THERMAL_KEY = "cpu temp (°c)"
MEM_THERMAL_KEY = "lpddr5 temp (°c)"
GPU_THERMAL_KEY = "gpu temp (°c)"

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


#AI-HUB models

GOOGLENET_CLASSIFFICATION ="<DATA_SRC> ! \
    qtivtransform ! \
    video/x-raw(memory:GBM),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc ! \
    queue ! tee name=split \
    split. ! queue ! \
    qtivcomposer name=mixer ! \
    queue ! <SINGLE_DISPLAY> \
    split. ! queue ! \
    qtimlvconverter ! \
    queue ! \
    qtimltflite \
        delegate=external \
        external-delegate-path=libQnnTFLiteDelegate.so \
        external-delegate-options=QNNExternalDelegate,backend_type=htp \
        model=/opt/googlenet_quantized.tflite ! \
    queue ! \
    qtimlvclassification \
        threshold=51.0 \
        results=5 \
        module=mobilenet \
        labels=/opt/imagenet_labels.txt \
        extra-operation=softmax \
        constants=Mobilenet,q-offsets=<53.0>,q-scales=<0.08174873143434525> ! \
    video/x-raw,format=BGRA,width=640,height=480 ! \
    queue ! mixer."

HRH_POSE_ESTIMATION ='<DATA_SRC> ! qtivtransform ! \
video/x-raw(memory:GBM),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc ! queue ! tee name=split \
split. ! queue ! qtivcomposer name=mixer ! queue ! <SINGLE_DISPLAY> \
split. ! queue ! qtimlvconverter ! queue ! qtimltflite delegate=external external-delegate-path=libQnnTFLiteDelegate.so external-delegate-options=QNNExternalDelegate,backend_type=htp \
model=/opt/GA1.3-rel/hrnet_pose_quantized.tflite ! queue ! qtimlvpose threshold=51 module=hrnet \
labels=/opt/GA1.3-rel/hrnet_pose.labels constants="hrnet,q-offsets=<8.0>,q-scales=<0.0040499246679246426>" ! video/x-raw,format=BGRA,width=640,height=480 ! \
queue ! mixer.'

SUPER_RESOLUTION = '<DATA_SRC> ! qtivtransform ! video/x-raw(memory:GBM),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc ! tee name=split \
split. ! queue ! qtivcomposer name=mixer ! <SINGLE_DISPLAY> \
split. ! qtimlvconverter ! queue ! qtimltflite delegate=external external-delegate-path=libQnnTFLiteDelegate.so \
external-delegate-options="QNNExternalDelegate,backend_type=htp;" model=/opt/GA1.3-rel/quicksrnetsmall_quantized.tflite ! \
queue ! qtimlvsuperresolution module=srnet constants="qsrnetsmall,q-offsets=<0.0>,q-scales=<1.0>;" ! \
video/x-raw(memory:GBM),format=RGB ! queue ! mixer.'

SEGMENTATION_AUTOMOTIVE = '<DATA_SRC> ! qtivtransform ! video/x-raw(memory:GBM),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc !queue ! tee name=split \
split. ! queue ! qtivcomposer name=mixer ! queue ! <SINGLE_DISPLAY> \
split. ! queue ! qtimlvconverter ! queue ! qtimltflite delegate=external external-delegate-path=libQnnTFLiteDelegate.so \
external-delegate-options=QNNExternalDelegate,backend_type=htp model=/opt/ffnet_40s_quantized_aihub.tflite ! queue ! \
qtimlvsegmentation module=deeplab-argmax labels=/opt/voc_labels.txt constants=ffnet,q-offsets=<178.0>,q-scales=<0.2929433584213257> ! \
video/x-raw,format=BGRA,width=640,height=480 ! queue ! mixer.'

SEGMENTATION_HTP = '<DATA_SRC> ! qtivtransform ! video/x-raw(memory:GBM),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc !queue ! tee name=split \
split. ! queue ! qtivcomposer name=mixer ! queue ! <SINGLE_DISPLAY> \
split. ! queue ! \
  qtimlvconverter ! queue ! \
  qtimltflite \
      delegate=external \
      external-delegate-path=libQnnTFLiteDelegate.so \
      external-delegate-options="QNNExternalDelegate,backend_type=htp" \
      model=/opt/deeplabv3_plus_mobilenet_quantized_aihub.tflite ! queue ! \
  qtimlvsegmentation \
      module=deeplab-argmax \
      labels=/opt/voc_labels.txt \
      constants="deeplab,q-offsets=<0.0>,q-scales=<1.0>" ! \
  video/x-raw,format=BGRA,width=640,height=480 ! \
  queue ! mixer.'


APP_NAME = f"QCS6490 Vision AI"

TRIA = r"""
████████╗██████╗ ██╗ █████╗ 
╚══██╔══╝██╔══██╗██║██╔══██╗
   ██║   ██████╔╝██║███████║
   ██║   ██╔══██╗██║██╔══██║
   ██║   ██║  ██║██║██║  ██║
   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
"""


def lerp(a, b, t):
    """Linear interpolation between two values"""
    return a + t * (b - a)


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

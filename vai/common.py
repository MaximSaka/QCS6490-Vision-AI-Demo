import subprocess

CAMERA = "gst-launch-1.0 camera=x ! videoconvert ! videoscale ! video/x-raw, width=640, height=480, framerate=30/1 ! appsink drop=1"

POSE_DETECTION = "gst-launch-1.0 \
camera=x ! qtivtransform ! video/x-raw\(memory:GBM\),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc ! \
tee name=split \
split. ! queue ! qtivcomposer name=mixer ! videoconvert ! video/x-raw,format=BGRA ! appsink drop=1 \
split. ! queue ! qtimlvconverter ! qtimltflite delegate=external external-delegate-path=libQnnTFLiteDelegate.so external-delegate-options=QNNExternalDelegate,backend_type=htp; \
model=/opt/posenet_mobilenet_v1.tflite ! qtimlvpose threshold=51.0 results=2 module=posenet labels=/opt/posenet_mobilenet_v1.labels \
constants=Posenet,q-offsets=<128.0,128.0,117.0>,q-scales=<0.0784313753247261,0.0784313753247261,1.3875764608383179>; ! video/x-raw,format=BGRA,width=640,height=360 ! queue ! mixer."

SEGMENTATION = "gst-launch-1.0 \
camera=x ! video/x-raw\(memory:GBM\),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc ! queue ! tee name=split \
split. ! queue ! qtivcomposer name=mixer sink_1::alpha=0.5 ! queue ! videoconvert ! video/x-raw,format=BGRA ! appsink drop=1 \
split. ! queue ! qtimlvconverter ! queue ! qtimltflite delegate=external external-delegate-path=libQnnTFLiteDelegate.so external-delegate-options=QNNExternalDelegate,backend_type=htp; \
model=/opt/deeplabv3_resnet50.tflite ! queue ! qtimlvsegmentation module=deeplab-argmax labels=/opt/deeplabv3_resnet50.labels ! video/x-raw,width=256,height=144 ! queue ! mixer."

CLASSIFICATION_1 = "gst-launch-1.0 \
camera=x ! video/x-raw\(memory:GBM\),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc !queue ! tee name=split \
split. ! queue ! qtivcomposer name=mixer1 ! queue ! videoconvert ! video/x-raw,format=BGRA ! appsink drop=1 \
split. ! queue ! qtimlvconverter ! queue ! qtimlsnpe delegate=dsp model=/opt/inceptionv3.dlc ! queue ! qtimlvclassification threshold=40.0 results=2 module=mobilenet labels=/opt/classification.labels \
! video/x-raw,format=BGRA,width=640,height=480 ! queue ! mixer1."

CLASSIFICATION = "output.mp4"

"""
CLASSIFICATION = 'gst-launch-1.0 \
filesrc location=output.mp4 ! decodebin ! videoconvert ! video/x-raw,format=NV12,width=640,height=480,framerate=30/1 ! queue ! tee name=split \
split. ! queue ! qtivcomposer name=mixer sink_1::position="<30,30>" sink_1::dimensions="<320, 180>" ! queue ! videoconvert ! video/x-raw,format=BGRA ! appsink drop=1 \
split. ! queue ! qtimlvconverter ! queue ! qtimlsnpe delegate=dsp model=/opt/inceptionv3.dlc ! queue ! qtimlvclassification threshold=40.0 results=2 \
module=mobilenet labels=/opt/classification.labels ! video/x-raw,format=BGRA,width=640,height=360 ! queue ! mixer.'
"""

OBJECT_DETECTION = 'gst-launch-1.0 \
camera=x ! video/x-raw\(memory:GBM\),format=NV12,width=640,height=480,framerate=30/1,compression=ubwc !queue ! tee name=split \
split. ! queue ! qtivcomposer name=mixer1 ! queue ! videoconvert ! video/x-raw,format=BGRA ! appsink drop=1 \
split. ! queue ! qtimlvconverter ! queue ! qtimlsnpe delegate=dsp model=/opt/yolonas.dlc layers="</heads/Mul, /heads/Sigmoid>" ! queue ! qtimlvdetection threshold=51.0 results=10 module=yolo-nas labels=/opt/yolonas.labels \
! video/x-raw,format=BGRA,width=640,height=360 ! queue ! mixer1.'


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

        return version
    except subprocess.CalledProcessError:
        # Handle errors, such as not being in a Git repository
        return "unknown"


APP_HEADER = f"{APP_NAME} v({app_version()})"

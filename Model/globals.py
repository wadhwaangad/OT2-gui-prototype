from typing import Dict
from Model.camera import MultiprocessVideoCapture, frameOperations
from typing import Dict
robot_api=None
robot_initialized=False
get_run_info=False
calibration_frame=None
# Labware-related global variables
active_cameras: Dict[str, MultiprocessVideoCapture] = {}
custom_labware = False
protocol_labware = []
current_run_info = {}
deck_layout = {
    "slot_1": None,
    "slot_2": None,
    "slot_3": None,
    "slot_4": None,
    "slot_5": None,
    "slot_6": None,
    "slot_7": None,
    "slot_8": None,
    "slot_9": None,
    "slot_10": None,
    "slot_11": None,
    "slot_12": None
}
calibration_active = False
robot_coords = []
camera_coords = []
tip_calibration_frame = None
calibration_profile= "checkerboard"
if "HD USB CAMERA" in active_cameras and active_cameras["HD USB CAMERA"] is not None:
    frame_ops = frameOperations(*active_cameras["HD USB CAMERA"].shape[0:-1])
else:
    frame_ops = None
default_focus = 900
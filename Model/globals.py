from typing import Dict
from Model.camera import ThreadSafeVideoCapture, frameOperations
from typing import Dict
from PyQt6.QtCore import QMutex
import threading
robot_api=None
robot_initialized=False
get_run_info=False
calibration_frame=None
# Thread-safe camera management
_camera_mutex = QMutex()
active_cameras: Dict[str, ThreadSafeVideoCapture] = {}
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
cuboid_picking_frame = None  # Frame with annotations from the tissue picker FSM process - updated in real-time during picking
calibration_profile= "checkerboard"
frame_ops = frameOperations(2048,1536)
frame_ops.load_camera_intrinsics(config_profile=calibration_profile, use_new_cam_mtx=True)
default_focus = 900
OverviewCameraName = "overview_cam_2"  # User label for overview camera
UnderviewCameraName = "underview_cam" # User label for underview camera
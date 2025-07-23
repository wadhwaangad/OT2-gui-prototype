from typing import Dict
from Model.camera import MultiprocessVideoCapture
from typing import Dict
robot_api=None
robot_initialized=False
get_run_info=False
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
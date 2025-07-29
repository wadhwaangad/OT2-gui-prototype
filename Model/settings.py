"""
Settings model for the microtissue manipulator GUI.
Contains backend functions for robot control and settings management.
"""

from concurrent.futures import thread
import json
import os
from typing import Dict, Any, Optional
import numpy as np
import cv2
from Model.ot2_api import OpentronsAPI 
from PyQt6.QtCore import QThread
from Model.worker import Worker
import Model.globals as globals
import Model.utils as utils
from Model.manual_movement import ManualMovementModel
class SettingsModel:
    """Model for handling settings and robot control operations."""
    
    def __init__(self):
        self.lights_on = False
        self.active_threads=[]

    def run_in_thread(self, fn, *args, on_result=None, on_error=None, on_finished=None, **kwargs):
        """Run a function in a separate thread using Worker."""
        thread = QThread()
        worker = Worker(fn, *args, **kwargs)
        worker.moveToThread(thread)

        if on_result:
            worker.result.connect(on_result)
        if on_error:
            worker.error.connect(on_error)
        if on_finished:
            worker.finished.connect(on_finished)

        def cleanup():
            if thread in self.active_threads:
                self.active_threads.remove(thread)
            thread.quit()
            thread.wait()  # Wait for thread to finish
            worker.deleteLater()
            thread.deleteLater()

        worker.finished.connect(cleanup)
        thread.started.connect(worker.run)

        self.active_threads.append(thread)
        thread.start()
        return thread
    
    # Robot control functions (placeholder implementations)
    
    def initialize_robot(self) -> bool:
        """Initialize the robot connection."""
        try:
            globals.robot_api = OpentronsAPI()  # Use the global Opentrons API instance
            print("Initializing robot...")
            # Simulate initialization
            globals.robot_initialized = True
            return True
        except Exception as e:
            print(f"Error initializing robot: {e}")
            return False

    def add_slot_offsets(self, slots: list[int], x: float, y: float, z: float) -> bool:
        """Add slot offsets to the robot configuration."""
        try:
            if not globals.robot_api:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.add_slot_offsets(slots,(x, y, z))
            return True
        except Exception as e:
            print(f"Error adding slot offsets: {e}")
            return False
    
    def toggle_lights(self) -> bool:
        """Toggle the robot lights on/off."""
        try:
            if not globals.robot_api:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.toggle_lights()
            self.lights_on = not self.lights_on
            print(f"Lights {'ON' if self.lights_on else 'OFF'}")
            return True
        except Exception as e:
            print(f"Error toggling lights: {e}")
            return False
    
    def home_robot(self) -> bool:
        """Home the robot to its reference position."""
        try:
            if not globals.robot_api:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.home_robot()
            print("Homing robot...")
            return True
        except Exception as e:
            print(f"Error homing robot: {e}")
            return False
    
    def get_run_info(self) -> Dict[str, Any]:
        """Get current run information."""
        try:
            if not globals.robot_api:
                print("Robot not initialized. Please initialize first.")
                return {}
            globals.current_run_info = globals.robot_api.get_run_info()
            globals.get_run_info = True
            
            # Load protocol file names from protocols directory into protocol_labware
            protocols_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'protocols')
            protocol_files = []
            
            if os.path.exists(protocols_dir):
                for filename in os.listdir(protocols_dir):
                    if filename.endswith('.json'):
                        # Remove the .json extension to get the protocol name
                        protocol_name = os.path.splitext(filename)[0]
                        protocol_files.append(protocol_name)
                
                if protocol_files:
                    globals.protocol_labware = protocol_files
                    globals.custom_labware = True
                    print(f"Loaded protocol files into protocol_labware: {protocol_files}")
            
            # Parse run info only to recreate slot assignments from previous runs
            if globals.current_run_info:
                if isinstance(globals.current_run_info, list) and len(globals.current_run_info) > 0:
                    # Get the last entry in the data array
                    last_run_data = globals.current_run_info[-1]
                    
                    if 'labware' in last_run_data:
                        # Parse labware items to recreate slot assignments only
                        for labware_item in last_run_data['labware']:
                            load_name = None
                            slot = None
                            
                            if 'loadName' in labware_item:
                                load_name = labware_item['loadName']
                            
                            if 'location' in labware_item and 'slotName' in labware_item['location']:
                                try:
                                    slot = int(labware_item['location']['slotName'])
                                    if 1 <= slot <= 12 and load_name:  # Valid slot range and load_name exists
                                        # Create proper labware info structure
                                        globals.deck_layout[f'slot_{slot}'] = {
                                            "labware_name": load_name,
                                            "labware_type": load_name.split('_')[2] if len(load_name.split('_')) > 2 else load_name
                                        }
                                        
                                except (ValueError, TypeError):
                                    print(f"Warning: Invalid slot name in labware item: {labware_item.get('location', {}).get('slotName')}")
                                    continue
                        print("Recreated slot assignments from previous run info")

            
            print("Getting run info...")
            return globals.current_run_info
        except Exception as e:
            print(f"Error getting run info: {e}")
            return {}
    

    
    def create_run(self, run_config: Dict[str, Any]) -> bool:
        """Create a new run with the given configuration."""
        try:
            if not globals.robot_api:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api=OpentronsAPI()
            globals.robot_api.create_run()
            
            # Clear all labware from the list including protocol labware and slot assignments
            globals.custom_labware = False
            globals.protocol_labware = []
            globals.deck_layout = {
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
            print("Cleared all labware from the list including protocol labware and all slot assignments")
            
            print(f"Creating run with config: {run_config}")
            return True
        except Exception as e:
            print(f"Error creating run: {e}")
            return False
    
    def load_pipette(self) -> bool:
        """Load a pipette of the specified type and mount."""
        try:
            if not globals.robot_api:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.load_pipette()
            return True
        except Exception as e:
            print(f"Error loading pipette: {e}")
            return False

    
    def calibrate_camera(self, calibration_profile) -> bool:
        """Calibrate the camera."""
        if not globals.robot_initialized:
            print("Robot not initialized. Please initialize first.")
            return False
        try:
            calibration_data = utils.load_calibration_config(calibration_profile)
            manual_movement = ManualMovementModel()
            location=calibration_data["calib_origin"]
            globals.robot_api.retract_axis("leftZ")
            globals.robot_api.move_to_coordinates(location,min_z_height=1, verbose=False)
            cap=globals.active_cameras["HD USB CAMERA"]
            ret, globals.calibration_frame = cap.read()
            squaresX=7
            squaresY=5 
            squareLength=0.022
            markerLength=0.011
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
            params = cv2.aruco.DetectorParameters()
            detector = cv2.aruco.ArucoDetector(aruco_dict, params)
            board = cv2.aruco.CharucoBoard((squaresX, squaresY), squareLength, markerLength, aruco_dict)
            globals.calibration_active = True
            while globals.calibration_active:
                ret, frame = cap.read()
   
                x, y, z = globals.robot_api.get_position(verbose=False)[0].values()
                (text_width, text_height), _ = cv2.getTextSize(f"Robot coords: ({x:.2f}, {y:.2f}, {z:.2f})", cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
                cv2.rectangle(frame, (10, 0), (10 + text_width, text_height + 100), (0, 0, 0), -1)
                cv2.putText(frame, f"Robot coords: ({x:.2f}, {y:.2f}, {z:.2f})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Step size: {manual_movement.step} mm", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                center_screen_x = frame.shape[1] // 2
                center_screen_y = frame.shape[0] // 2
                cv2.circle(frame, (center_screen_x, center_screen_y), 5, (0, 0, 255), -1)
                cv2.putText(frame, f"Center: ({center_screen_x}, {center_screen_y})", (center_screen_x + 10, center_screen_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                # Calculate the center of each quarter of the screen
                quarter_centers = [
                (center_screen_x // 2, center_screen_y // 2),
                (3 * center_screen_x // 2, center_screen_y // 2),
                (center_screen_x // 2, 3 * center_screen_y // 2),
                (3 * center_screen_x // 2, 3 * center_screen_y // 2)
                ]

                # Draw circles at the center of each quarter
                for qx, qy in quarter_centers:
                cv2.circle(frame, (qx, qy), 5, (0, 255, 255), -1)
                cv2.putText(frame, f"({qx}, {qy})", (qx + 10, qy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                marker_corners, marker_ids, _ = detector.detectMarkers(frame)
                if marker_corners:
                for corner in marker_corners:
                corner = corner.reshape((4, 2))
                for point in corner:
                    cv2.circle(frame, tuple(point.astype(int)), 5, (0, 255, 0), -1)

                center_x = int(np.mean(corner[:, 0]))
                center_y = int(np.mean(corner[:, 1]))
                cv2.circle(frame, (center_x, center_y), 5, (255, 0, 0), -1)
                cv2.putText(frame, f"({center_x}, {center_y})", (center_x + 10, center_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                # Calculate side lengths
                side_lengths = []
                if marker_corners:
                for corner in marker_corners[0]:
                for i in range(4):
                    side_length = np.linalg.norm(corner[i] - corner[(i + 1) % 4])
                    side_lengths.append(side_length)

                # Calculate the average side length
                average_side_length = np.mean(side_lengths)
                area = cv2.contourArea(marker_corners[0])
                one_d_ratio = 13.83 / average_side_length
                size_conversion_ratio = 13.83 ** 2 / area
                cv2.putText(frame, f"Area of marker: {area:.2f}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                globals.calibration_frame = frame
                if key_pressed == ord('q'):
                    keyboard.unhook_all()
                    break
                if key_pressed == ord('s'):
                    x, y, z = globals.robot_api.get_position(verbose=False)[0].values()
                    globals.robot_coords.append((x, y))
                    globals.camera_coords.append((center_x, center_y))
            calibration_data = utils.load_calibration_config(calibration_profile)
            calibration_data['size_conversion_ratio'] = size_conversion_ratio
            calibration_data['one_d_ratio'] = one_d_ratio
            utils.save_calibration_config(calibration_profile, calibration_data)
            spacing = 5  # Distance from the calib_point in mm
            # Calculate the four coordinates
            calibration_points = [
                (calib_origin[0] + spacing, calib_origin[1] + spacing),  # Right
                (calib_origin[0] + spacing, calib_origin[1] - spacing),  # Left
                (calib_origin[0] - spacing, calib_origin[1] - spacing),  # Up
                (calib_origin[0] - spacing, calib_origin[1] + spacing)   # Down
            ]

            robot_coords = []
            camera_coords = []
            return True

        except Exception as e:
            print(f"Error in calibrating camera: {e}")
            return False
    
    def placeholder_function_2(self) -> bool:
        """Placeholder function 2."""
        try:
            print("Executing placeholder function 2...")
            return True
        except Exception as e:
            print(f"Error in placeholder function 2: {e}")
            return False
    
    def placeholder_function_3(self) -> bool:
        """Placeholder function 3."""
        try:
            print("Executing placeholder function 3...")
            return True
        except Exception as e:
            print(f"Error in placeholder function 3: {e}")
            return False
    
    def is_robot_initialized(self) -> bool:
        """Check if the robot is initialized."""
        return globals.robot_initialized
    
    def get_lights_status(self) -> bool:
        """Get current lights status."""
        return self.lights_on
    
class MarkerDetector():
    def __init__(self, 
                 squaresX: int = 7, 
                 squaresY: int = 5,
                 squareLength: float = 0.022, 
                 markerLength: float = 0.011,
                 physicalSize: float = 13.83):
        
        self.squaresX = squaresX
        self.squaresY = squaresY
        self.squareLength = squareLength
        self.markerLength = markerLength
        self.physicalSize = physicalSize
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        self.parameters = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.parameters)


    def detect_markers(self, frame: np.ndarray):
        self.marker_corners, self.marker_ids, _ = self.detector.detectMarkers(frame)
        return self.marker_corners, self.marker_ids

    def calculate_size_ratios(self, marker_corners):
        if not marker_corners or len(marker_corners) == 0:
            return None, None
        
        side_lengths = []
        if marker_corners:
            for corner in marker_corners[0]:
                for i in range(4):
                    side_length = np.linalg.norm(corner[i] - corner[(i + 1) % 4])
                    side_lengths.append(side_length)

        # Calculate the average side length
        average_side_length = np.mean(side_lengths)
        area = cv2.contourArea(marker_corners[0])
        self.one_d_ratio = self.physicalSize / average_side_length
        self.size_conversion_ratio = self.physicalSize ** 2 / area
        return self.one_d_ratio, self.size_conversion_ratio

    
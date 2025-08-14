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
from Model.frame_capture import get_frame_capturer
import Model.globals as globals
import Model.utils as utils
from Model.manual_movement import ManualMovementModel
from Model.camera import frameOperations as frame_ops
import keyboard
import time

# Camera name constants - using user labels that match controller
OverviewCameraName = "overview_cam_2"  # User label for overview camera

class SettingsModel:
    """Model for handling settings and robot control operations."""
    
    def __init__(self):
        self.lights_on = False
        self.active_threads=[]
        # Frame capturer will be initialized with proper controller later
        self.frame_capturer = get_frame_capturer()

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
            # print("Robot initialized successfully.")
            time.sleep(0.1)                        
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

    
    def _initialize_marker_detector(self) -> tuple:
        """Initialize ArUco marker detector and board."""
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        params = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, params)
        
        # Board parameters
        squares_x, squares_y = 7, 5
        square_length, marker_length = 0.022, 0.011
        board = cv2.aruco.CharucoBoard((squares_x, squares_y), square_length, marker_length, aruco_dict)
        
        return detector, board

    def _draw_calibration_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw calibration overlay with robot coordinates and reference points."""
        # Get robot position
        x, y, z = globals.robot_api.get_position(verbose=False)[0].values()
        
        # Prepare text overlay
        (text_width, text_height), _ = cv2.getTextSize(f"Robot coords: ({x:.2f}, {y:.2f}, {z:.2f})", 
                                                       cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        cv2.rectangle(frame, (10, 0), (10 + text_width, text_height + 100), (0, 0, 0), -1)
        cv2.putText(frame, f"Robot coords: ({x:.2f}, {y:.2f}, {z:.2f})", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Draw center point
        center_screen_x = frame.shape[1] // 2
        center_screen_y = frame.shape[0] // 2
        cv2.circle(frame, (center_screen_x, center_screen_y), 5, (0, 0, 255), -1)
        cv2.putText(frame, f"Center: ({center_screen_x}, {center_screen_y})", 
                   (center_screen_x + 10, center_screen_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Draw quarter centers
        quarter_centers = [
            (center_screen_x // 2, center_screen_y // 2),
            (3 * center_screen_x // 2, center_screen_y // 2),
            (center_screen_x // 2, 3 * center_screen_y // 2),
            (3 * center_screen_x // 2, 3 * center_screen_y // 2)
        ]
        
        for qx, qy in quarter_centers:
            cv2.circle(frame, (qx, qy), 5, (0, 255, 255), -1)
            cv2.putText(frame, f"({qx}, {qy})", (qx + 10, qy - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        return frame

    def _detect_and_draw_markers(self, frame: np.ndarray, detector) -> tuple:
        """Detect ArUco markers and draw them on the frame."""
        marker_corners, marker_ids, _ = detector.detectMarkers(frame)
        
        if marker_corners:
            for corner in marker_corners:
                corner = corner.reshape((4, 2))
                for point in corner:
                    cv2.circle(frame, tuple(point.astype(int)), 5, (0, 255, 0), -1)
                
                center_x = int(np.mean(corner[:, 0]))
                center_y = int(np.mean(corner[:, 1]))
                cv2.circle(frame, (center_x, center_y), 5, (255, 0, 0), -1)
                cv2.putText(frame, f"({center_x}, {center_y})", (center_x + 10, center_y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        return marker_corners, marker_ids

    def _calculate_size_ratios(self, marker_corners) -> tuple:
        """Calculate size conversion ratios from marker corners."""
        if not marker_corners:
            return None, None
        
        side_lengths = []
        for corner in marker_corners[0]:
            for i in range(4):
                side_length = np.linalg.norm(corner[i] - corner[(i + 1) % 4])
                side_lengths.append(side_length)
        
        average_side_length = np.mean(side_lengths)
        area = cv2.contourArea(marker_corners[0])
        physical_size = 13.83  # Physical size constant
        
        one_d_ratio = physical_size / average_side_length
        size_conversion_ratio = physical_size ** 2 / area
        
        return one_d_ratio, size_conversion_ratio

    def _generate_calibration_points(self, calib_origin: tuple, spacing: float = 5.0) -> list:
        """Generate calibration points around the origin."""
        return [
            (calib_origin[0] + spacing, calib_origin[1] + spacing),  # Right-Down
            (calib_origin[0] + spacing, calib_origin[1] - spacing),  # Right-Up
            (calib_origin[0] - spacing, calib_origin[1] - spacing),  # Left-Up
            (calib_origin[0] - spacing, calib_origin[1] + spacing)   # Left-Down
        ]

    def _perform_multi_point_calibration(self, calibration_points: list, detector) -> tuple:
        """Perform calibration at multiple points and collect coordinate pairs."""
        robot_coords = []
        camera_coords = []
        
        for calib_pt in calibration_points:
            # Move robot to calibration point
            globals.robot_api.move_to_coordinates((*calib_pt, 100), min_z_height=1, verbose=False)
            time.sleep(1)
            frame = self.frame_capturer.capture_frame(OverviewCameraName)
            if frame is None:
                print(f"Failed to capture frame at calibration point {calib_pt}")
                continue
            # frame = frame_ops.undistort_frame(frame)
            # Draw overlay
            frame = self._draw_calibration_overlay(frame)
            
            # Detect markers
            marker_corners, _ = self._detect_and_draw_markers(frame, detector)
            
            if marker_corners:
                center_x = int(np.mean(marker_corners[0].reshape((4, 2))[:, 0]))
                center_y = int(np.mean(marker_corners[0].reshape((4, 2))[:, 1]))
                
                # Store coordinate pairs
                x, y, z = globals.robot_api.get_position(verbose=False)[0].values()
                robot_coords.append((x, y))
                camera_coords.append((center_x, center_y))
            
            globals.calibration_frame = frame
            
        
        return robot_coords, camera_coords

    def _compute_transformation_matrix(self, robot_coords: list, camera_coords: list) -> np.ndarray:
        """Compute transformation matrix from coordinate pairs."""
        sorted_camera_coords = utils.sort_coordinates(camera_coords)
        sorted_robot_coords = utils.sort_coordinates(robot_coords, reverse_y=True)
        
        robot_to_camera_coords = {
            tuple(robot_coord): tuple(camera_coord) 
            for robot_coord, camera_coord in zip(sorted_robot_coords, sorted_camera_coords)
        }
        
        return utils.compute_tf_mtx(robot_to_camera_coords)

    def calibrate_camera(self, calibration_profile) -> bool:
        """Calibrate the camera using ArUco markers."""
        if not globals.robot_initialized:
            print("Robot not initialized. Please initialize first.")
            return False
        
        try:
            # Load calibration configuration
            calibration_data = utils.load_calibration_config(calibration_profile)
            calib_origin = calibration_data["calib_origin"]
            
            # Initialize robot position
            globals.robot_api.retract_axis("leftZ")
            globals.robot_api.move_to_coordinates(calib_origin, min_z_height=1, verbose=False)
            
            # Get initial frame using frame capturer
            initial_frame = self.frame_capturer.capture_frame(OverviewCameraName)
            if initial_frame is None:
                print("Failed to capture initial frame from overview camera")
                return False
            globals.calibration_frame = initial_frame
            
            # Initialize marker detection
            detector, board = self._initialize_marker_detector()
            
            # Initial marker detection and size ratio calculation
            globals.calibration_active = True
            one_d_ratio = None
            size_conversion_ratio = None
            
            print("Starting initial marker detection phase...")
            while True:
                if globals.calibration_active is False:
                    return False
                frame = self.frame_capturer.capture_frame(OverviewCameraName)
                if frame is None:
                    print("Failed to capture frame during calibration")
                    continue
                
                # Draw overlay
                frame = self._draw_calibration_overlay(frame)
                
                # Detect and draw markers
                marker_corners, marker_ids = self._detect_and_draw_markers(frame, detector)
                
                # Calculate size ratios
                if marker_corners:
                    one_d_ratio, size_conversion_ratio = self._calculate_size_ratios(marker_corners)
                    cv2.putText(frame, f"Area of marker: {cv2.contourArea(marker_corners[0]):.2f}", 
                               (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                globals.calibration_frame = frame
                if keyboard.is_pressed('q'):
                    current_position = globals.robot_api.get_position(verbose=False)[0]
                    calib_origin = (current_position['x'], current_position['y'], current_position['z'])
                    calibration_data['calib_origin'] = calib_origin
                    keyboard.unhook_all()  
                    break
            
            # Save size ratios
            if one_d_ratio is not None and size_conversion_ratio is not None:
                calibration_data['size_conversion_ratio'] = size_conversion_ratio
                calibration_data['one_d_ratio'] = one_d_ratio
                utils.save_calibration_config(calibration_profile, calibration_data)
                print(f"Saved size ratios: 1D={one_d_ratio:.4f}, 2D={size_conversion_ratio:.4f}")
            
            # Multi-point calibration
            print("Starting multi-point calibration...")
            calibration_points = self._generate_calibration_points(calib_origin)
            robot_coords, camera_coords = self._perform_multi_point_calibration(
                calibration_points, detector
            )
            
            # Compute transformation matrix
            if len(robot_coords) >= 4 and len(camera_coords) >= 4:
                tf_mtx = self._compute_transformation_matrix(robot_coords, camera_coords)
                calibration_data['tf_mtx'] = tf_mtx.tolist()
                utils.save_calibration_config(calibration_profile, calibration_data)
                print("Camera calibration completed successfully!")
                # Reset calibration state
                globals.calibration_active = False
                return True
            else:
                print("Insufficient calibration points collected.")
                # Reset calibration state
                globals.calibration_active = False
                return False
            
        except Exception as e:
            print(f"Error in calibrating camera: {e}")
            # Reset calibration state
            globals.calibration_active = False
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



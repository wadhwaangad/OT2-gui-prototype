"""
Labware model for the microtissue manipulator GUI.
Contains functionality for managing labware declarations and configurations.
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
import Model.globals as globals
import paths
import requests
from PyQt6.QtCore import QThread
from Model.worker import Worker
import cv2
import Model.utils as utils
import time
import numpy as np
from ultralytics import YOLO
import pandas as pd
OverviewCameraName = "HD USB CAMERA"
UnderviewCameraName = "Arducam B0478 (USB3 48MP)"
class LabwareModel:
    """Model for handling labware declarations and configurations."""
    
    def __init__(self):
        # Initialize global deck layout if not already set or if empty
        if not isinstance(globals.deck_layout, dict) or not globals.deck_layout:
            globals.deck_layout = self.get_default_deck_layout()
        
        self.available_labware = self.get_available_labware()
        self.active_threads = []

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
        
    def get_default_deck_layout(self) -> Dict[str, Any]:
        """Get default deck layout configuration."""
        return {
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
    
    def get_available_labware(self) -> List[str]:
        """Get list of available labware types as strings, including protocol JSONs."""
        # Add protocol JSONs (without .json extension)
        if globals.get_run_info or globals.custom_labware:
            return self.get_built_in_labware() + globals.protocol_labware
        return self.get_built_in_labware()
    
    def get_built_in_labware(self) -> List[str]:
        return [
            "corning_12_wellplate_6.9ml_flat",
            "corning_24_wellplate_3.4ml_flat",
            "corning_384_wellplate_112ul_flat",
            "corning_48_wellplate_1.6ml_flat",
            "corning_6_wellplate_16.8ml_flat",
            "corning_96_wellplate_360ul_flat",
            "corning_96_wellplate_360ul_lid",
            "opentrons_96_tiprack_300ul"
        ]


    def get_slot_configuration(self, slot: str) -> Optional[str]:
        """Get configuration for a specific deck slot."""
        return globals.deck_layout.get(slot)
    
    def set_slot_configuration(self, slot: int, labware: str) -> bool:
        """Set labware configuration for a specific deck slot."""
        try:
            if not globals.robot_api:
                print("Robot not initialized. Please initialize first.")
                return False
            
            if not globals.robot_initialized:
                print("Robot not properly initialized. Please initialize first.")
                return False
            
            # Validate slot number
            if slot not in range(1, 12):
                print(f"Invalid slot number: {slot}. Must be between 1 and 11.")
                return False
            
            # Extract labware type from labware name (word between second and third underscore)
            parts = labware.split('_')
            if len(parts) > 2:
                labware_type = parts[2]
            else:
                # Fallback to the full labware name if format doesn't match expected pattern
                labware_type = labware
            
            # Load labware on the robot
            try:
                if labware in globals.protocol_labware:
                    globals.robot_api.load_labware(labware, slot,  namespace='custom_beta', verbose=True)
                else:
                    globals.robot_api.load_labware(labware, slot, namespace='opentrons', verbose=True)
            except Exception as e:
                print(f"error: {e}")
                return False
            
            # Update both global and local configuration
            slot_key = f"slot_{slot}"
            slot_config = {
                "labware_name": labware,
                "labware_type": labware_type,
            }
            
            # Update global deck layout
            globals.deck_layout[slot_key] = slot_config
            
            print(f"Successfully assigned {labware} to slot {slot}")
            return True
        except Exception as e:
            print(f"Error setting slot configuration: {e}")
            return False
    
    def clear_slot(self, slot: int) -> bool:
        """Clear labware from a specific deck slot."""
        try:
            globals.robot_api.move_labware(globals.robot_api.labware_dct[str(slot)], "offDeck")
            print(globals.robot_api.labware_dct[str(slot)])
            # Clear from global configuration
            globals.deck_layout[f"slot_{slot}"] = None
            return True
        except Exception as e:
            print(f"Error clearing slot: {e}")
            return False
    
    def get_deck_layout(self) -> Dict[str, Any]:
        """Get the current deck layout configuration."""
        return globals.deck_layout
    
    def clear_deck(self) -> bool:
        """Clear all labware from the deck."""
        try:
            # Clear global deck layout
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
            return True
        except Exception as e:
            print(f"Error clearing deck: {e}")
            return False
    
    def add_custom_labware(self) -> bool:
        protocols_dir = os.path.join(paths.BASE_DIR, 'protocols')
        
        # Check if protocols directory exists and has JSON files
        if not os.path.isdir(protocols_dir):
            print("Protocols directory not found.")
            return False
            
        json_files = [f for f in os.listdir(protocols_dir) if f.endswith('.json')]
        if not json_files:
            print("No custom labware JSON files found.")
            return False

        success = True

        # Upload custom labware to robot
        if not globals.robot_api or not globals.robot_initialized:
            print("Robot not initialized. Please initialize first.")
            return False

        for json_file_name in json_files:
            custom_labware_path = os.path.join(protocols_dir, json_file_name)
            try:
                with open(custom_labware_path, 'r', encoding='utf-8') as json_file:
                    custom_labware = json.load(json_file)

                command_dict = {
                    "data": custom_labware
                }
                command_payload = json.dumps(command_dict)

                url = globals.robot_api.get_url('runs') + f'/{globals.robot_api.run_id}/' + 'labware_definitions'
                r = requests.post(url=url, headers=globals.robot_api.HEADERS, params={"waitUntilComplete": True}, data=command_payload)
                if not r.ok:
                    print(f"Failed to upload {json_file_name}: {r.text}")
                    success = False
                else:
                    print(f"Successfully uploaded {json_file_name}")
            except Exception as e:
                print(f"Error uploading {json_file_name}: {e}")
                success = False
        
        # Only set custom_labware to True and update the list if we were successful
        if success:
            globals.custom_labware = True
            protocols_dir = os.path.join(paths.BASE_DIR, 'protocols')
            if os.path.isdir(protocols_dir):
                globals.protocol_labware = []
                for f in os.listdir(protocols_dir):
                    if f.endswith('.json'):
                        globals.protocol_labware.append(os.path.splitext(f)[0])
            # Update available labware list to include protocol JSONs
            self.available_labware = self.get_available_labware()
            print("Custom labware list updated successfully.")
        else:
            print("Failed to add custom labware due to upload errors.")
            
        return success
    
    def get_occupied_slots(self) -> List[str]:
        """Get list of slots that have labware assigned."""
        occupied = []
        for slot, config in globals.deck_layout.items():
            if config is not None:
                occupied.append(slot)
        return occupied
    
    def get_empty_slots(self) -> List[str]:
        """Get list of empty slots on the deck."""
        empty = []
        for slot, config in globals.deck_layout.items():
            if config is None:
                empty.append(slot)
        return empty
    
    def get_tiprack_slots(self) -> List[Dict[str, Any]]:
        """Get list of slots containing tiprack labware."""
        tipracks = []
        for slot, config in globals.deck_layout.items():
            if config and "tiprack" in config["labware_name"].lower():
                tipracks.append({
                    "slot": slot,
                    "slot_number": slot.replace("slot_", ""),
                    "labware_name": config["labware_name"],
                    "labware_type": config["labware_type"]
                })
        return tipracks
    
    def pick_up_tip(self, slot: int, row: str, column: int) -> bool:
        """Pick up a tip from specified tiprack location."""
        try:
            if not globals.robot_api or not globals.robot_initialized:
                print("Robot not initialized. Please initialize first.")
                return False
            
            # Validate slot has tiprack
            slot_key = f"slot_{slot}"
            slot_config = globals.deck_layout.get(slot_key)
            if not slot_config:
                print(f"No labware found in slot {slot}")
                return False
            
            if not row.isalpha() or len(row) != 1:
                print("Row must be a single letter (e.g., A, B, C)")
                return False
            
            if not isinstance(column, int) or column < 1:
                print("Column must be a positive integer")
                return False
            
            # Construct well name (e.g., A1, B12)
            well_name = f"{row.upper()}{column}"
            labware_id = globals.robot_api.labware_dct[f'{slot}']
            # Pick up the tip using the robot API
            globals.robot_api.pick_up_tip(labware_id, well_name)

            print(f"Successfully picked up tip from {well_name} in slot {slot}")
            return True
            
        except Exception as e:
            print(f"Error picking up tip: {e}")
            return False

    def _ensure_lights_on(self) -> None:
        """Ensure robot lights are turned on for calibration."""
        current_status = globals.robot_api.get("lights", globals.robot_api.HEADERS)
        current_status = json.loads(current_status.text)
        if not current_status['on']:
            globals.robot_api.toggle_lights()

    def _load_calibration_resources(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Any, Any, Any]:
        """Load calibration data, model, and cameras."""
        # Load calibration data
        calibration_data = utils.load_calibration_config(globals.calibration_profile)
        tf_mtx = np.array(calibration_data['tf_mtx'])
        calib_origin = np.array(calibration_data['calib_origin'])[:2]
        offset = np.array(calibration_data['offset'])
        
        # Load YOLO model
        model_path = os.path.join(paths.ML_MODELS_DIR, 'tip_detector_v1.pt')
        model = YOLO(model_path)
        
        # Get cameras
        over_cam = globals.active_cameras[OverviewCameraName]
        under_cam = globals.active_cameras[UnderviewCameraName]
        
        return tf_mtx, calib_origin, offset, model, over_cam, under_cam

    def _predict_objects(self, model: Any, image: np.ndarray) -> List[Dict[str, Any]]:
        """Run YOLO prediction on image and extract object data."""
        results = model.predict(
            source=image,
            conf=0.25,
            save=False,
            save_txt=False,
            show=False,
            imgsz=2016,
            verbose=False
        )
        
        data = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                data.append({
                    'class': model.names[cls], 
                    'confidence': conf, 
                    'center_x': center_x, 
                    'center_y': center_y
                })
        return data

    def _find_closest_point(self, data: List[Dict[str, Any]], image_center: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """Find the point object closest to the center of the image."""
        if not data:
            return None
            
        closest_obj = min(
            (obj for obj in data if obj['class'] == 'point'),
            key=lambda obj: (obj['center_x'] - image_center[0]) ** 2 + (obj['center_y'] - image_center[1]) ** 2,
            default=None
        )
        return closest_obj

    def _calculate_robot_coordinates(self, crosshair_x: int, crosshair_y: int, 
                                   tf_mtx: np.ndarray, calibration_data: Dict, 
                                   detection_offset_x: float, detection_offset_y: float) -> Tuple[float, float]:
        """Calculate robot coordinates from detected point."""
        X_init, Y_init, _ = tf_mtx @ (crosshair_x, crosshair_y, 1)
        print(f'Initial coordinates: {X_init}, {Y_init}')

        x, y, _ = globals.robot_api.get_position(verbose=False)[0].values()
        diff = np.array([x, y]) - np.array(calibration_data['calib_origin'])[:2]
        X = X_init + diff[0] + calibration_data['offset'][0]
        Y = Y_init + diff[1] + calibration_data['offset'][1]

        print(f"Robot coords: ({x}, {y})")
        print(f"Target coords: ({X}, {Y})")
        
        return X + detection_offset_x, Y + detection_offset_y

    def _analyze_tip_position(self, df: pd.DataFrame, image_center: Tuple[int, int]) -> Tuple[float, float]:
        """Analyze tip position relative to calibration points."""
        # Calculate distance to center for each point
        df['distance_to_center'] = ((df['center_x'] - image_center[0]) ** 2 + 
                                   (df['center_y'] - image_center[1]) ** 2) ** 0.5

        # Identify closest point to center
        point_distances = df.loc[df['class'] == 'point', 'distance_to_center']
        if point_distances.empty:
            raise AssertionError("No 'point' class detected in the underview image.")
            
        min_distance = point_distances.min()
        df['is_closest_to_center'] = ((df['class'] == 'point') & 
                                     (df['distance_to_center'] == min_distance) & 
                                     (df['distance_to_center'] < 100))
        
        print(df)
        
        if not df['is_closest_to_center'].any():
            raise AssertionError("No suitable center point found.")
            
        if 'tip' not in df['class'].values:
            raise AssertionError("No 'tip' class detected in the underview image.")

        # Calculate linear distance ratio
        closest_point_mask = df['is_closest_to_center'] & (df['class'] == 'point')
        closest_point_coords = df.loc[closest_point_mask, ['center_x', 'center_y']].values[0]
        
        point_coords = df.loc[df['class'] == 'point', ['center_x', 'center_y']].values
        distances_from_closest = np.sqrt(
            (closest_point_coords[0] - point_coords[:, 0])**2 +
            (closest_point_coords[1] - point_coords[:, 1])**2
        )
        distances_from_closest = distances_from_closest[distances_from_closest > 0]
        
        if len(distances_from_closest) == 0:
            raise AssertionError("Unable to calculate distance ratio - insufficient reference points.")
            
        linear_distance_ratio = 20.25 / np.mean(distances_from_closest)

        # Calculate distance to tip
        tip_coords = df.loc[df['class'] == 'tip', ['center_x', 'center_y']].values[0]
        x_dist_to_tip = closest_point_coords[0] - tip_coords[0]
        y_dist_to_tip = closest_point_coords[1] - tip_coords[1]
        
        print(f"Pixel distances to tip: x={x_dist_to_tip}, y={y_dist_to_tip}")

        # Convert to mm (note: coordinate system transformation)
        y_dist_to_tip_mm = x_dist_to_tip * linear_distance_ratio
        x_dist_to_tip_mm = y_dist_to_tip * linear_distance_ratio
        
        print(f"MM distances to tip: x={x_dist_to_tip_mm}, y={y_dist_to_tip_mm}")
        
        return x_dist_to_tip_mm, y_dist_to_tip_mm

    def _capture_verification_frame(self, under_cam: Any) -> np.ndarray:
        """Capture verification frame from under camera."""
        time.sleep(0.5)
        ret, verification_frame = under_cam.read()
        if not ret:
            raise AssertionError("Failed to capture verification frame from under_cam.")
        time.sleep(0.5)
        return verification_frame

    def calibrate_tip(self) -> bool:
        """
        Calibrate tip position using computer vision and robot positioning.
        
        Returns:
            bool: True if calibration successful, False otherwise
        """
        try:
            # Configuration constants
            CALIB_MODULE_COORDINATES = (255, 145.25, 100)
            CALIB_MODULE_HEIGHT = 69
            DETECTION_OFFSET_X = 2
            DETECTION_OFFSET_Y = 2
            MAX_OFFSET_THRESHOLD = 40
            
            # Step 1: Setup
            self._ensure_lights_on()
            tf_mtx, calib_origin, offset, model, over_cam, under_cam = self._load_calibration_resources()
            calibration_data = utils.load_calibration_config(globals.calibration_profile)
            
            # Step 2: Move to calibration module
            globals.robot_api.move_to_coordinates(
                CALIB_MODULE_COORDINATES, 
                min_z_height=CALIB_MODULE_HEIGHT - 0.1, 
                verbose=False
            )
            time.sleep(1)

            # Step 3: Capture and analyze overview camera image
            ret, frame = over_cam.read()
            if not ret:
                raise AssertionError("Failed to capture frame from overview camera.")
                
            image = frame.copy()[..., ::-1]  # Convert BGR to RGB
            image_center = (image.shape[1] // 2, image.shape[0] // 2)
            
            data = self._predict_objects(model, image)
            closest_obj = self._find_closest_point(data, image_center)
            
            if closest_obj is None:
                raise AssertionError("No 'point' class detected in the overview image.")
                
            # Annotate frame for debugging
            cv2.circle(frame, (closest_obj['center_x'], closest_obj['center_y']), 8, (0, 255, 255), 2)
            cv2.putText(frame, "Closest", (closest_obj['center_x'] + 10, closest_obj['center_y'] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            crosshair_x, crosshair_y = closest_obj['center_x'], closest_obj['center_y']

            # Step 4: Calculate and move to target coordinates
            target_x, target_y = self._calculate_robot_coordinates(
                crosshair_x, crosshair_y, tf_mtx, calibration_data, 
                DETECTION_OFFSET_X, DETECTION_OFFSET_Y
            )
            
            globals.robot_api.move_to_coordinates(
                (target_x, target_y, CALIB_MODULE_HEIGHT), 
                min_z_height=CALIB_MODULE_HEIGHT - 0.1, 
                verbose=False
            )
            time.sleep(1)

            # Step 5: Capture and analyze underview camera image
            ret, under_frame = under_cam.read()
            if not ret:
                raise AssertionError("Failed to capture frame from underview camera.")
                
            under_image = under_frame[..., ::-1]  # Convert BGR to RGB
            under_image_center = (under_image.shape[1] // 2, under_image.shape[0] // 2)
            
            under_data = self._predict_objects(model, under_image)
            df = pd.DataFrame(under_data)
            
            if df.empty:
                raise AssertionError("No objects detected in underview image.")

            # Step 6: Calculate tip offset
            x_dist_to_tip_mm, y_dist_to_tip_mm = self._analyze_tip_position(df, under_image_center)
            
            if not (x_dist_to_tip_mm and y_dist_to_tip_mm):
                raise AssertionError("Failed to calculate distances to tip.")

            # Step 7: Validate and apply offset
            actual_offset_x = x_dist_to_tip_mm + DETECTION_OFFSET_X
            actual_offset_y = y_dist_to_tip_mm + DETECTION_OFFSET_Y
            
            if abs(actual_offset_x) >= MAX_OFFSET_THRESHOLD or abs(actual_offset_y) >= MAX_OFFSET_THRESHOLD:
                raise AssertionError(f"Offsets too large: ({actual_offset_x:.2f}, {actual_offset_y:.2f}) mm. "
                                   f"Maximum allowed: {MAX_OFFSET_THRESHOLD} mm.")
            
            globals.robot_api.move_relative('x', x_dist_to_tip_mm, verbose=False)
            globals.robot_api.move_relative('y', y_dist_to_tip_mm, verbose=False)

            # Step 8: Capture verification frame
            verification_frame = self._capture_verification_frame(under_cam)
            globals.tip_calibration_frame = verification_frame

            # Step 9: Update calibration data
            print(f"Actual offset applied: ({actual_offset_x:.2f}, {actual_offset_y:.2f}) mm")
            current_x, current_y, _ = globals.robot_api.get_position(verbose=False)[0].values()
            
            # Calculate new offset based on current position
            X_init, Y_init, _ = tf_mtx @ (crosshair_x, crosshair_y, 1)
            current_diff = np.array([current_x, current_y]) - np.array(calibration_data['calib_origin'])[:2]
            calibration_data['offset'] = [current_x - (X_init + current_diff[0]), 
                                        current_y - (Y_init + current_diff[1])]
            
            utils.save_calibration_config(globals.calibration_profile, calibration_data)

            # Step 10: Retract and finish
            globals.robot_api.retract_axis('leftZ')
            
            print("Tip calibration completed successfully.")
            return True
            
        except Exception as e:
            print(f"Tip calibration failed: {e}")
            # Attempt to retract axis even on failure
            try:
                globals.robot_api.retract_axis('leftZ')
            except:
                pass
            return False    

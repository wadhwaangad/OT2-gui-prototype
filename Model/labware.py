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
    
    def __init__(self, labware_file: str = "labware_config.json"):
        self.labware_file = labware_file
        self.labware_config = self.load_labware_config()  
        # Initialize global deck layout if not already set or if empty
        if not isinstance(globals.deck_layout, dict) or not globals.deck_layout:
            globals.deck_layout = self.labware_config["deck_layout"].copy()
        
        self.available_labware = self.get_available_labware()
        self.active_threads = []
        
        # Clear any saved configuration to ensure fresh start
        self.save_labware_config()

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
        
    def load_labware_config(self) -> Dict[str, Any]:
        """Load labware configuration from JSON file."""
        if os.path.exists(self.labware_file):
            try:
                with open(self.labware_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self.get_default_labware_config()
        return self.get_default_labware_config()
    
    def save_labware_config(self) -> None:
        """Save current labware configuration to JSON file."""
        try:
            with open(self.labware_file, 'w') as f:
                json.dump(self.labware_config, f, indent=2)
        except IOError as e:
            print(f"Error saving labware config: {e}")
    
    def get_default_labware_config(self) -> Dict[str, Any]:
        """Get default labware configuration."""
        return {
            "deck_layout": {
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
        deck_layout = globals.deck_layout if isinstance(globals.deck_layout, dict) else self.labware_config["deck_layout"]
        return deck_layout.get(slot)
    
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
            
            # Update local configuration  
            self.labware_config["deck_layout"][slot_key] = slot_config
            
            # Save configuration to file
            self.save_labware_config()
            
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
            # Clear from both global and local configuration
            globals.deck_layout[f"slot_{slot}"] = None
            self.labware_config["deck_layout"][f"slot_{slot}"] = None
            self.save_labware_config()
            return True
        except Exception as e:
            print(f"Error clearing slot: {e}")
            return False
    
    def get_deck_layout(self) -> Dict[str, Any]:
        """Get the current deck layout configuration."""
        # Use global deck layout if it exists as a dictionary, otherwise fall back to file config
        return globals.deck_layout if isinstance(globals.deck_layout, dict) else self.labware_config["deck_layout"]
    
    def clear_deck(self) -> bool:
        """Clear all labware from the deck."""
        try:
            # Clear both global and file-based deck layout
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
            for slot in self.labware_config["deck_layout"]:
                self.labware_config["deck_layout"][slot] = None
            self.save_labware_config()
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
        deck_layout = globals.deck_layout if isinstance(globals.deck_layout, dict) else self.labware_config["deck_layout"]
        for slot, config in deck_layout.items():
            if config is not None:
                occupied.append(slot)
        return occupied
    
    def get_empty_slots(self) -> List[str]:
        """Get list of empty slots on the deck."""
        empty = []
        deck_layout = globals.deck_layout if isinstance(globals.deck_layout, dict) else self.labware_config["deck_layout"]
        for slot, config in deck_layout.items():
            if config is None:
                empty.append(slot)
        return empty
    
    def get_tiprack_slots(self) -> List[Dict[str, Any]]:
        """Get list of slots containing tiprack labware."""
        tipracks = []
        deck_layout = globals.deck_layout if isinstance(globals.deck_layout, dict) else self.labware_config["deck_layout"]
        for slot, config in deck_layout.items():
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
            deck_layout = globals.deck_layout if isinstance(globals.deck_layout, dict) else self.labware_config["deck_layout"]
            slot_config = deck_layout.get(slot_key)
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

    def calibrate_tip(self):
        current_status = globals.robot_api.get("lights", globals.robot_api.HEADERS)
        current_status = json.loads(current_status.text)
        is_on = current_status['on']
        if not is_on:
            globals.robot_api.toggle_lights()
        calibration_profile = "checkerboard"
        path = os.path.join(paths.BASE_DIR, 'outputs', 'images', 'target_template_2.png')
        template = cv2.imread(path, 0)  # Replace 'template.png' with your template image path
        template_height, template_width = template.shape[:2]
        calibration_data = utils.load_calibration_config(calibration_profile)
        tf_mtx = np.array(calibration_data['tf_mtx'])
        calib_origin = np.array(calibration_data['calib_origin'])[:2]
        offset = np.array(calibration_data['offset'])
        model_path = os.path.join(paths.ML_MODELS_DIR,'tip_detector_v1.pt')
        model = YOLO(model_path)
        over_cam = globals.active_cameras[OverviewCameraName]
        under_cam = globals.active_cameras[UnderviewCameraName]


        #Settings
        calib_module_coordinates = (255, 145.25, 100)  # Coordinates for the pipette offset calibration module
        calib_module_height = 69  # Height for the pipette offset calibration module
        detection_offset_x = 2
        detection_offset_y = 2  # Offset to apply to the detected coordinates
        #Move to pipette offset calibration module:
        globals.robot_api.move_to_coordinates(calib_module_coordinates, min_z_height=calib_module_height-0.1, verbose=False)
        time.sleep(1)

        ret, frame = over_cam.read()
        assert ret, "Failed to capture frame from over_cam."
        image = frame.copy()
        image = image[..., ::-1]  # Convert BGR to RGB as YOLO expects RGB input
        results = model.predict(
                source=image,  # Now pointing to a directory instead of a single file
                conf=0.25,         # Confidence threshold
                save=False,         # Save the annotated images
                save_txt=False,    # Save YOLO-format prediction labels (optional)
                show=False,         # Show images in pop-up windows (if GUI available)
                imgsz=2016,
                verbose = False               # Ensure inference matches your training resolution
            )

        image_center = (image.shape[1] // 2, image.shape[0] // 2)
        data = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                data.append({'class': model.names[cls], 'confidence': conf, 'center_x': center_x, 'center_y': center_y})

        # Select the point closest to the center of the image
        if data:
            closest_obj = min(
                (obj for obj in data if obj['class'] == 'point'),
                key=lambda obj: (obj['center_x'] - image_center[0]) ** 2 + (obj['center_y'] - image_center[1]) ** 2,
                default=None
            )
            if closest_obj is not None:
                cv2.circle(frame, (closest_obj['center_x'], closest_obj['center_y']), 8, (0, 255, 255), 2)
                cv2.putText(frame, "Closest", (closest_obj['center_x'] + 10, closest_obj['center_y'] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        assert closest_obj is not None, "No 'point' class detected in the image."
        crosshair_x, crosshair_y = closest_obj['center_x'], closest_obj['center_y']

        #Move to the center of the detected template
        X_init, Y_init, _ = tf_mtx @ (crosshair_x, crosshair_y, 1)
        print('init:', X_init, Y_init)

        x, y, _ = globals.robot_api.get_position(verbose=False)[0].values()
        diff = np.array([x,y]) - np.array(calibration_data['calib_origin'])[:2]
        X = X_init + diff[0] + offset[0]
        Y = Y_init + diff[1] + offset[1]

        print(f"Robot coords: ({x}, {y})")
        print(f"Clicked on: ({X}, {Y})")
        globals.robot_api.move_to_coordinates((X + detection_offset_x, Y + detection_offset_y, calib_module_height), min_z_height=calib_module_height-0.1, verbose=False)
        time.sleep(1)

        ret, frame = under_cam.read()
        assert ret, "Failed to capture frame from under_cam."
        frame = frame[..., ::-1]  # Convert BGR to RGB as YOLO expects RGB input
        results = model.predict(
                source=frame,  # Now pointing to a directory instead of a single file
                conf=0.25,         # Confidence threshold
                save=False,         # Save the annotated images
                save_txt=False,    # Save YOLO-format prediction labels (optional)
                show=False,         # Show images in pop-up windows (if GUI available)
                imgsz=2016,
                verbose = False               # Ensure inference matches your training resolution
            )

        image = frame.copy()
        image_center = (image.shape[1] // 2, image.shape[0] // 2)
        data = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                data.append({'class': model.names[cls], 'confidence': conf, 'center_x': center_x, 'center_y': center_y})

        # Create a dataframe
        df = pd.DataFrame(data)

        # Calculate the distance of each "point" to the center of the frame
        df['distance_to_center'] = ((df['center_x'] - image_center[0]) ** 2 + (df['center_y'] - image_center[1]) ** 2) ** 0.5

        # Identify the closest "point" to the center of the frame
        df['is_closest_to_center'] = (df['class'] == 'point') & (df['distance_to_center'] == df.loc[df['class'] == 'point', 'distance_to_center'].min()) & (df['distance_to_center'] < 100)

        if df['is_closest_to_center'].any():
            assert 'tip' in df['class'].values and 'point' in df['class'].values, "Both 'tip' and 'point' classes must be present in the dataframe."
            distances_from_closest = np.sqrt(
                (df.loc[df['is_closest_to_center'] & (df['class'] == 'point'), 'center_x'].values[0] - df.loc[df['class'] == 'point', 'center_x'])**2 +
                (df.loc[df['is_closest_to_center'] & (df['class'] == 'point'), 'center_y'].values[0] - df.loc[df['class'] == 'point', 'center_y'])**2
            )
            distances_from_closest = distances_from_closest[distances_from_closest > 0]
            linear_distance_ratio = 20.25 / np.mean(distances_from_closest)
                # Calculate the distance from the center-most "point" class to the "tip" class
            center_point_coords = df.loc[df['is_closest_to_center'], ['center_x', 'center_y']].values[0]
            tip_coords = df.loc[df['class'] == 'tip', ['center_x', 'center_y']].values[0]

            x_dist_to_tip = center_point_coords[0] - tip_coords[0]
            y_dist_to_tip = center_point_coords[1] - tip_coords[1]
            print(x_dist_to_tip, y_dist_to_tip)

            y_dist_to_tip_mm = x_dist_to_tip * linear_distance_ratio
            x_dist_to_tip_mm = y_dist_to_tip * linear_distance_ratio
            print(f"x_dist_to_tip_mm: {x_dist_to_tip_mm}, y_dist_to_tip_mm: {y_dist_to_tip_mm}")

        assert x_dist_to_tip_mm and y_dist_to_tip_mm, "Failed to calculate distances to tip."
        actual_offset_x = x_dist_to_tip_mm + detection_offset_x
        actual_offset_y = y_dist_to_tip_mm + detection_offset_y
        assert abs(actual_offset_x) < 40 and abs(actual_offset_y) < 40, "Offsets are too large, please check the calibration."
        globals.robot_api.move_relative('x', x_dist_to_tip_mm, verbose=False)
        globals.robot_api.move_relative('y', y_dist_to_tip_mm, verbose=False)

        # Take one frame from the under camera and display it for verification
        time.sleep(0.5)
        ret, verification_frame = under_cam.read()
        assert ret, "Failed to capture verification frame from under_cam."

        globals.tip_calibration_frame = verification_frame


        print(f"Actual offset applied: ({actual_offset_x}, {actual_offset_y}) mm")
        x, y, _ = globals.robot_api.get_position(verbose=False)[0].values()
        calibration_data['offset'] = [x-(X_init+diff[0]), y-(Y_init+diff[1])]
        utils.save_calibration_config(calibration_profile, calibration_data)

        globals.robot_api.retract_axis('leftZ')    

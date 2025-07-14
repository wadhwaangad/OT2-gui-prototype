"""
Main controller for the microtissue manipulator GUI.
Manages communication between models and views.
"""

from typing import Dict, Any, List, Optional
from unittest import result
from Model.camera import CameraManagerWindows, MultiprocessVideoCapture
from Model.settings import SettingsModel
from Model.labware import LabwareModel
import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paths import CAM_CONFIGS_DIR
from Model.manual_movement import ManualMovementModel


class MainController:
    """Main controller that coordinates between models and views."""
    
    def __init__(self):
        # Initialize models
        self.camera_manager = CameraManagerWindows()
        self.settings_model = SettingsModel()
        self.labware_model = LabwareModel()
        self.manual_movement_model = ManualMovementModel()
        
        # Active camera captures
        self.active_cameras: Dict[str, MultiprocessVideoCapture] = {}
        
        # View references (will be set by the main view)
        self.main_view = None
        self.settings_view = None
        self.labware_view = None
        self.camera_view = None
        self.manual_movement_view = None
    
    def set_views(self, main_view, settings_view, labware_view, camera_view):
        """Set references to view components."""
        self.main_view = main_view
        self.settings_view = settings_view
        self.labware_view = labware_view
        self.camera_view = camera_view
        # The manual movement view is set in main.py when the tab is created
    
    # Camera control methods
    def get_available_cameras(self) -> List[tuple]:
        """Get list of available cameras with user-friendly labels if available."""
        # Load camera labels
        label_path = os.path.join(CAM_CONFIGS_DIR, 'camera_labels.json')
        try:
            with open(label_path, 'r') as f:
                camera_labels = json.load(f)
        except Exception:
            camera_labels = {}

        cameras = self.camera_manager.get_available_cameras()
        labeled_cameras = []
        for cam_name, cam_index in cameras:
            # Try to find a user label for this camera
            user_label = None
            config_file = None
            for key, label in camera_labels.items():
                if label in cam_name:
                    user_label = key
                    config_file = key + '.json'
                    break
            if user_label and config_file:
                # Try to load default resolution
                config_path = os.path.join(CAM_CONFIGS_DIR, config_file)
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    default_res = config.get('default_resolution', None)
                except Exception:
                    default_res = None
                labeled_cameras.append((user_label, cam_index, cam_name, default_res))
            else:
                labeled_cameras.append((cam_name, cam_index, cam_name, None))
        return labeled_cameras
    
    def start_camera_capture(self, camera_name: str, camera_index: int, width: int = None, height: int = None, focus: int = None) -> bool:
        """Start capturing from a specific camera, using default resolution if available."""
        try:
            if camera_name in self.active_cameras:
                self.stop_camera_capture(camera_name)

            # Try to use default resolution if not provided
            if width is None or height is None:
                # Load camera labels
                label_path = os.path.join(CAM_CONFIGS_DIR, 'camera_labels.json')
                try:
                    with open(label_path, 'r') as f:
                        camera_labels = json.load(f)
                except Exception:
                    camera_labels = {}

                # If camera_name is a user label, get config
                config_file = None
                if camera_name in camera_labels:
                    config_file = camera_name + '.json'
                else:
                    # Try to match by label value
                    for key, label in camera_labels.items():
                        if label in camera_name:
                            config_file = key + '.json'
                            break
                if config_file:
                    config_path = os.path.join(CAM_CONFIGS_DIR, config_file)
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        default_res = config.get('default_resolution', None)
                        if default_res and len(default_res) == 2:
                            width, height = default_res
                    except Exception:
                        pass
            # Fallback if still None
            if width is None:
                width = 640
            if height is None:
                height = 480

            capture = MultiprocessVideoCapture(camera_index, width, height, focus=focus)
            self.active_cameras[camera_name] = capture
            return True
        except Exception as e:
            print(f"Error starting camera capture: {e}")
            return False
    
    def stop_camera_capture(self, camera_name: str) -> bool:
        """Stop capturing from a specific camera."""
        try:
            if camera_name in self.active_cameras:
                self.active_cameras[camera_name].release()
                del self.active_cameras[camera_name]
            return True
        except Exception as e:
            print(f"Error stopping camera capture: {e}")
            return False
    
    def get_camera_frame(self, camera_name: str):
        """Get the latest frame from a specific camera."""
        if camera_name in self.active_cameras:
            return self.active_cameras[camera_name].read()
        return False, None
    
    def set_camera_focus(self, camera_name: str, focus_value: int) -> bool:
        """Set focus for a specific camera."""
        try:
            if camera_name in self.active_cameras:
                self.active_cameras[camera_name].set_focus(focus_value)
                return True
            return False
        except Exception as e:
            print(f"Error setting camera focus: {e}")
            return False
    
    def is_camera_active(self, camera_name: str) -> bool:
        """Check if a camera is actively capturing."""
        return camera_name in self.active_cameras
    
    # Settings control methods
    def initialize_robot(self, on_result=None, on_error=None, on_finished=None):
        """Initialize robot connection in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.initialize_robot, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def add_slot_offsets(self, slots: list[int], x: float, y: float, z: float, on_result=None, on_error=None, on_finished=None):
        """Add slot offsets in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.add_slot_offsets, slots, x, y, z, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def toggle_lights(self, on_result=None, on_error=None, on_finished=None):
        """Toggle robot lights in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.toggle_lights, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def home_robot(self, on_result=None, on_error=None, on_finished=None):
        """Home the robot in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.home_robot, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def get_run_info(self, on_result=None, on_error=None, on_finished=None):
        """Get current run information in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.get_run_info, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def retract_axis(self, axis: str, on_result=None, on_error=None, on_finished=None):
        """Retract a specific axis in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.retract_axis, axis, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def create_run(self, run_config: Dict[str, Any], on_result=None, on_error=None, on_finished=None):
        """Create a new run in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.create_run, run_config, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def load_pipette(self, pipette_type: str, mount: str, on_result=None, on_error=None, on_finished=None):
        """Load a pipette in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.load_pipette, pipette_type, mount, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def placeholder_function_1(self, on_result=None, on_error=None, on_finished=None):
        """Placeholder function 1 in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.placeholder_function_1, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def placeholder_function_2(self, on_result=None, on_error=None, on_finished=None):
        """Placeholder function 2 in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.placeholder_function_2, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def placeholder_function_3(self, on_result=None, on_error=None, on_finished=None):
        """Placeholder function 3 in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.placeholder_function_3, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def update_robot_status(self):
        """Update robot status display - only captures StreamRedirector output."""
        # This method exists to maintain the timer structure
        # All actual status updates come through the StreamRedirector
        pass
    
    def get_robot_status(self) -> Dict[str, Any]:
        """Get current robot status information."""
        return {
            'initialized': self.settings_model.is_robot_initialized(),
            'lights_on': self.settings_model.get_lights_status()
        }
    
    # Labware control methods
    def get_available_labware(self) -> List[str]:
        """Get list of available labware."""
        return self.labware_model.get_available_labware()
    
    def get_deck_layout(self) -> Dict[str, Any]:
        """Get current deck layout."""
        return self.labware_model.get_deck_layout()
    
    def set_slot_labware(self, slot: str, labware_type: str, labware_name: str = None) -> bool:
        """Set labware for a specific slot."""
        success = self.labware_model.set_slot_configuration(slot, labware_type, labware_name)
        if success and self.labware_view:
            self.labware_view.update_deck_display()
        return success
    
    def clear_slot(self, slot: str) -> bool:
        """Clear labware from a specific slot."""
        success = self.labware_model.clear_slot(slot)
        return success

    def add_custom_labware(self) -> bool:
        """Add custom labware definition."""
        success = self.labware_model.add_custom_labware()
        if success and self.labware_view:
            self.labware_view.update_labware_list()
        return success
    
    def get_slot_info(self, slot: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific slot."""
        return self.labware_model.get_slot_configuration(slot)
    
    def get_occupied_slots(self) -> List[str]:
        """Get list of occupied slots."""
        return self.labware_model.get_occupied_slots()
    
    def get_empty_slots(self) -> List[str]:
        """Get list of empty slots."""
        return self.labware_model.get_empty_slots()
    
    # Manual movement control methods
    def drop_tip_in_place(self) -> bool:
        """Drop tip in place."""
        try:
            self.manual_movement_model.run_in_thread(self.manual_movement_model.drop_tip_in_place())
            print("Tip dropped in place")
            return True
        except Exception as e:
            print(f"Error dropping tip: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop robot movement."""
        try:
            self.manual_movement_model.run_in_thread(self.manual_movement_model.stop)
            print("Robot stopped")
            return True
        except Exception as e:
            print(f"Error stopping robot: {e}")
            return False
    
    def move_left(self) -> bool:
        """Move robot left."""
        try:
            self.manual_movement_model.move_left()
            print("Robot moved left")
            return True
        except Exception as e:
            print(f"Error moving left: {e}")
            return False
    
    def move_right(self) -> bool:
        """Move robot right."""
        try:
            self.manual_movement_model.move_right()
            print("Robot moved right")
            return True
        except Exception as e:
            print(f"Error moving right: {e}")
            return False
    
    def move_forward(self) -> bool:
        """Move robot forward."""
        try:
            self.manual_movement_model.move_forward()
            print("Robot moved forward")
            return True
        except Exception as e:
            print(f"Error moving forward: {e}")
            return False
    
    def move_backward(self) -> bool:
        """Move robot backward."""
        try:
            self.manual_movement_model.move_backward()
            print("Robot moved backward")
            return True
        except Exception as e:
            print(f"Error moving backward: {e}")
            return False
    
    # Cleanup methods
    def cleanup(self):
        """Cleanup resources when closing application."""
        # Stop all active cameras
        for camera_name in list(self.active_cameras.keys()):
            self.stop_camera_capture(camera_name)

        self.labware_model.save_labware_config()
        
        print("Application cleanup completed")

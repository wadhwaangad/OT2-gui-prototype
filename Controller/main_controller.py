"""
Main controller for the microtissue manipulator GUI.
Manages communication between models and views.
"""

from typing import Dict, Any, List, Optional
from Model.camera import CameraManagerWindows, ThreadSafeVideoCapture, CameraFrameEmitter, CameraViewer
from Model.settings import SettingsModel
from Model.labware import LabwareModel
import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paths import CAM_CONFIGS_DIR
from Model.manual_movement import ManualMovementModel
from Model.cuboid_picking import CuboidPickingModel
import Model.globals as globals
import time
from PyQt6.QtCore import QObject


class MainController(QObject):
    """Main controller that coordinates between models and views."""
    
    def __init__(self):
        super().__init__()
        # Initialize frame emitter for camera signals first
        self.frame_emitter = CameraFrameEmitter()
        
        # Initialize models with frame emitter
        self.camera_manager = CameraManagerWindows()
        self.settings_model = SettingsModel()
        self.labware_model = LabwareModel()
        self.manual_movement_model = ManualMovementModel()
        self.cuboid_picking_model = CuboidPickingModel()
        
        # Set frame emitter for models that need it
        self._inject_frame_emitter_dependencies()
        
        # View references (will be set by the main view)
        self.main_view = None
        self.settings_view = None
        self.labware_view = None
        self.camera_view = None
        self.manual_movement_view = None
        self.wellplate_view = None
        
    def _inject_frame_emitter_dependencies(self):
        """Inject controller into models that need it for frame capture."""
        # Update frame capturer instances in models to use controller
        if hasattr(self.labware_model, 'frame_capturer'):
            self.labware_model.frame_capturer.set_controller(self)
        if hasattr(self.settings_model, 'frame_capturer'):
            self.settings_model.frame_capturer.set_controller(self)
        if hasattr(self.manual_movement_model, 'frame_capturer'):
            self.manual_movement_model.frame_capturer.set_controller(self)
    
    def update_frame_emitter_for_model(self, model):
        """Update controller for a specific model that has frame_capturer."""
        if hasattr(model, 'frame_capturer'):
            model.frame_capturer.set_controller(self)
        
    
    def set_views(self, main_view, settings_view, labware_view, camera_view, wellplate_view=None):
        """Set references to view components."""
        self.main_view = main_view
        self.settings_view = settings_view
        self.labware_view = labware_view
        self.camera_view = camera_view
        self.wellplate_view = wellplate_view
        # The manual movement view is set in main.py when the tab is created
    
    def set_status_widget(self, status_widget):
        """Set reference to the universal status widget."""
        self.status_widget = status_widget
    
    def get_frame_emitter(self):
        """Get the frame emitter for signal connections."""
        return self.frame_emitter
    
    def shutdown_cameras(self):
        """Shutdown all cameras when app closes."""
        try:
            # Get list of active cameras before stopping
            active_camera_names = self.frame_emitter.get_active_camera_names()
            
            # Stop all cameras
            for camera_name in active_camera_names:
                self.stop_camera_capture(camera_name)
            
            # Stop the frame emitter
            self.frame_emitter.stop()
            print("All cameras shut down successfully")
        except Exception as e:
            print(f"Error shutting down cameras: {e}")
    
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
            # Check if camera is already running
            is_active = self.frame_emitter.is_camera_active(camera_name)
            print(f"Camera {camera_name} is_active check: {is_active}")
            if is_active:
                # Camera is already running, just return success
                print(f"Camera {camera_name} is already active, skipping start")
                return True

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

            print(f"Starting camera capture: {camera_name} (index: {camera_index}) at {width}x{height}")

            # Create and start thread-safe capture
            capture = ThreadSafeVideoCapture(camera_index, width, height, focus=focus)
            success = capture.start_capture()
            
            if success:
                # Add camera to frame emitter (this manages the camera lifecycle)
                self.frame_emitter.add_camera(camera_name, capture)
                print(f"Successfully started camera capture for {camera_name}")
                return True
            else:
                print(f"Failed to start camera capture for {camera_name}")
                capture.release()
                
                # If initial attempt failed, try refreshing cameras and getting updated index
                print(f"Refreshing cameras and retrying for {camera_name}")
                self.refresh_cameras()
                
                # Try to get updated camera index
                cameras = self.get_available_cameras()
                updated_index = None
                for user_label, cam_index, cam_name, default_res in cameras:
                    if user_label == camera_name or cam_name == camera_name:
                        updated_index = cam_index
                        break
                
                if updated_index is not None and updated_index != camera_index:
                    print(f"Camera index updated from {camera_index} to {updated_index}, retrying...")
                    capture = ThreadSafeVideoCapture(updated_index, width, height, focus=focus)
                    success = capture.start_capture()
                    if success:
                        self.frame_emitter.add_camera(camera_name, capture)
                        print(f"Successfully started camera capture for {camera_name} with updated index")
                        return True
                    else:
                        capture.release()
                
                return False
                
        except Exception as e:
            print(f"Error starting camera capture: {e}")
            return False
    
    def stop_camera_capture(self, camera_name: str) -> bool:
        """Stop capturing from a specific camera."""
        try:
            # Remove from frame emitter (this will stop and cleanup the camera)
            self.frame_emitter.remove_camera(camera_name)
            return True
        except Exception as e:
            print(f"Error stopping camera capture for {camera_name}: {e}")
            return False
    
    def get_camera_frame(self, camera_name: str):
        """Get the latest frame from a specific camera."""
        return self.frame_emitter.get_camera_frame(camera_name)
    
    def set_camera_focus(self, camera_name: str, focus_value: int) -> bool:
        """Set focus for a specific camera."""
        try:
            success = self.frame_emitter.set_camera_focus(camera_name, focus_value)
            if success:
                globals.default_focus = focus_value
            return success
        except Exception as e:
            print(f"Error setting camera focus: {e}")
            return False
            
    def is_camera_active(self, camera_name: str) -> bool:
        """Check if a camera is actively capturing."""
        return self.frame_emitter.is_camera_active(camera_name)
    
    def connect_to_camera_stream(self, camera_name: str, slot):
        """Connect a slot directly to a camera's frame stream for multiple viewers."""
        return self.frame_emitter.connect_to_camera(camera_name, slot)
    
    def disconnect_from_camera_stream(self, camera_name: str, slot):
        """Disconnect a slot from a camera's frame stream."""
        return self.frame_emitter.disconnect_from_camera(camera_name, slot)
    
    def get_active_camera_names(self) -> List[str]:
        """Get list of currently active camera names."""
        return self.frame_emitter.get_active_camera_names()
    
    def get_camera_viewer_count(self, camera_name: str) -> int:
        """Get the number of viewers connected to a camera."""
        return self.frame_emitter.get_camera_viewer_count(camera_name)
    
    def create_camera_viewer(self, camera_name: str) -> 'CameraViewer':
        """Create a new camera viewer for the specified camera.
        Multiple viewers can be created for the same camera to display in different locations.
        """
        return CameraViewer(camera_name, self.frame_emitter)
    
    def refresh_cameras(self):
        """Refresh the list of available cameras."""
        self.camera_manager.refresh_devices()
    
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
        return self.manual_movement_model.run_in_thread(self.manual_movement_model.retract_axis, axis, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def create_run(self, run_config: Dict[str, Any], on_result=None, on_error=None, on_finished=None):
        """Create a new run in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.create_run, run_config, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def load_pipette(self, on_result=None, on_error=None, on_finished=None):
        """Load a pipette in a thread."""
        return self.settings_model.run_in_thread(self.settings_model.load_pipette, on_result=on_result, on_error=on_error, on_finished=on_finished)

    def calibrate_camera(self, calibration_profile, on_result=None, on_error=None, on_finished=None):
        """Calibrate the camera in a thread."""
        cameras = self.get_available_cameras()
        # Look for overview camera first
        overview_camera = None
        for camera_data in cameras:
            user_label, camera_index, cam_name, default_res = camera_data
            if "overview_cam" in user_label.lower():
                overview_camera = (cam_name, camera_index, user_label, default_res)
                break
        
        if overview_camera:
            cam_name, camera_index, user_label, default_res = overview_camera
            print(f"Starting camera for calibration: {user_label}")
            success = self.start_camera_capture(
                user_label,  # Use the user_label as camera_name for consistency
                camera_index,
                width=default_res[0] if default_res else 640,
                height=default_res[1] if default_res else 480
            )
            if success:
                print(f"Camera started successfully for calibration. Viewers: {self.get_camera_viewer_count(user_label)}")
                # Check if camera is active in frame emitter
                print(f"Camera active in frame emitter: {self.frame_emitter.is_camera_active(user_label)}")
                # Check active camera names
                print(f"Active cameras: {self.get_active_camera_names()}")
            else:
                print(f"Failed to start camera for calibration: {user_label}")
        else:
            print("Warning: No overview camera found for calibration")
        
        # Wait longer for camera to stabilize and ensure it's properly registered
        time.sleep(2)
        return self.settings_model.run_in_thread(self.settings_model.calibrate_camera, calibration_profile, on_result=on_result, on_error=on_error, on_finished=on_finished)
    def get_calibration_frame(self):
        """Get the last captured calibration frame."""
        return globals.calibration_frame

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
    
    def get_wellplate_labware(self) -> List[str]:
        """Get list of wellplate labware types from available labware."""
        all_labware = self.labware_model.get_available_labware()
        wellplates = []
        
        for labware in all_labware:
            if "wellplate" in labware.lower():
                wellplates.append(labware)
        
        return wellplates
    
    def get_wellplate_info(self, wellplate_name: str) -> Dict[str, Any]:
        """Get information about a specific wellplate."""
        import re
        
        # Extract well count from name
        parts = wellplate_name.split('_')
        well_count = 96  # default
        
        for part in parts:
            if part.isdigit():
                well_count = int(part)
                break
        
        # If no direct number found, try regex
        if well_count == 96:
            numbers = re.findall(r'\d+', wellplate_name)
            if numbers:
                well_count = int(numbers[0])
        
        return {
            "name": wellplate_name,
            "well_count": well_count,
            "type": "wellplate"
        }
    
    def get_deck_layout(self) -> Dict[str, Any]:
        """Get current deck layout."""
        return self.labware_model.get_deck_layout()

    def set_slot_labware(self, slot: int, labware: str, on_result=None, on_error=None, on_finished=None) -> bool:
        """Set labware for a specific slot."""
        def on_success(result):
            if result and self.labware_view:
                self.labware_view.update_deck_display()
            if on_result:
                on_result(result)
        
        thread = self.labware_model.run_in_thread(
            self.labware_model.set_slot_configuration, 
            slot, 
            labware, 
            on_result=on_success, 
            on_error=on_error, 
            on_finished=on_finished
        )
        return thread is not None
    
    def clear_slot(self, slot: str) -> bool:
        """Clear labware from a specific slot."""
        success = self.labware_model.clear_slot(slot)
        if success and self.labware_view:
            self.labware_view.update_deck_display()
        return success

    def add_custom_labware(self, on_result=None, on_error=None, on_finished=None) -> bool:
        """Add custom labware definition."""
        thread = self.labware_model.run_in_thread(
            self.labware_model.add_custom_labware, 
            on_result=on_result, 
            on_error=on_error, 
            on_finished=on_finished
        )
        return thread is not None
    def pickup_tip(self, slot: int, row: str, column: int, on_result=None, on_error=None, on_finished=None) -> bool:
        """Pickup a tip from a specific slot."""  
        thread = self.labware_model.run_in_thread(
            self.labware_model.pick_up_tip, 
            slot, 
            row, 
            column, 
            on_result=on_result, 
            on_error=on_error, 
            on_finished=on_finished
        )
        return thread is not None
    
    def calibrate_tip(self, on_result=None, on_error=None, on_finished=None) -> bool:
        """Calibrate the tip using overview and underview cameras."""
        cameras = self.get_available_cameras()
        # Look for overview and underview cameras
        overview_camera = None
        underview_camera = None
        
        for camera_data in cameras:
            user_label, camera_index, cam_name, default_res = camera_data
            if "overview_cam" in user_label.lower():
                overview_camera = (cam_name, camera_index, user_label, default_res)
            elif "underview_cam" in user_label.lower():
                underview_camera = (cam_name, camera_index, user_label, default_res)
        
        # Start overview camera
        if overview_camera:
            cam_name, camera_index, user_label, default_res = overview_camera
            print(f"Starting overview camera for tip calibration: {user_label}")
            success = self.start_camera_capture(
                user_label,  # Use the user_label as camera_name for consistency
                camera_index,
                width=default_res[0] if default_res else 640,
                height=default_res[1] if default_res else 480
            )
            if success:
                print(f"Overview camera started. Viewers: {self.get_camera_viewer_count(user_label)}")
            else:
                print(f"Failed to start overview camera: {user_label}")
        else:
            print("Warning: No overview camera found for tip calibration")

        # Start underview camera
        if underview_camera:
            cam_name, camera_index, user_label, default_res = underview_camera
            print(f"Starting underview camera for tip calibration: {user_label}")
            success = self.start_camera_capture(
                user_label,  # Use the user_label as camera_name for consistency
                camera_index,
                width=default_res[0] if default_res else 640,
                height=default_res[1] if default_res else 480,
                focus=globals.default_focus
            )
            if success:
                print(f"Underview camera started. Viewers: {self.get_camera_viewer_count(user_label)}")
            else:
                print(f"Failed to start underview camera: {user_label}")
        else:
            print("Warning: No underview camera found for tip calibration")
        
        time.sleep(2)  # Allow cameras to stabilize
        thread = self.labware_model.run_in_thread(
            self.labware_model.calibrate_tip,
            on_result=on_result,
            on_error=on_error,
            on_finished=on_finished
        )
        return thread is not None
    
    def get_slot_info(self, slot: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific slot."""
        return self.labware_model.get_slot_configuration(slot)
    
    def get_occupied_slots(self) -> List[str]:
        """Get list of occupied slots."""
        return self.labware_model.get_occupied_slots()
    
    def get_empty_slots(self) -> List[str]:
        """Get list of empty slots."""
        return self.labware_model.get_empty_slots()
    
    def get_tiprack_slots(self) -> list:
        """Get list of slots containing tiprack labware."""
        return self.labware_model.get_tiprack_slots()

    
    # Manual movement control methods
    def drop_tip_in_place(self, on_result=None, on_error=None, on_finished=None) -> bool:
        """Drop tip in place."""
        try:
            result = self.manual_movement_model.run_in_thread(self.manual_movement_model.drop_tip_in_place, on_result=on_result, on_error=on_error, on_finished=on_finished)
            if result:
                print("Tip dropped in place")
            return result
        except Exception as e:
            print(f"Error dropping tip: {e}")
            return False
    
    def stop(self, on_result=None, on_error=None, on_finished=None) -> bool:
        """Stop robot movement."""
        try:
            result = self.manual_movement_model.run_in_thread(self.manual_movement_model.stop, on_result=on_result, on_error=on_error, on_finished=on_finished)
            if result:
                print("Robot stopped")
            return result
        except Exception as e:
            print(f"Error stopping robot: {e}")
            return False
    
    def move_robot(self, x: float, y: float, z: float, on_result=None, on_error=None, on_finished=None) -> bool:
        try:
            result = self.manual_movement_model.run_in_thread(
                self.manual_movement_model.move_robot, 
                x, 
                y, 
                z, 
                on_result=on_result, 
                on_error=on_error, 
                on_finished=on_finished
            )
            if result:
                print(f"Robot moved to coordinates: X={x}, Y={y}, Z={z}")
            return result
        except Exception as e:
            print(f"Error moving robot: {e}")
            return False

    # Keyboard movement control methods
    def activate_keyboard_movement(self) -> bool:
        """Activate keyboard movement controls."""
        return self.manual_movement_model.activate_keyboard_movement()

    def deactivate_keyboard_movement(self) -> bool:
        """Deactivate keyboard movement controls."""
        return self.manual_movement_model.deactivate_keyboard_movement()

    def increase_step(self) -> bool:
        """Increase movement step size."""
        return self.manual_movement_model.increase_step()

    def decrease_step(self) -> bool:
        """Decrease movement step size."""
        return self.manual_movement_model.decrease_step()

    def save_position(self) -> bool:
        """Save current robot position."""
        return self.manual_movement_model.save_position()

    def clear_saved_positions(self):
        """Clear all saved positions."""
        self.manual_movement_model.clear_saved_positions()

    def get_saved_positions(self) -> list:
        """Get all saved positions."""
        return self.manual_movement_model.get_saved_positions()

    def get_current_step(self) -> float:
        """Get the current step size."""
        return self.manual_movement_model.get_current_step()

    def set_step(self, step: float) -> bool:
        """Set the step size."""
        return self.manual_movement_model.set_step(step)

    def is_keyboard_active(self) -> bool:
        """Check if keyboard movement is active."""
        return self.manual_movement_model.is_keyboard_active()

    # Pipetting operation methods
    def aspirate(self, labware_id: str, well_name: str, well_location: str = 'top', 
                 offset: tuple = (0,0,0), volume_offset: int = 0, volume: int = 25, 
                 flow_rate: int = 25) -> bool:
        """Aspirate from a specific well."""
        return self.manual_movement_model.aspirate(labware_id, well_name, well_location, 
                                                  offset, volume_offset, volume, flow_rate)

    def dispense(self, labware_id: str, well_name: str, well_location: str = 'top',
                 offset: tuple = (0,0,0), volume_offset: int = 0, volume: int = 25,
                 flow_rate: int = 25, pushout: int = 0) -> bool:
        """Dispense to a specific well."""
        return self.manual_movement_model.dispense(labware_id, well_name, well_location, offset,
                                                  volume_offset, volume, flow_rate, pushout)

    def blow_out(self, labware_id: str, well_name: str, well_location: str = 'top',
                 flow_rate: int = 25) -> bool:
        """Blow out to a specific well."""
        return self.manual_movement_model.blow_out(labware_id, well_name, well_location, flow_rate)

    def move_to_well(self, labware_id: str, well_name: str, well_location: str = 'top',
                     offset: tuple = (0,0,0), volume_offset: int = 0, 
                     force_direct: bool = False, speed: int = None, 
                     min_z_height: float = None) -> bool:
        """Move to a specific well."""
        return self.manual_movement_model.move_to_well(labware_id, well_name, well_location, 
                                                      offset, volume_offset, force_direct, speed, min_z_height)

    def set_aspirate_params(self, volume: int, flow_rate: int):
        """Set parameters for aspirate in place."""
        self.manual_movement_model.set_aspirate_params(volume, flow_rate)

    def set_dispense_params(self, volume: int, flow_rate: int, pushout: int = 0):
        """Set parameters for dispense in place."""
        self.manual_movement_model.set_dispense_params(volume, flow_rate, pushout)

    def set_blow_out_params(self, flow_rate: int):
        """Set parameters for blow out in place."""
        self.manual_movement_model.set_blow_out_params(flow_rate)

    def get_aspirate_params(self):
        """Get current aspirate parameters."""
        return self.manual_movement_model.get_aspirate_params()

    def get_dispense_params(self):
        """Get current dispense parameters."""
        return self.manual_movement_model.get_dispense_params()

    def get_blow_out_params(self):
        """Get current blow out parameters."""
        return self.manual_movement_model.get_blow_out_params()
    
    def start_cuboid_picking(self, well_plan, config_data: Dict[str, Any]) -> bool:
        cameras = self.get_available_cameras()
        for camera_data in cameras:
            user_label, camera_index, cam_name, default_res = camera_data
            if "overview_cam" in user_label.lower():
                overview_camera = (cam_name, camera_index, user_label, default_res)
        if overview_camera:
            cam_name, camera_index, user_label, default_res = overview_camera
            print(f"Starting overview camera for tip calibration: {user_label}")
            success = self.start_camera_capture(
                user_label,  # Use the user_label as camera_name for consistency
                camera_index,
                width=default_res[0] if default_res else 640,
                height=default_res[1] if default_res else 480
            )
            if success:
                print(f"Overview camera started. Viewers: {self.get_camera_viewer_count(user_label)}")
            else:
                print(f"Failed to start overview camera: {user_label}")
        else:
            print("Warning: No overview camera found for tip calibration")
        
        try:
            self.cuboid_picking_model.start_cuboid_picking(
            well_plan, 
            config_data)
            return True
        except Exception as e:
            print(f"Error starting cuboid picking: {e}")
            return False
    def get_default_picking_config(self) -> Dict[str, Any]:
        """Get the default configuration for cuboid picking."""
        return self.cuboid_picking_model.get_default_picking_config()


    # Cleanup methods
    def cleanup(self):
        """Cleanup resources when closing application."""
        try:
            # Stop frame emitter first
            if hasattr(self, 'frame_emitter'):
                self.frame_emitter.stop()
            
            # Stop all active cameras
            camera_names = list(globals.active_cameras.keys())
            for camera_name in camera_names:
                try:
                    self.stop_camera_capture(camera_name)
                except Exception as e:
                    print(f"Error stopping camera {camera_name}: {e}")
        
            print("Application cleanup completed")
        except Exception as e:
            print(f"Error during cleanup: {e}")

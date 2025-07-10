"""
Settings model for the microtissue manipulator GUI.
Contains backend functions for robot control and settings management.
"""

from concurrent.futures import thread
import json
import os
from typing import Dict, Any, Optional
from Model.ot2_api import OpentronsAPI 
from PyQt6.QtCore import QThread
from Model.worker import Worker
import Model.globals as globals
class SettingsModel:
    """Model for handling settings and robot control operations."""
    
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = settings_file
        self.settings = self.load_settings()
        self.lights_on = False
        self.current_run_info = {}
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
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self.get_default_settings()
        return self.get_default_settings()
    
    def save_settings(self) -> None:
        """Save current settings to JSON file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except IOError as e:
            print(f"Error saving settings: {e}")
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default settings configuration."""
        return {
            "robot_config": {
                "port": "COM3",
                "baudrate": 115200,
                "timeout": 30
            },
            "slot_offsets": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
            },
            "pipette_config": {
                "type": "p300_single",
                "mount": "right"
            },
            "lighting": {
                "brightness": 100,
                "enabled": False
            }
        }
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a specific setting value."""
        self.settings[key] = value
        self.save_settings()
    
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
            # TODO: Implement actual slot offset addition
            globals.robot_api.add_slot_offsets(slots,(x, y, z))
            print(f"Adding slot offsets: X={x}, Y={y}, Z={z}")
            self.settings["slot_offsets"] = {"x": x, "y": y, "z": z}
            self.save_settings()
            return True
        except Exception as e:
            print(f"Error adding slot offsets: {e}")
            return False
    
    def toggle_lights(self) -> bool:
        """Toggle the robot lights on/off."""
        try:
            globals.robot_api.toggle_lights()
            self.lights_on = not self.lights_on
            print(f"Lights {'ON' if self.lights_on else 'OFF'}")
            self.settings["lighting"]["enabled"] = self.lights_on
            self.save_settings()
            return True
        except Exception as e:
            print(f"Error toggling lights: {e}")
            return False
    
    def home_robot(self) -> bool:
        """Home the robot to its reference position."""
        try:
            globals.robot_api.home_robot()
            print("Homing robot...")
            if not globals.robot_api:
                print("Robot not initialized. Please initialize first.")
                return False
            return True
        except Exception as e:
            print(f"Error homing robot: {e}")
            return False
    
    def get_run_info(self) -> Dict[str, Any]:
        """Get current run information."""
        try:
            self.current_run_info = globals.robot_api.get_run_info()
            print("Getting run info...")
            return self.current_run_info
        except Exception as e:
            print(f"Error getting run info: {e}")
            return {}
    
    def retract_axis(self, axis: str) -> bool:
        """Retract a specific axis."""
        try:
            if not globals.robot_initialized:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.retract_axis(axis)
            print(f"Retracting axis: {axis}")
            return True
        except Exception as e:
            print(f"Error retracting axis {axis}: {e}")
            return False
    
    def create_run(self, run_config: Dict[str, Any]) -> bool:
        """Create a new run with the given configuration."""
        try:
            # TODO: Implement actual run creation
            globals.robot_api.create_run()
            print(f"Creating run with config: {run_config}")
            return True
        except Exception as e:
            print(f"Error creating run: {e}")
            return False
    
    def load_pipette(self, pipette_type: str, mount: str) -> bool:
        """Load a pipette of the specified type and mount."""
        try:
            globals.robot_api.load_pipette()
            # TODO: Implement actual pipette loading
            print(f"Loading pipette: {pipette_type} on {mount} mount")
            self.settings["pipette_config"]["type"] = pipette_type
            self.settings["pipette_config"]["mount"] = mount
            self.save_settings()
            return True
        except Exception as e:
            print(f"Error loading pipette: {e}")
            return False
    
    
    
    def placeholder_function_1(self) -> bool:
        """Placeholder function 1."""
        try:
            print("Executing placeholder function 1...")
            return True
        except Exception as e:
            print(f"Error in placeholder function 1: {e}")
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
    
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
    
    def __init__(self):
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
            globals.robot_api.add_slot_offsets(slots,(x, y, z))
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
            globals.robot_api.create_run()
            print(f"Creating run with config: {run_config}")
            return True
        except Exception as e:
            print(f"Error creating run: {e}")
            return False
    
    def load_pipette(self) -> bool:
        """Load a pipette of the specified type and mount."""
        try:
            globals.robot_api.load_pipette()
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
    
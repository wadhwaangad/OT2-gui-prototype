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

class LabwareModel:
    """Model for handling labware declarations and configurations."""
    
    def __init__(self, labware_file: str = "labware_config.json"):
        self.labware_file = labware_file
        self.labware_config = self.load_labware_config()
        self.custom_labware = False
        self.protocol_labware = []
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
    
    def get_default_labware_config(self) -> list[str]:
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
        protocols_dir = os.path.join(paths.BASE_DIR, 'protocols')
        self.protocol_labware = []  # Update instance variable
        if os.path.isdir(protocols_dir):
            for f in os.listdir(protocols_dir):
                if f.endswith('.json'):
                    self.protocol_labware.append(os.path.splitext(f)[0])
        if self.custom_labware:
            return self.get_built_in_labware() + self.protocol_labware
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
        return self.labware_config["deck_layout"].get(slot)
    
    def set_slot_configuration(self, slot: int, labware: str) -> bool:
        """Set labware configuration for a specific deck slot."""
        try:
            if not globals.robot_api:
                print("Robot not initialized. Please initialize first.")
                return False
            
            # Load labware on the robot
            if labware in self.protocol_labware:
                globals.robot_api.load_labware(labware, slot,  namespace='custom_beta', verbose=True)
            else:
                globals.robot_api.load_labware(labware, slot, namespace='opentrons', verbose=True)
            
            # Update local configuration
            slot_key = f"slot_{slot}"
            self.labware_config["deck_layout"][slot_key] = {
                "labware_name": labware,
                "labware_type": labware,
                "slot": slot
            }
            
            # Save configuration to file
            self.save_labware_config()
            
            print(f"Successfully assigned {labware} to slot {slot}")
            return True
        except Exception as e:
            print(f"Error setting slot configuration: {e}")
            return False
    
    def clear_slot(self, slot: str) -> bool:
        """Clear labware from a specific deck slot."""
        try:
            if slot not in self.labware_config["deck_layout"]:
                print(f"Invalid slot: {slot}")
                return False
            
            self.labware_config["deck_layout"][slot] = None
            self.save_labware_config()
            return True
        except Exception as e:
            print(f"Error clearing slot: {e}")
            return False
    
    def get_deck_layout(self) -> Dict[str, Any]:
        """Get the current deck layout configuration."""
        return self.labware_config["deck_layout"]
    
    def clear_deck(self) -> bool:
        """Clear all labware from the deck."""
        try:
            for slot in self.labware_config["deck_layout"]:
                self.labware_config["deck_layout"][slot] = None
            self.save_labware_config()
            return True
        except Exception as e:
            print(f"Error clearing deck: {e}")
            return False
    
    def add_custom_labware(self) -> bool:
        if not globals.robot_api or not globals.robot_initialized:
            print("Robot not initialized. Please initialize first.")
            return False
        protocols_dir = os.path.join(paths.BASE_DIR, 'protocols')
        json_files = [f for f in os.listdir(protocols_dir) if f.endswith('.json')]

        if not json_files:
            print("No custom labware JSON files found.")
            return False

        success = True
        for json_file_name in json_files:
            custom_labware_path = os.path.join(protocols_dir, json_file_name)
            try:
                with open(custom_labware_path, 'r', encoding='utf-8') as json_file:
                    custom_labware = json.load(json_file)

                command_dict = {
                    "data": custom_labware
                }
                command_payload = json.dumps(command_dict)
                with open(f"{os.path.splitext(json_file_name)[0]}_payload.json", "w") as payload_file:
                    json.dump(command_dict, payload_file, indent=2)

                url = globals.robot_api.get_url('runs') + f'/{globals.robot_api.run_id}/' + 'labware_definitions'
                r = requests.post(url=url, headers=globals.robot_api.HEADERS, params={"waitUntilComplete": True}, data=command_payload)
                if not r.ok:
                    print(f"Failed to upload {json_file_name}: {r.text}")
                    success = False
            except Exception as e:
                print(f"Error uploading {json_file_name}: {e}")
                success = False
        self.custom_labware = True
        # Update available labware list to include protocol JSONs
        self.available_labware = self.get_available_labware()
        return success
    
    def get_occupied_slots(self) -> List[str]:
        """Get list of slots that have labware assigned."""
        occupied = []
        for slot, config in self.labware_config["deck_layout"].items():
            if config is not None:
                occupied.append(slot)
        return occupied
    
    def get_empty_slots(self) -> List[str]:
        """Get list of empty slots on the deck."""
        empty = []
        for slot, config in self.labware_config["deck_layout"].items():
            if config is None:
                empty.append(slot)
        return empty

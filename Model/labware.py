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
            return self.get_built_in_labware() + globals.protcol_labware
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
            if slot not in self.labware_config["deck_layout"]:
                print(f"Invalid slot: {slot}")
                return False
            globals.robot_api.move_labware(globals.robot_api.labware_dct[slot], "offDeck")
            # Clear from both global and local configuration
            globals.deck_layout[slot] = None
            self.labware_config["deck_layout"][slot] = None
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
        
        # If we have run info available, skip the upload process (already uploaded)
        if globals.get_run_info:
            print("Using existing run info, skipping labware upload.")
        else:
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

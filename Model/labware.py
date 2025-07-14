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

class LabwareModel:
    """Model for handling labware declarations and configurations."""
    
    def __init__(self, labware_file: str = "labware_config.json"):
        self.labware_file = labware_file
        self.labware_config = self.load_labware_config()
        self.custom_labware = False
        self.available_labware = self.get_available_labware()
        
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
        built_in = [
            "corning_12_wellplate_6.9ml_flat",
            "corning_24_wellplate_3.4ml_flat",
            "corning_384_wellplate_112ul_flat",
            "corning_48_wellplate_1.6ml_flat",
            "corning_6_wellplate_16.8ml_flat",
            "corning_96_wellplate_360ul_flat",
            "corning_96_wellplate_360ul_lid",
            "opentrons_96_tiprack_300ul"
        ]
        # Add protocol JSONs (without .json extension)
        protocols_dir = os.path.join(paths.BASE_DIR, 'protocols')
        protocol_labware = []
        if os.path.isdir(protocols_dir):
            for f in os.listdir(protocols_dir):
                if f.endswith('.json'):
                    protocol_labware.append(os.path.splitext(f)[0])
        if self.custom_labware:
            return built_in + protocol_labware
        return built_in

    def get_slot_configuration(self, slot: str) -> Optional[str]:
        """Get configuration for a specific deck slot."""
        return self.labware_config["deck_layout"].get(slot)
    
    def set_slot_configuration(self, slot: int, labware_type: str, labware_name: str = None) -> bool:
        """Set labware configuration for a specific deck slot."""
        try:
            if slot not in self.labware_config["deck_layout"]:
                print(f"Invalid slot: {slot}")
                return False

            # Only allow labware_type if it's in available_labware
            if labware_type not in self.available_labware:
                print(f"Unknown labware type: {labware_type}")
                return False

            # For custom labware, get the name from config, else use type as name
            custom_labware = self.labware_config.get("custom_labware", {})
            if labware_type in custom_labware:
                labware_name_final = custom_labware[labware_type].get("name", labware_type)
            else:
                labware_name_final = labware_type

            self.labware_config["deck_layout"][slot] = {
                "labware_type": labware_type,
                "labware_name": labware_name or labware_name_final,
                "labware_info": None  # No dict, just string type
            }
            globals.robot_api.load_labware(labware_name or labware_name_final, slot)
            self.save_labware_config()
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
        if not globals.robot_initialized:
            print("Robot not initialized. Please initialize first.")
            return False
        protocols_dir = os.path.join(paths.BASE_DIR, 'protocols')
        # Find all JSON files in the protocols directory
        json_files = [f for f in os.listdir(protocols_dir) if f.endswith('.json')]

        if not json_files:
            print("No custom labware JSON files found.")
            return False

        success = True
        for json_file_name in json_files:
            custom_labware_path = os.path.join(protocols_dir, json_file_name)
            try:
                with open(custom_labware_path, 'r') as json_file:
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
            except Exception as e:
                print(f"Error uploading {json_file_name}: {e}")
                success = False
        self.custom_labware = True
        # Update available labware list to include protocol JSONs
        self.available_labware = self.get_available_labware()
        return success
    
    def remove_custom_labware(self, labware_type: str) -> bool:
        """Remove a custom labware definition."""
        try:
            if labware_type in self.labware_config["custom_labware"]:
                del self.labware_config["custom_labware"][labware_type]
                # Remove from available labware list (just string)
                self.available_labware = [lw for lw in self.available_labware if lw != labware_type]
                self.save_labware_config()
                return True
            return False
        except Exception as e:
            print(f"Error removing custom labware: {e}")
            return False
    
    def validate_deck_layout(self) -> Tuple[bool, List[str]]:
        """Validate the current deck layout and return any issues."""
        issues = []
        
        try:
            # Check for required labware
            has_tip_rack = False
            has_sample_plate = False
            
            for slot, config in self.labware_config["deck_layout"].items():
                if config is None:
                    continue
                    
                labware_type = config.get("labware_type", "")
                
                if "tip_rack" in labware_type:
                    has_tip_rack = True
                elif "plate" in labware_type:
                    has_sample_plate = True
            
            if not has_tip_rack:
                issues.append("No tip rack found on deck")
            
            if not has_sample_plate:
                issues.append("No sample plate found on deck")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Error validating deck layout: {e}")
            return False, issues
    
    def export_deck_layout(self, filename: str) -> bool:
        """Export current deck layout to a file."""
        try:
            export_data = {
                "deck_layout": self.labware_config["deck_layout"],
                "custom_labware": self.labware_config["custom_labware"],
                "timestamp": "2025-01-01 12:00:00"
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error exporting deck layout: {e}")
            return False
    
    def import_deck_layout(self, filename: str) -> bool:
        """Import deck layout from a file."""
        try:
            if not os.path.exists(filename):
                print(f"File not found: {filename}")
                return False
            
            with open(filename, 'r') as f:
                import_data = json.load(f)
            
            if "deck_layout" in import_data:
                self.labware_config["deck_layout"] = import_data["deck_layout"]
            
            if "custom_labware" in import_data:
                self.labware_config["custom_labware"] = import_data["custom_labware"]
                # Update available labware with custom ones
                for labware in import_data["custom_labware"].values():
                    if labware not in self.available_labware:
                        self.available_labware.append(labware)
            
            self.save_labware_config()
            return True
        except Exception as e:
            print(f"Error importing deck layout: {e}")
            return False
    
    def get_labware_by_type(self, labware_type: str) -> Optional[str]:
        """Get labware type string if available."""
        if labware_type in self.available_labware:
            return labware_type
        return None
    
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

import requests
import json
import functools
from typing import Union

class Decorators():
    def check_error(func):
        """Decorator to check if the HTTP request was successful or not. If not, an exception is raised."""
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            r = func(self, *args, **kwargs)
            if r.status_code not in range(200, 300):
                raise Exception(r.text)
            return r
        return wrapper
    
    def require_ids(id_names: list[str]):
        """Decorator to ensure that the specified IDs are set before proceeding."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                for id_name in id_names:
                    if not getattr(self, id_name, None):
                        raise ValueError(f"{id_name} is not set. Set it before executing commands.")
                return func(self, *args, **kwargs)
            return wrapper
        return decorator

class OpentronsAPI(Decorators):
    BASE_URL = "http://169.254.241.245:31950"

    ENDPOINTS = {
        "runs": "/runs",
        "labwareOffsets": "/labwareOffsets",
        "lights": "/robot/lights",
        "home": "/robot/home",
        "protocols": "/protocols",
        "commands": None,
        "actions": None
    }

    def __init__(self) -> None:
        self.HEADERS = {"opentrons-version": "3"}
        self.PIPETTE = "p300_single_gen2"
        self.run_id = None
        self.pipette_id = None
        self.protocol_id = None
        self.labware_dct = {str(i): None for i in range(1, 12)}
        self.slot_offsets = {"data":[]}

    def get_url(self, endpoint_key: str) -> str:
        """Construct the full URL for a given endpoint key."""
        if endpoint_key in self.ENDPOINTS and self.ENDPOINTS[endpoint_key] is not None:
            return f"{self.BASE_URL}{self.ENDPOINTS[endpoint_key]}"
        raise ValueError(f"Invalid endpoint key: {endpoint_key}")

    @Decorators.check_error
    def post(self, endpoint_key: str, 
                   headers: dict, 
                   params: dict = None, 
                   data: dict = None, 
                   files: list = None) -> requests.models.Response:
        """Post method to post to HTTP API.

        Args:
            url (str): Endpoint URL.
            headers (dict): Headers.
            params (dict, optional): Optional parameters, like 'waitUntilComplete'. Defaults to None.
            data (dict, optional): Usually a dictionary with a command. Defaults to None.
            files (list, optional): A list of file paths that need to be uploaded to the robot's onboard RaspberryPi. Defaults to None.

        Returns:
            requests.models.Response: a responce from the robot's server.
        """        
        url = self.get_url(endpoint_key)

        r = requests.post(
            url=url,
            headers=headers,
            params=params,
            data=data,
            files=files)
        return r
    
    @Decorators.check_error
    def get(self, endpoint_key: str, 
                  headers: dict) -> requests.models.Response:
        """Get method to query the HTTP API.

        Args:
            url (str): Endpoint URL.
            headers (dict): Headers.

        Returns:
            requests.models.Response: a responce from the robot's server.
        """        
        url = self.get_url(endpoint_key)

        r = requests.get(
            url=url,
            headers=headers)
        return r
    
    def display_responce(self, responce: requests.models.Response) -> None:
        """Simple method to print the responce from the server. The responce is formatted to be more readable.

        Args:
            responce (requests.models.Response): a responce object from the robot's server.
        """        
        json_formatted_str = json.dumps(json.loads(responce.text), indent = 2)
        print(f"Request status:\n{responce}\n{json_formatted_str}")
    
    def toggle_lights(self, verbose: bool = False) -> requests.models.Response:
        """Method to toggle the OT-2's top LED strips on/off.

        Args:
            verbose (bool, optional): Print the responce from server or not. Defaults to False.
        """        
        current_status = self.get("lights", self.HEADERS)
        current_status = json.loads(current_status.text)
        is_on = current_status['on']
        responce_data = json.dumps({"on": not(is_on)})
        r = self.post("lights", headers=self.HEADERS, data=responce_data)
        if verbose:
            self.display_responce(r)
        return r

    def create_run(self, protocol_id: str = None, 
                         verbose: bool = True) -> requests.models.Response:
        """Method to create a run for the OT-2. A run needs to be created before any commands 
           like movement, aspiration, etc. are executed, but not for basic commands such as 
           light toggle or homing the robot.  

        Args:
            protocol_id (str, optional): Optional argument to include protocol that is being executed. Defaults to None.
            verbose (bool, optional): Print the responce from server or not. Defaults to True.
        """        
        if protocol_id:
            protocol_id_payload = json.dumps({"data":{"protocolId": protocol_id}})
            r = self.post("runs", self.HEADERS, data = protocol_id_payload)
        else:
            r = self.post("runs", self.HEADERS)
        
        resp_dict = json.loads(r.text)
        if 'data' not in resp_dict:
            print('Error creating run...')
        else:
            if 'id' not in resp_dict['data']:
                print('Error creating run...')
            else:
                run_id = json.loads(r.text)['data']['id']
                self.run_id = run_id
                self.ENDPOINTS['commands'] = f"/runs/{run_id}/commands"
                self.ENDPOINTS['actions'] = f"/runs/{run_id}/actions"
                self.ENDPOINTS['runLabwareOffsets'] = f"/runs/{run_id}/labware_offsets"
        if verbose:
            self.display_responce(r)
        return r
    
    def get_all_runs(self) -> requests.models.Response:
        """Get a responce from robot's server with the information of the last 20 runs.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """        
        r = self.get("runs", self.HEADERS)
        return r
    
    def get_run_info(self) -> dict:
        """Gets information on the current run (if any), and simple statistics on how many runs exited with which status.

        Returns:
            dict: dictionary detailed info about the runs. 
        """        
        all_runs_json = self.get_all_runs()
        all_runs_json = json.loads(all_runs_json.text)
        data = all_runs_json['data']
        current_run_id = None
        current_run_status = None
        for run in data:
            if run['current'] == True:
                current_run_id = run['id']
                current_run_status = run['status']
                self.run_id = current_run_id
                self.ENDPOINTS['commands'] = f"/runs/{self.run_id}/commands"
                self.ENDPOINTS['actions'] = f"/runs/{self.run_id}/actions"
                self.ENDPOINTS['runLabwareOffsets'] = f"/runs/{self.run_id}/labware_offsets"

                if run['pipettes']:
                    self.pipette_id = run['pipettes'][0]['id']

                if run['labware']:
                    for labware in run['labware']:
                        labware_id = labware['id']
                        location = labware['location']
                        if type(location) == dict:
                            self.labware_dct[location['slotName']] = labware_id

        print(f'Total number of runs: {all_runs_json["meta"]["totalLength"]}')
        print(f'Current run ID: {current_run_id}')
        print(f'Current run status: {current_run_status}')
        return data

    def home_robot(self, verbose: bool = True) -> requests.models.Response:
        """Method to home the robot's gantry. Needs to be performed at least once before operation. 

        Args:
            verbose (bool, optional): Print the responce from server or not. Defaults to True.
        """        
        command_dict = {"target": "robot"}
        command_payload = json.dumps(command_dict)
        r = self.post("home", headers=self.HEADERS, data = command_payload)
        if verbose:
            self.display_responce(r)
        return r
    
    def add_slot_offsets(self, slot_names: list[int], offset: tuple[float, float, float]):
        """
        Adds the slot offsets to the given slot names.
        """
        if not isinstance(slot_names, list) or not all(isinstance(s, int) for s in slot_names):
            raise ValueError("slot_names must be a list of integers.")
        if not isinstance(offset, tuple) or len(offset) != 3 or not all(isinstance(o, (int, float)) for o in offset):
            raise ValueError("offset must be a tuple of 3 numbers (int or float).")
        
        new_offsets = {"slots": slot_names, "offset": offset}
        for entry in self.slot_offsets["data"]:
            if entry["slots"] == slot_names:
                raise ValueError(f"Offsets for slots {slot_names} already exist.")
        self.slot_offsets["data"].append(new_offsets)

    def get_offset_for_slot(self, slot: int):
        """
        Returns the offset for a given slot if it exists in slot_offsets, else returns None.
        """
        for entry in self.slot_offsets["data"]:
            if slot in entry["slots"]:
                return entry["offset"]
        return None

    @Decorators.require_ids(["run_id"])
    def load_pipette(self, mount: str = 'left', 
                           verbose: bool = True) -> requests.models.Response:
        """Method that provides the currently attached pipette with a unique ID. Needed to keep track of
           attached/detached pipette tips, etc.

        Args:
            mount (str, optional): 'left' or 'right'. Defaults to 'left'.
            verbose (bool, optional): Print the responce from server or not. Defaults to True.
        """        
        command_dict = {
            "data": {
                "commandType": "loadPipette",
                "params": {
                    "pipetteName": self.PIPETTE,
                    "mount": mount
                },
                "intent": "setup"
            }
        }
        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers= self.HEADERS,
                      params={"waitUntilComplete": True}, data = command_payload)
        
        r_dict = json.loads(r.text)
        assert r_dict['data']['status'] == 'succeeded', "Error loading pipette..."
        self.pipette_id = r_dict['data']['result']['pipetteId']
        
        if verbose:
            self.display_responce(r)
        return r

    def upload_protocol(self, PROTOCOL_FILE: str, 
                              LABWARE_FILE: str = None, 
                              verbose: bool = True) -> requests.models.Response:
        """Method that allows to upload a protocol file (as well as custom labware) to the onboard
           RaspberryPi of the robot. The custom labware has to be uploaded together with a protocol file.

        Args:
            PROTOCOL_FILE (str): path to protocol file in your file system.
            LABWARE_FILE (str, optional): path to a custom labware file. Defaults to None.
            verbose (bool, optional): Print the responce from server or not. Defaults to True.
        """        
        protocol_file_payload = open(PROTOCOL_FILE, "rb")
        files = [("files", protocol_file_payload)]
        if LABWARE_FILE:
            labware_file_payload = open(LABWARE_FILE, "rb")
            files.append(("files", labware_file_payload))

        r = self.post("protocols", headers = self.HEADERS, files = files)

        if verbose:
            self.display_responce(r)
        r_dict = json.loads(r.text)
        self.protocol_id = r_dict["data"]["id"]
        print(f"Protocol ID:\n{self.protocol_id}")

        protocol_file_payload.close()
        if LABWARE_FILE:
            labware_file_payload.close()
        return r

    @Decorators.require_ids(["run_id"])
    def control_run(self, action: str) -> requests.models.Response:
        """Method for execution of a run labeled as the current one."""
        
        assert action in ["play", "pause", "stop", "resume-from-recovery"], "Invalid action argument..."
        payload = json.dumps({"data":{"actionType": action}})
        r = self.post("actions", headers=self.HEADERS, data=payload)
        return r

    @Decorators.require_ids(["run_id", "pipette_id"])
    def move_to_coordinates(self, coordinates: tuple, 
                                  min_z_height: float = 20.0, 
                                  force_direct: bool = False, 
                                  verbose: bool = True) -> requests.models.Response:
        """Method to move the robot's end-effector (mount tip or pipette tip if it is attached) to a coordinate position.

        Args:
            coordinates (tuple): Tuple of x,y,z coordinates. 
            min_z_height (float, optional): Minimum height above the platform. Defaults to 20.0.
            force_direct (bool, optional): Force direct movement from one point to the other. Defaults to False.
            verbose (bool, optional): Print the responce from server or not. Defaults to True.
        """        
        if len(coordinates) != 3:
            print(f'Coordinate tuple needs 3 values, got {len(coordinates)} instead.')
            return

        x,y,z = coordinates
        command_dict = {
            "data": {
                "commandType": "moveToCoordinates",
                "params": {
                    "coordinates": {"x": x, "y": y, "z": z},
                    "minimumZHeight": min_z_height,
                    "forceDirect": force_direct,
                    "pipetteId": self.pipette_id
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                      params={"waitUntilComplete": True}, data = command_payload)
        if verbose == True:
            self.display_responce(r)

        return r
    
    @Decorators.require_ids(["run_id", "pipette_id"])
    def move_to_well(self, labware_id: str, 
                            well_name: str,  
                            well_location: str = 'top',  
                            offset: tuple = (0,0,0),
                            volume_offset: int = 0,  
                            verbose: bool = False,
                            force_direct: bool = False,
                            speed: int = None,
                            min_z_height: float = None) -> requests.models.Response:
         
        well_location_dict = {"origin": well_location,
                             "offset": {"x": offset[0], 
                                        "y": offset[1], 
                                        "z": offset[2]},
                             "volumeOffset": volume_offset}

        command_dict = {
            "data": {
                "commandType": "moveToWell",
                "params": {
                    "labwareId": labware_id,
                    "wellName": well_name,
                    "wellLocation": well_location_dict,
                    "pipetteId": self.pipette_id,
                    "forceDirect": force_direct,
                    "speed": speed,
                    "minimumZHeight": min_z_height
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                    params={"waitUntilComplete": True}, data = command_payload)

        if verbose == True:
            self.display_responce(r)
        return r

    @Decorators.require_ids(["run_id", "pipette_id"])
    def move_relative(self, axis: str, 
                            distance: float, 
                            verbose: bool = False) -> requests.models.Response:
        """Method to move the robot's end-effector (mount tip or pipette tip if it is attached) a relative distance along an axis.

        Args:
            axis (str): Should be 'x', 'y' or 'z'.
            distance (float): Distance to move along the axis in mm.
            verbose (bool, optional): Print the responce from server or not. Defaults to False.
        """        
        if axis not in ('x', 'y', 'z'):
            print('Axis argument must be either x, y or z ...')
            return
        
        command_dict = {
            "data": {
                "commandType": "moveRelative",
                "params": {
                    "axis": axis,
                    "distance": distance,
                    "pipetteId": self.pipette_id
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                      params={"waitUntilComplete": True}, data = command_payload)
        if verbose == True:
            self.display_responce(r)

        return r

    @Decorators.require_ids(["run_id", "pipette_id"])
    def get_position(self, verbose: bool = True) -> dict:
        """Get current position (mount tip or pipette tip if attached). Method is a bit hacky, as it rely's
           on the savePosition command which is used for calibration.

        Args:
            verbose (bool, optional): Print the responce from server or not. Defaults to True.

        Returns:
            dict: returns dictionary with coordinates: {"x":, "y":, "z":}.
        """        
        
        command_dict = {
            "data" : {
                "commandType": "savePosition",
                "params": {
                    "pipetteId": self.pipette_id,
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS, 
                  params={"waitUntilComplete": True}, data = command_payload)
        
        r_dict = json.loads(r.text)
        assert r_dict['data']['status'] == 'succeeded', "Error getting position..."

        coordinates = r_dict['data']['result']['position']
        if verbose:
            print(coordinates)
        return coordinates, r
    

    @Decorators.require_ids(["run_id"])
    def load_labware(self, labware_api_name: str, 
                           slot_name: int, 
                           namespace: str = 'opentrons', 
                           verbose: bool = True) -> requests.models.Response:
        """Method to load a labware (tip rack, reservoir, etc.) into a slot on the robot. The labware is given a unique ID.

        Args:
            labware_api_name (str): Labware name from the Opentrons API.
            slot_name (int): Slot number on the robot. E.g. 1, 2, 3, etc.
            namespace (str, optional): Namespace where the labware definition 'lives'. Defaults to 'opentrons'.
            verbose (bool, optional): Print the responce from server or not. Defaults to True.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """    
        assert slot_name in range(1, 12), "Slot number must be between 1 and 11."

        command_dict = {
            "data": {
                "commandType": "loadLabware",
                "params": {
                    "location": {"slotName": str(slot_name)},
                    "loadName": labware_api_name,
                    "namespace": namespace,
                    "version": 1
                },
                "intent": "setup"
            }
        }

        offset_for_slot = self.get_offset_for_slot(slot_name)
        if offset_for_slot:
            labware_uri = f'{namespace}/{labware_api_name}/1'
            self.add_labware_offset_to_run(labware_uri, slot_name, offset_for_slot)
            print(f"Offset {offset_for_slot} added to run for {labware_api_name} in slot {slot_name}.")
            print(f"Labware URI:\n{labware_uri}\n")
            print("Check offset before using ...")

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                  params={"waitUntilComplete": True}, data = command_payload)
        
        r_dict = json.loads(r.text)
        assert r_dict['data']['status'] == 'succeeded', "Error loading labware..."

        #Cheking if offset was applied to the labware
        if offset_for_slot:
            assert "offsetId" in r.text, "Offset was not applied to the labware..."

        labware_id = r_dict["data"]["result"]["labwareId"]
        self.labware_dct[str(slot_name)] = labware_id

        if verbose == True:
            print(f"Labware ID:\n{labware_id}\n")
        return r
    
    @Decorators.require_ids(["run_id"])
    def add_labware_offset_to_run(self, definitionUri: str, slot_name: int, offset: tuple[float, float, float]) -> requests.models.Response:
        """Method to add a labware offset to the current run. The offset is given in mm.

        Args:
            definitionUri (str): Definition URI of the labware. Format: namespace/loadname/version. 
            For example: 'opentrons/opentrons_96_tiprack_300ul/1'.
            slot_name (int): Slot name where the labware is located. E.g. '1', '2', '3', etc. (OT2)
            offset (tuple[float, float, float]): Offset in mm. Tuple of x, y, z coordinates.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """       
        assert slot_name in range(1, 12), "Slot number must be between 1 and 11."
        x, y, z = offset
        data = {
            "data": {
                "definitionUri": definitionUri,
                "location": {
                    "slotName": str(slot_name)
                },
                "vector": {
                "x": x,
                "y": y,
                "z": z
                }
            }
        }

        data_payload = json.dumps(data)
        r = self.post("runLabwareOffsets", headers = self.HEADERS,
                  params={"waitUntilComplete": True}, data = data_payload)
        return r
    
    @Decorators.require_ids(["run_id"])
    def move_labware(self, labware_id: str, new_location: Union[str, int], strategy: str = 'manualMoveWithoutPause', verbose: bool = False) -> requests.models.Response:
        """Method to move a labware to a new location on the robot, or move labware off the deck.

        Args:
            labware_id (str): unique ID of the labware produced in the load_labware method.
            new_location (Union[str, int]): new location for the labware. Can be a slot name or 'offDeck'.
            strategy (str, optional): how the labware is moved. Defaults to 'manualMoveWithoutPause'.
            verbose (bool, optional): print the responce from server or not. Defaults to False.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """
        if type(new_location) == int:
            new_location = {"slotName": str(new_location)}

        assert strategy in ['usingGripper','manualMoveWithoutPause', 'manualMoveWithPause'], "Invalid strategy argument..."
        command_dict = {
            "data": {
                "commandType": "moveLabware",
                "params": {
                    "labwareId": labware_id,
                    "newLocation": new_location,
                    "strategy": strategy
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                  params={"waitUntilComplete": True}, data = command_payload)
        
        if verbose == True:
            self.display_responce(r)

        return r

    @Decorators.require_ids(["run_id", "pipette_id"])
    def pick_up_tip(self, labware_id: str, 
                          well_name: str, 
                          xyz_offset: tuple = (0,0,0), 
                          verbose: bool = False) -> requests.models.Response:
        """Method to pick up a tip from a well in a tip rack.

        Args:
            labware_id (str): unique ID of the labware produced in the load_labware method.
            well_name (str): coordinate of the tip, e.g. 'A1'.
            xyz_offset (tuple, optional): xyz offset. Defaults to (0,0,0).
            verbose (bool, optional): Print the responce from server or not. Defaults to False.
        """        
        
        command_dict = {
            "data": {
                "commandType": "pickUpTip",
                "params": {
                    "labwareId": labware_id,
                    "wellName": well_name,
                    "wellLocation": {
                        "origin": "top", 
                        "offset": {"x": xyz_offset[0], "y": xyz_offset[1], "z": xyz_offset[2]}
                    },
                    "pipetteId": self.pipette_id
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                  params={"waitUntilComplete": True}, data = command_payload)
        
        if verbose == True:
            self.display_responce(r)
        return r

    @Decorators.require_ids(["run_id", "pipette_id"])
    def drop_tip(self, labware_id: str, 
                       well_name: str, 
                       xyz_offset: tuple = (0,0,0), 
                       verbose: bool = False) -> requests.models.Response:
        """Method to drop a tip into a well in a tip rack.

        Args:
            labware_id (str): unique ID of the labware produced in the load_labware method.
            well_name (str): coordinate of the tip, e.g. 'A1'.
            xyz_offset (tuple, optional): xyz offset. Defaults to (0,0,0).
            verbose (bool, optional): Print the responce from server or not. Defaults to False.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """
        
        command_dict = {
            "data": {
                "commandType": "dropTip",
                "params": {
                    "labwareId": labware_id,
                    "wellName": well_name,
                    "wellLocation": {
                        "origin": "top",
                        "offset": {"x": xyz_offset[0], "y": xyz_offset[1], "z": xyz_offset[2]}
                    },
                    "pipetteId": self.pipette_id
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                  params={"waitUntilComplete": True}, data = command_payload)
        
        if verbose == True:
            self.display_responce(r)
        return r

    @Decorators.require_ids(["run_id", "pipette_id"])
    def drop_tip_in_place(self, verbose: bool = False) -> requests.models.Response:
        """Method to drop a tip in place.

        Args:
            verbose (bool, optional): Print the responce from server or not. Defaults to False.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """
        
        command_dict = {
            "data": {
                "commandType": "dropTipInPlace",
                "params": {
                    "pipetteId": self.pipette_id
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                  params={"waitUntilComplete": True}, data = command_payload)
        
        if verbose == True:
            self.display_responce(r)
        return r

    @Decorators.require_ids(["run_id", "pipette_id"])
    def aspirate(self, labware_id: str, 
                       well_name: str,  
                       well_location: str = 'top',  
                       offset: tuple = (0,0,0),
                       volume_offset: int = 0,
                       volume: int = 25,  
                       flow_rate: int = 25,  
                       verbose: bool = False) -> requests.models.Response:
        """Method to aspirate a volume of liquid from a well in a labware.

        Args:
            labware_id (str): labware ID associated with the labware.
            well_name (str): well name, e.g. 'A1'.
            well_location (str, optional): location within the well, e.g. 'top', 'bottom', 'center'. Defaults to 'top'.
            volume (int, optional): volume to aspirate, uL. Defaults to 25.
            flow_rate (int, optional): flow rate, uL/sec. Defaults to 25.
            verbose (bool, optional): print the responce from server or not. Defaults to False.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """
        well_location_dict = {"origin": well_location,
                             "offset": {"x": offset[0], 
                                        "y": offset[1], 
                                        "z": offset[2]},
                             "volumeOffset": volume_offset}

        command_dict = {
            "data": {
                "commandType": "aspirate",
                "params": {
                    "labwareId": labware_id,
                    "wellName": well_name,
                    "wellLocation": well_location_dict,
                    "flowRate": flow_rate,
                    "volume": volume,
                    "pipetteId": self.pipette_id
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                    params={"waitUntilComplete": True}, data = command_payload)

        if verbose == True:
            self.display_responce(r)
        return r
    
    @Decorators.require_ids(["run_id", "pipette_id"])
    def retract_axis(self, axis: str, verbose: bool = False) -> requests.models.Response:
        """Method to retract the pipette axis to a specified position.

        Args:
            axis (str): The axis to retract "x" "y" "leftZ" "rightZ" "leftPlunger" "rightPlunger" "extensionZ" "extensionJaw" "axis96ChannelCam".
            verbose (bool, optional): print the responce from server or not. Defaults to False.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """
        if axis not in ('x', 'y', 'leftZ', 'rightZ', 'leftPlunger', 'rightPlunger', 'extensionZ', 'extensionJaw', 'axis96ChannelCam'):
            raise ValueError(f"Invalid axis: {axis}")

        command_dict = {
            "data": {
                "commandType": "retractAxis",
                "params": {
                    "axis": axis
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                    params={"waitUntilComplete": True}, data = command_payload)

        if verbose == True:
            self.display_responce(r)
        return r

    @Decorators.require_ids(["run_id", "pipette_id"])
    def dispense(self, labware_id: str, 
                       well_name: str,  
                       well_location: str = 'top',
                       offset: tuple = (0,0,0),
                       volume_offset: int = 0,  
                       volume: int = 25,  
                       flow_rate: int = 25, 
                       pushout: int = 0,  
                       verbose: bool = False) -> requests.models.Response:
        """Method to dispense a volume of liquid into a well in a labware.

        Args:
            labware_id (str): labware ID associated with the labware.
            well_name (str): well name, e.g. 'A1'.
            well_location (str, optional): location within the well, e.g. 'top', 'bottom', 'center'. Defaults to 'top'.
            volume (int, optional): volume to dispense, uL. Defaults to 25.
            flow_rate (int, optional): flow rate, ul/sec. Defaults to 25.
            pushout (int, optional): pushout volume after dispensing, uL (does not work as expected). Defaults to 0.
            verbose (bool, optional): print the response from server or not. Defaults to False.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """ 
        well_location_dict = {"origin": well_location,
                        "offset": {"x": offset[0], 
                                "y": offset[1], 
                                "z": offset[2]},
                        "volumeOffset": volume_offset}

        command_dict = {
            "data": {
                "commandType": "dispense",
                "params": {
                    "labwareId": labware_id,
                    "wellName": well_name,
                    "wellLocation": well_location_dict,
                    "flowRate": flow_rate,
                    "volume": volume,
                    "pipetteId": self.pipette_id,
                    "pushOut": pushout
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                    params={"waitUntilComplete": True}, data = command_payload)

        if verbose == True:
            self.display_responce(r)
        return r

    @Decorators.require_ids(["run_id", "pipette_id"])   
    def aspirate_in_place(self, volume: int = 25, 
                                flow_rate: int = 25, 
                                verbose: bool = False) -> requests.models.Response:
        """Method to aspirate a volume of liquid at the current position of the robot.

        Args:
            flow_rate (int, optional): The flowrate for the pump (uL/s?). Defaults to 25.
            volume (int, optional): Volume to be aspirated (uL). Defaults to 25.
            verbose (bool, optional): Print the responce from server or not. Defaults to False.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """
        command_dict = {
            "data": {
                "commandType": "aspirateInPlace",
                "params": {
                    "flowRate": flow_rate,
                    "volume": volume,
                    "pipetteId": self.pipette_id
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                    params={"waitUntilComplete": True}, data = command_payload)

        if verbose == True:
            self.display_responce(r)
        return r
    
    @Decorators.require_ids(["run_id", "pipette_id"])
    def dispense_in_place(self, volume: int = 25, 
                                flow_rate: int = 25,
                                pushout: int = 0, 
                                verbose: bool = False) -> requests.models.Response:
        """Method to dispense a volume of liquid at the current position of the robot.

        Args:
            flow_rate (int, optional): The flowrate for the pump (uL/s). Defaults to 25.
            volume (int, optional): Volume to be dispenced (uL). Defaults to 25.
            pushout (int, optional): Pushout volume after dispensing, uL (does not work as expected). Defaults to 0.
            verbose (bool, optional): Print the responce from server or not. Defaults to False.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """
        command_dict = {
                    "data": {
                        "commandType": "dispenseInPlace",
                        "params": {
                            "flowRate": flow_rate,
                            "volume": volume,
                            "pipetteId": self.pipette_id,
                            "pushOut": pushout
                        },
                        "intent": "setup"
                    }
                }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                    params={"waitUntilComplete": True}, data = command_payload)
        
        if verbose == True:
            self.display_responce(r)
        return r
    
    @Decorators.require_ids(["run_id", "pipette_id"])
    def blow_out(self, labware_id: str, well_name: str,  well_location: str = 'top', flow_rate: int = 25) -> requests.models.Response:
        """Method to blow out liquid from the pipette tip into a well in a labware.

        Args:
            labware_id (str): labware ID associated with the labware.
            well_name (str): well name, e.g. 'A1'.
            well_location (str, optional): location within the well, e.g. 'top', 'bottom', 'center'. Defaults to 'top'.
            flow_rate (int, optional): the flowrate for the pump (uL/s). Defaults to 25.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """
        command_dict = {
                    "data": {
                        "commandType": "blowout",
                        "params": {
                            "labwareId": labware_id,
                            "wellName": well_name,
                            "wellLocation": {"origin": well_location},
                            "flowRate": flow_rate,
                            "pipetteId": self.pipette_id,
                        },
                        "intent": "setup"
                    }
                }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                    params={"waitUntilComplete": True}, data = command_payload)
        
        return r


    @Decorators.require_ids(["run_id", "pipette_id"])
    def blow_out_in_place(self, flow_rate: int = 25) -> requests.models.Response:
        """Method to blow out liquid from the pipette tip at the current position of the robot.

        Args:
            flow_rate (int, optional): the flowrate for the pump (uL/s). Defaults to 25.

        Returns:
            requests.models.Response: responce object from the robot's server.
        """        
        command_dict = {
            "data": {
                "commandType": "blowOutInPlace",
                "params": {
                    "flowRate": flow_rate,
                    "pipetteId": self.pipette_id
                },
                "intent": "setup"
            }
        }

        command_payload = json.dumps(command_dict)
        r = self.post("commands", headers = self.HEADERS,
                    params={"waitUntilComplete": True}, data = command_payload)
        
        return r
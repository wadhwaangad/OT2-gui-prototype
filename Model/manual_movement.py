import Model.globals as globals
from Model.worker import Worker
from PyQt6.QtCore import QThread
import keyboard


class ManualMovementModel:
    """Placeholder model for manual movement controls."""
    def __init__(self):
        self.active_threads = []
        # Keyboard movement attributes
        self.keyboard_active = False
        self.positions = []
        self.possible_steps = [0.01, 0.1, 0.5, 1, 3, 5, 10, 30, 50]
        self.step = 1
        self.hotkeys = []
        
        # Pipetting parameters for "in place" operations
        self.aspirate_volume = 25
        self.aspirate_flow_rate = 25
        self.dispense_volume = 25
        self.dispense_flow_rate = 25
        self.dispense_pushout = 0
        self.blow_out_flow_rate = 25

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

    def activate_keyboard_movement(self):
        """Activate keyboard movement controls."""
        if self.keyboard_active:
            print("Keyboard movement already active")
            return True
            
        if not globals.robot_api:
            print("Robot not initialized. Please initialize first.")
            return False
            
        try:
            # Clear any existing hotkeys
            self.deactivate_keyboard_movement()
            
            # Add hotkeys
            self.hotkeys.append(keyboard.add_hotkey('up', lambda: self.run_in_thread(self.move_forward)))
            self.hotkeys.append(keyboard.add_hotkey('down', lambda: self.run_in_thread(self.move_backward)))
            self.hotkeys.append(keyboard.add_hotkey('left', lambda: self.run_in_thread(self.move_left)))
            self.hotkeys.append(keyboard.add_hotkey('right', lambda: self.run_in_thread(self.move_right)))
            self.hotkeys.append(keyboard.add_hotkey('pagedown', lambda: self.run_in_thread(self.move_z_down)))
            self.hotkeys.append(keyboard.add_hotkey('pageup', lambda: self.run_in_thread(self.move_z_up)))
            self.hotkeys.append(keyboard.add_hotkey('+', lambda: self.run_in_thread(self.increase_step)))
            self.hotkeys.append(keyboard.add_hotkey('-', lambda: self.run_in_thread(self.decrease_step)))
            self.hotkeys.append(keyboard.add_hotkey('s', lambda: self.run_in_thread(self.save_position)))
            self.hotkeys.append(keyboard.add_hotkey('a', lambda: self.run_in_thread(self.aspirate_in_place_action)))
            self.hotkeys.append(keyboard.add_hotkey('d', lambda: self.run_in_thread(self.dispense_in_place_action)))
            self.hotkeys.append(keyboard.add_hotkey('b', lambda: self.run_in_thread(self.blow_out_in_place_action)))
            
            self.keyboard_active = True
            print("Keyboard movement activated")
            print(f"Current step size: {self.step}mm")
            print("Controls: Arrow keys (XY), Page Up/Down (Z), +/- (step size), S (save position)")
            print("Pipetting: A (aspirate in place), D (dispense in place), B (blow out in place)")
            return True
            
        except Exception as e:
            print(f"Error activating keyboard movement: {e}")
            return False

    def deactivate_keyboard_movement(self):
        """Deactivate keyboard movement controls."""
        try:
            # Remove all hotkeys
            for hotkey in self.hotkeys:
                keyboard.remove_hotkey(hotkey)
            self.hotkeys.clear()
            self.keyboard_active = False
            print("Keyboard movement deactivated")
            return True
        except Exception as e:
            print(f"Error deactivating keyboard movement: {e}")
            return False

    def position_safeguard(self, position):
        """Check if the position is within safe bounds."""
        x, y, z = position
        x_condition = x >= 0 and x <= 380
        y_condition = y >= 0 and y <= 350
        z_condition = z >= 0.1 and z <= 205

        return x_condition and y_condition and z_condition

    def get_current_position(self):
        """Get current robot position."""
        try:
            position_data = globals.robot_api.get_position(verbose=False)
            if position_data and len(position_data) > 0:
                return position_data[0].values()
            return None
        except Exception as e:
            print(f"Error getting position: {e}")
            return None

    def move_z_down(self):
        """Move Z axis down by current step size."""
        try:
            position = self.get_current_position()
            if position is None:
                return False
                
            x, y, z = position
            potential_position = (x, y, z - self.step)
            
            if self.position_safeguard(potential_position):
                globals.robot_api.move_relative('z', -self.step)
                print(f"Moved Z down by {self.step}mm")
                return True
            else:
                print(f"Cannot move Z down by {self.step}mm - would exceed safe bounds")
                return False
        except Exception as e:
            print(f"Error moving Z down: {e}")
            return False

    def move_z_up(self):
        """Move Z axis up by current step size."""
        try:
            position = self.get_current_position()
            if position is None:
                return False
                
            x, y, z = position
            potential_position = (x, y, z + self.step)
            
            if self.position_safeguard(potential_position):
                globals.robot_api.move_relative('z', self.step)
                print(f"Moved Z up by {self.step}mm")
                return True
            else:
                print(f"Cannot move Z up by {self.step}mm - would exceed safe bounds")
                return False
        except Exception as e:
            print(f"Error moving Z up: {e}")
            return False

    def move_forward(self):
        """Move Y axis forward by current step size."""
        try:
            position = self.get_current_position()
            if position is None:
                return False
                
            x, y, z = position
            potential_position = (x, y + self.step, z)
            
            if self.position_safeguard(potential_position):
                globals.robot_api.move_relative('y', self.step)
                print(f"Moved forward by {self.step}mm")
                return True
            else:
                print(f"Cannot move forward by {self.step}mm - would exceed safe bounds")
                return False
        except Exception as e:
            print(f"Error moving forward: {e}")
            return False

    def move_backward(self):
        """Move Y axis backward by current step size."""
        try:
            position = self.get_current_position()
            if position is None:
                return False
                
            x, y, z = position
            potential_position = (x, y - self.step, z)
            
            if self.position_safeguard(potential_position):
                globals.robot_api.move_relative('y', -self.step)
                print(f"Moved backward by {self.step}mm")
                return True
            else:
                print(f"Cannot move backward by {self.step}mm - would exceed safe bounds")
                return False
        except Exception as e:
            print(f"Error moving backward: {e}")
            return False

    def move_left(self):
        """Move X axis left by current step size."""
        try:
            position = self.get_current_position()
            if position is None:
                return False
                
            x, y, z = position
            potential_position = (x - self.step, y, z)
            
            if self.position_safeguard(potential_position):
                globals.robot_api.move_relative('x', -self.step)
                print(f"Moved left by {self.step}mm")
                return True
            else:
                print(f"Cannot move left by {self.step}mm - would exceed safe bounds")
                return False
        except Exception as e:
            print(f"Error moving left: {e}")
            return False

    def move_right(self):
        """Move X axis right by current step size."""
        try:
            position = self.get_current_position()
            if position is None:
                return False
                
            x, y, z = position
            potential_position = (x + self.step, y, z)
            
            if self.position_safeguard(potential_position):
                globals.robot_api.move_relative('x', self.step)
                print(f"Moved right by {self.step}mm")
                return True
            else:
                print(f"Cannot move right by {self.step}mm - would exceed safe bounds")
                return False
        except Exception as e:
            print(f"Error moving right: {e}")
            return False

    def increase_step(self):
        """Increase the movement step size."""
        try:
            current_index = self.possible_steps.index(self.step)
            if current_index < len(self.possible_steps) - 1:
                self.step = self.possible_steps[current_index + 1]
                print(f"Step size increased to {self.step}mm")
            else:
                print(f"Already at maximum step size: {self.step}mm")
            return True
        except Exception as e:
            print(f"Error increasing step: {e}")
            return False

    def decrease_step(self):
        """Decrease the movement step size."""
        try:
            current_index = self.possible_steps.index(self.step)
            if current_index > 0:
                self.step = self.possible_steps[current_index - 1]
                print(f"Step size decreased to {self.step}mm")
            else:
                print(f"Already at minimum step size: {self.step}mm")
            return True
        except Exception as e:
            print(f"Error decreasing step: {e}")
            return False

    def save_position(self):
        """Save the current position."""
        try:
            position_data = globals.robot_api.get_position(verbose=False)
            if position_data and len(position_data) > 0:
                position = position_data[0]
                self.positions.append((position['x'], position['y'], position['z']))
                print(f"Saved position: {position}")
                return True
            else:
                print("Could not get current position")
                return False
        except Exception as e:
            print(f"Error saving position: {e}")
            return False

    def get_saved_positions(self):
        """Get all saved positions."""
        return self.positions.copy()

    def clear_saved_positions(self):
        """Clear all saved positions."""
        self.positions.clear()
        print("Cleared all saved positions")

    def get_current_step(self):
        """Get the current step size."""
        return self.step

    def set_step(self, step):
        """Set the step size."""
        if step in self.possible_steps:
            self.step = step
            print(f"Step size set to {self.step}mm")
            return True
        else:
            print(f"Invalid step size. Available: {self.possible_steps}")
            return False

    def is_keyboard_active(self):
        """Check if keyboard movement is active."""
        return self.keyboard_active
    
    def drop_tip_in_place(self):
        """Placeholder for move up action."""
        if not globals.robot_api:
            print("Robot not initialized. Please initialize first.")
            return False
        globals.robot_api.drop_tip_in_place()
        return True
        
    def stop(self):
        """Placeholder for stop action."""
        if not globals.robot_api:
            print("Robot not initialized. Please initialize first.")
            return False
        globals.robot_api.control_run("stop")
        return True

    def move_robot(self, x: float, y: float, z: float) -> bool:
        if not globals.robot_initialized:
            print("Robot not initialized. Please initialize first.")
            return False
        globals.robot_api.move_to_coordinates((x,y,z))
        return True

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

    # Pipetting methods
    def aspirate(self, labware_id: str, well_name: str, well_location: str = 'top', 
                 offset: tuple = (0,0,0), volume_offset: int = 0, volume: int = 25, 
                 flow_rate: int = 25) -> bool:
        """Aspirate from a specific well."""
        try:
            if not globals.robot_initialized:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.aspirate(labware_id, well_name, well_location, offset, 
                                     volume_offset, volume, flow_rate)
            print(f"Aspirated {volume}uL from {well_name} at {flow_rate}uL/s")
            return True
        except Exception as e:
            print(f"Error aspirating: {e}")
            return False

    def dispense(self, labware_id: str, well_name: str, well_location: str = 'top',
                 offset: tuple = (0,0,0), volume_offset: int = 0, volume: int = 25,
                 flow_rate: int = 25, pushout: int = 0) -> bool:
        """Dispense to a specific well."""
        try:
            if not globals.robot_initialized:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.dispense(labware_id, well_name, well_location, offset,
                                     volume_offset, volume, flow_rate, pushout)
            print(f"Dispensed {volume}uL to {well_name} at {flow_rate}uL/s")
            return True
        except Exception as e:
            print(f"Error dispensing: {e}")
            return False

    def blow_out(self, labware_id: str, well_name: str, well_location: str = 'top',
                 flow_rate: int = 25) -> bool:
        """Blow out to a specific well."""
        try:
            if not globals.robot_initialized:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.blow_out(labware_id, well_name, well_location, flow_rate)
            print(f"Blew out to {well_name} at {flow_rate}uL/s")
            return True
        except Exception as e:
            print(f"Error blowing out: {e}")
            return False

    def aspirate_in_place_action(self) -> bool:
        """Aspirate in place using stored parameters."""
        try:
            if not globals.robot_initialized:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.aspirate_in_place(self.aspirate_volume, self.aspirate_flow_rate)
            print(f"Aspirated {self.aspirate_volume}uL in place at {self.aspirate_flow_rate}uL/s")
            return True
        except Exception as e:
            print(f"Error aspirating in place: {e}")
            return False

    def dispense_in_place_action(self) -> bool:
        """Dispense in place using stored parameters."""
        try:
            if not globals.robot_initialized:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.dispense_in_place(self.dispense_volume, self.dispense_flow_rate, 
                                               self.dispense_pushout)
            print(f"Dispensed {self.dispense_volume}uL in place at {self.dispense_flow_rate}uL/s")
            return True
        except Exception as e:
            print(f"Error dispensing in place: {e}")
            return False

    def blow_out_in_place_action(self) -> bool:
        """Blow out in place using stored parameters."""
        try:
            if not globals.robot_initialized:
                print("Robot not initialized. Please initialize first.")
                return False
            globals.robot_api.blow_out_in_place(self.blow_out_flow_rate)
            print(f"Blew out in place at {self.blow_out_flow_rate}uL/s")
            return True
        except Exception as e:
            print(f"Error blowing out in place: {e}")
            return False

    # Parameter setters for in-place operations
    def set_aspirate_params(self, volume: int, flow_rate: int):
        """Set parameters for aspirate in place."""
        self.aspirate_volume = volume
        self.aspirate_flow_rate = flow_rate
        print(f"Aspirate parameters set: {volume}uL at {flow_rate}uL/s")

    def set_dispense_params(self, volume: int, flow_rate: int, pushout: int = 0):
        """Set parameters for dispense in place."""
        self.dispense_volume = volume
        self.dispense_flow_rate = flow_rate
        self.dispense_pushout = pushout
        print(f"Dispense parameters set: {volume}uL at {flow_rate}uL/s, pushout: {pushout}uL")

    def set_blow_out_params(self, flow_rate: int):
        """Set parameters for blow out in place."""
        self.blow_out_flow_rate = flow_rate
        print(f"Blow out flow rate set: {flow_rate}uL/s")

    def get_aspirate_params(self):
        """Get current aspirate parameters."""
        return self.aspirate_volume, self.aspirate_flow_rate

    def get_dispense_params(self):
        """Get current dispense parameters."""
        return self.dispense_volume, self.dispense_flow_rate, self.dispense_pushout

    def get_blow_out_params(self):
        """Get current blow out parameters."""
        return self.blow_out_flow_rate

"""
Cuboid picking model for the microtissue manipulator GUI.
Handles cuboid picking procedure logic and FSM management.
"""

import threading
from typing import Dict, Any, Optional, Callable
from PyQt6.QtCore import QThread
from Model.worker import Worker
import Model.globals as globals
import Model.picking_procedure as picking_procedure
from Model.TissuePickerFSM import TissuePickerFSM


class CuboidPickingModel:
    """Model for managing cuboid picking procedures using the TissuePickerFSM."""
    
    def __init__(self):
        self.tissue_picker_fsm: Optional[TissuePickerFSM] = None
        self.controller = None
        self.is_picking_active = False
        self.active_threads = []
        self.fsm_thread = None  # Dedicated thread for FSM
    
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
    
    def set_controller(self, controller):
        """Set reference to the main controller."""
        self.controller = controller
    
    def start_cuboid_picking(self, well_plan, config_data: Dict[str, Any]) -> bool:
        """Start cuboid picking procedure using the TissuePickerFSM."""
        try:
            if self.is_picking_active:
                print("Cuboid picking procedure is already active")
                return False
            
            # Create destination and routine
            dest = picking_procedure.Destination(plate_type)
            
            # Create routine
            routine = picking_procedure.Routine(dest, well_plan_dict, fill_strategy=fill_strategy)
            
            # Create picking configuration
            picking_config = picking_procedure.PickingConfig.from_dict(config_data)
            
            # Create logger
            logger = picking_procedure.MarkdownLogger(
                experiment_name="GUI-Cuboid-Picking",
                settings=config_data,
                well_plate=well_plan
            )
            logger.log_section("Execution start:")
            
            # Create FSM
            self.tissue_picker_fsm = TissuePickerFSM(picking_config, routine, logger)
            self.is_picking_active = True
            
            # Start FSM in its own thread (not using Worker since FSM has its own threading logic)
            def run_fsm():
                try:
                    self.tissue_picker_fsm.start()
                except Exception as e:
                    print(f"FSM error: {e}")
                    self.is_picking_active = False
                    self.tissue_picker_fsm = None
            
            self.fsm_thread = threading.Thread(target=run_fsm, daemon=True)
            self.fsm_thread.start()
            
            print("Cuboid picking procedure started successfully")
            return True
            
        except Exception as e:
            print(f"Error starting cuboid picking: {e}")
            self.is_picking_active = False
            self.tissue_picker_fsm = None
            raise e
    
    
    def get_default_picking_config(self) -> Dict[str, Any]:
        """Get default picking configuration based on PickingConfig dataclass."""
        return {
            'vol': 25.0,
            'dish_bottom': 65.6,
            'pickup_offset': 0.5,
            'pickup_height': 66.1,  # dish_bottom + pickup_offset
            'flow_rate': 50.0,
            'cuboid_size_theshold': (350, 550),
            'failure_threshold': 0.5,
            'minimum_distance': 1.7,
            'wait_time_after_deposit': 0.5,
            'well_offset_x': 0.0,
            'well_offset_y': 0.0,
            'deposit_offset_z': 0.2,
            'destination_slot': 5,
            'circle_center': (1296, 972),
            'circle_radius': 900,
            'contour_filter_window': (50, 3000),
            'aspect_ratio_window': (0.75, 1.25),
            'min_circularity': 0.6
        }
    
    def is_procedure_active(self) -> bool:
        """Check if a cuboid picking procedure is currently active."""
        return self.is_picking_active and self.tissue_picker_fsm is not None
    
    def get_procedure_status(self) -> Dict[str, Any]:
        """Get current status of the picking procedure."""
        if not self.is_procedure_active():
            return {
                'active': False,
                'state': None,
                'current_well': None
            }
        
        try:
            return {
                'active': True,
                'state': self.tissue_picker_fsm.state.name if hasattr(self.tissue_picker_fsm.state, 'name') else str(self.tissue_picker_fsm.state),
                'current_well': self.tissue_picker_fsm.current_well if hasattr(self.tissue_picker_fsm, 'current_well') else None
            }
        except Exception as e:
            print(f"Error getting procedure status: {e}")
            return {
                'active': self.is_picking_active,
                'state': 'Unknown',
                'current_well': None
            }
    
    def cleanup(self):
        """Cleanup resources when shutting down."""
        try:
            # Stop any active picking procedure
            if self.is_procedure_active():
                self.stop_cuboid_picking()
                
            # Clean up any remaining active threads
            for thread in self.active_threads[:]:  # Copy list to avoid modification during iteration
                try:
                    thread.quit()
                    thread.wait(1000)  # Wait up to 1 second
                except Exception as e:
                    print(f"Error cleaning up thread: {e}")
            
            self.active_threads.clear()
            
        except Exception as e:
            print(f"Error during cuboid picking cleanup: {e}")
        finally:
            self.tissue_picker_fsm = None
            self.fsm_thread = None
            self.is_picking_active = False

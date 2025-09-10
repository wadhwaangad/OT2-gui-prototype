"""
TissuePickerFSM - Finite State Machine for Cuboid Picking Procedure

This module implements a finite state machine for automated tissue cuboid picking
with integrated Qt-based visual display window.

The display window shows:
- Real-time camera feed with vision analysis annotations
- Status information and current state
- Control buttons for pause/resume and emergency stop
- Zoomable and pannable video display

The display window automatically opens when cuboid picking starts from the GUI
and provides visual feedback throughout the picking procedure.
"""

import keyboard
import threading
import numpy as np
import cv2
import json
import time
from enum import Enum
import Model.picking_procedure as pp
import Model.core as core
import Model.globals as globals
import Model.camera as camera
import Model.utils as utils
from Model.frame_capture import get_frame_capturer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QGroupBox, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from View.zoomable_video_widget import VideoDisplayWidget
from View.cuboidpicking_view import TissuePickerDisplayWindow

KEYBOARD_AVAILABLE = True


class RobotState(Enum):
    IDLE = 'idle'
    CAPTURE_FRAME = 'capture_frame'
    ANALYZE_FRAME = 'analyze_frame'
    APPROACH_TARGET = 'approach_target'
    PICKUP_SAMPLE = 'pickup_sample'
    VERIFY_PICKUP = 'verify_pickup'
    DEPOSIT_BACK = 'deposit_liquid_back'
    TRANSFER_TO_WELL = 'transfer_to_well'
    AUTO_SHAKE = 'auto_shake'
    PAUSED = 'paused'
    CANCELED = 'canceled'
    COMPLETED = 'completed'
    
class TissuePickerFSM():
    def __init__(self, config: pp.PickingConfig, routine: pp.Routine, logger: pp.MarkdownLogger):
        
        try:
            self.state = RobotState.IDLE
            
            # Don't create display window here - it will be set from main thread
            self.display_window = None
            
            self.logger = logger
            self.running = True
            self.paused = False
            self.keyboard_lock = threading.Lock()
            self.keyboard_hooks = []
            
            # Get frame capturer
            self.frame_capturer = get_frame_capturer()

            self.config = config
            self.routine = routine
            
            
            self.cr = core.Core()

            # Use global calibration profile
            self.calibration_data = utils.load_calibration_config(globals.calibration_profile)
            
            self.tf_mtx = np.array(self.calibration_data['tf_mtx'])
            self.calib_origin = np.array(self.calibration_data['calib_origin'])[:2]
            self.offset = np.array(self.calibration_data['offset'])
            self.size_conversion_ratio = self.calibration_data['size_conversion_ratio']
            self.one_d_ratio = self.calibration_data['one_d_ratio']

            # Initialize as empty DataFrames, not lists
            import pandas as pd
            self.isolated = pd.DataFrame()
            self.pickable_cuboids = pd.DataFrame()
            self.world_coordinates = []
            self.cuboid_choice = None
            self.current_frame = None
            
            self.current_well = self.routine.get_next_well()
            
        except Exception as e:
            print(f"Error during TissuePickerFSM initialization: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def calculate_robot_coordinates(self, cX, cY, robot_x, robot_y):
        X_init, Y_init, _ = self.tf_mtx @ (cX, cY, 1)
        diff = np.array([robot_x,robot_y]) - self.calib_origin
        X = X_init + diff[0] + self.offset[0]
        Y = Y_init + diff[1] + self.offset[1]
        return X, Y
    
    def cv_pipeline(self, frame):
        mask = np.zeros_like(frame, dtype=np.uint8)
        cv2.circle(mask, self.config.circle_center, self.config.circle_radius + int(self.config.minimum_distance / self.one_d_ratio), (255, 255, 255), -1)
        masked_frame = cv2.bitwise_and(frame, mask)

        gray = cv2.cvtColor(masked_frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (11, 11), 0) #was (11, 11)
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,41,3) #was 4
        self.bubble_thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,35,5)
        kernel = np.ones((3,3),np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        mask_inv = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        thresh = cv2.bitwise_and(thresh, mask_inv)

        # Find contours in the masked frame
        contours, hei = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        filtered_contours = [contour for contour in contours if self.config.contour_filter_window[0] < cv2.contourArea(contour) < self.config.contour_filter_window[1]]
        self.cr.cuboids = filtered_contours
        self.cr.cuboid_dataframe(self.cr.cuboids)

        cuboid_size_micron2 = self.cr.cuboid_df.area * self.size_conversion_ratio * 10e5
        cuboid_diameter = 2 * np.sqrt(cuboid_size_micron2 / np.pi)
        dist_mm = self.cr.cuboid_df.min_dist * self.one_d_ratio
        self.cr.cuboid_df['diameter_microns'] = cuboid_diameter
        self.cr.cuboid_df['min_dist_mm'] = dist_mm
        # Check if the dataframe is not empty before applying operations
        if len(self.cr.cuboid_df) > 0:
            self.cr.cuboid_df['bubble'] = self.cr.cuboid_df.apply(lambda row: not bool(self.bubble_thresh[int(row['cY']), int(row['cX'])]), axis=1)

            # Filter out elongated contours
            self.pickable_cuboids = self.cr.cuboid_df.loc[((self.config.cuboid_size_theshold[0] < self.cr.cuboid_df['diameter_microns']) & 
                                                (self.cr.cuboid_df['diameter_microns'] < self.config.cuboid_size_theshold[1])) &
                                                ((self.cr.cuboid_df['aspect_ratio'] > self.config.aspect_ratio_window[0]) & 
                                                    (self.cr.cuboid_df['aspect_ratio'] < self.config.aspect_ratio_window[1])) &
                                                ((self.cr.cuboid_df['circularity'] > self.config.circularity_window[0]) &
                                                    (self.cr.cuboid_df['circularity'] < self.config.circularity_window[1])) & 
                                                (self.cr.cuboid_df['bubble'] != True)].copy()

            # Check if cuboid centers are within the circle radius from the current circle center
            self.pickable_cuboids['distance_to_center'] = self.pickable_cuboids.apply(
                lambda row: np.sqrt((row['cX'] - self.config.circle_center[0])**2 + (row['cY'] - self.config.circle_center[1])**2), axis=1
            )
            self.pickable_cuboids = self.pickable_cuboids[self.pickable_cuboids['distance_to_center'] <= self.config.circle_radius]
            self.isolated = self.pickable_cuboids.loc[self.pickable_cuboids.min_dist_mm > self.config.minimum_distance]
        else:
            self.pickable_cuboids = []
            self.isolated = []

    def draw_annotations(self, frame):
        cv2.circle(frame, self.config.circle_center, self.config.circle_radius + int(self.config.minimum_distance / self.one_d_ratio), (0, 0, 255), 2)
        cv2.circle(frame, self.config.circle_center, self.config.circle_radius, (0, 255, 0), 2)
        # Add a black rectangle behind the text
        text_background_height = 250  # Adjust height to fit all text lines
        text_background_width = 320  # Full width of the frame
        cv2.rectangle(frame, (0, 0), (text_background_width, text_background_height), (0, 0, 0), -1)
        if self.routine.current_well is None:
            self.routine.get_next_well()
        cv2.putText(frame, f"Filling well: {self.routine.current_well}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        if self.paused:
            cv2.putText(frame, "Paused", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        if self.cr.cuboids:
            cv2.drawContours(frame, self.cr.cuboids, -1, (0, 0, 255), 2)
            cv2.drawContours(frame, self.pickable_cuboids.contour.values.tolist(), -1, (0, 255, 255), 2)
            cv2.drawContours(frame, self.isolated.contour.values.tolist(), -1, (0, 255, 0), 2)
            if hasattr(self.cr.cuboid_df, 'bubble'):
                bubble_contours = self.cr.cuboid_df[self.cr.cuboid_df['bubble']].contour.values.tolist()
                if bubble_contours:
                    cv2.drawContours(frame, bubble_contours, -1, (255, 0, 255), 2)  # Purple color for bubbles
        cv2.putText(frame, f"# Objects: {len(self.cr.cuboids)}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"# Pickable: {len(self.pickable_cuboids)}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"# Isolated: {len(self.isolated)}", (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cuboids_in_size_range = self.cr.cuboid_df.loc[(self.config.cuboid_size_theshold[0] < self.cr.cuboid_df['diameter_microns']) & 
                                        (self.cr.cuboid_df['diameter_microns'] < self.config.cuboid_size_theshold[1])].copy()
        cv2.putText(frame, f"# In size range: {len(cuboids_in_size_range)}", (10, 230), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        if self.cuboid_choice is not None:
            for idx, row in self.cuboid_choice.iterrows():
                rect = cv2.minAreaRect(row['contour'])  # ((center_x, center_y), (width, height), angle)
                box = cv2.boxPoints(rect)
                box = np.intp(box)  # Convert to integer coordinates
                cv2.drawContours(frame, [box], 0, (0, 0, 0), 2)
            # for idx, row in self.cuboid_choice.iterrows():
                # x, y, w, h = cv2.boundingRect(row['contour'])
                # # Calculate center and size of the bounding box
                # center_x = x + w / 2
                # center_y = y + h / 2
                # new_w = int(w * 1.25)
                # new_h = int(h * 1.25)
                # new_x = int(center_x - new_w / 2)
                # new_y = int(center_y - new_h / 2)
                # cv2.rectangle(frame, (new_x, new_y), (new_x + new_w, new_y + new_h), (0, 0, 0), 2)

        return frame

    def _setup_keyboard_hooks(self):
        """Setup global keyboard hooks using the keyboard module"""
        if not KEYBOARD_AVAILABLE:
            print("Keyboard module not available. No keyboard controls will work.")
            return
            
        def on_pause_key(event):
            if event.event_type == keyboard.KEY_DOWN:
                with self.keyboard_lock:
                    self.paused = not self.paused
                    status = "PAUSED" if self.paused else "RESUMED"
                    print(f"\n[CONTROL] Robot {status}")
        
        def on_escape_key(event):
            if event.event_type == keyboard.KEY_DOWN:
                with self.keyboard_lock:
                    print("\n[CONTROL] Emergency stop! Shutting down...")
                    self.running = False
        
        # Register keyboard hooks
        try:
            self.keyboard_hooks.append(keyboard.on_press_key('p', on_pause_key))
            self.keyboard_hooks.append(keyboard.on_press_key('esc', on_escape_key))
            print("Keyboard hooks registered successfully!")
        except Exception as e:
            print(f"Failed to register keyboard hooks: {e}")
            print("Note: On some systems, you may need to run as administrator/root.")
    
    def _cleanup_keyboard_hooks(self):
        """Remove keyboard hooks"""
        if KEYBOARD_AVAILABLE:
            try:
                for hook in self.keyboard_hooks:
                    keyboard.unhook(hook)
                self.keyboard_hooks.clear()
            except Exception as e:
                print(f"Error cleaning up keyboard hooks: {e}")
    
    def start(self):
        """Start the FSM with global keyboard controls"""
        print("=== Tissue Picker Robot FSM Started ===")
        if KEYBOARD_AVAILABLE:
            print("  'p' - Pause/Resume")
            print("  'ESC' - Emergency stop and quit")
        else:
            print("No keyboard controls available (keyboard module not installed)")
        print("=" * 60)
        
        # Setup keyboard hooks
        self._setup_keyboard_hooks()
        
        try:
            while self.running:
                try:  # Add inner try-catch for each iteration
                    with self.keyboard_lock:
                        if self.paused:
                            time.sleep(0.1)
                            continue
                
                    # Execute current state
                    if hasattr(self, f"state_{self.state.value}"):
                        getattr(self, f"state_{self.state.value}")()
                    else:
                        print(f"Error: Unknown state {self.state.value}")
                        self.running = False
                
                    # Small delay to prevent overwhelming the output
                    time.sleep(0.1)
                
                except Exception as e:
                    print(f"Error in state {self.state.value}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Decide whether to continue or stop based on error type
                    if isinstance(e, (KeyError, AttributeError)):
                        print("Critical error, stopping FSM")
                        self.running = False
                    else:
                        print("Non-critical error, continuing...")
                        time.sleep(1)  # Wait a bit before retrying
    
        except KeyboardInterrupt:
            print("\n[CONTROL] Keyboard interrupt received. Shutting down...")
            self.running = False
    
        finally:
            # Cleanup keyboard hooks
            self._cleanup_keyboard_hooks()
            print("\n=== Tissue Picker Robot FSM Stopped ===")

    def state_idle(self):
        print("Robot is idle. Press 'p' to continue...")
        self.paused = True  # Ensure the robot is paused in idle state
        
        try:
            # Move to picking position
            globals.robot_api.retract_axis('leftZ')
            globals.robot_api.move_to_coordinates((self.calib_origin[0],self.calib_origin[1],115), min_z_height=self.config.dish_bottom, verbose=False)
            # Turn off lights
            current_status = globals.robot_api.get("lights", globals.robot_api.HEADERS)
            current_status = json.loads(current_status.text)
            is_on = current_status['on']
            if is_on:
                globals.robot_api.toggle_lights()
        except Exception as e:
            print(f"Error setting up robot in idle state: {e}")

        # Only send status if display window exists and is safe to use
        try:
            if self.display_window and hasattr(self.display_window, 'send_status'):
                self.display_window.send_status("Robot IDLE - Press 'p' to continue", (0, 0, 255))
        except Exception as e:
            print(f"Error sending status to display window: {e}")

        while self.paused and self.running:
            try:
                # Use frame capturer instead of direct camera read
                frame = self.frame_capturer.capture_frame("overview_cam_2")
                if frame is None:
                    time.sleep(0.1)
                    continue
                    
                frame = globals.frame_ops.undistort_frame(frame)
                if frame is None:
                    time.sleep(0.1)
                    continue
                    
                plot_frame = frame.copy()
                self.cv_pipeline(frame)
                self.draw_annotations(plot_frame)
                
                # Update global frame for display elsewhere
                globals.cuboid_picking_frame = plot_frame.copy()
                
            except Exception as e:
                print(f"Error in idle state frame processing: {e}")
                # Don't crash, just wait and try again
                time.sleep(0.5)
                continue

        self.state = RobotState.CAPTURE_FRAME
        self.start_time = time.time()

    def state_capture_frame(self):
        globals.robot_api.move_to_coordinates((self.calib_origin[0],self.calib_origin[1],115), min_z_height=self.config.dish_bottom, verbose=False)
        time.sleep(0.75)
        
        # Use frame capturer instead of direct camera read
        frame = self.frame_capturer.capture_frame("overview_cam_2")
        frame = globals.frame_ops.undistort_frame(frame)
        if frame is not None:
            self.current_frame = globals.frame_ops.undistort_frame(frame)
            self.state = RobotState.ANALYZE_FRAME
        else:
            print("Failed to capture frame, retrying...")
            time.sleep(0.1)
            
    def state_auto_shake(self):
        openapi.retract_axis('leftZ')
        openapi.move_to_coordinates((235, 223, 64.6), verbose=False)
        for _ in range(3):
            openapi.move_relative('x', -10)
            openapi.move_relative('x', 10)
            time.sleep(0.5)
        openapi.move_relative('x', 2)
        time.sleep(0.5)
        openapi.move_relative('x', -2)
        openapi.retract_axis('leftZ')
        time.sleep(2)
        self.state = RobotState.CAPTURE_FRAME

    def state_analyze_frame(self):
        self.cv_pipeline(self.current_frame)
        # Fix: Use .empty instead of len() == 0
        if self.isolated.empty:
            print("No isolated cuboids found. Pausing...")
            self.logger.log("No cuboids found in the selected region. Pausing...")
            self.state = RobotState.AUTO_SHAKE
            return

        next_well = self.routine.get_next_well()
        cuboids_to_fill = self.routine.well_plan[next_well] - self.routine.filled_wells[next_well]
        
        if not self.config.one_by_one:
            # Fix: Use len() properly with DataFrame
            if len(self.isolated) > cuboids_to_fill:
                self.cuboid_choice = self.isolated.sample(n=cuboids_to_fill)
            else:
                self.cuboid_choice = self.isolated.copy()
        else:
            self.cuboid_choice = self.isolated.sample(n=1)

        # Ensure we don't try to log empty DataFrames
        if not self.cuboid_choice.empty:
            log_columns = [col for col in self.cuboid_choice.columns if col != 'contour']
            self.logger.log_table(self.cuboid_choice[log_columns], title=f"Filling well {next_well}")
        
        plot_frame = self.current_frame.copy()
        self.draw_annotations(plot_frame)
        
        # Update global frame for display elsewhere
        globals.cuboid_picking_frame = plot_frame.copy()
        
        self.state = RobotState.APPROACH_TARGET

    def state_approach_target(self):
        cuboid_coordinates = self.cuboid_choice[['cX', 'cY']].values
        self.world_coordinates = []
        for cX, cY in cuboid_coordinates:
            X, Y = self.calculate_robot_coordinates(cX, cY, self.calib_origin[0], self.calib_origin[1])
            self.world_coordinates.append((X, Y))
        self.state = RobotState.PICKUP_SAMPLE

    def state_pickup_sample(self):
        for x,y in self.world_coordinates:
            globals.robot_api.move_to_coordinates((x, y, self.config.pickup_height+20), min_z_height=self.config.dish_bottom, verbose=False, force_direct=True)
            globals.robot_api.move_to_coordinates((x, y, self.config.pickup_height), min_z_height=self.config.dish_bottom, verbose=False, force_direct=True)
            globals.robot_api.aspirate_in_place(flow_rate = self.config.flow_rate, volume = self.config.vol)
            globals.robot_api.move_relative('z', 20)

        self.state = RobotState.VERIFY_PICKUP

    def state_verify_pickup(self):
        globals.robot_api.move_to_coordinates((self.calib_origin[0],self.calib_origin[1],115), min_z_height=self.config.dish_bottom, verbose=False, force_direct=True)
        time.sleep(0.75)
        
        # Use frame capturer instead of direct camera read
        frame = self.frame_capturer.capture_frame("overview_cam_2")
        frame = globals.frame_ops.undistort_frame(frame)
        if frame is not None:
            self.current_frame = globals.frame_ops.undistort_frame(frame)
            self.cv_pipeline(self.current_frame)
        else:
            print("Failed to capture verification frame")
            self.state = RobotState.IDLE
            return

        plot_frame = self.current_frame.copy()
        self.draw_annotations(plot_frame)
        miss_occurred = False
        if self.cuboid_choice is not None and not self.cuboid_choice.empty:
            for prev_x, prev_y in self.cuboid_choice[['cX', 'cY']].values:
                cv2.circle(plot_frame, (int(prev_x), int(prev_y)), int(round(self.config.failure_threshold / self.one_d_ratio)), (255, 0, 0), 2)
                
                # Fix: Check if cr.cuboid_df exists and is not empty before filtering
                if not self.cr.cuboid_df.empty and 'bubble' in self.cr.cuboid_df.columns:
                    check_miss_df = self.cr.cuboid_df.loc[self.cr.cuboid_df['bubble'] == False].copy()
                    
                    if not check_miss_df.empty:
                        distances = check_miss_df.apply(lambda row: np.sqrt((row['cX'] - prev_x)**2 + (row['cY'] - prev_y)**2), axis=1).to_numpy()
                        distances *= self.one_d_ratio
                        if any(distances <= self.config.failure_threshold):
                            print(f"Miss detected at well {self.routine.current_well}.")
                            self.routine.update_well(success=False)
                            miss_occurred = True
                            self.logger.log(f"Miss detected at well {self.routine.current_well}.")

            if not miss_occurred:
                for _, _ in self.cuboid_choice[['cX', 'cY']].values:
                    self.routine.update_well(success=True)

        if miss_occurred:
            self.state = RobotState.DEPOSIT_BACK
        else:
            self.state = RobotState.TRANSFER_TO_WELL

        # Update global frame for display elsewhere
        globals.cuboid_picking_frame = plot_frame.copy()
        

    def state_deposit_liquid_back(self):
        x,y = self.world_coordinates[0]  # Use the first coordinate for depositing back
        globals.robot_api.move_to_coordinates((x, y, self.config.pickup_height+20), min_z_height=self.config.dish_bottom, verbose=False, force_direct=True)
        globals.robot_api.move_to_coordinates((x, y, self.config.pickup_height+0.5), min_z_height=self.config.dish_bottom, verbose=False, force_direct=True)
        globals.robot_api.dispense_in_place(flow_rate = self.config.flow_rate, volume = self.config.vol * len(self.world_coordinates))
        globals.robot_api.move_relative('z', 20)

        self.state = RobotState.CAPTURE_FRAME

    def state_transfer_to_well(self):

        globals.robot_api.move_to_well(globals.robot_api.labware_dct[str(self.config.destination_slot)], self.current_well, 
                             well_location='top', 
                             offset=(self.config.well_offset_x, self.config.well_offset_y, 5), 
                             verbose = False, 
                             force_direct = True)
        globals.robot_api.dispense(globals.robot_api.labware_dct[str(self.config.destination_slot)], self.current_well, 
                         well_location='bottom', 
                         offset=(self.config.well_offset_x, self.config.well_offset_y, self.config.deposit_offset_z), 
                         volume = self.config.vol * len(self.world_coordinates), 
                         flow_rate = self.config.flow_rate)
        
        time.sleep(self.config.wait_time_after_deposit)
        
        globals.robot_api.move_to_well(globals.robot_api.labware_dct[str(self.config.destination_slot)], self.current_well, 
                             well_location='top', 
                             offset=(self.config.well_offset_x, self.config.well_offset_y, 5), 
                             verbose=False)
        globals.robot_api.move_to_coordinates((self.calib_origin[0],self.calib_origin[1],115), 
                                    min_z_height=self.config.dish_bottom, 
                                    verbose=False, 
                                    force_direct=True)

        self.current_well = self.routine.get_next_well() # Check if the routine is done
        if self.routine.is_done():
            self.state = RobotState.COMPLETED
        else:
            self.state = RobotState.CAPTURE_FRAME

    def state_completed(self):
        self.end_time = time.time()
        print("Process completed successfully.")
        self.logger.log("Picking procedure finished.")
        cv2.destroyAllWindows()
        self.running = False
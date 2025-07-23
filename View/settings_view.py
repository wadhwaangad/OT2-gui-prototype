"""
Settings view for the microtissue manipulator GUI.
"""

import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                           QPushButton, QLabel, QGroupBox, QProgressBar,
                           QDoubleSpinBox, QLineEdit, QComboBox, QTextEdit, QScrollArea, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QSpinBox
from View.zoomable_video_widget import VideoDisplayWidget
class SettingsView(QWidget):
    """Settings view widget for robot control and configuration."""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setup_ui()
        self.setup_status_timer()
        self.update_robot_status()

    
    def setup_ui(self):
        """Setup the user interface."""
        # Create scroll area for the main content
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        main_layout = QVBoxLayout(scroll_widget)
        
        # Robot Control Section
        robot_group = self.create_robot_control_group()
        main_layout.addWidget(robot_group)
        
        # Configuration Section
        config_group = self.create_configuration_group()
        main_layout.addWidget(config_group)
        
        # Additional Functions Section
        additional_group = self.create_additional_functions_group()
        main_layout.addWidget(additional_group)
        
        # Set up scroll area
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        self.setLayout(layout)
    
    def create_robot_control_group(self):
        """Create robot control group."""
        group = QGroupBox("Robot Control")
        layout = QGridLayout()
        
        # Initialize Robot
        self.init_robot_btn = QPushButton("Initialize Robot")
        self.init_robot_btn.clicked.connect(self.on_initialize_robot)
        layout.addWidget(self.init_robot_btn, 0, 0)
        
        # Home Robot
        self.home_robot_btn = QPushButton("Home Robot")
        self.home_robot_btn.clicked.connect(self.on_home_robot)
        layout.addWidget(self.home_robot_btn, 0, 1)
        
        # Toggle Lights
        self.toggle_lights_btn = QPushButton("Toggle Lights")
        self.toggle_lights_btn.clicked.connect(self.on_toggle_lights)
        layout.addWidget(self.toggle_lights_btn, 0, 2)
        
        # Get Run Info
        self.get_run_info_btn = QPushButton("Get Run Info")
        self.get_run_info_btn.clicked.connect(self.on_get_run_info)
        layout.addWidget(self.get_run_info_btn, 1, 0)
        
        # Create Run
        self.create_run_btn = QPushButton("Create Run")
        self.create_run_btn.clicked.connect(self.on_create_run)
        layout.addWidget(self.create_run_btn, 1, 1)
        
        # Load Pipette
        self.load_pipette_btn = QPushButton("Load Pipette")
        self.load_pipette_btn.clicked.connect(self.on_load_pipette)
        layout.addWidget(self.load_pipette_btn, 1, 2)
        self.load_pipette_btn.clicked.connect(self.on_load_pipette)
        layout.addWidget(self.load_pipette_btn, 2, 0)
        
        # Placeholder buttons
        self.placeholder_btn_1 = QPushButton("Calibrate Camera")
        self.placeholder_btn_1.clicked.connect(self.on_calibrate_camera)
        layout.addWidget(self.placeholder_btn_1, 2, 1)
        
        self.placeholder_btn_2 = QPushButton("Placeholder 2")
        self.placeholder_btn_2.clicked.connect(self.on_placeholder_2)
        layout.addWidget(self.placeholder_btn_2, 2, 2)
        
        self.placeholder_btn_3 = QPushButton("Placeholder 3")
        self.placeholder_btn_3.clicked.connect(self.on_placeholder_3)
        layout.addWidget(self.placeholder_btn_3, 3, 0)
        
        group.setLayout(layout)
        return group
    
    def create_configuration_group(self):
        """Create configuration group."""
        group = QGroupBox("Configuration")
        layout = QGridLayout()

        # Slot selection checkboxes
        layout.addWidget(QLabel("Select Slots:"), 0, 0, 1, 4)
        
        # Create checkboxes for slots 1-12 in a 3x4 grid
        self.slot_checkboxes = {}
        for i in range(1, 13):
            row = 1 + (i - 1) // 4  # Rows 1, 2, 3
            col = (i - 1) % 4       # Columns 0, 1, 2, 3
            checkbox = QCheckBox(f"Slot {i}")
            self.slot_checkboxes[i] = checkbox
            layout.addWidget(checkbox, row, col)

        # X, Y, Z spinboxes moved down and spaced out
        layout.addWidget(QLabel("X:"), 4, 0)
        self.offset_x_spinbox = QDoubleSpinBox()
        self.offset_x_spinbox.setMinimum(-1000.0)
        self.offset_x_spinbox.setMaximum(1000.0)
        self.offset_x_spinbox.setDecimals(2)
        layout.addWidget(self.offset_x_spinbox, 4, 1)

        layout.addWidget(QLabel("Y:"), 5, 0)
        self.offset_y_spinbox = QDoubleSpinBox()
        self.offset_y_spinbox.setMinimum(-1000.0)
        self.offset_y_spinbox.setMaximum(1000.0)
        self.offset_y_spinbox.setDecimals(2)
        layout.addWidget(self.offset_y_spinbox, 5, 1)

        layout.addWidget(QLabel("Z:"), 6, 0)
        self.offset_z_spinbox = QDoubleSpinBox()
        self.offset_z_spinbox.setMinimum(-1000.0)
        self.offset_z_spinbox.setMaximum(1000.0)
        self.offset_z_spinbox.setDecimals(2)
        layout.addWidget(self.offset_z_spinbox, 6, 1)

        # Add Slot Offsets Button
        self.add_offsets_btn = QPushButton("Add Slot Offsets")
        self.add_offsets_btn.clicked.connect(self.on_add_slot_offsets)
        layout.addWidget(self.add_offsets_btn, 7, 0, 1, 2)

        group.setLayout(layout)
        return group
    
    def create_additional_functions_group(self):
        """Create additional functions group."""
        group = QGroupBox("Additional Functions")
        layout = QVBoxLayout()

        # Instructions (run name removed)
        instructions = QLabel("""
        Instructions:
        
        1. Initialize Robot: Connect to and initialize the robot system
        2. Add Slot Offsets: Configure positional offsets for precise alignment
        3. Toggle Lights: Turn robot lighting on/off
        4. Home Robot: Move robot to home position
        5. Get Run Info: Retrieve current run status and information
        6. Create Run: Initialize a new experimental run
        
        Note: Some functions require the robot to be initialized first.
        """)
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(instructions)

        group.setLayout(layout)
        return group
    
    def setup_status_timer(self):
        """Setup timer for status updates."""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_robot_status)
        self.status_timer.start(100)  # Update every 2 seconds
    
    def update_robot_status(self):
        """Update robot status display - only captures StreamRedirector output."""
        # All actual status updates come through the StreamRedirector
        pass
    
    # Event handlers
    def on_initialize_robot(self):
        """Handle initialize robot button click."""
        # Disable button to prevent multiple clicks
        self.init_robot_btn.setEnabled(False)
        
        def on_result(success):
            pass
        
        def on_error(error_msg):
            print(f"Robot initialization error: {error_msg}")
        
        def on_finished():
            # Re-enable button when done
            self.init_robot_btn.setEnabled(True)
        
        self.controller.initialize_robot(on_result=on_result, on_error=on_error, on_finished=on_finished)
    
    def on_home_robot(self):
        """Handle home robot button click."""
        def on_result(success):
            pass
        def on_error(error_msg):
            pass
        self.controller.home_robot(on_result=on_result, on_error=on_error, on_finished=lambda: None)
    
    def on_toggle_lights(self):
        """Handle toggle lights button click."""
        def on_result(success):
            pass
        def on_error(error_msg):
            pass
        self.controller.toggle_lights(on_result=on_result, on_error=on_error, on_finished=lambda: None)
    
    def on_get_run_info(self):
        """Handle get run info button click."""
        def on_result(run_info):
            # Update labware view when run info is retrieved
            if hasattr(self.controller, 'labware_view') and self.controller.labware_view:
                self.controller.labware_view.update_labware_list()
                self.controller.labware_view.update_deck_display()
        self.controller.get_run_info(on_result=on_result, on_finished=lambda: None)
    
    def on_create_run(self):
        """Handle create run button click (run name removed)."""
        run_config = {
            "timestamp": "2025-01-01 12:00:00",
            "status": "created"
        }
        def on_result(success):
            # Update labware view when run is created (clears labware)
            if hasattr(self.controller, 'labware_view') and self.controller.labware_view:
                self.controller.labware_view.update_labware_list()
                self.controller.labware_view.update_deck_display()
        self.controller.create_run(run_config, on_result=on_result, on_finished=lambda: None)
    
    def on_load_pipette(self):
        """Handle load pipette button click (removed from UI, but method kept for compatibility)."""
        def on_result(success):
            pass
        # No pipette type or mount selection
        self.controller.load_pipette(on_result=on_result, on_finished=lambda: None)
    
    def on_add_slot_offsets(self):
        """Handle add slot offsets button click."""
        x = self.offset_x_spinbox.value()
        y = self.offset_y_spinbox.value()
        z = self.offset_z_spinbox.value()
        # Get selected slots from checkboxes
        slots = [slot_num for slot_num, checkbox in self.slot_checkboxes.items() if checkbox.isChecked()]
        if not slots:
            return

        def on_result(success):
            pass
        self.controller.add_slot_offsets(slots, x, y, z, on_result=on_result, on_error=None, on_finished=lambda: None)
    
    def on_calibrate_camera(self):
        """Handle camera calibration button click."""
        cameras = self.controller.get_available_cameras()
        
        # Look for overview camera first
        overview_camera = None
        for camera_data in cameras:
            user_label, camera_index, cam_name, default_res = camera_data
            if "overview_cam" in user_label.lower():
                overview_camera = (cam_name, camera_index, user_label)
                break
        
        if overview_camera:
            # Open camera test window for overview camera
            cam_name, camera_index, user_label = overview_camera
            self.open_camera_test_window(cam_name, camera_index, user_label)
        else:
            # No overview camera found, run general calibration
            def on_result(success):
                if success:
                    print("Camera calibration completed successfully")
                else:
                    print("Camera calibration failed")
            
            def on_error(error_msg):
                print(f"Camera calibration error: {error_msg}")
            
            self.controller.calibrate_camera(on_result=on_result, on_error=on_error, on_finished=lambda: None)

    def on_placeholder_2(self):
        """Handle placeholder 2 button click."""
        def on_result(success):
            pass
        self.controller.placeholder_function_2(on_result=on_result, on_finished=lambda: None)
    
    def on_placeholder_3(self):
        """Handle placeholder 3 button click."""
        def on_result(success):
            pass
        self.controller.placeholder_function_3(on_result=on_result, on_finished=lambda: None)

    def open_camera_test_window(self, camera_name, camera_index):
        """Open a separate window for camera testing."""
        self.camera_test_window = CameraTestWindow(camera_name, camera_index, self.controller)
        self.camera_test_window.show()



class CameraTestWindow(QDialog):
    """Separate window for testing individual cameras."""

    def __init__(self, camera_name: str, camera_index: int, user_label: str, controller, parent=None):
        super().__init__(parent)
        self.camera_name = camera_name
        self.user_label = user_label
        self.camera_index = camera_index
        self.controller = controller
        self.is_capturing = False
        
        self.setWindowTitle(f"Camera Calibration - {self.user_label}")
        self.setMinimumSize(800, 600)
        
        self.setup_ui()
        self.setup_timer()
        
        # Start camera capture
        self.start_capture()
    
    def setup_ui(self):
        """Setup the user interface."""
        import os, json
        layout = QVBoxLayout()

        # Camera info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"Camera: {self.user_label}"))
        info_layout.addWidget(QLabel(f"Index: {self.camera_index}"))
        info_layout.addStretch()

        # Camera controls
        controls_group = QGroupBox("Camera Controls")
        controls_layout = QHBoxLayout()

        # Resolution selection
        res_layout = QVBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))
        res_input_layout = QHBoxLayout()
        self.res_combo = QComboBox()
        self.custom_width = None
        self.custom_height = None
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cam_configs")
        config_file = os.path.join(config_dir, f"{self.user_label}.json")
        resolutions = []
        default_res = (640, 480)
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                resolutions = config.get("resolutions", [])
                default_res = tuple(config.get("default_resolution", [640, 480]))
            except Exception:
                resolutions = []
                default_res = (640, 480)
        if resolutions:
            for w, h in resolutions:
                self.res_combo.addItem(f"{w} x {h}", (w, h))
            # Set to default resolution if present
            default_index = 0
            for i in range(self.res_combo.count()):
                if self.res_combo.itemData(i) == default_res:
                    default_index = i
                    break
            self.res_combo.setCurrentIndex(default_index)
            res_input_layout.addWidget(self.res_combo)
        else:
            self.custom_width = QSpinBox()
            self.custom_width.setRange(1, 10000)
            self.custom_width.setValue(default_res[0])
            self.custom_width.setPrefix("W: ")
            self.custom_height = QSpinBox()
            self.custom_height.setRange(1, 10000)
            self.custom_height.setValue(default_res[1])
            self.custom_height.setPrefix("H: ")
            res_input_layout.addWidget(self.custom_width)
            res_input_layout.addWidget(self.custom_height)
        res_layout.addLayout(res_input_layout)

        # Control buttons
        button_layout = QVBoxLayout()
        self.reset_view_btn = QPushButton("Reset View")
        self.reset_view_btn.clicked.connect(self.reset_view)
        button_layout.addWidget(self.reset_view_btn)

        self.capture_btn = QPushButton("Stop Capture")
        self.capture_btn.clicked.connect(self.toggle_capture)
        button_layout.addWidget(self.capture_btn)

        controls_layout.addLayout(res_layout)
        controls_layout.addLayout(button_layout)
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)

        # Video display
        self.video_display = VideoDisplayWidget()

        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.close)

        # Add to main layout
        layout.addLayout(info_layout)
        layout.addWidget(controls_group)
        layout.addWidget(self.video_display)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def get_selected_resolution(self):
        if self.res_combo and self.res_combo.count() > 0:
            return self.res_combo.currentData()
        elif self.custom_width and self.custom_height:
            return (self.custom_width.value(), self.custom_height.value())
        return (640, 480)
    
    def setup_timer(self):
        """Setup timer for video updates."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)  # ~30 FPS
    
    def start_capture(self):
        """Start camera capture."""
        width, height = self.get_selected_resolution()
        success = self.controller.start_camera_capture(
            self.camera_name,
            self.camera_index,
            width=width,
            height=height
        )
        if success:
            self.is_capturing = True
            self.capture_btn.setText("Stop Capture")
        else:
            pass  # Backend handles error messaging
    
    def stop_capture(self):
        """Stop camera capture."""
        self.controller.stop_camera_capture(self.camera_name)
        self.is_capturing = False
        self.capture_btn.setText("Start Capture")
        self.video_display.clear_frame()
    
    def toggle_capture(self):
        """Toggle camera capture."""
        if self.is_capturing:
            self.stop_capture()
        else:
            self.start_capture()
    
    def update_frame(self):
        """Update the video frame."""
        if self.is_capturing:
            ret, frame = self.controller.get_camera_frame(self.camera_name)
            if ret and frame is not None:
                self.video_display.set_frame(frame)
    
    
    def reset_view(self):
        """Reset the video view."""
        self.video_display.reset_view()
    
    def closeEvent(self, event):
        """Handle close event."""
        self.timer.stop()
        if self.is_capturing:
            self.stop_capture()
        event.accept()

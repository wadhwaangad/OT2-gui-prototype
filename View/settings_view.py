"""
Settings view for the microtissue manipulator GUI.
"""

import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                           QPushButton, QLabel, QGroupBox, QProgressBar,
                           QDoubleSpinBox, QLineEdit, QComboBox, QTextEdit, QScrollArea, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


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
        self.placeholder_btn_1 = QPushButton("Placeholder 1")
        self.placeholder_btn_1.clicked.connect(self.on_placeholder_1)
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

        # Slot selection list (expanded size)
        layout.addWidget(QLabel("Select Slots:"), 0, 0, 1, 2)
        self.slot_list_widget = QListWidget()
        self.slot_list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.slot_list_widget.setMinimumHeight(120)  # Make the slot list taller
        self.slot_list_widget.setMinimumWidth(120)   # Make the slot list wider
        for i in range(1, 13):
            self.slot_list_widget.addItem(QListWidgetItem(str(i)))
        layout.addWidget(self.slot_list_widget, 1, 0, 1, 2)

        # X, Y, Z spinboxes moved down and spaced out
        layout.addWidget(QLabel("X:"), 2, 0)
        self.offset_x_spinbox = QDoubleSpinBox()
        self.offset_x_spinbox.setMinimum(-1000.0)
        self.offset_x_spinbox.setMaximum(1000.0)
        self.offset_x_spinbox.setDecimals(2)
        layout.addWidget(self.offset_x_spinbox, 2, 1)

        layout.addWidget(QLabel("Y:"), 3, 0)
        self.offset_y_spinbox = QDoubleSpinBox()
        self.offset_y_spinbox.setMinimum(-1000.0)
        self.offset_y_spinbox.setMaximum(1000.0)
        self.offset_y_spinbox.setDecimals(2)
        layout.addWidget(self.offset_y_spinbox, 3, 1)

        layout.addWidget(QLabel("Z:"), 4, 0)
        self.offset_z_spinbox = QDoubleSpinBox()
        self.offset_z_spinbox.setMinimum(-1000.0)
        self.offset_z_spinbox.setMaximum(1000.0)
        self.offset_z_spinbox.setDecimals(2)
        layout.addWidget(self.offset_z_spinbox, 4, 1)

        # Add Slot Offsets Button
        self.add_offsets_btn = QPushButton("Add Slot Offsets")
        self.add_offsets_btn.clicked.connect(self.on_add_slot_offsets)
        layout.addWidget(self.add_offsets_btn, 5, 0, 1, 2)

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
        # Get selected slots as a list of ints
        selected_items = self.slot_list_widget.selectedItems()
        slots = [int(item.text()) for item in selected_items]
        if not slots:
            return

        def on_result(success):
            pass
        self.controller.add_slot_offsets(slots, x, y, z, on_result=on_result, on_error=None, on_finished=lambda: None)
    
    def on_placeholder_1(self):
        """Handle placeholder 1 button click."""
        def on_result(success):
            pass
        self.controller.placeholder_function_1(on_result=on_result, on_finished=lambda: None)
    
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

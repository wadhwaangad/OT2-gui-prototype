from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, 
                           QLabel, QGroupBox, QLineEdit, QFormLayout, QDoubleSpinBox, QComboBox, 
                           QSpinBox, QTextEdit, QScrollArea)
from PyQt6.QtCore import Qt

class ManualMovementView(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface for manual movement controls."""
        # Create scroll area for the content
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Manual Movement Controls")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Movement controls group
        movement_group = QGroupBox("Robot Movement")
        movement_layout = QVBoxLayout()
        
        # Coordinate input section
        coord_group = QGroupBox("Move Robot to Coordinates")
        coord_layout = QVBoxLayout()
        
        # Coordinate inputs in a grid
        coord_inputs_layout = QGridLayout()
        coord_inputs_layout.setSpacing(5)  # Reduce spacing between widgets
        
        # X coordinate input
        coord_inputs_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_input = QDoubleSpinBox()
        self.x_input.setRange(-1000, 1000)
        self.x_input.setDecimals(2)
        self.x_input.setMaximumWidth(100)  # Limit width
        coord_inputs_layout.addWidget(self.x_input, 0, 1)
        
        # Y coordinate input
        coord_inputs_layout.addWidget(QLabel("Y:"), 0, 2)
        self.y_input = QDoubleSpinBox()
        self.y_input.setRange(-1000, 1000)
        self.y_input.setDecimals(2)
        self.y_input.setMaximumWidth(100)  # Limit width
        coord_inputs_layout.addWidget(self.y_input, 0, 3)
        
        # Z coordinate input
        coord_inputs_layout.addWidget(QLabel("Z:"), 0, 4)
        self.z_input = QDoubleSpinBox()
        self.z_input.setRange(-1000, 1000)
        self.z_input.setDecimals(2)
        self.z_input.setMaximumWidth(100)  # Limit width
        coord_inputs_layout.addWidget(self.z_input, 0, 5)
        
        # Move robot button in same row
        self.move_robot_btn = QPushButton("Move Robot")
        self.move_robot_btn.clicked.connect(self.on_move_robot)
        self.move_robot_btn.setMinimumSize(80, 30)
        coord_inputs_layout.addWidget(self.move_robot_btn, 0, 6)
        
        coord_layout.addLayout(coord_inputs_layout)
        
        coord_group.setLayout(coord_layout)
        movement_layout.addWidget(coord_group)
        
        # Axis retraction section
        retract_group = QGroupBox("Retract Axis")
        retract_layout = QVBoxLayout()
        
        # Axis selection and button in one row
        retract_row = QHBoxLayout()
        retract_row.setSpacing(5)  # Reduce spacing
        retract_row.addWidget(QLabel("Axis:"))
        self.retract_axis_combo = QComboBox()
        self.retract_axis_combo.addItems(["x", "y", "leftZ", "rightZ", "leftPlunger", "rightPlunger", "extensionZ", "extensionJaw", "axis96ChannelCam"])
        self.retract_axis_combo.setMaximumWidth(120)  # Limit width
        retract_row.addWidget(self.retract_axis_combo)
        
        # Retract axis button
        self.retract_axis_btn = QPushButton("Retract Axis")
        self.retract_axis_btn.clicked.connect(self.on_retract_axis)
        self.retract_axis_btn.setMinimumSize(80, 30)
        retract_row.addWidget(self.retract_axis_btn)
        retract_row.addStretch()
        
        retract_layout.addLayout(retract_row)
        
        retract_group.setLayout(retract_layout)
        movement_layout.addWidget(retract_group)
        
        movement_group.setLayout(movement_layout)
        layout.addWidget(movement_group)
        
        # Pipetting Controls Group
        pipetting_group = QGroupBox("Pipetting Operations")
        pipetting_layout = QVBoxLayout()
        
        # In-place operations parameters
        inplace_group = QGroupBox("In-Place Operation Parameters")
        inplace_layout = QFormLayout()
        
        # Aspirate in-place parameters
        aspirate_params_layout = QHBoxLayout()
        aspirate_params_layout.setSpacing(5)  # Reduce spacing
        self.aspirate_volume_input = QSpinBox()
        self.aspirate_volume_input.setRange(1, 1000)
        self.aspirate_volume_input.setValue(25)
        self.aspirate_volume_input.setSuffix(" uL")
        self.aspirate_volume_input.setMaximumWidth(80)  # Limit width
        aspirate_params_layout.addWidget(QLabel("Volume:"))
        aspirate_params_layout.addWidget(self.aspirate_volume_input)
        
        self.aspirate_flow_rate_input = QSpinBox()
        self.aspirate_flow_rate_input.setRange(1, 1000)
        self.aspirate_flow_rate_input.setValue(25)
        self.aspirate_flow_rate_input.setSuffix(" uL/s")
        self.aspirate_flow_rate_input.setMaximumWidth(80)  # Limit width
        aspirate_params_layout.addWidget(QLabel("Flow Rate:"))
        aspirate_params_layout.addWidget(self.aspirate_flow_rate_input)
        
        self.set_aspirate_params_btn = QPushButton("Set Aspirate Params (A)")
        self.set_aspirate_params_btn.clicked.connect(self.on_set_aspirate_params)
        self.set_aspirate_params_btn.setMinimumSize(100, 25)  # Smaller button
        aspirate_params_layout.addWidget(self.set_aspirate_params_btn)
        aspirate_params_layout.addStretch()  # Add stretch to prevent over-expansion
        
        inplace_layout.addRow("Aspirate In-Place:", aspirate_params_layout)
        
        # Dispense in-place parameters
        dispense_params_layout = QHBoxLayout()
        dispense_params_layout.setSpacing(5)  # Reduce spacing
        self.dispense_volume_input = QSpinBox()
        self.dispense_volume_input.setRange(1, 1000)
        self.dispense_volume_input.setValue(25)
        self.dispense_volume_input.setSuffix(" uL")
        self.dispense_volume_input.setMaximumWidth(80)  # Limit width
        dispense_params_layout.addWidget(QLabel("Volume:"))
        dispense_params_layout.addWidget(self.dispense_volume_input)
        
        self.dispense_flow_rate_input = QSpinBox()
        self.dispense_flow_rate_input.setRange(1, 1000)
        self.dispense_flow_rate_input.setValue(25)
        self.dispense_flow_rate_input.setSuffix(" uL/s")
        self.dispense_flow_rate_input.setMaximumWidth(80)  # Limit width
        dispense_params_layout.addWidget(QLabel("Flow Rate:"))
        dispense_params_layout.addWidget(self.dispense_flow_rate_input)
        
        self.dispense_pushout_input = QSpinBox()
        self.dispense_pushout_input.setRange(0, 100)
        self.dispense_pushout_input.setValue(0)
        self.dispense_pushout_input.setSuffix(" uL")
        self.dispense_pushout_input.setMaximumWidth(80)  # Limit width
        dispense_params_layout.addWidget(QLabel("Pushout:"))
        dispense_params_layout.addWidget(self.dispense_pushout_input)
        
        self.set_dispense_params_btn = QPushButton("Set Dispense Params (D)")
        self.set_dispense_params_btn.clicked.connect(self.on_set_dispense_params)
        self.set_dispense_params_btn.setMinimumSize(100, 25)  # Smaller button
        dispense_params_layout.addWidget(self.set_dispense_params_btn)
        dispense_params_layout.addStretch()  # Add stretch to prevent over-expansion
        
        inplace_layout.addRow("Dispense In-Place:", dispense_params_layout)
        
        # Blow out in-place parameters
        blow_out_params_layout = QHBoxLayout()
        blow_out_params_layout.setSpacing(5)  # Reduce spacing
        self.blow_out_flow_rate_input = QSpinBox()
        self.blow_out_flow_rate_input.setRange(1, 1000)
        self.blow_out_flow_rate_input.setValue(25)
        self.blow_out_flow_rate_input.setSuffix(" uL/s")
        self.blow_out_flow_rate_input.setMaximumWidth(80)  # Limit width
        blow_out_params_layout.addWidget(QLabel("Flow Rate:"))
        blow_out_params_layout.addWidget(self.blow_out_flow_rate_input)
        
        self.set_blow_out_params_btn = QPushButton("Set Blow Out Params (B)")
        self.set_blow_out_params_btn.clicked.connect(self.on_set_blow_out_params)
        self.set_blow_out_params_btn.setMinimumSize(100, 25)  # Smaller button
        blow_out_params_layout.addWidget(self.set_blow_out_params_btn)
        blow_out_params_layout.addStretch()  # Add stretch to prevent over-expansion
        
        inplace_layout.addRow("Blow Out In-Place:", blow_out_params_layout)
        
        inplace_group.setLayout(inplace_layout)
        pipetting_layout.addWidget(inplace_group)
        
        # Regular pipetting operations
        regular_pipetting_group = QGroupBox("Well-Based Pipetting Operations")
        regular_pipetting_layout = QVBoxLayout()
        
        # Drop tip button
        drop_tip_row = QHBoxLayout()
        drop_tip_row.setSpacing(5)  # Reduce spacing
        self.drop_tip_btn = QPushButton("Drop Tip in Place")
        self.drop_tip_btn.clicked.connect(self.on_drop_tip_in_place)
        self.drop_tip_btn.setMinimumSize(100, 30)  # Smaller button
        drop_tip_row.addWidget(self.drop_tip_btn)
        drop_tip_row.addStretch()
        regular_pipetting_layout.addLayout(drop_tip_row)
        
        # Operation selection dropdown
        operation_selection_row = QHBoxLayout()
        operation_selection_row.setSpacing(5)  # Reduce spacing
        operation_selection_row.addWidget(QLabel("Select Operation:"))
        self.operation_combo = QComboBox()
        self.operation_combo.addItems(["Aspirate", "Dispense", "Blow Out"])
        self.operation_combo.currentTextChanged.connect(self.on_operation_changed)
        self.operation_combo.setMaximumWidth(120)  # Limit width
        operation_selection_row.addWidget(self.operation_combo)
        operation_selection_row.addStretch()
        regular_pipetting_layout.addLayout(operation_selection_row)
        
        # Dynamic operation section
        self.operation_section = QGroupBox("Operation Details")
        self.operation_section_layout = QFormLayout()
        
        # Common inputs for all operations
        # Slot number
        self.slot_input = QSpinBox()
        self.slot_input.setRange(1, 11)
        self.slot_input.setValue(1)
        self.slot_input.setMaximumWidth(60)  # Limit width
        self.operation_section_layout.addRow("Slot Number:", self.slot_input)
        
        # Well name
        self.well_name_input = QLineEdit()
        self.well_name_input.setPlaceholderText("e.g., A1")
        self.well_name_input.setMaximumWidth(80)  # Limit width
        self.operation_section_layout.addRow("Well Name:", self.well_name_input)
        
        # Well location
        self.well_location_combo = QComboBox()
        self.well_location_combo.addItems(["top", "bottom", "center"])
        self.well_location_combo.setMaximumWidth(80)  # Limit width
        self.operation_section_layout.addRow("Well Location:", self.well_location_combo)
        
        # Parameters row (will be populated dynamically)
        self.params_row = QHBoxLayout()
        self.params_row_widget = QWidget()
        self.params_row_widget.setLayout(self.params_row)
        self.operation_section_layout.addRow("Parameters:", self.params_row_widget)
        
        # Offset inputs (for Aspirate and Dispense only)
        self.offset_row = QHBoxLayout()
        self.offset_row.setSpacing(5)  # Reduce spacing
        self.x_offset_input = QDoubleSpinBox()
        self.x_offset_input.setRange(-100, 100)
        self.x_offset_input.setDecimals(2)
        self.x_offset_input.setMaximumWidth(70)  # Limit width
        self.offset_row.addWidget(QLabel("X:"))
        self.offset_row.addWidget(self.x_offset_input)
        
        self.y_offset_input = QDoubleSpinBox()
        self.y_offset_input.setRange(-100, 100)
        self.y_offset_input.setDecimals(2)
        self.y_offset_input.setMaximumWidth(70)  # Limit width
        self.offset_row.addWidget(QLabel("Y:"))
        self.offset_row.addWidget(self.y_offset_input)
        
        self.z_offset_input = QDoubleSpinBox()
        self.z_offset_input.setRange(-100, 100)
        self.z_offset_input.setDecimals(2)
        self.z_offset_input.setMaximumWidth(70)  # Limit width
        self.offset_row.addWidget(QLabel("Z:"))
        self.offset_row.addWidget(self.z_offset_input)
        
        self.volume_offset_input = QSpinBox()
        self.volume_offset_input.setRange(0, 1000)
        self.volume_offset_input.setMaximumWidth(70)  # Limit width
        self.offset_row.addWidget(QLabel("Vol Offset:"))
        self.offset_row.addWidget(self.volume_offset_input)
        self.offset_row.addStretch()  # Add stretch to prevent over-expansion
        
        self.offset_row_widget = QWidget()
        self.offset_row_widget.setLayout(self.offset_row)
        self.operation_section_layout.addRow("Offsets:", self.offset_row_widget)
        
        # Action button
        self.action_btn = QPushButton("Aspirate")
        self.action_btn.setMinimumSize(80, 30)  # Smaller button
        self.operation_section_layout.addRow(self.action_btn)
        
        self.operation_section.setLayout(self.operation_section_layout)
        regular_pipetting_layout.addWidget(self.operation_section)
        
        # Initialize the first operation (Aspirate)
        self.setup_operation_inputs("Aspirate")
        
        regular_pipetting_group.setLayout(regular_pipetting_layout)
        pipetting_layout.addWidget(regular_pipetting_group)
        
        pipetting_group.setLayout(pipetting_layout)
        layout.addWidget(pipetting_group)
        
        # Keyboard Movement Controls Group
        keyboard_group = QGroupBox("Keyboard Movement Controls")
        keyboard_layout = QVBoxLayout()
        
        # Keyboard control buttons
        keyboard_button_row = QHBoxLayout()
        
        self.keyboard_activate_btn = QPushButton("Activate Keyboard Movement")
        self.keyboard_activate_btn.clicked.connect(self.on_activate_keyboard)
        self.keyboard_activate_btn.setMinimumSize(150, 40)
        self.keyboard_activate_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        keyboard_button_row.addWidget(self.keyboard_activate_btn)

        self.keyboard_deactivate_btn = QPushButton("Deactivate Keyboard Movement")
        self.keyboard_deactivate_btn.clicked.connect(self.on_deactivate_keyboard)
        self.keyboard_deactivate_btn.setMinimumSize(150, 40)
        self.keyboard_deactivate_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.keyboard_deactivate_btn.setEnabled(False)
        keyboard_button_row.addWidget(self.keyboard_deactivate_btn)
        
        keyboard_layout.addLayout(keyboard_button_row)
        
        # Step size controls
        step_row = QHBoxLayout()
        
        step_label = QLabel("Step Size (mm):")
        step_row.addWidget(step_label)
        
        self.step_display = QLabel("1.0")
        self.step_display.setStyleSheet("font-weight: bold; font-size: 14px;")
        step_row.addWidget(self.step_display)
        
        self.decrease_step_btn = QPushButton("- Decrease")
        self.decrease_step_btn.clicked.connect(self.on_decrease_step)
        self.decrease_step_btn.setMinimumSize(80, 30)
        step_row.addWidget(self.decrease_step_btn)
        
        self.increase_step_btn = QPushButton("+ Increase")
        self.increase_step_btn.clicked.connect(self.on_increase_step)
        self.increase_step_btn.setMinimumSize(80, 30)
        step_row.addWidget(self.increase_step_btn)
        
        step_row.addStretch()
        keyboard_layout.addLayout(step_row)
        
        # Keyboard instructions
        instructions = QLabel(
            "Keyboard Controls (when activated):\n"
            "• Arrow Keys: Move X/Y axes\n"
            "• Page Up/Down: Move Z axis\n"
            "• +/- Keys: Adjust step size\n"
            "• S Key: Save current position\n"
            "• A Key: Aspirate in place\n"
            "• D Key: Dispense in place\n"
            "• B Key: Blow out in place"
        )
        instructions.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px; color: black;")
        keyboard_layout.addWidget(instructions)
        
        # Position management
        position_row = QHBoxLayout()
        
        self.save_position_btn = QPushButton("Save Current Position")
        self.save_position_btn.clicked.connect(self.on_save_position)
        self.save_position_btn.setMinimumSize(120, 30)
        position_row.addWidget(self.save_position_btn)
        
        self.clear_positions_btn = QPushButton("Clear Saved Positions")
        self.clear_positions_btn.clicked.connect(self.on_clear_positions)
        self.clear_positions_btn.setMinimumSize(120, 30)
        position_row.addWidget(self.clear_positions_btn)
        
        self.show_positions_btn = QPushButton("Show Saved Positions")
        self.show_positions_btn.clicked.connect(self.on_show_positions)
        self.show_positions_btn.setMinimumSize(120, 30)
        position_row.addWidget(self.show_positions_btn)
        
        position_row.addStretch()
        keyboard_layout.addLayout(position_row)
        
        # Saved positions display
        self.positions_display = QTextEdit()
        self.positions_display.setMaximumHeight(100)
        self.positions_display.setReadOnly(True)
        self.positions_display.setPlaceholderText("Saved positions will appear here...")
        keyboard_layout.addWidget(self.positions_display)
        
        keyboard_group.setLayout(keyboard_layout)
        layout.addWidget(keyboard_group)
        
        # Add spacer
        layout.addStretch()
        
        scroll_widget.setLayout(layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # Main layout for the view
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def on_activate_keyboard(self):
        """Activate keyboard movement controls."""
        success = self.controller.activate_keyboard_movement()
        if success:
            self.keyboard_activate_btn.setEnabled(False)
            self.keyboard_deactivate_btn.setEnabled(True)
            self.update_step_display()
            print("Keyboard movement activated successfully")
        else:
            print("Failed to activate keyboard movement")

    def on_deactivate_keyboard(self):
        """Deactivate keyboard movement controls."""
        success = self.controller.deactivate_keyboard_movement()
        if success:
            self.keyboard_activate_btn.setEnabled(True)
            self.keyboard_deactivate_btn.setEnabled(False)
            print("Keyboard movement deactivated successfully")
        else:
            print("Failed to deactivate keyboard movement")

    def on_increase_step(self):
        """Increase step size."""
        success = self.controller.increase_step()
        if success:
            self.update_step_display()

    def on_decrease_step(self):
        """Decrease step size."""
        success = self.controller.decrease_step()
        if success:
            self.update_step_display()

    def update_step_display(self):
        """Update the step size display."""
        step = self.controller.get_current_step()
        self.step_display.setText(f"{step}")

    def on_save_position(self):
        """Save current position."""
        success = self.controller.save_position()
        if success:
            self.update_positions_display()

    def on_clear_positions(self):
        """Clear all saved positions."""
        self.controller.clear_saved_positions()
        self.update_positions_display()

    def on_show_positions(self):
        """Show saved positions."""
        self.update_positions_display()

    def update_positions_display(self):
        """Update the positions display."""
        positions = self.controller.get_saved_positions()
        if positions:
            text = "Saved Positions:\n"
            for i, (x, y, z) in enumerate(positions, 1):
                text += f"{i}. X: {x:.2f}, Y: {y:.2f}, Z: {z:.2f}\n"
        else:
            text = "No saved positions"
        self.positions_display.setText(text)
    
    def on_drop_tip_in_place(self):
        """Drop tip in place."""
        success = self.controller.drop_tip_in_place()
        if not success:
            print("Failed to drop tip in place")

    def on_operation_changed(self, operation):
        """Handle operation selection change."""
        self.setup_operation_inputs(operation)
    
    def setup_operation_inputs(self, operation):
        """Setup input fields based on selected operation."""
        # Clear existing parameter widgets
        while self.params_row.count():
            child = self.params_row.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Setup parameters based on operation type
        if operation == "Aspirate":
            self.setup_aspirate_inputs()
            self.offset_row_widget.setVisible(True)
            self.action_btn.setText("Aspirate")
            try:
                self.action_btn.clicked.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            self.action_btn.clicked.connect(self.on_aspirate)
            
        elif operation == "Dispense":
            self.setup_dispense_inputs()
            self.offset_row_widget.setVisible(True)
            self.action_btn.setText("Dispense")
            try:
                self.action_btn.clicked.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            self.action_btn.clicked.connect(self.on_dispense)
            
        elif operation == "Blow Out":
            self.setup_blow_out_inputs()
            self.offset_row_widget.setVisible(False)
            self.action_btn.setText("Blow Out")
            try:
                self.action_btn.clicked.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            self.action_btn.clicked.connect(self.on_blow_out)
    
    def setup_aspirate_inputs(self):
        """Setup inputs for aspirate operation."""
        # Volume input
        self.volume_input = QSpinBox()
        self.volume_input.setRange(1, 1000)
        self.volume_input.setValue(25)
        self.volume_input.setSuffix(" uL")
        self.volume_input.setMaximumWidth(80)  # Limit width
        self.params_row.addWidget(QLabel("Volume:"))
        self.params_row.addWidget(self.volume_input)
        
        # Flow rate input
        self.flow_rate_input = QSpinBox()
        self.flow_rate_input.setRange(1, 1000)
        self.flow_rate_input.setValue(25)
        self.flow_rate_input.setSuffix(" uL/s")
        self.flow_rate_input.setMaximumWidth(80)  # Limit width
        self.params_row.addWidget(QLabel("Flow Rate:"))
        self.params_row.addWidget(self.flow_rate_input)
        self.params_row.addStretch()  # Add stretch to prevent over-expansion
    
    def setup_dispense_inputs(self):
        """Setup inputs for dispense operation."""
        # Volume input
        self.volume_input = QSpinBox()
        self.volume_input.setRange(1, 1000)
        self.volume_input.setValue(25)
        self.volume_input.setSuffix(" uL")
        self.volume_input.setMaximumWidth(80)  # Limit width
        self.params_row.addWidget(QLabel("Volume:"))
        self.params_row.addWidget(self.volume_input)
        
        # Flow rate input
        self.flow_rate_input = QSpinBox()
        self.flow_rate_input.setRange(1, 1000)
        self.flow_rate_input.setValue(25)
        self.flow_rate_input.setSuffix(" uL/s")
        self.flow_rate_input.setMaximumWidth(80)  # Limit width
        self.params_row.addWidget(QLabel("Flow Rate:"))
        self.params_row.addWidget(self.flow_rate_input)
        
        # Pushout input
        self.pushout_input = QSpinBox()
        self.pushout_input.setRange(0, 100)
        self.pushout_input.setValue(0)
        self.pushout_input.setSuffix(" uL")
        self.pushout_input.setMaximumWidth(80)  # Limit width
        self.params_row.addWidget(QLabel("Pushout:"))
        self.params_row.addWidget(self.pushout_input)
        self.params_row.addStretch()  # Add stretch to prevent over-expansion
    
    def setup_blow_out_inputs(self):
        """Setup inputs for blow out operation."""
        # Flow rate input only
        self.flow_rate_input = QSpinBox()
        self.flow_rate_input.setRange(1, 1000)
        self.flow_rate_input.setValue(25)
        self.flow_rate_input.setSuffix(" uL/s")
        self.flow_rate_input.setMaximumWidth(80)  # Limit width
        self.params_row.addWidget(QLabel("Flow Rate:"))
        self.params_row.addWidget(self.flow_rate_input)
        self.params_row.addStretch()  # Add stretch to prevent over-expansion

    def on_move_robot(self):
        """Handle move robot to coordinates action."""
        x = self.x_input.value()
        y = self.y_input.value()
        z = self.z_input.value()
        
        print(f"Moving robot to coordinates: X={x}, Y={y}, Z={z}")
        success = self.controller.move_robot(x, y, z)
        if not success:
            print(f"Failed to move robot to coordinates X={x}, Y={y}, Z={z}")

    def on_retract_axis(self):
        """Handle retract axis button action."""
        axis = self.retract_axis_combo.currentText()
        print(f"Retracting axis: {axis}")
        success = self.controller.retract_axis(axis)
        if not success:
            print(f"Failed to retract axis: {axis}")
        else:
            print(f"Successfully retracted axis: {axis}")
    
    # Pipetting operation handlers
    def on_set_aspirate_params(self):
        """Set aspirate in-place parameters."""
        volume = self.aspirate_volume_input.value()
        flow_rate = self.aspirate_flow_rate_input.value()
        self.controller.set_aspirate_params(volume, flow_rate)

    def on_set_dispense_params(self):
        """Set dispense in-place parameters."""
        volume = self.dispense_volume_input.value()
        flow_rate = self.dispense_flow_rate_input.value()
        pushout = self.dispense_pushout_input.value()
        self.controller.set_dispense_params(volume, flow_rate, pushout)

    def on_set_blow_out_params(self):
        """Set blow out in-place parameters."""
        flow_rate = self.blow_out_flow_rate_input.value()
        self.controller.set_blow_out_params(flow_rate)

    def on_aspirate(self):
        """Handle aspirate button action."""
        slot_number = self.slot_input.value()
        well_name = self.well_name_input.text().strip()
        well_location = self.well_location_combo.currentText()
        
        if not well_name:
            print("Please enter a well name for aspirate operation")
            return
        
        # Get labware ID from slot number
        try:
            import Model.globals as globals
            if not globals.robot_api or not hasattr(globals.robot_api, 'labware_dct'):
                print("Robot API not initialized or labware dictionary not available")
                return
            
            labware_id = globals.robot_api.labware_dct.get(str(slot_number))
            if not labware_id:
                print(f"No labware found in slot {slot_number}. Please load labware first.")
                return
        except Exception as e:
            print(f"Error getting labware ID for slot {slot_number}: {e}")
            return
        
        offset = (
            self.x_offset_input.value(),
            self.y_offset_input.value(),
            self.z_offset_input.value()
        )
        volume_offset = self.volume_offset_input.value()
        volume = self.volume_input.value()
        flow_rate = self.flow_rate_input.value()
        
        print(f"Aspirating from slot {slot_number} (labware: {labware_id}), well {well_name}")
        success = self.controller.aspirate(labware_id, well_name, well_location, 
                                         offset, volume_offset, volume, flow_rate)
        if not success:
            print(f"Failed to aspirate from {well_name} in slot {slot_number}")

    def on_dispense(self):
        """Handle dispense button action."""
        slot_number = self.slot_input.value()
        well_name = self.well_name_input.text().strip()
        well_location = self.well_location_combo.currentText()
        
        if not well_name:
            print("Please enter a well name for dispense operation")
            return
        
        # Get labware ID from slot number
        try:
            import Model.globals as globals
            if not globals.robot_api or not hasattr(globals.robot_api, 'labware_dct'):
                print("Robot API not initialized or labware dictionary not available")
                return
            
            labware_id = globals.robot_api.labware_dct.get(str(slot_number))
            if not labware_id:
                print(f"No labware found in slot {slot_number}. Please load labware first.")
                return
        except Exception as e:
            print(f"Error getting labware ID for slot {slot_number}: {e}")
            return
        
        offset = (
            self.x_offset_input.value(),
            self.y_offset_input.value(),
            self.z_offset_input.value()
        )
        volume_offset = self.volume_offset_input.value()
        volume = self.volume_input.value()
        flow_rate = self.flow_rate_input.value()
        pushout = self.pushout_input.value()
        
        print(f"Dispensing to slot {slot_number} (labware: {labware_id}), well {well_name}")
        success = self.controller.dispense(labware_id, well_name, well_location, 
                                         offset, volume_offset, volume, flow_rate, pushout)
        if not success:
            print(f"Failed to dispense to {well_name} in slot {slot_number}")

    def on_blow_out(self):
        """Handle blow out button action."""
        slot_number = self.slot_input.value()
        well_name = self.well_name_input.text().strip()
        well_location = self.well_location_combo.currentText()
        
        if not well_name:
            print("Please enter a well name for blow out operation")
            return
        
        # Get labware ID from slot number
        try:
            import Model.globals as globals
            if not globals.robot_api or not hasattr(globals.robot_api, 'labware_dct'):
                print("Robot API not initialized or labware dictionary not available")
                return
            
            labware_id = globals.robot_api.labware_dct.get(str(slot_number))
            if not labware_id:
                print(f"No labware found in slot {slot_number}. Please load labware first.")
                return
        except Exception as e:
            print(f"Error getting labware ID for slot {slot_number}: {e}")
            return
        
        flow_rate = self.flow_rate_input.value()
        
        print(f"Blowing out to slot {slot_number} (labware: {labware_id}), well {well_name}")
        success = self.controller.blow_out(labware_id, well_name, well_location, flow_rate)
        if not success:
            print(f"Failed to blow out to {well_name} in slot {slot_number}")

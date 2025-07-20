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
        
        # Control buttons row
        button_row = QHBoxLayout()
        
        self.drop_tip_btn = QPushButton("Drop Tip in Place")
        self.drop_tip_btn.clicked.connect(self.on_drop_tip_in_place)
        self.drop_tip_btn.setMinimumSize(120, 40)
        button_row.addWidget(self.drop_tip_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.on_stop)
        self.stop_btn.setMinimumSize(80, 40)
        button_row.addWidget(self.stop_btn)
        
        movement_layout.addLayout(button_row)
        
        # Coordinate input section
        coord_group = QGroupBox("Move Robot to Coordinates")
        coord_layout = QFormLayout()
        
        # X coordinate input
        self.x_input = QDoubleSpinBox()
        self.x_input.setRange(-1000, 1000)
        self.x_input.setDecimals(2)
        coord_layout.addRow("X Coordinate:", self.x_input)
        
        # Y coordinate input
        self.y_input = QDoubleSpinBox()
        self.y_input.setRange(-1000, 1000)
        self.y_input.setDecimals(2)
        coord_layout.addRow("Y Coordinate:", self.y_input)
        
        # Z coordinate input
        self.z_input = QDoubleSpinBox()
        self.z_input.setRange(-1000, 1000)
        self.z_input.setDecimals(2)
        coord_layout.addRow("Z Coordinate:", self.z_input)
        
        # Move robot button
        self.move_robot_btn = QPushButton("Move Robot")
        self.move_robot_btn.clicked.connect(self.on_move_robot)
        self.move_robot_btn.setMinimumSize(100, 40)
        coord_layout.addRow(self.move_robot_btn)
        
        coord_group.setLayout(coord_layout)
        movement_layout.addWidget(coord_group)
        
        # Axis retraction section
        retract_group = QGroupBox("Retract Axis")
        retract_layout = QFormLayout()
        
        # Axis selection dropdown
        self.retract_axis_combo = QComboBox()
        self.retract_axis_combo.addItems(["x", "y", "leftZ", "rightZ", "leftPlunger", "rightPlunger", "extensionZ", "extensionJaw", "axis96ChannelCam"])
        retract_layout.addRow("Axis:", self.retract_axis_combo)
        
        # Retract axis button
        self.retract_axis_btn = QPushButton("Retract Axis")
        self.retract_axis_btn.clicked.connect(self.on_retract_axis)
        self.retract_axis_btn.setMinimumSize(100, 40)
        retract_layout.addRow(self.retract_axis_btn)
        
        retract_group.setLayout(retract_layout)
        movement_layout.addWidget(retract_group)
        
        movement_group.setLayout(movement_layout)
        layout.addWidget(movement_group)
        
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
            "• S Key: Save current position"
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
    
    def on_stop(self):
        """Handle stop button action."""
        success = self.controller.stop()
        if not success:
            print("Failed to stop")

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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, 
                           QLabel, QGroupBox, QLineEdit, QFormLayout, QDoubleSpinBox)
from PyQt6.QtCore import Qt

class ManualMovementView(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface for manual movement controls."""
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
        self.x_input.setSuffix(" mm")
        coord_layout.addRow("X Coordinate:", self.x_input)
        
        # Y coordinate input
        self.y_input = QDoubleSpinBox()
        self.y_input.setRange(-1000, 1000)
        self.y_input.setDecimals(2)
        self.y_input.setSuffix(" mm")
        coord_layout.addRow("Y Coordinate:", self.y_input)
        
        # Z coordinate input
        self.z_input = QDoubleSpinBox()
        self.z_input.setRange(-1000, 1000)
        self.z_input.setDecimals(2)
        self.z_input.setSuffix(" mm")
        coord_layout.addRow("Z Coordinate:", self.z_input)
        
        # Move robot button
        self.move_robot_btn = QPushButton("Move Robot")
        self.move_robot_btn.clicked.connect(self.on_move_robot)
        self.move_robot_btn.setMinimumSize(100, 40)
        coord_layout.addRow(self.move_robot_btn)
        
        coord_group.setLayout(coord_layout)
        movement_layout.addWidget(coord_group)
        
        movement_group.setLayout(movement_layout)
        layout.addWidget(movement_group)
        
        # Add spacer
        layout.addStretch()
        
        self.setLayout(layout)
    
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

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QGroupBox
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
        movement_layout = QGridLayout()
        
        # Create movement buttons in a cross pattern
        self.up_btn = QPushButton("Drop Tip in Place")
        self.up_btn.clicked.connect(self.on_drop_tip_in_place)
        movement_layout.addWidget(self.up_btn, 0, 1)
        
        self.left_btn = QPushButton("Left")
        self.left_btn.clicked.connect(self.on_move_left)
        movement_layout.addWidget(self.left_btn, 1, 0)
        
        self.right_btn = QPushButton("Right")
        self.right_btn.clicked.connect(self.on_move_right)
        movement_layout.addWidget(self.right_btn, 1, 2)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.on_stop)
        movement_layout.addWidget(self.stop_btn, 2, 1)

        # Forward/Backward buttons
        self.forward_btn = QPushButton("Forward")
        self.forward_btn.clicked.connect(self.on_move_forward)
        movement_layout.addWidget(self.forward_btn, 0, 3)
        
        self.backward_btn = QPushButton("Backward")
        self.backward_btn.clicked.connect(self.on_move_backward)
        movement_layout.addWidget(self.backward_btn, 2, 3)
        
        # Set button sizes
        for button in [self.up_btn, self.stop_btn, self.left_btn, self.right_btn, 
                      self.forward_btn, self.backward_btn]:
            button.setMinimumSize(80, 40)
        
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

    def on_move_left(self):
        """Handle move left button action."""
        success = self.controller.move_left()
        if not success:
            print("Failed to move left")
    
    def on_move_right(self):
        """Handle move right button action."""
        success = self.controller.move_right()
        if not success:
            print("Failed to move right")
    
    def on_move_forward(self):
        """Handle move forward button action."""
        success = self.controller.move_forward()
        if not success:
            print("Failed to move forward")
    
    def on_move_backward(self):
        """Handle move backward button action."""
        success = self.controller.move_backward()
        if not success:
            print("Failed to move backward")

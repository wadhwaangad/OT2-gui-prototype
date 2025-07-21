"""
Labware view for the microtissue manipulator GUI.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                           QPushButton, QLabel, QGroupBox, QComboBox, QListWidget,
                           QListWidgetItem, QFileDialog, QLineEdit,
                           QSpinBox, QTextEdit, QScrollArea, QFrame, QDialog,
                           QDialogButtonBox, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
import Model.globals as globals

class AddCustomLabwareDialog(QDialog):
    """Dialog for adding custom labware."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Custom Labware")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)
        
        self.type_edit = QLineEdit()
        form_layout.addRow("Type ID:", self.type_edit)
        
        self.description_edit = QLineEdit()
        form_layout.addRow("Description:", self.description_edit)
        
        self.rows_spinbox = QSpinBox()
        self.rows_spinbox.setMinimum(1)
        self.rows_spinbox.setMaximum(100)
        self.rows_spinbox.setValue(8)
        form_layout.addRow("Rows:", self.rows_spinbox)
        
        self.columns_spinbox = QSpinBox()
        self.columns_spinbox.setMinimum(1)
        self.columns_spinbox.setMaximum(100)
        self.columns_spinbox.setValue(12)
        form_layout.addRow("Columns:", self.columns_spinbox)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_labware_data(self):
        """Get the labware data from the dialog."""
        return {
            "name": self.name_edit.text(),
            "type": self.type_edit.text(),
            "description": self.description_edit.text(),
            "dimensions": {
                "rows": self.rows_spinbox.value(),
                "columns": self.columns_spinbox.value()
            }
        }


class DeckSlotWidget(QFrame):
    """Widget representing a single deck slot."""
    
    slot_clicked = pyqtSignal(str)
    
    def __init__(self, slot_number: str, parent=None):
        super().__init__(parent)
        self.slot_number = slot_number
        self.labware_info = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setMinimumSize(120, 80)
        self.setMaximumSize(120, 80)
        
        layout = QVBoxLayout()
        
        # Slot number label
        self.slot_label = QLabel(f"Slot {self.slot_number}")
        self.slot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slot_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.slot_label.setStyleSheet("color: black;")
        layout.addWidget(self.slot_label)
        
        # Labware info label
        self.labware_label = QLabel("Empty")
        self.labware_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labware_label.setWordWrap(True)
        self.labware_label.setFont(QFont("Arial", 8))
        self.labware_label.setStyleSheet("color: black;")
        layout.addWidget(self.labware_label)
        
        self.setLayout(layout)
        self.update_appearance()
    
    def set_labware(self, labware_info):
        """Set the labware for this slot."""
        self.labware_info = labware_info
        if labware_info:
            # Handle both string and dictionary formats
            if isinstance(labware_info, dict):
                self.labware_label.setText(labware_info["labware_name"])
            else:
                # Backward compatibility for string format
                self.labware_label.setText(str(labware_info))
                # Convert string to dict format for consistency
                self.labware_info = {
                    "labware_name": str(labware_info),
                    "labware_type": str(labware_info)
                }
        else:
            self.labware_label.setText("Empty")
        self.update_appearance()
    
    def update_appearance(self):
        """Update the visual appearance based on content."""
        if self.labware_info:
            self.setStyleSheet("""
                DeckSlotWidget {
                    background-color: #e6f3ff;
                    border: 2px solid #0066cc;
                    border-radius: 5px;
                }
                DeckSlotWidget:hover {
                    background-color: #ccebff;
                }
            """)
        else:
            self.setStyleSheet("""
                DeckSlotWidget {
                    background-color: #f0f0f0;
                    border: 2px solid #cccccc;
                    border-radius: 5px;
                }
                DeckSlotWidget:hover {
                    background-color: #e0e0e0;
                }
            """)
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.slot_clicked.emit(self.slot_number)
        super().mousePressEvent(event)


class LabwareView(QWidget):
    """Labware view widget for deck configuration."""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.deck_slots = {}
        self.setup_ui()
        self.update_deck_display()
        self.update_labware_list()
    
    def setup_ui(self):
        """Setup the user interface."""
        main_layout = QHBoxLayout()
        
        # Left panel - Deck visualization
        left_panel = self.create_deck_panel()
        main_layout.addWidget(left_panel)
        
        # Right panel - Controls
        right_panel = self.create_controls_panel()
        main_layout.addWidget(right_panel)
        
        self.setLayout(main_layout)
    
    def create_deck_panel(self):
        """Create the deck visualization panel."""
        group = QGroupBox("Deck Layout")
        layout = QVBoxLayout()
        
        # Create deck grid
        deck_layout = QGridLayout()
        deck_layout.setSpacing(10)
        
        # Create deck slots (OT-2 has 11 slots in specific layout)
        slot_positions = {
            '10': (0, 0), '11': (0, 1),
            '7': (1, 0), '8': (1, 1), '9': (1, 2),
            '4': (2, 0), '5': (2, 1), '6': (2, 2),
            '1': (3, 0), '2': (3, 1), '3': (3, 2)
        }

        for slot_num, (row, col) in slot_positions.items():
            slot_widget = DeckSlotWidget(slot_num)
            slot_widget.slot_clicked.connect(self.on_slot_clicked)
            self.deck_slots[slot_num] = slot_widget
            deck_layout.addWidget(slot_widget, row, col)

        # Add trash slot at top right (row 0, col 2)
        trash_widget = DeckSlotWidget("Trash")
        trash_widget.labware_label.setText("Trash")
        trash_widget.labware_label.setStyleSheet("color: black;")
        trash_widget.setStyleSheet("""
            DeckSlotWidget {
                background-color: #ffebee;
                border: 2px solid #f44336;
                border-radius: 5px;
            }
        """)
        deck_layout.addWidget(trash_widget, 0, 2)

        layout.addLayout(deck_layout)
        
        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Legend:"))
        
        empty_label = QLabel("Empty")
        empty_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; padding: 2px; color: black;")
        legend_layout.addWidget(empty_label)
        
        occupied_label = QLabel("Occupied")
        occupied_label.setStyleSheet("background-color: #e6f3ff; border: 1px solid #0066cc; padding: 2px; color: black;")
        legend_layout.addWidget(occupied_label)
        
        legend_layout.addStretch()
        layout.addLayout(legend_layout)
        
        group.setLayout(layout)
        return group
    
    def create_controls_panel(self):
        """Create the controls panel."""
        group = QGroupBox("Labware Controls")
        layout = QVBoxLayout()
        
        # Labware selection
        labware_group = QGroupBox("Available Labware")
        labware_layout = QVBoxLayout()
        
        self.labware_list = QListWidget()
        self.labware_list.setMaximumHeight(200)
        labware_layout.addWidget(self.labware_list)
        
        # Add custom labware button
        self.add_custom_btn = QPushButton("Add Custom Labware")
        self.add_custom_btn.clicked.connect(self.on_add_custom_labware)
        labware_layout.addWidget(self.add_custom_btn)
        
        labware_group.setLayout(labware_layout)
        layout.addWidget(labware_group)
        
        # Slot operations
        slot_group = QGroupBox("Slot Operations")
        slot_layout = QVBoxLayout()
        
        # Selected slot info
        self.selected_slot_label = QLabel("No slot selected")
        self.selected_slot_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        slot_layout.addWidget(self.selected_slot_label)
        
        # Slot operations buttons
        self.assign_labware_btn = QPushButton("Assign Selected Labware")
        self.assign_labware_btn.clicked.connect(self.on_assign_labware)
        self.assign_labware_btn.setEnabled(False)
        slot_layout.addWidget(self.assign_labware_btn)
        
        self.clear_slot_btn = QPushButton("Clear Selected Slot")
        self.clear_slot_btn.clicked.connect(self.on_clear_slot)
        self.clear_slot_btn.setEnabled(False)
        slot_layout.addWidget(self.clear_slot_btn)
        
        slot_group.setLayout(slot_layout)
        layout.addWidget(slot_group)
        
       
        # Tip pickup section
        tip_group = QGroupBox("Tip Pickup")
        tip_layout = QVBoxLayout()
        
        # Tiprack slot selector
        tiprack_layout = QHBoxLayout()
        tiprack_layout.addWidget(QLabel("Tiprack Slot:"))
        self.tiprack_combo = QComboBox()
        self.tiprack_combo.currentTextChanged.connect(self.on_tiprack_selection_changed)
        tiprack_layout.addWidget(self.tiprack_combo)
        tip_layout.addLayout(tiprack_layout)
        
        # Row and column inputs
        position_layout = QHBoxLayout()
        
        # Row input (letter)
        position_layout.addWidget(QLabel("Row:"))
        self.row_edit = QLineEdit()
        self.row_edit.setMaxLength(1)
        self.row_edit.setPlaceholderText("A")
        self.row_edit.setMaximumWidth(50)
        position_layout.addWidget(self.row_edit)
        
        # Column input (number)
        position_layout.addWidget(QLabel("Column:"))
        self.column_spinbox = QSpinBox()
        self.column_spinbox.setMinimum(1)
        self.column_spinbox.setMaximum(100)
        self.column_spinbox.setValue(1)
        self.column_spinbox.setMaximumWidth(70)
        position_layout.addWidget(self.column_spinbox)
        
        position_layout.addStretch()
        tip_layout.addLayout(position_layout)
        
        # Pick up tip button
        self.pickup_tip_btn = QPushButton("Pick Up Tip")
        self.pickup_tip_btn.clicked.connect(self.on_pickup_tip)
        self.pickup_tip_btn.setEnabled(False)
        tip_layout.addWidget(self.pickup_tip_btn)
        
        tip_group.setLayout(tip_layout)
        layout.addWidget(tip_group)
        
        group.setLayout(layout)
        return group
    
    def update_deck_display(self):
        """Update the deck display with current layout."""
        deck_layout = self.controller.get_deck_layout()

        for slot_num, slot_widget in self.deck_slots.items():
            labware_info = deck_layout.get(f"slot_{slot_num}")
            slot_widget.set_labware(labware_info)
    
    def update_labware_list(self):
        """Update the available labware list."""
        self.labware_list.clear()
        self.available_labware = self.controller.get_available_labware()
        
        # Add labware items to the list widget
        for labware_type in self.available_labware:
            item = QListWidgetItem(labware_type)
            item.setData(Qt.ItemDataRole.UserRole, labware_type)
            self.labware_list.addItem(item)
        
        # Update tiprack combobox
        self.update_tiprack_list()
    
    def update_tiprack_list(self):
        """Update the tiprack slots combobox."""
        self.tiprack_combo.clear()
        tipracks = self.controller.get_tiprack_slots()
        
        if not tipracks:
            self.tiprack_combo.addItem("No tipracks loaded")
            self.pickup_tip_btn.setEnabled(False)
        else:
            for tiprack in tipracks:
                display_text = f"Slot {tiprack['slot_number']} - {tiprack['labware_name']}"
                self.tiprack_combo.addItem(display_text, tiprack['slot_number'])
            self.pickup_tip_btn.setEnabled(True)
    
    def on_slot_clicked(self, slot_number):
        """Handle slot click events."""
        self.selected_slot = slot_number
        self.selected_slot_label.setText(f"Selected: Slot {slot_number}")
        self.assign_labware_btn.setEnabled(True)
        self.clear_slot_btn.setEnabled(True)

    def on_tiprack_selection_changed(self, text):
        """Set selected_slot to the slot number of the selected tiprack."""
        slot_number = self.tiprack_combo.currentData()
        self.selected_slot = slot_number
    
    def on_assign_labware(self):
        """Handle assign labware button click."""
        if not hasattr(self, 'selected_slot'):
            return
        
        if not self.labware_list.currentItem():
            return
            
        slot_number = int(self.selected_slot)
        labware_name = self.labware_list.currentItem().text()
        
        def on_success(result):
            if result:
                self.update_deck_display()
                self.update_tiprack_list()
            self.assign_labware_btn.setEnabled(True)
        
        def on_error(error):
            self.assign_labware_btn.setEnabled(True)
        
        def on_finished():
            self.assign_labware_btn.setEnabled(True)
        
        # Disable button during operation
        self.assign_labware_btn.setEnabled(False)
        
        self.controller.set_slot_labware(
            slot_number, 
            labware_name,
            on_result=on_success,
            on_error=on_error,
            on_finished=on_finished
        )

    def on_clear_slot(self):
        """Handle clear slot button click."""
        if not hasattr(self, 'selected_slot'):
            return
        
        success = self.controller.clear_slot(self.selected_slot)
        # Update display regardless of success/failure - backend handles it
    
    def on_add_custom_labware(self):
        """Handle add custom labware button click."""
        def on_success(result):
            """Called when custom labware is successfully added."""
            self.update_labware_list()  # Refresh the labware list
            
        def on_error(error):
            """Called when there's an error adding custom labware."""
            pass
            
        def on_finished():
            """Called when the operation finishes (success or failure)."""
            # Re-enable the button
            self.add_custom_btn.setEnabled(True)
        
        # Disable button during operation
        self.add_custom_btn.setEnabled(False)
        
        # Call controller with callbacks
        self.controller.add_custom_labware(
            on_result=on_success,
            on_error=on_error, 
            on_finished=on_finished
        )
    
    def on_pickup_tip(self):
        """Handle pick up tip button click."""
        if not hasattr(self, 'selected_slot'):
            return
        
        row = self.row_edit.text().strip().upper()
        column = self.column_spinbox.value()
        
        if not row or len(row) != 1 or not row.isalpha():
            return
        
        if column < 1 or column > 12:
            return
        
        def on_success(result):
            self.pickup_tip_btn.setEnabled(True)
        
        def on_error(error):
            self.pickup_tip_btn.setEnabled(True)
        
        def on_finished():
            self.pickup_tip_btn.setEnabled(True)
        
        # Disable button during operation
        self.pickup_tip_btn.setEnabled(False)
        
        self.controller.pickup_tip(
            int(self.selected_slot), 
            row, 
            column,
            on_result=on_success,
            on_error=on_error,
            on_finished=on_finished
        )

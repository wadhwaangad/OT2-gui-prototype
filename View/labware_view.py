"""
Labware view for the microtissue manipulator GUI.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                           QPushButton, QLabel, QGroupBox, QComboBox, QListWidget,
                           QListWidgetItem, QMessageBox, QFileDialog, QLineEdit,
                           QSpinBox, QTextEdit, QScrollArea, QFrame, QDialog,
                           QDialogButtonBox, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor


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
        layout.addWidget(self.slot_label)
        
        # Labware info label
        self.labware_label = QLabel("Empty")
        self.labware_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labware_label.setWordWrap(True)
        self.labware_label.setFont(QFont("Arial", 8))
        layout.addWidget(self.labware_label)
        
        self.setLayout(layout)
        self.update_appearance()
    
    def set_labware(self, labware_info):
        """Set the labware for this slot."""
        self.labware_info = labware_info
        if labware_info:
            self.labware_label.setText(labware_info["labware_name"])
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
        empty_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; padding: 2px;")
        legend_layout.addWidget(empty_label)
        
        occupied_label = QLabel("Occupied")
        occupied_label.setStyleSheet("background-color: #e6f3ff; border: 1px solid #0066cc; padding: 2px;")
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
        
       
        # Information panel
        info_group = QGroupBox("Information")
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(150)
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
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
        self.labware_list = self.controller.get_available_labware()
        
    
    def on_slot_clicked(self, slot_number):
        """Handle slot click events."""
        self.selected_slot_label.setText(f"Selected: Slot {slot_number}")
        self.assign_labware_btn.setEnabled(True)
        self.clear_slot_btn.setEnabled(True)
        self.selected_slot = slot_number

        # Show slot information
        slot_info = self.controller.get_slot_info(f"slot_{slot_number}")
        custom_labware = self.controller.labware_model.labware_config.get("custom_labware", {})
        if slot_info:
            info_text = f"Slot {slot_number}:\n"
            info_text += f"Labware: {slot_info['labware_name']}\n"
            info_text += f"Type: {slot_info['labware_type']}\n"
            # Only show description if custom
            if slot_info['labware_type'] in custom_labware:
                desc = custom_labware[slot_info['labware_type']].get('description', '')
                if desc:
                    info_text += f"Description: {desc}\n"
        else:
            info_text = f"Slot {slot_number}: Empty"
        self.info_text.setPlainText(info_text)
    
    def on_assign_labware(self):
        """Handle assign labware button click."""
        if not hasattr(self, 'selected_slot'):
            QMessageBox.warning(self, "Warning", "Please select a slot first.")
            return

        current_item = self.labware_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a labware type.")
            return

        labware_type = current_item.data(Qt.ItemDataRole.UserRole)
        custom_labware = self.controller.labware_model.labware_config.get("custom_labware", {})
        if labware_type in custom_labware:
            name = custom_labware[labware_type].get("name", labware_type)
        else:
            name = labware_type
        success = self.controller.set_slot_labware(
            f"slot_{self.selected_slot}",
            labware_type,
            name
        )
        if success:
            self.info_text.append(f"\n✓ Assigned {name} to slot {self.selected_slot}")
        else:
            self.info_text.append(f"\n✗ Failed to assign labware to slot {self.selected_slot}")
    
    def on_clear_slot(self):
        """Handle clear slot button click."""
        if not hasattr(self, 'selected_slot'):
            QMessageBox.warning(self, "Warning", "Please select a slot first.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm", 
            f"Are you sure you want to clear slot {self.selected_slot}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.controller.clear_slot(f"slot_{self.selected_slot}")
            if success:
                self.info_text.append(f"\\n✓ Cleared slot {self.selected_slot}")
            else:
                self.info_text.append(f"\\n✗ Failed to clear slot {self.selected_slot}")
    
    
    
    def on_add_custom_labware(self):
        self.controller.add_custom_labware()

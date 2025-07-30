"""
Dialog for selecting calibration profile.
"""

import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                           QListWidgetItem, QPushButton, QLabel, QMessageBox)
from PyQt6.QtCore import Qt
import paths


class CalibrationProfileDialog(QDialog):
    """Dialog for selecting a calibration profile."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_profile = None
        self.setup_ui()
        self.load_profiles()
        
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Select Calibration Profile")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        
        # Title label
        title_label = QLabel("Select a calibration profile:")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.profile_list)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.setEnabled(False)  # Initially disabled
        self.ok_button.clicked.connect(self.accept_selection)
        button_layout.addWidget(self.ok_button)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Connect selection change
        self.profile_list.itemSelectionChanged.connect(self.on_selection_changed)
        
    def load_profiles(self):
        """Load available calibration profiles from configs directory."""
        try:
            if os.path.exists(paths.PROFILES_DIR):
                # Get all subdirectories in configs folder
                profiles = [name for name in os.listdir(paths.PROFILES_DIR) 
                           if os.path.isdir(os.path.join(paths.PROFILES_DIR, name))]
                
                if profiles:
                    for profile in sorted(profiles):
                        item = QListWidgetItem(profile)
                        self.profile_list.addItem(item)
                else:
                    # No profiles found
                    item = QListWidgetItem("No calibration profiles found")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    self.profile_list.addItem(item)
            else:
                # Configs directory doesn't exist
                item = QListWidgetItem("Configs directory not found")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.profile_list.addItem(item)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load calibration profiles: {str(e)}")
            
    def on_selection_changed(self):
        """Handle selection change in profile list."""
        current_item = self.profile_list.currentItem()
        if current_item and current_item.flags() & Qt.ItemFlag.ItemIsEnabled:
            self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)
            
    def accept_selection(self):
        """Accept the selected profile."""
        current_item = self.profile_list.currentItem()
        if current_item and current_item.flags() & Qt.ItemFlag.ItemIsEnabled:
            self.selected_profile = current_item.text()
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a calibration profile.")
            
    def get_selected_profile(self):
        """Get the selected calibration profile."""
        return self.selected_profile

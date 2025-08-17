"""
Cuboid Picking view for microtissue manipulator GUI.
Displays available wellplate labware types with interactive grid visualization and cuboid assignment.
"""

import re
import math
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                           QPushButton, QLabel, QGroupBox, QComboBox, QFrame,
                           QScrollArea, QSizePolicy, QCheckBox, QButtonGroup,
                           QSpacerItem, QApplication, QSpinBox, QDoubleSpinBox,
                           QDialog, QDialogButtonBox, QFormLayout, QSplitter,
                           QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QBrush, QPen, QLinearGradient
import Model.globals as globals
import Model.picking_procedure as picking_procedure
import keyboard 
from View.zoomable_video_widget import VideoDisplayWidget
import Model.globals as globals
KEYBOARD_AVAILABLE = True
class WellWidget(QFrame):
    """Individual well widget with enhanced animation and interaction for cuboid assignment."""
    
    well_clicked = pyqtSignal(str, bool, bool)  # well_id, ctrl_pressed, shift_pressed
    
    def __init__(self, well_id: str, parent=None):
        super().__init__(parent)
        self.well_id = well_id
        self.is_selected = False
        self.is_hovered = False
        self.animation = None
        self.cuboid_count = 0  # Number of cuboids assigned to this well
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the well widget UI with professional styling."""
        self.setFixedSize(38, 38)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.update_appearance()
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Set tooltip
        self.update_tooltip()
        
        # Create label for well ID or cuboid count
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        self.label = QLabel(str(self.cuboid_count) if self.cuboid_count > 0 else self.well_id)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        layout.addWidget(self.label)
        self.setLayout(layout)
    
    def set_cuboid_count(self, count: int):
        """Set the number of cuboids assigned to this well."""
        self.cuboid_count = count
        self.label.setText(str(count) if count > 0 else self.well_id)
        self.update_tooltip()
        self.update_appearance()
    
    def get_cuboid_count(self) -> int:
        """Get the number of cuboids assigned to this well."""
        return self.cuboid_count
    
    def update_tooltip(self):
        """Update the tooltip with current information."""
        if self.cuboid_count > 0:
            self.setToolTip(f"Well {self.well_id}: {self.cuboid_count} cuboids\nClick to toggle selection\nDrag to select area")
        else:
            self.setToolTip(f"Well {self.well_id}: No cuboids assigned\nClick to toggle selection\nDrag to select area")
    
    def update_appearance(self):
        """Update the visual appearance with professional styling."""
        if self.cuboid_count > 0:
            if self.is_selected:
                bg_color = "#27ae60"  # Green for assigned wells
                text_color = "white"
                border_color = "#229954"
                border_width = "2px"
            elif self.is_hovered:
                bg_color = "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #a9dfbf, stop: 1 #7fb069)"
                text_color = "#1e3d59"
                border_color = "#27ae60"
                border_width = "2px"
            else:
                bg_color = "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #d5f4e6, stop: 1 #a9dfbf)"
                text_color = "#1e3d59"
                border_color = "#58d68d"
                border_width = "1px"
        else:
            if self.is_selected:
                bg_color = "#3498db"  # Professional blue
                text_color = "white"
                border_color = "#2980b9"
                border_width = "2px"
            elif self.is_hovered:
                bg_color = "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ecf0f1, stop: 1 #d5dbdb)"
                text_color = "#2c3e50"
                border_color = "#3498db"
                border_width = "2px"
            else:
                bg_color = "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffffff, stop: 1 #f8f9fa)"
                text_color = "#34495e"
                border_color = "#bdc3c7"
                border_width = "1px"
        
        self.setStyleSheet(f"""
            WellWidget {{
                background: {bg_color};
                border: {border_width} solid {border_color};
                border-radius: 18px;
            }}
            QLabel {{
                color: {text_color};
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        
        # Animate scale effect for selection
        if self.is_selected and not self.animation:
            self.animate_selection()
    
    def animate_selection(self):
        """Add subtle animation for selection."""
        if self.animation:
            self.animation.stop()
        
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        current_geo = self.geometry()
        # Keep consistent size - no scaling animation to avoid transform issues
        new_geo = QRect(
            current_geo.x(),
            current_geo.y(),
            current_geo.width(),
            current_geo.height()
        )
        
        self.animation.setEndValue(new_geo)
        self.animation.start()
    
    def set_selected(self, selected: bool):
        """Set the selection state with animation."""
        if self.is_selected != selected:
            self.is_selected = selected
            self.update_appearance()
    
    def mousePressEvent(self, event):
        """Handle mouse press events - delegate to parent for unified drag handling."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check modifiers for different selection modes
            ctrl_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            shift_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            
            # Emit the click event
            self.well_clicked.emit(self.well_id, ctrl_pressed, shift_pressed)
        
        # Don't call super() - let the parent grid handle mouse events
        event.ignore()
    
    def mouseMoveEvent(self, event):
        """Ignore mouse move to let parent handle drag selection."""
        event.ignore()
    
    def mouseReleaseEvent(self, event):
        """Ignore mouse release to let parent handle drag selection."""
        event.ignore()
    
    def enterEvent(self, event):
        """Handle mouse enter events."""
        self.is_hovered = True
        self.update_appearance()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave events."""
        self.is_hovered = False
        self.update_appearance()
        super().leaveEvent(event)


class CuboidAssignmentDialog(QDialog):
    """Dialog for assigning cuboid counts to selected wells."""
    
    def __init__(self, selected_wells, current_counts, parent=None):
        super().__init__(parent)
        self.selected_wells = selected_wells
        self.current_counts = current_counts
        self.cuboid_count = 1
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Assign Cuboids to Wells")
        self.setModal(True)
        self.setFixedSize(350, 200)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel(f"Assign cuboids to {len(self.selected_wells)} selected wells")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Well list
        wells_text = ", ".join(sorted(self.selected_wells))
        if len(wells_text) > 50:
            wells_text = wells_text[:47] + "..."
        wells_label = QLabel(f"Wells: {wells_text}")
        wells_label.setWordWrap(True)
        wells_label.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(wells_label)
        
        # Cuboid count input
        form_layout = QFormLayout()
        
        self.cuboid_spin = QSpinBox()
        self.cuboid_spin.setRange(0, 50)
        self.cuboid_spin.setValue(self.cuboid_count)
        self.cuboid_spin.setToolTip("Number of cuboids to assign (0 to clear)")
        form_layout.addRow("Number of cuboids:", self.cuboid_spin)
        
        layout.addLayout(form_layout)
        
        # Info text
        info_label = QLabel("Set to 0 to remove cuboid assignment from wells")
        info_label.setStyleSheet("color: #888; font-style: italic; font-size: 10px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_cuboid_count(self):
        """Get the selected cuboid count."""
        return self.cuboid_spin.value()


class PickingSettingsWidget(QGroupBox):
    """Widget for picking procedure settings."""
    
    settings_changed = pyqtSignal(dict)  # Emit when settings change
    
    def __init__(self, parent=None):
        super().__init__("Picking Settings", parent)
        self.settings = {
            'vol': 10.0,
            'dish_bottom': 65.6,
            'pickup_offset': 0.5,
            'flow_rate': 50.0,
            'cuboid_size_theshold': (350, 550),
            'failure_threshold': 0.5,
            'minimum_distance': 1.7,
            'wait_time_after_deposit': 0.3,
            'one_by_one': False,
            'well_offset_x': 0.0,
            'well_offset_y': 0.0,
            'deposit_offset_z': 0.2,
            'destination_slot': 5,
            'circle_center': (1296, 972),
            'circle_radius': 900,
            'contour_filter_window': (50, 3000),
            'aspect_ratio_window': (0.75, 1.25),
            'circularity_window': (0.6, 0.9)
        }
        self.input_widgets = {}
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the settings widget UI."""
        layout = QVBoxLayout()
        
        # Create scroll area for all settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Container widget for all settings
        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        
        # Basic settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()
        
        # Volume
        vol_spin = QDoubleSpinBox()
        vol_spin.setRange(0.1, 100.0)
        vol_spin.setValue(self.settings['vol'])
        vol_spin.setSuffix(" μL")
        vol_spin.setDecimals(1)
        self.input_widgets['vol'] = vol_spin
        basic_layout.addRow("Volume:", vol_spin)
        
        # Dish bottom
        dish_spin = QDoubleSpinBox()
        dish_spin.setRange(0.0, 200.0)
        dish_spin.setValue(self.settings['dish_bottom'])
        dish_spin.setSuffix(" mm")
        dish_spin.setDecimals(1)
        self.input_widgets['dish_bottom'] = dish_spin
        basic_layout.addRow("Dish Bottom:", dish_spin)
        
        # Pickup offset
        pickup_spin = QDoubleSpinBox()
        pickup_spin.setRange(0.0, 5.0)
        pickup_spin.setValue(self.settings['pickup_offset'])
        pickup_spin.setSuffix(" mm")
        pickup_spin.setDecimals(1)
        self.input_widgets['pickup_offset'] = pickup_spin
        basic_layout.addRow("Pickup Offset:", pickup_spin)
        
        # Flow rate
        flow_spin = QDoubleSpinBox()
        flow_spin.setRange(1.0, 200.0)
        flow_spin.setValue(self.settings['flow_rate'])
        flow_spin.setSuffix(" μL/s")
        flow_spin.setDecimals(1)
        self.input_widgets['flow_rate'] = flow_spin
        basic_layout.addRow("Flow Rate:", flow_spin)
        
        # Destination slot
        slot_spin = QSpinBox()
        slot_spin.setRange(1, 11)
        slot_spin.setValue(self.settings['destination_slot'])
        self.input_widgets['destination_slot'] = slot_spin
        basic_layout.addRow("Destination Slot:", slot_spin)
        
        basic_group.setLayout(basic_layout)
        container_layout.addWidget(basic_group)
        
        # Movement and positioning settings
        movement_group = QGroupBox("Movement Settings")
        movement_layout = QFormLayout()
        
        # Minimum distance
        dist_spin = QDoubleSpinBox()
        dist_spin.setRange(0.1, 10.0)
        dist_spin.setValue(self.settings['minimum_distance'])
        dist_spin.setSuffix(" mm")
        dist_spin.setDecimals(1)
        self.input_widgets['minimum_distance'] = dist_spin
        movement_layout.addRow("Min Distance:", dist_spin)
        
        # Failure threshold
        fail_spin = QDoubleSpinBox()
        fail_spin.setRange(0.1, 5.0)
        fail_spin.setValue(self.settings['failure_threshold'])
        fail_spin.setSuffix(" mm")
        fail_spin.setDecimals(1)
        self.input_widgets['failure_threshold'] = fail_spin
        movement_layout.addRow("Failure Threshold:", fail_spin)
        
        # Wait time
        wait_spin = QDoubleSpinBox()
        wait_spin.setRange(0.0, 5.0)
        wait_spin.setValue(self.settings['wait_time_after_deposit'])
        wait_spin.setSuffix(" s")
        wait_spin.setDecimals(1)
        self.input_widgets['wait_time_after_deposit'] = wait_spin
        movement_layout.addRow("Wait Time:", wait_spin)
        
        # One by one checkbox
        one_by_one_check = QCheckBox()
        one_by_one_check.setChecked(self.settings['one_by_one'])
        self.input_widgets['one_by_one'] = one_by_one_check
        movement_layout.addRow("One by One:", one_by_one_check)
        
        movement_group.setLayout(movement_layout)
        container_layout.addWidget(movement_group)
        
        # Well offset settings
        offset_group = QGroupBox("Well Offsets")
        offset_layout = QFormLayout()
        
        # Well offset X
        well_x_spin = QDoubleSpinBox()
        well_x_spin.setRange(-10.0, 10.0)
        well_x_spin.setValue(self.settings['well_offset_x'])
        well_x_spin.setSuffix(" mm")
        well_x_spin.setDecimals(1)
        self.input_widgets['well_offset_x'] = well_x_spin
        offset_layout.addRow("Well Offset X:", well_x_spin)
        
        # Well offset Y
        well_y_spin = QDoubleSpinBox()
        well_y_spin.setRange(-10.0, 10.0)
        well_y_spin.setValue(self.settings['well_offset_y'])
        well_y_spin.setSuffix(" mm")
        well_y_spin.setDecimals(1)
        self.input_widgets['well_offset_y'] = well_y_spin
        offset_layout.addRow("Well Offset Y:", well_y_spin)
        
        # Deposit offset Z
        deposit_z_spin = QDoubleSpinBox()
        deposit_z_spin.setRange(-5.0, 5.0)
        deposit_z_spin.setValue(self.settings['deposit_offset_z'])
        deposit_z_spin.setSuffix(" mm")
        deposit_z_spin.setDecimals(1)
        self.input_widgets['deposit_offset_z'] = deposit_z_spin
        offset_layout.addRow("Deposit Offset Z:", deposit_z_spin)
        
        offset_group.setLayout(offset_layout)
        container_layout.addWidget(offset_group)
        
        # Size thresholds
        size_group = QGroupBox("Size Filters")
        size_layout = QFormLayout()
        
        # Cuboid size range
        size_min_spin = QSpinBox()
        size_min_spin.setRange(50, 1000)
        size_min_spin.setValue(self.settings['cuboid_size_theshold'][0])
        size_min_spin.setSuffix(" μm")
        self.input_widgets['cuboid_size_min'] = size_min_spin
        size_layout.addRow("Size Min:", size_min_spin)
        
        size_max_spin = QSpinBox()
        size_max_spin.setRange(100, 2000)
        size_max_spin.setValue(self.settings['cuboid_size_theshold'][1])
        size_max_spin.setSuffix(" μm")
        self.input_widgets['cuboid_size_max'] = size_max_spin
        size_layout.addRow("Size Max:", size_max_spin)
        
        size_group.setLayout(size_layout)
        container_layout.addWidget(size_group)
        
        # Circle detection settings
        circle_group = QGroupBox("Circle Detection")
        circle_layout = QFormLayout()
        
        # Circle center X
        center_x_spin = QSpinBox()
        center_x_spin.setRange(0, 2000)
        center_x_spin.setValue(self.settings['circle_center'][0])
        center_x_spin.setSuffix(" px")
        self.input_widgets['circle_center_x'] = center_x_spin
        circle_layout.addRow("Circle Center X:", center_x_spin)
        
        # Circle center Y
        center_y_spin = QSpinBox()
        center_y_spin.setRange(0, 2000)
        center_y_spin.setValue(self.settings['circle_center'][1])
        center_y_spin.setSuffix(" px")
        self.input_widgets['circle_center_y'] = center_y_spin
        circle_layout.addRow("Circle Center Y:", center_y_spin)
        
        # Circle radius
        radius_spin = QSpinBox()
        radius_spin.setRange(100, 1500)
        radius_spin.setValue(self.settings['circle_radius'])
        radius_spin.setSuffix(" px")
        self.input_widgets['circle_radius'] = radius_spin
        circle_layout.addRow("Circle Radius:", radius_spin)
        
        circle_group.setLayout(circle_layout)
        container_layout.addWidget(circle_group)
        
        # Contour filter settings
        contour_group = QGroupBox("Contour Filters")
        contour_layout = QFormLayout()
        
        # Contour filter min
        contour_min_spin = QSpinBox()
        contour_min_spin.setRange(10, 500)
        contour_min_spin.setValue(self.settings['contour_filter_window'][0])
        contour_min_spin.setSuffix(" px²")
        self.input_widgets['contour_filter_min'] = contour_min_spin
        contour_layout.addRow("Contour Area Min:", contour_min_spin)
        
        # Contour filter max
        contour_max_spin = QSpinBox()
        contour_max_spin.setRange(1000, 10000)
        contour_max_spin.setValue(self.settings['contour_filter_window'][1])
        contour_max_spin.setSuffix(" px²")
        self.input_widgets['contour_filter_max'] = contour_max_spin
        contour_layout.addRow("Contour Area Max:", contour_max_spin)
        
        contour_group.setLayout(contour_layout)
        container_layout.addWidget(contour_group)
        
        # Shape filter settings
        shape_group = QGroupBox("Shape Filters")
        shape_layout = QFormLayout()
        
        # Aspect ratio min
        aspect_min_spin = QDoubleSpinBox()
        aspect_min_spin.setRange(0.1, 2.0)
        aspect_min_spin.setValue(self.settings['aspect_ratio_window'][0])
        aspect_min_spin.setDecimals(2)
        self.input_widgets['aspect_ratio_min'] = aspect_min_spin
        shape_layout.addRow("Aspect Ratio Min:", aspect_min_spin)
        
        # Aspect ratio max
        aspect_max_spin = QDoubleSpinBox()
        aspect_max_spin.setRange(0.1, 2.0)
        aspect_max_spin.setValue(self.settings['aspect_ratio_window'][1])
        aspect_max_spin.setDecimals(2)
        self.input_widgets['aspect_ratio_max'] = aspect_max_spin
        shape_layout.addRow("Aspect Ratio Max:", aspect_max_spin)
        
        # Circularity min
        circ_min_spin = QDoubleSpinBox()
        circ_min_spin.setRange(0.1, 1.0)
        circ_min_spin.setValue(self.settings['circularity_window'][0])
        circ_min_spin.setDecimals(2)
        self.input_widgets['circularity_min'] = circ_min_spin
        shape_layout.addRow("Circularity Min:", circ_min_spin)
        
        # Circularity max
        circ_max_spin = QDoubleSpinBox()
        circ_max_spin.setRange(0.1, 1.0)
        circ_max_spin.setValue(self.settings['circularity_window'][1])
        circ_max_spin.setDecimals(2)
        self.input_widgets['circularity_max'] = circ_max_spin
        shape_layout.addRow("Circularity Max:", circ_max_spin)
        
        shape_group.setLayout(shape_layout)
        container_layout.addWidget(shape_group)
        
        # Set the container widget as the scroll area's widget
        scroll_area.setWidget(container_widget)
        layout.addWidget(scroll_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        apply_btn = QPushButton("Apply Settings")
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_settings)
        button_layout.addWidget(reset_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def apply_settings(self):
        """Apply current settings."""
        # Update settings from widgets
        self.settings['vol'] = self.input_widgets['vol'].value()
        self.settings['dish_bottom'] = self.input_widgets['dish_bottom'].value()
        self.settings['pickup_offset'] = self.input_widgets['pickup_offset'].value()
        self.settings['flow_rate'] = self.input_widgets['flow_rate'].value()
        self.settings['minimum_distance'] = self.input_widgets['minimum_distance'].value()
        self.settings['failure_threshold'] = self.input_widgets['failure_threshold'].value()
        self.settings['wait_time_after_deposit'] = self.input_widgets['wait_time_after_deposit'].value()
        self.settings['one_by_one'] = self.input_widgets['one_by_one'].isChecked()
        self.settings['well_offset_x'] = self.input_widgets['well_offset_x'].value()
        self.settings['well_offset_y'] = self.input_widgets['well_offset_y'].value()
        self.settings['deposit_offset_z'] = self.input_widgets['deposit_offset_z'].value()
        self.settings['destination_slot'] = self.input_widgets['destination_slot'].value()
        
        # Update tuple values
        self.settings['cuboid_size_theshold'] = (
            self.input_widgets['cuboid_size_min'].value(),
            self.input_widgets['cuboid_size_max'].value()
        )
        
        self.settings['circle_center'] = (
            self.input_widgets['circle_center_x'].value(),
            self.input_widgets['circle_center_y'].value()
        )
        self.settings['circle_radius'] = self.input_widgets['circle_radius'].value()
        
        self.settings['contour_filter_window'] = (
            self.input_widgets['contour_filter_min'].value(),
            self.input_widgets['contour_filter_max'].value()
        )
        
        self.settings['aspect_ratio_window'] = (
            self.input_widgets['aspect_ratio_min'].value(),
            self.input_widgets['aspect_ratio_max'].value()
        )
        
        self.settings['circularity_window'] = (
            self.input_widgets['circularity_min'].value(),
            self.input_widgets['circularity_max'].value()
        )
        
        self.settings_changed.emit(self.settings.copy())
        
        # Show confirmation
        QMessageBox.information(self, "Settings Applied", "Picking settings have been updated successfully.")
    
    def reset_settings(self):
        """Reset settings to defaults."""
        # Reset to default values
        self.input_widgets['vol'].setValue(10.0)
        self.input_widgets['dish_bottom'].setValue(65.6)
        self.input_widgets['pickup_offset'].setValue(0.5)
        self.input_widgets['flow_rate'].setValue(50.0)
        self.input_widgets['minimum_distance'].setValue(1.7)
        self.input_widgets['failure_threshold'].setValue(0.5)
        self.input_widgets['wait_time_after_deposit'].setValue(0.3)
        self.input_widgets['one_by_one'].setChecked(False)
        self.input_widgets['well_offset_x'].setValue(0.0)
        self.input_widgets['well_offset_y'].setValue(0.0)
        self.input_widgets['deposit_offset_z'].setValue(0.2)
        self.input_widgets['destination_slot'].setValue(5)
        self.input_widgets['cuboid_size_min'].setValue(350)
        self.input_widgets['cuboid_size_max'].setValue(550)
        self.input_widgets['circle_center_x'].setValue(1296)
        self.input_widgets['circle_center_y'].setValue(972)
        self.input_widgets['circle_radius'].setValue(900)
        self.input_widgets['contour_filter_min'].setValue(50)
        self.input_widgets['contour_filter_max'].setValue(3000)
        self.input_widgets['aspect_ratio_min'].setValue(0.75)
        self.input_widgets['aspect_ratio_max'].setValue(1.25)
        self.input_widgets['circularity_min'].setValue(0.6)
        self.input_widgets['circularity_max'].setValue(0.9)
    
    def get_settings(self):
        """Get current settings."""
        return self.settings.copy()


class WellplateGridWidget(QFrame):
    """Interactive wellplate grid widget with unified drag selection and cuboid assignment."""
    
    wells_clicked = pyqtSignal(str, list)  # wellplate_name, selected_wells_list
    
    def __init__(self, wellplate_name: str, well_count: int, parent=None):
        super().__init__(parent)
        self.wellplate_name = wellplate_name
        self.well_count = well_count
        self.well_widgets = {}
        self.selected_wells = set()
        self.last_selected_well = None  # For range selection
        self.well_positions = {}  # Store well positions for range selection
        self.well_cuboid_counts = {}  # Store cuboid counts for each well
        
        # Drag selection state
        self.drag_start_pos = None
        self.drag_current_pos = None
        self.is_dragging = False
        self.drag_start_well = None
        
        # Grid layout reference
        self.grid_layout = None
        self.rows = 0
        self.cols = 0
        
        self.setup_ui()
        
        # Enable mouse tracking for the entire widget
        self.setMouseTracking(True)
    
    def setup_ui(self):
        """Setup the wellplate grid UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setLineWidth(2)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel(self.wellplate_name)
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #1976D2; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Well count info
        rows, cols = self.calculate_grid_dimensions(self.well_count)
        info_label = QLabel(f"{self.well_count} wells ({rows}×{cols} grid)")
        info_label.setFont(QFont("Arial", 10))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_wells)
        controls_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("Clear Selection")
        self.select_none_btn.clicked.connect(self.clear_selection)
        controls_layout.addWidget(self.select_none_btn)
        
        # Cuboid assignment controls
        self.assign_cuboids_btn = QPushButton("Assign Cuboids")
        self.assign_cuboids_btn.clicked.connect(self.assign_cuboids_to_selected)
        self.assign_cuboids_btn.setEnabled(False)
        controls_layout.addWidget(self.assign_cuboids_btn)
        
        self.clear_cuboids_btn = QPushButton("Clear All Cuboids")
        self.clear_cuboids_btn.clicked.connect(self.clear_all_cuboids)
        controls_layout.addWidget(self.clear_cuboids_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Grid layout for wells
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        self.rows, self.cols = rows, cols
        
        # Add clickable row labels (A, B, C, etc.)
        for row in range(rows):
            row_label = QPushButton(chr(ord('A') + row))
            row_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            row_label.setStyleSheet("""
                QPushButton {
                    color: #7f8c8d; 
                    background: transparent;
                    border: 1px solid transparent;
                    padding: 2px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background: #ecf0f1;
                    border: 1px solid #bdc3c7;
                }
                QPushButton:pressed {
                    background: #d5dbdb;
                }
            """)
            row_label.setFixedSize(30, 30)
            row_label.clicked.connect(lambda checked, r=row: self.select_row(r))
            row_label.setToolTip(f"Click to toggle entire row {chr(ord('A') + row)} selection")
            self.grid_layout.addWidget(row_label, row + 1, 0)
        
        # Add clickable column labels (1, 2, 3, etc.)
        for col in range(cols):
            col_label = QPushButton(str(col + 1))
            col_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            col_label.setStyleSheet("""
                QPushButton {
                    color: #7f8c8d; 
                    background: transparent;
                    border: 1px solid transparent;
                    padding: 2px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background: #ecf0f1;
                    border: 1px solid #bdc3c7;
                }
                QPushButton:pressed {
                    background: #d5dbdb;
                }
            """)
            col_label.setFixedSize(30, 30)
            col_label.clicked.connect(lambda checked, c=col: self.select_column(c))
            col_label.setToolTip(f"Click to toggle entire column {col + 1} selection")
            self.grid_layout.addWidget(col_label, 0, col + 1)
        
        # Create wells
        for i in range(self.well_count):
            row = i // cols
            col = i % cols
            well_id = self.get_well_id(row, col)
            
            well_widget = WellWidget(well_id, self)  # Pass parent explicitly
            
            # Only connect the click signal - grid will handle drag
            well_widget.well_clicked.connect(
                lambda wid, ctrl, shift, well=well_id: 
                self.on_well_clicked(self.wellplate_name, well, ctrl, shift)
            )
            
            self.well_widgets[well_id] = well_widget
            self.well_positions[well_id] = (row, col)
            self.well_cuboid_counts[well_id] = 0
            self.grid_layout.addWidget(well_widget, row + 1, col + 1)
        
        layout.addLayout(self.grid_layout)
        
        # Selected well info
        self.selected_info = QLabel("Click wells to toggle selection • Drag to select area • Click row/column labels to toggle entire row/column")
        self.selected_info.setFont(QFont("Arial", 9))
        self.selected_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected_info.setStyleSheet("color: #7f8c8d; margin-top: 10px; font-style: italic;")
        layout.addWidget(self.selected_info)
        
        self.setLayout(layout)
    
    def assign_cuboids_to_selected(self):
        """Open dialog to assign cuboids to selected wells."""
        if not self.selected_wells:
            QMessageBox.warning(self, "No Wells Selected", "Please select wells before assigning cuboids.")
            return
        
        # Get current counts for selected wells
        current_counts = {well: self.well_cuboid_counts.get(well, 0) for well in self.selected_wells}
        
        dialog = CuboidAssignmentDialog(list(self.selected_wells), current_counts, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            count = dialog.get_cuboid_count()
            
            # Update cuboid counts for selected wells
            for well_id in self.selected_wells:
                self.well_cuboid_counts[well_id] = count
                if well_id in self.well_widgets:
                    self.well_widgets[well_id].set_cuboid_count(count)
            
            self.update_selection_info()
    
    def clear_all_cuboids(self):
        """Clear all cuboid assignments."""
        reply = QMessageBox.question(
            self, 
            "Clear All Cuboids", 
            "Are you sure you want to clear all cuboid assignments?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for well_id in self.well_cuboid_counts:
                self.well_cuboid_counts[well_id] = 0
                if well_id in self.well_widgets:
                    self.well_widgets[well_id].set_cuboid_count(0)
            
            self.update_selection_info()
    
    def get_cuboid_assignment_matrix(self):
        """Generate pandas DataFrame with cuboid assignments similar to picking_procedure format."""
        rows, cols = self.calculate_grid_dimensions(self.well_count)
        row_labels = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:rows])
        col_labels = list(range(1, cols + 1))
        
        # Create empty DataFrame
        well_df = pd.DataFrame(np.zeros((rows, cols), dtype=int), index=row_labels, columns=col_labels)
        
        # Fill with cuboid counts
        for well_id, count in self.well_cuboid_counts.items():
            if count > 0:
                row_letter = well_id[0]
                col_number = int(well_id[1:])
                if row_letter in row_labels and col_number in col_labels:
                    well_df.loc[row_letter, col_number] = count
        
        return well_df
    
    def get_well_plan_dict(self):
        """Generate well plan dictionary for picking procedure."""
        well_df = self.get_cuboid_assignment_matrix()
        well_plan = {
            f"{row}{col}": well_df.loc[row, col] 
            for row in well_df.index 
            for col in well_df.columns 
            if well_df.loc[row, col] > 0
        }
        return well_plan
    
    def mousePressEvent(self, event):
        """Handle mouse press for unified drag selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Find which well (if any) was clicked
            pos = event.position().toPoint()
            clicked_well = self.get_well_at_position(pos)
            
            if clicked_well:
                self.drag_start_pos = pos
                self.drag_start_well = clicked_well
                self.is_dragging = False  # Will become true when we start moving
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for drag selection."""
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_start_well:
            pos = event.position().toPoint()
            
            # Start dragging if we've moved enough
            if not self.is_dragging:
                start_pos = self.drag_start_pos
                if abs(pos.x() - start_pos.x()) > 5 or abs(pos.y() - start_pos.y()) > 5:
                    self.is_dragging = True
            
            # If we're dragging, update selection
            if self.is_dragging:
                current_well = self.get_well_at_position(pos)
                if current_well:
                    self.update_drag_selection(self.drag_start_well, current_well)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to end drag selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            # If we weren't dragging, just handle as a click
            if not self.is_dragging and self.drag_start_well:
                # This is a simple click - let the well widget handle it
                pass
            
            # Reset drag state
            self.is_dragging = False
            self.drag_start_well = None
            self.drag_start_pos = None
        
        super().mouseReleaseEvent(event)
    
    def get_well_at_position(self, pos):
        """Get the well widget at the given position."""
        # Find the widget at the position
        child = self.childAt(pos)
        
        # Check if it's a well widget or if it's inside a well widget
        while child:
            if isinstance(child, WellWidget):
                return child.well_id
            child = child.parent()
            if child == self:
                break
        
        return None
    
    def update_drag_selection(self, start_well, end_well):
        """Update selection for drag area from start_well to end_well."""
        if start_well not in self.well_positions or end_well not in self.well_positions:
            return
        
        start_row, start_col = self.well_positions[start_well]
        end_row, end_col = self.well_positions[end_well]
        
        # Clear all previous selections during drag
        for well_id in list(self.selected_wells):
            if well_id in self.well_widgets:
                self.well_widgets[well_id].set_selected(False)
        self.selected_wells.clear()
        
        # Select rectangular area from start to end position
        min_row, max_row = min(start_row, end_row), max(start_row, end_row)
        min_col, max_col = min(start_col, end_col), max(start_col, end_col)
        
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                well_id = self.get_well_id(row, col)
                if well_id in self.well_widgets:
                    self.selected_wells.add(well_id)
                    self.well_widgets[well_id].set_selected(True)
        
        self.update_selection_info()
        self.wells_clicked.emit(self.wellplate_name, list(self.selected_wells))
        self.assign_cuboids_btn.setEnabled(len(self.selected_wells) > 0)
    
    def select_row(self, row_index: int):
        """Toggle selection of all wells in the specified row."""
        rows, cols = self.calculate_grid_dimensions(self.well_count)
        
        # Get all wells in this row
        row_wells = []
        for col in range(cols):
            well_id = self.get_well_id(row_index, col)
            if well_id in self.well_widgets:
                row_wells.append(well_id)
        
        # Check if all wells in the row are already selected
        all_selected = all(well_id in self.selected_wells for well_id in row_wells)
        
        if all_selected:
            # Deselect all wells in the row
            for well_id in row_wells:
                if well_id in self.selected_wells:
                    self.selected_wells.remove(well_id)
                    self.well_widgets[well_id].set_selected(False)
        else:
            # Select all wells in the row
            for well_id in row_wells:
                self.selected_wells.add(well_id)
                self.well_widgets[well_id].set_selected(True)
        
        self.update_selection_info()
        self.wells_clicked.emit(self.wellplate_name, list(self.selected_wells))
        self.assign_cuboids_btn.setEnabled(len(self.selected_wells) > 0)
    
    def select_column(self, col_index: int):
        """Toggle selection of all wells in the specified column."""
        rows, cols = self.calculate_grid_dimensions(self.well_count)
        
        # Get all wells in this column
        col_wells = []
        for row in range(rows):
            well_id = self.get_well_id(row, col_index)
            if well_id in self.well_widgets:
                col_wells.append(well_id)
        
        # Check if all wells in the column are already selected
        all_selected = all(well_id in self.selected_wells for well_id in col_wells)
        
        if all_selected:
            # Deselect all wells in the column
            for well_id in col_wells:
                if well_id in self.selected_wells:
                    self.selected_wells.remove(well_id)
                    self.well_widgets[well_id].set_selected(False)
        else:
            # Select all wells in the column
            for well_id in col_wells:
                self.selected_wells.add(well_id)
                self.well_widgets[well_id].set_selected(True)
        
        self.update_selection_info()
        self.wells_clicked.emit(self.wellplate_name, list(self.selected_wells))
        self.assign_cuboids_btn.setEnabled(len(self.selected_wells) > 0)
    
    def select_all_wells(self):
        """Select all wells in the wellplate."""
        for well_id, well_widget in self.well_widgets.items():
            self.selected_wells.add(well_id)
            well_widget.set_selected(True)
        self.update_selection_info()
        self.wells_clicked.emit(self.wellplate_name, list(self.selected_wells))
        self.assign_cuboids_btn.setEnabled(len(self.selected_wells) > 0)
    
    def clear_selection(self):
        """Clear all selected wells."""
        for well_id in list(self.selected_wells):
            if well_id in self.well_widgets:
                self.well_widgets[well_id].set_selected(False)
        self.selected_wells.clear()
        self.last_selected_well = None
        self.assign_cuboids_btn.setEnabled(False)
        self.update_selection_info()
        self.wells_clicked.emit(self.wellplate_name, list(self.selected_wells))
    
    def update_selection_info(self):
        """Update the selection information display."""
        count = len(self.selected_wells)
        total_cuboids = sum(self.well_cuboid_counts.get(well, 0) for well in self.well_cuboid_counts)
        assigned_wells = sum(1 for count in self.well_cuboid_counts.values() if count > 0)
        
        if count == 0:
            self.selected_info.setText(f"Total cuboids assigned: {total_cuboids} in {assigned_wells} wells • Click wells to select")
            self.assign_cuboids_btn.setEnabled(False)
        elif count == 1:
            well = list(self.selected_wells)[0]
            well_count = self.well_cuboid_counts.get(well, 0)
            row_letter = well[0]
            column_number = well[1:]
            self.selected_info.setText(f"Selected: {well} ({well_count} cuboids) • Total: {total_cuboids} in {assigned_wells} wells")
            self.assign_cuboids_btn.setEnabled(True)
        else:
            selected_cuboids = sum(self.well_cuboid_counts.get(well, 0) for well in self.selected_wells)
            sorted_wells = sorted(list(self.selected_wells))
            if count <= 5:
                wells_text = ', '.join(sorted_wells)
            else:
                wells_text = f"{', '.join(sorted_wells[:3])}... (+{count - 3} more)"
            self.selected_info.setText(f"Selected {count} wells ({selected_cuboids} cuboids): {wells_text}")
            self.assign_cuboids_btn.setEnabled(True)
    
    def calculate_grid_dimensions(self, well_count: int) -> tuple:
        """Calculate the optimal grid dimensions for the well count."""
        # Standard wellplate formats
        standard_formats = {
            6: (2, 3),   # 2x3
            12: (3, 4),  # 3x4
            24: (4, 6),  # 4x6
            48: (6, 8),  # 6x8
            96: (8, 12), # 8x12
            384: (16, 24) # 16x24
        }
        
        if well_count in standard_formats:
            return standard_formats[well_count]
        
        # For non-standard formats, try to make a roughly square grid
        cols = math.ceil(math.sqrt(well_count))
        rows = math.ceil(well_count / cols)
        return (rows, cols)
    
    def get_well_id(self, row: int, col: int) -> str:
        """Generate well ID in standard format (A1, B2, etc.)."""
        row_letter = chr(ord('A') + row)
        col_number = col + 1
        return f"{row_letter}{col_number}"
    
    def on_well_clicked(self, wellplate_name: str, well_id: str, ctrl_pressed: bool, shift_pressed: bool):
        """Handle well click events with toggle selection."""
        # If we were dragging, don't process click (drag takes precedence)
        if self.is_dragging:
            return
        
        # Toggle selection behavior - click once to select, click again to deselect
        if well_id in self.selected_wells:
            # Well is already selected - deselect it
            self.selected_wells.remove(well_id)
            self.well_widgets[well_id].set_selected(False)
        else:
            # Well is not selected - select it (add to existing selection)
            self.selected_wells.add(well_id)
            self.well_widgets[well_id].set_selected(True)
        
        self.update_selection_info()
        self.wells_clicked.emit(wellplate_name, list(self.selected_wells))
        self.assign_cuboids_btn.setEnabled(len(self.selected_wells) > 0)



class CuboidPickingView(QWidget):
    """Main cuboid picking view widget with settings panel and wellplate interaction."""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.wellplate_grids = {}
        self.picking_settings = self.controller.get_default_picking_config()
        self.current_wellplate_name = ""
        self.tissue_picker_window = None  # Initialize tissue picker display window
        self.setup_ui()
        self.load_wellplates()
    
    def setup_ui(self):
        """Setup the main UI with settings panel and wellplate view."""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Settings
        self.settings_widget = PickingSettingsWidget()
        self.settings_widget.settings_changed.connect(self.on_settings_changed)
        self.settings_widget.setMaximumWidth(400)
        self.settings_widget.setMinimumWidth(300)
        splitter.addWidget(self.settings_widget)
        
        # Right panel - Wellplate control
        wellplate_widget = QWidget()
        wellplate_layout = QVBoxLayout(wellplate_widget)
        wellplate_layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Cuboid Picking Configuration")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        wellplate_layout.addWidget(title)
        
        # Controls group
        controls_group = QGroupBox("Wellplate Selection")
        controls_layout = QHBoxLayout()
        
        # Wellplate selector
        controls_layout.addWidget(QLabel("Select Wellplate:"))
        self.wellplate_combo = QComboBox()
        self.wellplate_combo.currentTextChanged.connect(self.on_wellplate_selected)
        controls_layout.addWidget(self.wellplate_combo)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_wellplates)
        controls_layout.addWidget(refresh_btn)
        
        # Pick cuboids button
        self.pick_cuboids_btn = QPushButton("Pick Cuboids")
        self.pick_cuboids_btn.clicked.connect(self.start_cuboid_picking)
        self.pick_cuboids_btn.setEnabled(False)
        self.pick_cuboids_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        controls_layout.addWidget(self.pick_cuboids_btn)
        
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        wellplate_layout.addWidget(controls_group)
        
        # Summary panel
        self.summary_group = QGroupBox("Assignment Summary")
        self.summary_layout = QVBoxLayout()
        
        summary_info_layout = QHBoxLayout()
        self.well_count_label = QLabel("Wells: -")
        summary_info_layout.addWidget(self.well_count_label)
        
        self.dimensions_label = QLabel("Dimensions: -")
        summary_info_layout.addWidget(self.dimensions_label)
        
        self.assigned_wells_label = QLabel("Assigned Wells: 0")
        summary_info_layout.addWidget(self.assigned_wells_label)
        
        self.total_cuboids_label = QLabel("Total Cuboids: 0")
        summary_info_layout.addWidget(self.total_cuboids_label)
        
        summary_info_layout.addStretch()
        
        # Clear all assignments button
        self.clear_all_btn = QPushButton("Clear All Assignments")
        self.clear_all_btn.clicked.connect(self.clear_all_assignments)
        summary_info_layout.addWidget(self.clear_all_btn)
        
        self.summary_layout.addLayout(summary_info_layout)
        self.summary_group.setLayout(self.summary_layout)
        self.summary_group.setVisible(False)
        wellplate_layout.addWidget(self.summary_group)
        
        # Scroll area for wellplate grids
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Container widget for grids
        self.grid_container = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(self.grid_container)
        wellplate_layout.addWidget(scroll_area)
        
        # Status area
        self.status_label = QLabel("Ready to load wellplates...")
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        wellplate_layout.addWidget(self.status_label)
        
        splitter.addWidget(wellplate_widget)
        
        # Set splitter proportions (30% settings, 70% wellplate)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 700])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def on_settings_changed(self, settings):
        """Handle settings changes."""
        self.picking_settings = settings
        self.status_label.setText("Picking settings updated successfully.")
    
    def load_wellplates(self):
        """Load available wellplate types with enhanced status updates."""
        try:
            self.status_label.setText("Loading wellplate configurations...")
            QApplication.processEvents()  # Update UI immediately
            
            # Get wellplate-specific labware
            wellplates = self.controller.get_wellplate_labware()
            
            # Update combo box with enhanced styling
            self.wellplate_combo.clear()
            self.wellplate_combo.addItem("Select a wellplate configuration...")
            
            if wellplates:
                for wellplate in sorted(wellplates):
                    self.wellplate_combo.addItem(wellplate)
                
                self.status_label.setText(f"Loaded {len(wellplates)} wellplate configurations")
            else:
                self.status_label.setText("No wellplate configurations found on deck")
                
        except Exception as e:
            self.status_label.setText(f"Error loading wellplates: {str(e)}")
    
    def extract_well_count(self, wellplate_name: str) -> int:
        """Extract well count from wellplate name with improved parsing."""
        # Clean the name first
        clean_name = wellplate_name.strip()
        
        # Look for number patterns in the name
        parts = clean_name.split('_')
        
        # Check for explicit well count patterns
        for part in parts:
            if part.isdigit():
                count = int(part)
                # Validate common wellplate sizes
                if count in [6, 12, 24, 48, 96, 384]:
                    return count
        
        # Look for patterns like "96well" or "well96"
        well_patterns = re.findall(r'(\d+)well|well(\d+)', clean_name.lower())
        for pattern in well_patterns:
            for num in pattern:
                if num and num.isdigit():
                    count = int(num)
                    if count in [6, 12, 24, 48, 96, 384]:
                        return count
        
        # If no direct number found, try regex for any numbers
        numbers = re.findall(r'\d+', clean_name)
        if numbers:
            # Take the first reasonable number
            for num_str in numbers:
                count = int(num_str)
                if count in [6, 12, 24, 48, 96, 384]:
                    return count
        
        # Default fallback to 96-well
        return 96
    
    def on_wellplate_selected(self, wellplate_name: str):
        """Handle wellplate selection with enhanced visual feedback."""
        # Clean the wellplate name
        clean_name = wellplate_name.strip()
        
        if clean_name.startswith("Select a wellplate") or not clean_name:
            self.clear_grids()
            self.summary_group.setVisible(False)
            self.pick_cuboids_btn.setEnabled(False)
            self.status_label.setText("Select a wellplate to begin")
            return
        
        # Clear existing grids
        self.clear_grids()
        
        try:
            self.current_wellplate_name = clean_name
            
            # Extract well count from name
            well_count = self.extract_well_count(clean_name)
            
            # Create the wellplate grid
            grid_widget = WellplateGridWidget(clean_name, well_count, self)
            grid_widget.wells_clicked.connect(self.on_wells_clicked)
            
            self.wellplate_grids[clean_name] = grid_widget
            self.grid_layout.addWidget(grid_widget)
            
            # Show summary panel
            self.summary_group.setVisible(True)
            
            # Update summary
            rows, cols = grid_widget.calculate_grid_dimensions(well_count)
            self.well_count_label.setText(f"Wells: {well_count}")
            self.dimensions_label.setText(f"Dimensions: {rows}×{cols}")
            self.update_assignment_summary()
            
            self.pick_cuboids_btn.setEnabled(True)
            self.status_label.setText(f"Loaded {clean_name} with {well_count} wells")
            
        except Exception as e:
            self.status_label.setText(f"Error loading wellplate: {str(e)}")
    
    def on_wells_clicked(self, wellplate_name: str, selected_wells: list):
        """Handle well click events."""
        self.update_assignment_summary()
    
    def update_assignment_summary(self):
        """Update the assignment summary display."""
        if not self.wellplate_grids:
            return
        
        # Get current grid
        current_grid = None
        for grid_name, grid_widget in self.wellplate_grids.items():
            if grid_name == self.current_wellplate_name:
                current_grid = grid_widget
                break
        
        if current_grid:
            total_cuboids = sum(current_grid.well_cuboid_counts.values())
            assigned_wells = sum(1 for count in current_grid.well_cuboid_counts.values() if count > 0)
            
            self.assigned_wells_label.setText(f"Assigned Wells: {assigned_wells}")
            self.total_cuboids_label.setText(f"Total Cuboids: {total_cuboids}")
    
    def clear_all_assignments(self):
        """Clear all cuboid assignments in current wellplate."""
        if self.current_wellplate_name in self.wellplate_grids:
            self.wellplate_grids[self.current_wellplate_name].clear_all_cuboids()
            self.update_assignment_summary()
    
    def start_cuboid_picking(self):
        """Start the cuboid picking procedure using FSM."""
        if not self.current_wellplate_name or self.current_wellplate_name not in self.wellplate_grids:
            QMessageBox.warning(self, "No Wellplate", "Please select a wellplate first.")
            return
        
        current_grid = self.wellplate_grids[self.current_wellplate_name]
        
        # Check if any cuboids are assigned
        total_cuboids = sum(current_grid.well_cuboid_counts.values())
        if total_cuboids == 0:
            QMessageBox.warning(self, "No Assignments", "Please assign cuboids to wells before starting picking procedure.")
            return
        
        try:

            # Open TissuePickerDisplayWindow
            self.tissue_picker_window = TissuePickerDisplayWindow(
                title="Tissue Picker Vision Display",
                controller=self.controller,
                parent=self
            )
            self.tissue_picker_window.start()
            self.tissue_picker_window.send_status("Initializing picking procedure...", (0, 255, 255))  # Cyan status
            
            # Extract plate type from well count
            well_count = current_grid.well_count
            
            # Create well plan DataFrame
            well_df = current_grid.get_cuboid_assignment_matrix()
            
            # Use the already configured picking settings (initialized with defaults and updated by user)
            config_data = self.picking_settings
            
            # Start the picking procedure using the controller
            success = self.controller.start_cuboid_picking(
                well_plan=well_df,
                config_data=config_data,
            )
            
            if not success:
                QMessageBox.critical(self, "Error", "Failed to initialize cuboid picking procedure")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start cuboid picking: {str(e)}")
    
    def stop_cuboid_picking(self):
        """Stop the current cuboid picking procedure."""
        try:
            def on_stop_result(success):
                if success:
                    QMessageBox.information(self, "Stopped", "Cuboid picking procedure stopped successfully")
                else:
                    QMessageBox.warning(self, "Warning", "No active picking procedure to stop")
                    
            def on_stop_error(error):
                QMessageBox.critical(self, "Error", f"Error stopping picking procedure: {error}")
                
            def on_stop_finished():
                self.pick_cuboids_btn.setText("Pick Cuboids")
                self.pick_cuboids_btn.clicked.disconnect()
                self.pick_cuboids_btn.clicked.connect(self.start_cuboid_picking)
                self.status_label.setText("Picking procedure stopped")
            
            self.controller.stop_cuboid_picking(
                on_result=on_stop_result,
                on_error=on_stop_error,
                on_finished=on_stop_finished
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to stop cuboid picking: {str(e)}")
    
    def clear_grids(self):
        """Clear all existing wellplate grids with proper cleanup."""
        for grid_widget in self.wellplate_grids.values():
            self.grid_layout.removeWidget(grid_widget)
            grid_widget.deleteLater()
        self.wellplate_grids.clear()
        
        # Reset summary
        if hasattr(self, 'summary_group'):
            self.summary_group.setVisible(False)


class TissuePickerDisplayWindow(QDialog):
    """Display window for tissue picker vision and status."""
    
    def __init__(self, title: str = "Tissue Picker Vision", controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.is_active = False
        self.status_text = ""
        self.status_color = (255, 255, 255)

        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.setModal(False)  # Make it non-modal so it doesn't block the main application
        
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()

        # Status info
        info_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Initializing...")
        self.status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #0066cc; padding: 5px;")
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()

        # Control group
        controls_group = QGroupBox("Controls")
        controls_layout = QHBoxLayout()

        # Control buttons
        self.pause_btn = QPushButton("Pause/Resume (P)")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setToolTip("Pause or resume the picking process")
        controls_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Emergency Stop (ESC)")
        self.stop_btn.clicked.connect(self.emergency_stop)
        self.stop_btn.setToolTip("Emergency stop the picking process")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #ff4444; color: white; font-weight: bold; }")
        controls_layout.addWidget(self.stop_btn)

        self.reset_view_btn = QPushButton("Reset View")
        self.reset_view_btn.clicked.connect(self.reset_view)
        self.reset_view_btn.setToolTip("Reset camera view zoom and pan")
        controls_layout.addWidget(self.reset_view_btn)

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
    
    def setup_timer(self):
        """Setup timer for video updates."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(33)  # ~30 FPS
    
    def start(self):
        """Start the display window."""
        self.is_active = True
        self.show()
        self.raise_()  # Bring window to front
        self.activateWindow()  # Make it the active window
    
    def stop(self):
        """Stop the display window."""
        self.is_active = False
        self.timer.stop()
        self.close()
    
    def send_status(self, status_text: str, color: tuple = (255, 255, 255)):
        """Send status text to be displayed."""
        self.status_text = status_text
        self.status_color = color
        
        # Update status label
        color_hex = f"#{color[2]:02x}{color[1]:02x}{color[0]:02x}"  # BGR to RGB hex
        self.status_label.setText(f"Status: {status_text}")
        self.status_label.setStyleSheet(f"color: {color_hex}; font-weight: bold; padding: 5px;")
    
    def update_display(self):
        """Update the video display."""
        if self.is_active and globals.cuboid_picking_frame is not None:
            self.video_display.set_frame(globals.cuboid_picking_frame)
    
    def toggle_pause(self):
        """Toggle pause/resume - emulate 'p' key press."""
        try:
            import keyboard
            keyboard.send('p')
        except Exception as e:
            print(f"Could not send pause command: {e}")
    
    def emergency_stop(self):
        """Emergency stop - emulate 'ESC' key press."""
        try:
            import keyboard
            keyboard.send('esc')
        except Exception as e:
            print(f"Could not send stop command: {e}")
    
    def reset_view(self):
        """Reset the video view."""
        self.video_display.reset_view()
    
    def closeEvent(self, event):
        """Handle close event."""
        self.stop()
        event.accept()


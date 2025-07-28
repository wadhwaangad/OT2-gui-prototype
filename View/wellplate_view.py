"""
Wellplate view    well_clicked = pyqtSignal(str, bool, bool)  # well_id, ctrl_pressed, shift_pressed
    
    def __init__(self, well_id: str, parent=None):
        super().__init__(parent)
        self.well_id = well_id
        self.is_selected = False
        self.is_hovered = False
        self.animation = None
        self.setup_ui()rotissue manipulator GUI.
Displays available wellplate labware types with interactive grid visualization.
"""

import re
import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                           QPushButton, QLabel, QGroupBox, QComboBox, QFrame,
                           QScrollArea, QSizePolicy, QCheckBox, QButtonGroup,
                           QSpacerItem, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QBrush, QPen, QLinearGradient
import Model.globals as globals


class WellWidget(QFrame):
    """Individual well widget with enhanced animation and interaction."""
    
    well_clicked = pyqtSignal(str, bool, bool)  # well_id, ctrl_pressed, shift_pressed
    
    def __init__(self, well_id: str, parent=None):
        super().__init__(parent)
        self.well_id = well_id
        self.is_selected = False
        self.is_hovered = False
        self.animation = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the well widget UI with professional styling."""
        self.setFixedSize(38, 38)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.update_appearance()
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Set tooltip
        self.setToolTip(f"Well {self.well_id}\nClick to toggle selection\nDrag to select area")
        
        # Create label for well ID
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        self.label = QLabel(self.well_id)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        layout.addWidget(self.label)
        self.setLayout(layout)
    
    def update_appearance(self):
        """Update the visual appearance with professional styling."""
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


class WellplateGridWidget(QFrame):
    """Interactive wellplate grid widget with unified drag selection."""
    
    wells_clicked = pyqtSignal(str, list)  # wellplate_name, selected_wells_list
    
    def __init__(self, wellplate_name: str, well_count: int, parent=None):
        super().__init__(parent)
        self.wellplate_name = wellplate_name
        self.well_count = well_count
        self.well_widgets = {}
        self.selected_wells = set()
        self.last_selected_well = None  # For range selection
        self.well_positions = {}  # Store well positions for range selection
        
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
        
        # Simple controls
        controls_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_wells)
        controls_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("Clear")
        self.select_none_btn.clicked.connect(self.clear_selection)
        controls_layout.addWidget(self.select_none_btn)
        
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
            self.grid_layout.addWidget(well_widget, row + 1, col + 1)
        
        layout.addLayout(self.grid_layout)
        
        # Selected well info
        self.selected_info = QLabel("Click wells to toggle selection • Drag to select area • Click row/column labels to toggle entire row/column")
        self.selected_info.setFont(QFont("Arial", 9))
        self.selected_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected_info.setStyleSheet("color: #7f8c8d; margin-top: 10px; font-style: italic;")
        layout.addWidget(self.selected_info)
        
        self.setLayout(layout)
    
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
    
    def select_all_wells(self):
        """Select all wells in the wellplate."""
        for well_id, well_widget in self.well_widgets.items():
            self.selected_wells.add(well_id)
            well_widget.set_selected(True)
        self.update_selection_info()
        self.wells_clicked.emit(self.wellplate_name, list(self.selected_wells))
    
    def clear_selection(self):
        """Clear all selected wells."""
        for well_id in list(self.selected_wells):
            if well_id in self.well_widgets:
                self.well_widgets[well_id].set_selected(False)
        self.selected_wells.clear()
        self.last_selected_well = None
        self.update_selection_info()
        self.wells_clicked.emit(self.wellplate_name, list(self.selected_wells))
    
    def update_selection_info(self):
        """Update the selection information display."""
        count = len(self.selected_wells)
        if count == 0:
            self.selected_info.setText("Click wells to toggle selection • Drag to select area • Click row/column labels to toggle entire row/column")
        elif count == 1:
            well = list(self.selected_wells)[0]
            row_letter = well[0]
            column_number = well[1:]
            self.selected_info.setText(f"Selected: {well} (Row {row_letter}, Column {column_number})")
        else:
            sorted_wells = sorted(list(self.selected_wells))
            if count <= 5:
                wells_text = ', '.join(sorted_wells)
            else:
                wells_text = f"{', '.join(sorted_wells[:3])}... (+{count - 3} more)"
            self.selected_info.setText(f"Selected {count} wells: {wells_text}")
    
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


class WellplateView(QWidget):
    """Main wellplate view widget with professional design."""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.wellplate_grids = {}
        self.setup_ui()
        self.load_wellplates()
    
    def setup_ui(self):
        """Setup the main UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Wellplate Controls")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
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
        
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Summary panel
        self.summary_group = QGroupBox("Wellplate Information")
        self.summary_layout = QHBoxLayout()
        
        self.well_count_label = QLabel("Wells: -")
        self.summary_layout.addWidget(self.well_count_label)
        
        self.dimensions_label = QLabel("Dimensions: -")
        self.summary_layout.addWidget(self.dimensions_label)
        
        self.selected_well_label = QLabel("Selected: None")
        self.summary_layout.addWidget(self.selected_well_label)
        
        # Clear selection button
        self.clear_btn = QPushButton("Clear Selection")
        self.clear_btn.clicked.connect(self.clear_selection)
        self.summary_layout.addWidget(self.clear_btn)
        
        self.summary_layout.addStretch()
        self.summary_group.setLayout(self.summary_layout)
        self.summary_group.setVisible(False)
        layout.addWidget(self.summary_group)
        
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
        layout.addWidget(scroll_area)
        
        # Status area
        self.status_label = QLabel("Ready to load wellplates...")
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
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
        import re
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
                num = int(num_str)
                if 6 <= num <= 384:  # Reasonable wellplate range
                    return num
        
        # Default fallback to 96-well
        return 96
    
    def on_wellplate_selected(self, wellplate_name: str):
        """Handle wellplate selection with enhanced visual feedback."""
        # Clean the wellplate name
        clean_name = wellplate_name.strip()
        
        if clean_name.startswith("Select a wellplate") or not clean_name:
            self.clear_grids()
            self.summary_group.setVisible(False)
            self.status_label.setText("Select a wellplate to begin")
            return
        
        # Clear existing grids
        self.clear_grids()
        
        try:
            self.status_label.setText(f"Generating {clean_name} visualization...")
            QApplication.processEvents()
            
            # Extract well count from cleaned name
            well_count = self.extract_well_count(clean_name)
            
            # Create enhanced grid widget
            grid_widget = WellplateGridWidget(clean_name, well_count)
            grid_widget.wells_clicked.connect(self.on_wells_clicked)
            
            # Add to layout with proper alignment
            self.grid_layout.addWidget(grid_widget, 0, Qt.AlignmentFlag.AlignCenter)
            self.wellplate_grids[clean_name] = grid_widget
            
            # Update summary information with enhanced formatting
            rows, cols = grid_widget.calculate_grid_dimensions(well_count)
            self.well_count_label.setText(f"Wells: {well_count}")
            self.dimensions_label.setText(f"Grid: {rows}×{cols}")
            self.selected_well_label.setText("Selected: None")
            self.summary_group.setVisible(True)
            
            # Update status with success message
            self.status_label.setText(
                f"{clean_name} loaded - {well_count} wells in {rows}×{cols} grid"
            )
            
        except Exception as e:
            self.status_label.setText(f"Error creating wellplate visualization: {str(e)}")
            self.summary_group.setVisible(False)
    
    def on_wells_clicked(self, wellplate_name: str, selected_wells: list):
        """Handle well click events with enhanced status updates."""
        # Update summary with detailed information
        if len(selected_wells) == 0:
            self.selected_well_label.setText("Selected: None")
            self.status_label.setText(f"Click wells to select in {wellplate_name}")
        elif len(selected_wells) == 1:
            well = selected_wells[0]
            self.selected_well_label.setText(f"Selected: {well}")
            row_letter = well[0]
            column_number = well[1:]
            self.status_label.setText(
                f"Selected {well} in {wellplate_name} (Row {row_letter}, Column {column_number})"
            )
        else:
            sorted_wells = sorted(selected_wells)
            if len(sorted_wells) <= 5:
                display_wells = ', '.join(sorted_wells)
            else:
                display_wells = f"{', '.join(sorted_wells[:3])}... (+{len(sorted_wells) - 3} more)"
            
            self.selected_well_label.setText(f"Selected: {display_wells}")
            self.status_label.setText(
                f"{len(selected_wells)} wells selected in {wellplate_name}"
            )
    
    def clear_selection(self):
        """Clear all selected wells with visual feedback."""
        cleared_count = 0
        for grid_widget in self.wellplate_grids.values():
            cleared_count += len(grid_widget.selected_wells)
            grid_widget.clear_selection()
        
        # Update summary
        self.selected_well_label.setText("Selected: None")
        if cleared_count > 0:
            self.status_label.setText(f"Cleared {cleared_count} selected wells")
        else:
            self.status_label.setText("No wells selected to clear")
    
    def clear_grids(self):
        """Clear all existing wellplate grids with proper cleanup."""
        for grid_widget in self.wellplate_grids.values():
            self.grid_layout.removeWidget(grid_widget)
            grid_widget.deleteLater()
        self.wellplate_grids.clear()
        
        # Reset summary
        if hasattr(self, 'summary_group'):
            self.summary_group.setVisible(False)
    
    def refresh_wellplates(self):
        """Refresh the wellplate list with status feedback."""
        self.status_label.setText("Refreshing wellplate configurations...")
        self.load_wellplates()

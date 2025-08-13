"""
Camera view for the microtissue manipulator GUI.
"""

import cv2
import numpy as np
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                           QListWidgetItem, QPushButton, QLabel, QSlider, 
                           QSpinBox, QGroupBox, QDialog, QDialogButtonBox,
                           QSplitter, QFrame, QCheckBox, QComboBox, QScrollArea)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from View.zoomable_video_widget import VideoDisplayWidget


class CameraTestWindow(QDialog):
    """Separate window for testing individual cameras."""
    
    def __init__(self, camera_name: str, camera_index: int, controller, parent=None):
        super().__init__(parent)
        self.camera_name = camera_name
        self.camera_index = camera_index
        self.controller = controller
        self.is_capturing = False
        self.rotation_angle = 0

        self.setWindowTitle(f"Camera Test - {camera_name}")
        self.setMinimumSize(800, 600)
        
        self.setup_ui()
        self.setup_timer()
        
        # Initialize focus max value after UI is setup
        self.on_focus_max_changed(1100)
        
        # Connect to existing camera stream (don't start new capture)
        self.connect_to_stream()
    
    def setup_ui(self):
        """Setup the user interface."""
        import os, json
        layout = QVBoxLayout()

        # Camera info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"Camera: {self.camera_name}"))
        info_layout.addWidget(QLabel(f"Index: {self.camera_index}"))
        info_layout.addStretch()

        # Camera controls
        controls_group = QGroupBox("Camera Controls")
        controls_layout = QHBoxLayout()

        # Resolution selection
        res_layout = QVBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))
        res_input_layout = QHBoxLayout()
        self.res_combo = QComboBox()
        self.custom_width = None
        self.custom_height = None
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cam_configs")
        config_file = os.path.join(config_dir, f"{self.camera_name}.json")
        resolutions = []
        default_res = (640, 480)
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                resolutions = config.get("resolutions", [])
                default_res = tuple(config.get("default_resolution", [640, 480]))
            except Exception:
                resolutions = []
                default_res = (640, 480)
        if resolutions:
            for w, h in resolutions:
                self.res_combo.addItem(f"{w} x {h}", (w, h))
            # Set to default resolution if present
            default_index = 0
            for i in range(self.res_combo.count()):
                if self.res_combo.itemData(i) == default_res:
                    default_index = i
                    break
            self.res_combo.setCurrentIndex(default_index)
            res_input_layout.addWidget(self.res_combo)
        else:
            self.custom_width = QSpinBox()
            self.custom_width.setRange(1, 10000)
            self.custom_width.setValue(default_res[0])
            self.custom_width.setPrefix("W: ")
            self.custom_height = QSpinBox()
            self.custom_height.setRange(1, 10000)
            self.custom_height.setValue(default_res[1])
            self.custom_height.setPrefix("H: ")
            res_input_layout.addWidget(self.custom_width)
            res_input_layout.addWidget(self.custom_height)
        res_layout.addLayout(res_input_layout)

        # Focus control
        focus_layout = QVBoxLayout()
        focus_layout.addWidget(QLabel("Focus:"))
        focus_input_layout = QHBoxLayout()
        self.focus_slider = QSlider(Qt.Orientation.Horizontal)
        self.focus_slider.setMinimum(0)
        self.focus_slider.setMaximum(1100)
        self.focus_slider.setValue(900)
        self.focus_slider.valueChanged.connect(self.on_focus_changed)
        focus_input_layout.addWidget(self.focus_slider)

        self.focus_max_spinbox = QSpinBox()
        self.focus_max_spinbox.setMinimum(1)
        self.focus_max_spinbox.setMaximum(10000)
        self.focus_max_spinbox.setValue(1100)
        self.focus_max_spinbox.setPrefix("Max: ")
        self.focus_max_spinbox.valueChanged.connect(self.on_focus_max_changed)
        focus_input_layout.addWidget(self.focus_max_spinbox)

        focus_layout.addLayout(focus_input_layout)
        self.focus_value_label = QLabel("900")
        focus_layout.addWidget(self.focus_value_label)

        # Control buttons
        button_layout = QVBoxLayout()
        self.reset_view_btn = QPushButton("Reset View")
        self.reset_view_btn.clicked.connect(self.reset_view)
        button_layout.addWidget(self.reset_view_btn)

        self.capture_btn = QPushButton("Stop Capture")
        self.capture_btn.clicked.connect(self.toggle_capture)
        button_layout.addWidget(self.capture_btn)

        self.rotate_btn = QPushButton("Rotate 90°")
        self.rotate_btn.clicked.connect(self.rotate_feed)
        button_layout.addWidget(self.rotate_btn)

        controls_layout.addLayout(res_layout)
        controls_layout.addLayout(focus_layout)
        controls_layout.addLayout(button_layout)
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
        """Setup camera viewer for this window."""
        try:
            # Create a dedicated camera viewer for this window
            self.camera_viewer = self.controller.create_camera_viewer(self.camera_name)
            self.camera_viewer.frame_received.connect(self.on_frame_received)
        except Exception as e:
            print(f"Error setting up camera viewer for {self.camera_name}: {e}")
            import traceback
            traceback.print_exc()
            self.camera_viewer = None

    def on_frame_received(self, frame):
        """Handle incoming frame from camera viewer."""
        if self.is_capturing:
            self.update_frame_display(frame)

    def update_frame_display(self, frame):
        """Update the video display with the given frame."""
        if frame is not None:
            # Apply rotation if needed
            if self.rotation_angle != 0:
                frame = self.rotate_frame(frame, self.rotation_angle)
            self.video_display.set_frame(frame)

    def get_selected_resolution(self):
        if self.res_combo and self.res_combo.count() > 0:
            return self.res_combo.currentData()
        elif self.custom_width and self.custom_height:
            return (self.custom_width.value(), self.custom_height.value())
        return (640, 480)

    def on_focus_max_changed(self, value):
        """Update the maximum value of the focus slider."""
        self.focus_slider.setMaximum(value)
        # If current value is above new max, adjust
        if self.focus_slider.value() > value:
            self.focus_slider.setValue(value)

    def start_capture(self):
        """Start camera capture."""
        try:
            # Refresh cameras before starting to ensure indices are current
            self.controller.refresh_cameras()
            
            # Get current resolution
            width, height = self.get_selected_resolution()
            
            # Check if camera viewer was created successfully
            if not hasattr(self, 'camera_viewer') or self.camera_viewer is None:
                print(f"Camera viewer not initialized for {self.camera_name}")
                return
            
            # Start camera capture (this will succeed even if camera is already running)
            success = self.controller.start_camera_capture(self.camera_name, self.camera_index, width, height)
            if success:
                # Connect this viewer to the stream
                if self.camera_viewer.connect_to_stream():
                    self.is_capturing = True
                    self.capture_btn.setText("Stop Capture")
                    # Set focus to current slider value
                    self.controller.set_camera_focus(self.camera_name, self.focus_slider.value())
                    print(f"Started test window for camera: {self.camera_name}, viewers: {self.controller.get_camera_viewer_count(self.camera_name)}")
                else:
                    print(f"Failed to connect viewer to camera stream: {self.camera_name}")
            else:
                print(f"Failed to start camera capture for {self.camera_name} at index {self.camera_index}")
        except Exception as e:
            print(f"Error in start_capture for {self.camera_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def connect_to_stream(self):
        """Connect to existing camera stream without starting new capture."""
        try:
            # Check if camera viewer was created successfully
            if not hasattr(self, 'camera_viewer') or self.camera_viewer is None:
                print(f"Camera viewer not initialized for {self.camera_name}")
                return
            
            # Connect this viewer to the existing stream
            if self.camera_viewer.connect_to_stream():
                self.is_capturing = True
                self.capture_btn.setText("Stop Capture")
                # Set focus to current slider value
                self.controller.set_camera_focus(self.camera_name, self.focus_slider.value())
                print(f"Connected test window to existing camera stream: {self.camera_name}, viewers: {self.controller.get_camera_viewer_count(self.camera_name)}")
            else:
                print(f"Failed to connect viewer to camera stream: {self.camera_name}")
                # If connection failed, try starting capture
                self.start_capture()
                
        except Exception as e:
            print(f"Error in connect_to_stream for {self.camera_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_capture(self):
        """Stop camera capture for this viewer only."""
        self.is_capturing = False
        self.capture_btn.setText("Start Capture")
        self.video_display.clear_frame()
        
        # Disconnect this viewer from the stream
        self.camera_viewer.disconnect_from_stream()
        print(f"Stopped test window for camera: {self.camera_name}, remaining viewers: {self.controller.get_camera_viewer_count(self.camera_name)}")
        
        # Only stop the actual camera capture if no other viewers are using it
        viewer_count = self.controller.get_camera_viewer_count(self.camera_name)
        if viewer_count == 0:
            print(f"No more viewers for {self.camera_name}, stopping camera capture")
            self.controller.stop_camera_capture(self.camera_name)
    
    def toggle_capture(self):
        """Toggle camera capture."""
        if self.is_capturing:
            self.stop_capture()
        else:
            self.start_capture()
    
    def rotate_feed(self):
        """Rotate the camera feed by 90 degrees clockwise."""
        self.rotation_angle = (self.rotation_angle + 90) % 360
        # Update button text to show current rotation
        if self.rotation_angle == 0:
            self.rotate_btn.setText("Rotate 90°")
        else:
            self.rotate_btn.setText(f"Rotate 90° ({self.rotation_angle}°)")

    def update_frame(self):
        """Legacy method - no longer used with signal system."""
        pass

    def rotate_frame(self, frame, angle):
        """Rotate frame by the specified angle."""
        if angle == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame
    def on_focus_changed(self, value):
        """Handle focus slider changes."""
        self.focus_value_label.setText(str(value))
        if self.is_capturing:
            self.controller.set_camera_focus(self.camera_name, value)
    
    def reset_view(self):
        """Reset the video view."""
        self.video_display.reset_view()
    
    def closeEvent(self, event):
        """Handle close event."""
        try:
            # Stop capturing for this window
            if self.is_capturing:
                self.stop_capture()
            
            # Disconnect this viewer from the stream (if not already done)
            if hasattr(self, 'camera_viewer') and self.camera_viewer and self.camera_viewer.is_connected:
                self.camera_viewer.disconnect_from_stream()
            
            event.accept()
            
        except Exception as e:
            print(f"Error during close event: {e}")
            event.accept()


class CameraView(QWidget):
    """Main camera view widget."""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.test_windows = {}
        self.active_embedded_cameras = {}
        self.embedded_camera_viewer = None  # For the embedded display
        
        self.setup_ui()
        self.setup_timer()
        self.refresh_cameras()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Create scroll area for the main content
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        main_layout = QVBoxLayout(scroll_widget)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Camera list and controls
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel - Embedded camera display
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([400, 800])
        
        # Add splitter to scroll widget
        main_layout.addWidget(main_splitter)
        
        # Set up scroll area
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        self.setLayout(layout)
        
        # Connect camera list selection
        self.camera_list.itemSelectionChanged.connect(self.on_camera_selection_changed)
    
    def create_left_panel(self):
        import os, json
        left_widget = QWidget()
        layout = QVBoxLayout()

        # Camera list group
        camera_group = QGroupBox("Available Cameras")
        camera_layout = QVBoxLayout()

        # Camera list
        self.camera_list = QListWidget()
        self.camera_list.itemDoubleClicked.connect(self.on_camera_double_clicked)
        camera_layout.addWidget(self.camera_list)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh Cameras")
        self.refresh_btn.clicked.connect(self.refresh_cameras)
        camera_layout.addWidget(self.refresh_btn)

        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)

        # Camera controls group
        controls_group = QGroupBox("Camera Controls")
        controls_layout = QVBoxLayout()

        # Selected camera info
        self.selected_camera_label = QLabel("No camera selected")
        self.selected_camera_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        controls_layout.addWidget(self.selected_camera_label)

        # Display option
        display_layout = QHBoxLayout()
        display_layout.addWidget(QLabel("Display:"))
        self.display_combo = QComboBox()
        self.display_combo.addItems(["Embedded View", "Separate Window"])
        display_layout.addWidget(self.display_combo)
        controls_layout.addLayout(display_layout)

        # Resolution selection
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))
        self.res_combo = QComboBox()
        self.custom_width = QSpinBox()
        self.custom_height = QSpinBox()
        self.custom_width.setRange(1, 10000)
        self.custom_height.setRange(1, 10000)
        self.res_combo.hide()
        self.custom_width.hide()
        self.custom_height.hide()
        res_layout.addWidget(self.res_combo)
        res_layout.addWidget(self.custom_width)
        res_layout.addWidget(self.custom_height)
        controls_layout.addLayout(res_layout)

        # Start/Stop camera button
        self.start_stop_btn = QPushButton("Start Camera")
        self.start_stop_btn.clicked.connect(self.toggle_selected_camera)
        self.start_stop_btn.setEnabled(False)
        controls_layout.addWidget(self.start_stop_btn)

        # Focus control
        focus_layout = QVBoxLayout()
        focus_layout.addWidget(QLabel("Focus:"))
        focus_input_layout = QHBoxLayout()
        self.focus_slider = QSlider(Qt.Orientation.Horizontal)
        self.focus_slider.setMinimum(0)
        self.focus_slider.setMaximum(1100)
        self.focus_slider.setValue(900)
        self.focus_slider.valueChanged.connect(self.on_focus_changed)
        self.focus_slider.setEnabled(False)
        focus_input_layout.addWidget(self.focus_slider)

        self.focus_max_spinbox = QSpinBox()
        self.focus_max_spinbox.setMinimum(1)
        self.focus_max_spinbox.setMaximum(10000)
        self.focus_max_spinbox.setValue(1100)
        self.focus_max_spinbox.setPrefix("Max: ")
        self.focus_max_spinbox.valueChanged.connect(self.on_focus_max_changed)
        focus_input_layout.addWidget(self.focus_max_spinbox)

        focus_layout.addLayout(focus_input_layout)
        self.focus_value_label = QLabel("900")
        focus_layout.addWidget(self.focus_value_label)
        controls_layout.addLayout(focus_layout)

        # Reset view button
        self.reset_view_btn = QPushButton("Reset View")
        self.reset_view_btn.clicked.connect(self.reset_embedded_view)
        self.reset_view_btn.setEnabled(False)
        controls_layout.addWidget(self.reset_view_btn)

        # Stop all cameras button
        self.stop_all_btn = QPushButton("Stop All Cameras")
        self.stop_all_btn.clicked.connect(self.stop_all_cameras)
        controls_layout.addWidget(self.stop_all_btn)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        left_widget.setLayout(layout)
        left_widget.setMaximumWidth(400)
        return left_widget
    
    def create_right_panel(self):
        """Create the right panel with embedded camera display."""
        right_widget = QWidget()
        layout = QVBoxLayout()
        
        # Embedded camera display group
        display_group = QGroupBox("Embedded Camera Display")
        display_layout = QVBoxLayout()
        
        # Active camera info
        self.active_camera_label = QLabel("No active camera")
        self.active_camera_label.setStyleSheet("font-weight: bold; color: #009900;")
        display_layout.addWidget(self.active_camera_label)
        
        # Video display widget
        self.embedded_video_display = VideoDisplayWidget()
        display_layout.addWidget(self.embedded_video_display, 1)  # Give it stretch factor
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        right_widget.setLayout(layout)
        return right_widget
    
    def setup_timer(self):
        """Setup for receiving camera frames - now handled by individual camera viewers."""
        pass  # Camera viewers handle their own connections
    
    def update_embedded_display_frame(self, frame):
        """Update the embedded camera display with the given frame."""
        if frame is not None:
            self.embedded_video_display.set_frame(frame)
    
    def on_focus_changed(self, value):
        """Handle focus slider changes."""
        self.focus_value_label.setText(str(value))
        
        # Apply focus to active embedded camera
        if self.active_embedded_cameras:
            camera_name = list(self.active_embedded_cameras.keys())[0]
            self.controller.set_camera_focus(camera_name, value)
    
    def on_focus_max_changed(self, value):
        """Update the maximum value of the focus slider."""
        self.focus_slider.setMaximum(value)
        # If current value is above new max, adjust
        if self.focus_slider.value() > value:
            self.focus_slider.setValue(value)
    
    def reset_embedded_view(self):
        """Reset the embedded video view."""
        self.embedded_video_display.reset_view()
    
    def on_camera_double_clicked(self, item):
        """Handle double-click on camera item."""
        camera_data = item.data(Qt.ItemDataRole.UserRole)
        if camera_data is not None:
            self.test_camera(camera_data[0], camera_data[1])
    
    def test_camera(self, camera_name: str, camera_index: int):
        """Open a test window for the specified camera."""
        # Refresh cameras before testing to ensure indices are current
        self.controller.refresh_cameras()
        
        # Close existing test window for this camera if it exists
        if camera_name in self.test_windows:
            self.test_windows[camera_name].close()
        
        # Get resolution
        if self.res_combo.isVisible() and self.res_combo.count() > 0:
            width, height = self.res_combo.currentData()
        else:
            width = self.custom_width.value()
            height = self.custom_height.value()
        
        # Start camera capture if not already active
        if not self.controller.is_camera_active(camera_name):
            success = self.controller.start_camera_capture(camera_name, camera_index, width, height)
            if not success:
                print(f"Failed to start camera capture for {camera_name} at index {camera_index}")
                return
        
        # Create new test window
        test_window = CameraTestWindow(camera_name, camera_index, self.controller, self)
        test_window.show()
        
        # Store reference
        self.test_windows[camera_name] = test_window
        
        # Connect close event to clean up reference
        test_window.finished.connect(lambda: self.on_test_window_closed(camera_name))
    
    def on_test_window_closed(self, camera_name: str):
        """Handle test window closure."""
        if camera_name in self.test_windows:
            del self.test_windows[camera_name]
        
        # Camera capture is already stopped by the test window's closeEvent
        # No additional action needed here since the window handles its own cleanup
    
    def refresh_cameras(self):
        """Refresh the list of available cameras."""
        # First, refresh the camera manager's device list
        self.controller.refresh_cameras()
        
        self.camera_list.clear()
        
        cameras = self.controller.get_available_cameras()
        
        if not cameras:
            item = QListWidgetItem("No cameras detected")
            item.setData(Qt.ItemDataRole.UserRole, None)
            self.camera_list.addItem(item)
            return
        
        for camera_data in cameras:
            # Unpack the camera data: (user_label, cam_index, cam_name, default_res)
            user_label, camera_index, cam_name, default_res = camera_data
            item = QListWidgetItem(f"{user_label} (Index: {camera_index})")
            item.setData(Qt.ItemDataRole.UserRole, (user_label, camera_index))
            self.camera_list.addItem(item)
    
    def on_camera_selection_changed(self):
        """Handle camera selection changes."""
        import os, json
        current_item = self.camera_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole) is not None:
            camera_data = current_item.data(Qt.ItemDataRole.UserRole)
            camera_name, camera_index = camera_data
            self.selected_camera_label.setText(f"Selected: {camera_name}")
            # Show resolution options
            config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cam_configs")
            config_file = os.path.join(config_dir, f"{camera_name}.json")
            self.res_combo.clear()
            default_res = (640, 480)
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        config = json.load(f)
                    resolutions = config.get("resolutions", [])
                    default_res = tuple(config.get("default_resolution", [640, 480]))
                except Exception:
                    resolutions = []
                    default_res = (640, 480)
                if resolutions:
                    self.res_combo.show()
                    self.custom_width.hide()
                    self.custom_height.hide()
                    for w, h in resolutions:
                        self.res_combo.addItem(f"{w} x {h}", (w, h))
                    # Set to default resolution if present
                    default_index = 0
                    for i in range(self.res_combo.count()):
                        if self.res_combo.itemData(i) == default_res:
                            default_index = i
                            break
                    self.res_combo.setCurrentIndex(default_index)
                else:
                    self.res_combo.hide()
                    self.custom_width.show()
                    self.custom_height.show()
                    self.custom_width.setValue(default_res[0])
                    self.custom_height.setValue(default_res[1])
            else:
                self.res_combo.hide()
                self.custom_width.show()
                self.custom_height.show()
                self.custom_width.setValue(default_res[0])
                self.custom_height.setValue(default_res[1])
            self.start_stop_btn.setEnabled(True)
            # Update button text based on current state
            if camera_name in self.active_embedded_cameras:
                self.start_stop_btn.setText("Stop Camera")
                self.focus_slider.setEnabled(True)
                self.reset_view_btn.setEnabled(True)
            else:
                self.start_stop_btn.setText("Start Camera")
                self.focus_slider.setEnabled(False)
                self.reset_view_btn.setEnabled(False)
        else:
            self.selected_camera_label.setText("No camera selected")
            self.res_combo.hide()
            self.custom_width.hide()
            self.custom_height.hide()
            self.start_stop_btn.setEnabled(False)
            self.focus_slider.setEnabled(False)
            self.reset_view_btn.setEnabled(False)
    
    def toggle_selected_camera(self):
        """Toggle the selected camera on/off."""
        current_item = self.camera_list.currentItem()
        if not current_item:
            return
        
        camera_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not camera_data:
            return
        
        camera_name, camera_index = camera_data
        display_mode = self.display_combo.currentText()
        
        if camera_name in self.active_embedded_cameras:
            # Stop camera
            self.stop_embedded_camera(camera_name)
        else:
            # Start camera
            if display_mode == "Embedded View":
                self.start_embedded_camera(camera_name, camera_index)
            else:
                self.test_camera(camera_name, camera_index)
    
    def start_embedded_camera(self, camera_name: str, camera_index: int):
        """Start a camera in embedded view."""
        try:
            # Refresh cameras before starting to ensure indices are current
            self.controller.refresh_cameras()
            
            # Stop any currently active embedded camera display
            if self.embedded_camera_viewer:
                self.embedded_camera_viewer.disconnect_from_stream()
                self.embedded_camera_viewer = None
            
            # Clear any previous embedded camera state
            self.active_embedded_cameras.clear()
            
            # Get resolution
            if self.res_combo.isVisible() and self.res_combo.count() > 0:
                width, height = self.res_combo.currentData()
            else:
                width = self.custom_width.value()
                height = self.custom_height.value()
            
            # Start camera capture (if not already running)
            success = self.controller.start_camera_capture(camera_name, camera_index, width, height)
            if success:
                # Create a camera viewer for the embedded display
                self.embedded_camera_viewer = self.controller.create_camera_viewer(camera_name)
                self.embedded_camera_viewer.frame_received.connect(self.update_embedded_display_frame)
                
                if self.embedded_camera_viewer.connect_to_stream():
                    self.active_embedded_cameras[camera_name] = camera_index
                    self.active_camera_label.setText(f"Active: {camera_name}")
                    self.start_stop_btn.setText("Stop Camera")
                    self.focus_slider.setEnabled(True)
                    self.reset_view_btn.setEnabled(True)
                    # Set initial focus
                    self.controller.set_camera_focus(camera_name, self.focus_slider.value())
                    
                    print(f"Started embedded camera: {camera_name}, viewers: {self.controller.get_camera_viewer_count(camera_name)}")
                else:
                    print(f"Failed to connect embedded viewer to camera stream: {camera_name}")
            else:
                print(f"Failed to start camera capture for {camera_name} at index {camera_index}")
        except Exception as e:
            print(f"Error starting embedded camera: {e}")
    
    def stop_embedded_camera(self, camera_name: str):
        """Stop an embedded camera display."""
        try:            
            if camera_name in self.active_embedded_cameras:
                # Disconnect the embedded viewer
                if self.embedded_camera_viewer:
                    self.embedded_camera_viewer.disconnect_from_stream()
                    self.embedded_camera_viewer = None
                
                del self.active_embedded_cameras[camera_name]
                print(f"Stopped embedded camera: {camera_name}, remaining viewers: {self.controller.get_camera_viewer_count(camera_name)}")
            
            self.active_camera_label.setText("No active camera")
            self.embedded_video_display.clear_frame()
            self.start_stop_btn.setText("Start Camera")
            self.focus_slider.setEnabled(False)
            self.reset_view_btn.setEnabled(False)
            
            # Only stop the actual camera capture if no other viewers are using it
            viewer_count = self.controller.get_camera_viewer_count(camera_name)
            if viewer_count == 0:
                print(f"No more viewers for {camera_name}, stopping camera capture")
                self.controller.stop_camera_capture(camera_name)
            
        except Exception as e:
            print(f"Error stopping embedded camera: {e}")
    
    def stop_all_cameras(self):
        """Stop all active cameras."""
        # Stop embedded camera viewer
        if self.embedded_camera_viewer:
            self.embedded_camera_viewer.disconnect_from_stream()
            self.embedded_camera_viewer = None
        
        # Clear active embedded cameras
        self.active_embedded_cameras.clear()
        
        # Close all test windows (they will stop their own cameras)
        for camera_name, window in list(self.test_windows.items()):
            window.close()

"""
Main GUI application for the microtissue manipulator.
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                           QVBoxLayout, QStatusBar, QMenuBar, QMenu, QSplitter)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon

from Controller.main_controller import MainController
from View.camera_view import CameraView
from View.settings_view import SettingsView
from View.labware_view import LabwareView
from View.terminal_side_panel import TerminalSidePanel
import traceback

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.controller = MainController()
        self.terminal_panel = None  # Initialize as None
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        
        # Connect controller to views
        self.controller.set_views(self, self.settings_view, self.labware_view, self.camera_view, self.wellplate_view)
        
        # Create terminal panel but don't show it initially
        self.terminal_panel = TerminalSidePanel()
        self.terminal_panel.panel_closed.connect(self.on_terminal_panel_closed)
        
        # Pass terminal panel to controller for universal access
        self.controller.set_status_widget(self.terminal_panel)
        
        # Delay status timer start to allow full initialization
        QTimer.singleShot(2000, self.start_status_timer)  # Start after 2 seconds
    
    def closeEvent(self, event):
        """Handle application close event."""
        try:
            # Shutdown cameras before closing
            self.controller.shutdown_cameras()
            print("Application shutting down - cameras stopped")
        except Exception as e:
            print(f"Error during shutdown: {e}")
        event.accept()
    
    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("Microtissue Manipulator Control")
        self.setMinimumSize(1200, 800)
        
        # Create central widget with splitter layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create horizontal splitter for main content and side panel
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create tab widget (main content)
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.create_tabs()
        
        # Add tab widget to splitter
        self.main_splitter.addWidget(self.tab_widget)
        
        # Set splitter properties
        self.main_splitter.setCollapsible(0, False)  # Main content can't be collapsed
        # Note: Will set collapsible for panel when it's added
        self.main_splitter.setSizes([1000])  # Start with only main content
        
        layout.addWidget(self.main_splitter)
    
    def create_tabs(self):
        """Create the main tabs."""
        # Settings tab
        self.settings_view = SettingsView(self.controller)
        self.tab_widget.addTab(self.settings_view, "Settings")
        
        # Labware Declaration tab
        self.labware_view = LabwareView(self.controller)
        self.tab_widget.addTab(self.labware_view, "Labware Declaration")
        
        # Camera View tab
        self.camera_view = CameraView(self.controller)
        self.tab_widget.addTab(self.camera_view, "Camera View")
        
        # Manual Movement tab
        from View.manual_movement_view import ManualMovementView
        self.manual_movement_view = ManualMovementView(self.controller)
        self.tab_widget.addTab(self.manual_movement_view, "Manual Movement")
        
        # Wellplate Viewer tab
        from View.cuboidpicking_view import CuboidPickingView
        self.wellplate_view = CuboidPickingView(self.controller)
        self.tab_widget.addTab(self.wellplate_view, "Cuboid Picking")
    
    def setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # Options menu
        options_menu = menubar.addMenu("Options")
        
        # Terminal panel toggle action
        self.terminal_action = QAction("Show Terminal Panel", self)
        self.terminal_action.setShortcut("Ctrl+T")
        self.terminal_action.setCheckable(True)
        self.terminal_action.setChecked(False)
        self.terminal_action.triggered.connect(self.toggle_terminal_panel)
        options_menu.addAction(self.terminal_action)
        
        # Refresh cameras action
        refresh_action = QAction("Refresh Cameras", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_cameras)
        options_menu.addAction(refresh_action)
    
    def setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Show ready message
        self.status_bar.showMessage("Ready")
        
        # Setup status update timer (will be started later)
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
    
    def start_status_timer(self):
        """Start the status update timer after initialization is complete."""
        self.status_timer.start(1000)  # Update every 1 second
    
    def update_status(self):
        """Update the status bar with current information."""
        try:
            # Check if we're shutting down
            if not hasattr(self, 'status_timer') or not self.status_timer.isActive():
                return
                
            # Add safety check for controller initialization
            if not hasattr(self, 'controller') or self.controller is None:
                self.status_bar.showMessage("Initializing...")
                return
                
            # Safety check for status bar existence
            if not hasattr(self, 'status_bar') or self.status_bar is None:
                return
                
            # Get system status with error handling
            try:
                robot_status = self.controller.get_robot_status()
                occupied_slots = len(self.controller.get_occupied_slots())
                
                status_text = f"Robot: {'Connected' if robot_status.get('initialized', False) else 'Disconnected'} | "
                status_text += f"Occupied Slots: {occupied_slots} | "
                status_text += f"Lights: {'On' if robot_status.get('lights_on', False) else 'Off'}"
                
                self.status_bar.showMessage(status_text)
            except AttributeError as e:
                # Controller methods might not be ready yet
                self.status_bar.showMessage("Loading components...")
            except Exception as e:
                self.status_bar.showMessage(f"Status update error: {str(e)}")
        except Exception as e:
            # Catch-all for any unexpected errors - but don't try to update status bar if it might be gone
            try:
                if hasattr(self, 'status_bar') and self.status_bar is not None:
                    self.status_bar.showMessage(f"System error: {str(e)}")
            except:
                # If even that fails, just print to console
                print(f"Status update error during shutdown: {str(e)}")
    
    def refresh_cameras(self):
        """Refresh the camera list."""
        self.camera_view.refresh_cameras()
        self.status_bar.showMessage("Cameras refreshed")
    
    def toggle_terminal_panel(self):
        """Toggle the visibility of the terminal panel."""
        if self.terminal_panel is None:
            return
            
        if self.terminal_action.isChecked():
            # Show terminal panel
            self.show_terminal_panel()
        else:
            # Hide terminal panel
            self.hide_terminal_panel()
    
    def show_terminal_panel(self):
        """Show the terminal panel in the splitter."""
        if self.terminal_panel is None:
            return
            
        # Add terminal panel to splitter if not already there
        if self.main_splitter.count() == 1:
            self.main_splitter.addWidget(self.terminal_panel)
            # Set collapsible property now that we have 2 widgets
            self.main_splitter.setCollapsible(1, True)  # Side panel can be collapsed
        
        # Show the panel and resize splitter
        self.terminal_panel.show()
        self.main_splitter.setSizes([800, 300])  # Give terminal panel some space
        
        # Update menu action
        self.terminal_action.setChecked(True)
        self.terminal_action.setText("Hide Terminal Panel")
        
        self.status_bar.showMessage("Terminal panel shown")
    
    def hide_terminal_panel(self):
        """Hide the terminal panel."""
        if self.terminal_panel is None:
            return
            
        # Hide the panel and resize splitter
        self.terminal_panel.hide()
        
        # Only set sizes if panel is actually in the splitter
        if self.main_splitter.count() == 2:
            self.main_splitter.setSizes([1000, 0])  # Hide terminal panel
        
        # Update menu action
        self.terminal_action.setChecked(False)
        self.terminal_action.setText("Show Terminal Panel")
        
        self.status_bar.showMessage("Terminal panel hidden")
    
    def on_terminal_panel_closed(self):
        """Handle terminal panel being closed via its close button."""
        self.hide_terminal_panel()
    
    def closeEvent(self, event):
        """Handle application close event."""
        try:
            # Stop the status timer first to prevent further updates
            if hasattr(self, 'status_timer'):
                self.status_timer.stop()
                self.status_timer.timeout.disconnect()
            
            # Cleanup view components that might have timers
            try:
                if hasattr(self, 'camera_view') and self.camera_view is not None:
                    self.camera_view.closeEvent(event)
            except Exception as e:
                print(f"Error cleaning up camera view: {e}")
                
            try:
                if hasattr(self, 'settings_view') and self.settings_view is not None:
                    self.settings_view.closeEvent(event)
            except Exception as e:
                print(f"Error cleaning up settings view: {e}")
            
            # Cleanup controller resources
            if hasattr(self, 'controller') and self.controller is not None:
                self.controller.cleanup()
        except Exception as e:
            print(f"Error during application cleanup: {e}")
        finally:
            # Always accept the close event
            event.accept()


def main():
    try:
        """Main application entry point."""
        app = QApplication(sys.argv)

        # Set application properties
        app.setApplicationName("Microtissue Manipulator")
        app.setApplicationVersion("1.0")
        app.setOrganizationName("Lab Automation")
    
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Run the application
        sys.exit(app.exec())
    except Exception as e:
        print(f"Application error: {e}")
        traceback.print_exc()
        
        # Ensure labware config is deleted in case of crash
        try:
            import os
            # No longer need to delete labware_config.json as it's not used
            print("Application crashed - cleanup completed")
        except Exception as config_error:
            print(f"Error deleting config file during crash: {config_error}")
        
        # Re-raise the exception to ensure proper exit
        raise


if __name__ == "__main__":
    main()

"""
Main GUI application for the microtissue manipulator.
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                           QVBoxLayout, QStatusBar, QMenuBar, QMenu)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon

from Controller.main_controller import MainController
from View.camera_view import CameraView
from View.settings_view import SettingsView
from View.labware_view import LabwareView
from View.status_widget import StatusWidget
import traceback

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.controller = MainController()
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        
        # Connect controller to views
        self.controller.set_views(self, self.settings_view, self.labware_view, self.camera_view)
        
        # Pass status widget to controller for universal access
        self.controller.set_status_widget(self.status_widget)
        
        # Delay status timer start to allow full initialization
        QTimer.singleShot(2000, self.start_status_timer)  # Start after 2 seconds
    
    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("Microtissue Manipulator Control")
        self.setMinimumSize(1200, 800)
        
        # Create central widget with tab widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Add universal status widget at the top
        self.status_widget = StatusWidget()
        layout.addWidget(self.status_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.create_tabs()
        
        layout.addWidget(self.tab_widget)
    
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
    
    def setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # New action
        new_action = QAction("New Configuration", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_configuration)
        file_menu.addAction(new_action)
        
        # Open action
        open_action = QAction("Open Configuration", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_configuration)
        file_menu.addAction(open_action)
        
        # Save action
        save_action = QAction("Save Configuration", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        # Refresh cameras action
        refresh_action = QAction("Refresh Cameras", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_cameras)
        view_menu.addAction(refresh_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # User Guide action
        guide_action = QAction("User Guide", self)
        guide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(guide_action)
    
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
    
    def new_configuration(self):
        """Create a new configuration."""
        # Clear deck
        self.controller.clear_deck()
        
        # Reset settings to defaults
        self.status_bar.showMessage("New configuration created")
    
    def open_configuration(self):
        """Open a configuration file."""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Configuration", "", "JSON Files (*.json)"
        )
        
        if filename:
            success = self.controller.import_deck_layout(filename)
            if success:
                self.status_bar.showMessage(f"Configuration loaded from {filename}")
            else:
                self.status_bar.showMessage("Failed to load configuration file.")
    
    def save_configuration(self):
        """Save the current configuration."""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "", "JSON Files (*.json)"
        )
        
        if filename:
            success = self.controller.export_deck_layout(filename)
            if success:
                self.status_bar.showMessage(f"Configuration saved to {filename}")
            else:
                self.status_bar.showMessage("Failed to save configuration file.")
    
    def refresh_cameras(self):
        """Refresh the camera list."""
        self.camera_view.refresh_cameras()
        self.status_bar.showMessage("Cameras refreshed")
    
    def show_about(self):
        """Show the about dialog."""
        # Removed modal dialog - info available in documentation
        self.status_bar.showMessage("Microtissue Manipulator Control v1.0")
    
    def show_user_guide(self):
        """Show the user guide."""
        # Removed modal dialog - info available in documentation
        self.status_bar.showMessage("User guide available in documentation")
    
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
            config_file = "labware_config.json"
            if os.path.exists(config_file):
                os.remove(config_file)
                print(f"Application crashed - deleted {config_file}")
        except Exception as config_error:
            print(f"Error deleting config file during crash: {config_error}")
        
        # Re-raise the exception to ensure proper exit
        raise


if __name__ == "__main__":
    main()

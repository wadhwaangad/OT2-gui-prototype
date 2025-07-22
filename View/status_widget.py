"""
Universal status widget for displaying terminal output and progress.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QProgressBar, 
                           QGroupBox, QPushButton, QHBoxLayout, QSizePolicy)
from PyQt6.QtCore import QTimer, pyqtSignal
from Model.redirector import StreamRedirector


class StatusWidget(QWidget):
    """Universal status widget for terminal output display."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded = False  # Start collapsed
        self.setup_ui()
        
        # Initialize output redirector with error handling
        try:
            self.output_redirector = StreamRedirector(self.status_text)
        except RuntimeError as e:
            print(f"StreamRedirector already active: {e}")
            self.output_redirector = None
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        
        # Create header with toggle button
        header_layout = QHBoxLayout()
        
        # Toggle button for expand/collapse
        self.toggle_button = QPushButton("▼ Terminal Output")
        self.toggle_button.setMaximumHeight(30)
        self.toggle_button.clicked.connect(self.toggle_visibility)
        header_layout.addWidget(self.toggle_button)
        
        layout.addLayout(header_layout)
        
        # Create status group
        self.group = QGroupBox()
        self.group.setVisible(self.expanded)  # Start collapsed
        group_layout = QVBoxLayout()
        
        # Status display
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)  # Increased from 60
        self.status_text.setMinimumHeight(80)   
        self.status_text.setReadOnly(True)
        group_layout.addWidget(self.status_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        group_layout.addWidget(self.progress_bar)
        
        self.group.setLayout(group_layout)
        layout.addWidget(self.group)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        
        # Update initial height
        self.update_height()
    
    def toggle_visibility(self):
        """Toggle the visibility of the status content."""
        self.expanded = not self.expanded
        self.group.setVisible(self.expanded)
        
        # Update button text
        if self.expanded:
            self.toggle_button.setText("▲ Terminal Output")
        else:
            self.toggle_button.setText("▼ Terminal Output")
        
        # Update widget height
        self.update_height()
    
    def update_height(self):
        """Update widget height based on expanded state."""
        if self.expanded:
            self.setMaximumHeight(150)  # Expanded height
            self.setMinimumHeight(120)
        else:
            self.setMaximumHeight(40)   # Collapsed height (just header)
            self.setMinimumHeight(40)
    
    def show_progress(self, message: str = "Processing..."):
        """Show progress bar with message."""
        # Auto-expand when showing progress
        if not self.expanded:
            self.toggle_visibility()
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_text.append(f"\\n{message}")
    
    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setVisible(False)
    
    def show_result(self, success: bool, message: str):
        """Show operation result."""
        # Auto-expand when showing result
        if not self.expanded:
            self.toggle_visibility()
            
        self.hide_progress()
        if success:
            self.status_text.append(f"✓ {message}")
        else:
            self.status_text.append(f"✗ {message}")
    
    def append_message(self, message: str):
        """Append a message to the status display."""
        # Auto-expand when showing message
        if not self.expanded:
            self.toggle_visibility()
            
        self.status_text.append(message)
    
    def clear(self):
        """Clear the status display."""
        self.status_text.clear()

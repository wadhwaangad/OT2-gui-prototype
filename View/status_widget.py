"""
Universal status widget for displaying terminal output and progress.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QProgressBar, QGroupBox
from PyQt6.QtCore import QTimer
from Model.redirector import StreamRedirector


class StatusWidget(QWidget):
    """Universal status widget for terminal output display."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
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
        
        # Create status group
        group = QGroupBox("Terminal Output")
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
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
    
    def show_progress(self, message: str = "Processing..."):
        """Show progress bar with message."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_text.append(f"\\n{message}")
    
    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setVisible(False)
    
    def show_result(self, success: bool, message: str):
        """Show operation result."""
        self.hide_progress()
        if success:
            self.status_text.append(f"✓ {message}")
        else:
            self.status_text.append(f"✗ {message}")
    
    def append_message(self, message: str):
        """Append a message to the status display."""
        self.status_text.append(message)
    
    def clear(self):
        """Clear the status display."""
        self.status_text.clear()

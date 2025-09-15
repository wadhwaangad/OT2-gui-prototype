"""
Terminal side panel widget for displaying terminal output and progress.
This panel can be collapsed/expanded and docked to the side of the main window.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QProgressBar, 
                           QGroupBox, QPushButton, QHBoxLayout, QLabel, QFrame)
from PyQt6.QtCore import QTimer, pyqtSignal, Qt, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QIcon
from Model.redirector import StreamRedirector


class TerminalSidePanel(QWidget):
    """Collapsible side panel for terminal output display."""
    
    # Signal emitted when panel is closed
    panel_closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded = True  # Start expanded when shown
        self.setup_ui()
        
        # Initialize output redirector with error handling
        try:
            self.output_redirector = StreamRedirector(self.status_text)
        except RuntimeError as e:
            print(f"StreamRedirector already active: {e}")
            self.output_redirector = None
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Terminal Output")
        self.setMinimumWidth(300)
        self.setMaximumWidth(600)
        self.setMinimumHeight(200)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with title and controls
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_frame.setMaximumHeight(40)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        # Title label
        title_label = QLabel("Terminal Output")
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Collapse/expand button
        self.toggle_button = QPushButton("−")
        self.toggle_button.setMaximumSize(25, 25)
        self.toggle_button.setToolTip("Collapse/Expand")
        self.toggle_button.clicked.connect(self.toggle_visibility)
        header_layout.addWidget(self.toggle_button)
        
        # Close button
        self.close_button = QPushButton("×")
        self.close_button.setMaximumSize(25, 25)
        self.close_button.setToolTip("Close Panel")
        self.close_button.clicked.connect(self.close_panel)
        header_layout.addWidget(self.close_button)
        
        layout.addWidget(header_frame)
        
        # Content area
        self.content_frame = QFrame()
        self.content_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        # Status display
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setFont(QFont("Consolas", 9))
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        content_layout.addWidget(self.status_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                text-align: center;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        content_layout.addWidget(self.progress_bar)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.setMaximumWidth(80)
        self.clear_button.clicked.connect(self.clear)
        controls_layout.addWidget(self.clear_button)
        
        controls_layout.addStretch()
        
        content_layout.addLayout(controls_layout)
        
        layout.addWidget(self.content_frame)
        
        self.setLayout(layout)
        
        # Apply dark theme styling
        self.apply_dark_theme()
    
    def apply_dark_theme(self):
        """Apply dark theme styling to the panel."""
        self.setStyleSheet("""
            TerminalSidePanel {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
            }
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
            }
            QLabel {
                color: #d4d4d4;
                background: transparent;
                border: none;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #5e5e5e;
                border-radius: 4px;
                padding: 4px 8px;
                color: #d4d4d4;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #505050;
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background-color: #0078d4;
            }
        """)
    
    def toggle_visibility(self):
        """Toggle the visibility of the content area."""
        self.expanded = not self.expanded
        self.content_frame.setVisible(self.expanded)
        
        # Update button text
        if self.expanded:
            self.toggle_button.setText("−")
            self.toggle_button.setToolTip("Collapse")
        else:
            self.toggle_button.setText("+")
            self.toggle_button.setToolTip("Expand")
        
        # Update panel size
        if not self.expanded:
            # Collapsed: only show header
            self.setMinimumHeight(50)
            self.setMaximumHeight(50)
        else:
            # Expanded: allow full size
            self.setMinimumHeight(200)
            self.setMaximumHeight(16777215)  # Remove max height limit
    
    def close_panel(self):
        """Close the panel and emit signal."""
        self.panel_closed.emit()
        self.hide()
    
    def show_progress(self, message: str = "Processing..."):
        """Show progress bar with message."""
        # Auto-expand when showing progress
        if not self.expanded:
            self.toggle_visibility()
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_text.append(f"\n{message}")
        
        # Scroll to bottom
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
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
        
        # Scroll to bottom
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def append_message(self, message: str):
        """Append a message to the status display."""
        # Auto-expand when showing message
        if not self.expanded:
            self.toggle_visibility()
            
        self.status_text.append(message)
        
        # Scroll to bottom
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def clear(self):
        """Clear the status display."""
        self.status_text.clear()
    
    def closeEvent(self, event):
        """Handle close event."""
        self.panel_closed.emit()
        super().closeEvent(event)
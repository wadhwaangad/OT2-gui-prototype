#!/usr/bin/env python3
"""
Quick test script to verify drag selection functionality in wellplate_view.py
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

# Add the project directory to Python path
sys.path.insert(0, '.')

from View.wellplate_view import WellplateGridWidget

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drag Selection Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Create a test wellplate grid
        self.grid = WellplateGridWidget("Test 96-well Plate", 96)
        self.grid.wells_clicked.connect(self.on_wells_selected)
        layout.addWidget(self.grid)
        
    def on_wells_selected(self, wellplate_name, selected_wells):
        """Handle well selection changes."""
        print(f"Selected wells in {wellplate_name}: {selected_wells}")

def main():
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    print("Test Instructions:")
    print("1. Click individual wells to select/deselect them")
    print("2. Click and drag to select rectangular areas")
    print("3. Click row/column labels to select entire rows/columns")
    print("4. Use 'Select All' and 'Clear' buttons")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

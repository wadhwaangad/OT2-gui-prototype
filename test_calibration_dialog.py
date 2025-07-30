"""
Simple test for the calibration profile dialog.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from View.calibration_profile_dialog import CalibrationProfileDialog

def test_dialog():
    """Test the calibration profile dialog."""
    app = QApplication(sys.argv)
    
    dialog = CalibrationProfileDialog()
    result = dialog.exec()
    
    if result == dialog.DialogCode.Accepted:
        selected_profile = dialog.get_selected_profile()
        print(f"Selected profile: {selected_profile}")
    else:
        print("Dialog cancelled")
    
    app.quit()

if __name__ == "__main__":
    test_dialog()

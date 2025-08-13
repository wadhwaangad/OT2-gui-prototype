"""
Frame capture utility for the microtissue manipulator GUI.
Provides a centralized way to capture frames from cameras using the new thread-safe system.
"""

from typing import Optional
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QEventLoop, QTimer


class FrameCapturer(QObject):
    """Helper class to capture a single frame from cameras using the new CameraViewer system."""
    
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.captured_frame = None
        self.event_loop = None
        
    def set_controller(self, controller):
        """Set the controller to use for creating camera viewers."""
        self.controller = controller
        
    def capture_frame(self, camera_name: str, timeout_ms: int = 5000) -> Optional[np.ndarray]:
        """
        Capture a single frame from the specified camera.
        
        Args:
            camera_name: Name of the camera to capture from
            timeout_ms: Timeout in milliseconds
            
        Returns:
            numpy array of the frame or None if failed
        """
        if not self.controller:
            print("Controller not available")
            return None
        
        # Create a temporary camera viewer
        camera_viewer = self.controller.create_camera_viewer(camera_name)
        
        # Try to get current frame first (faster)
        ret, frame = camera_viewer.get_current_frame()
        if ret and frame is not None:
            return frame.copy()
        
        # If no current frame, wait for new frame
        self.captured_frame = None
        
        # Connect to frame signal
        camera_viewer.frame_received.connect(self._on_frame_received)
        
        # Connect to camera stream
        if not camera_viewer.connect_to_stream():
            print(f"Failed to connect to camera stream: {camera_name}")
            return None
        
        # Create event loop for waiting
        self.event_loop = QEventLoop()
        
        # Set up timeout
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self.event_loop.quit)
        timer.start(timeout_ms)
        
        # Wait for frame or timeout
        self.event_loop.exec()
        
        # Cleanup
        camera_viewer.disconnect_from_stream()
        timer.stop()
        
        return self.captured_frame
        
    def _on_frame_received(self, frame: np.ndarray):
        """Handle incoming frame."""
        if self.captured_frame is None:
            self.captured_frame = frame.copy()
            if self.event_loop:
                self.event_loop.quit()


# Global frame capturer instance that can be used across modules
frame_capturer = None

def get_frame_capturer(controller=None) -> FrameCapturer:
    """Get or create the global frame capturer instance."""
    global frame_capturer
    if frame_capturer is None:
        frame_capturer = FrameCapturer(controller)
    elif controller is not None:
        frame_capturer.set_controller(controller)
    return frame_capturer

def capture_frame_from_camera(camera_name: str, controller=None, timeout_ms: int = 5000) -> Optional[np.ndarray]:
    """
    Convenience function to capture a frame from a specific camera.
    
    Args:
        camera_name: Name of the camera to capture from
        controller: Controller instance to use
        timeout_ms: Timeout in milliseconds
        
    Returns:
        numpy array of the frame or None if failed
    """
    capturer = get_frame_capturer(controller)
    return capturer.capture_frame(camera_name, timeout_ms)

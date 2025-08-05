"""
Frame capture utility for the microtissue manipulator GUI.
Provides a centralized way to capture frames from the frame emitter.
"""

from typing import Optional
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QEventLoop, QTimer


class FrameCapturer(QObject):
    """Helper class to capture a single frame from the frame emitter."""
    
    def __init__(self, frame_emitter=None):
        super().__init__()
        self.captured_frame = None
        self.target_camera = None
        self.event_loop = None
        self.frame_emitter = frame_emitter
        
    def set_frame_emitter(self, frame_emitter):
        """Set the frame emitter to use for capturing frames."""
        self.frame_emitter = frame_emitter
        
    def capture_frame(self, camera_name: str, timeout_ms: int = 5000) -> Optional[np.ndarray]:
        """
        Capture a single frame from the specified camera.
        
        Args:
            camera_name: Name of the camera to capture from
            timeout_ms: Timeout in milliseconds
            
        Returns:
            numpy array of the frame or None if failed
        """
        if not self.frame_emitter:
            print("Frame emitter not available")
            return None
            
        self.captured_frame = None
        self.target_camera = camera_name
        
        # Connect to frame signal
        self.frame_emitter.frame_ready.connect(self._on_frame_received)
        
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
        self.frame_emitter.frame_ready.disconnect(self._on_frame_received)
        timer.stop()
        
        return self.captured_frame
        
    def _on_frame_received(self, camera_name: str, frame: np.ndarray):
        """Handle incoming frame from emitter."""
        if camera_name == self.target_camera and self.captured_frame is None:
            self.captured_frame = frame.copy()
            if self.event_loop:
                self.event_loop.quit()


# Global frame capturer instance that can be used across modules
frame_capturer = None

def get_frame_capturer(frame_emitter=None) -> FrameCapturer:
    """Get or create the global frame capturer instance."""
    global frame_capturer
    if frame_capturer is None:
        frame_capturer = FrameCapturer(frame_emitter)
    elif frame_emitter is not None:
        frame_capturer.set_frame_emitter(frame_emitter)
    return frame_capturer

def capture_frame_from_camera(camera_name: str, frame_emitter=None, timeout_ms: int = 5000) -> Optional[np.ndarray]:
    """
    Convenience function to capture a frame from a specific camera.
    
    Args:
        camera_name: Name of the camera to capture from
        frame_emitter: Frame emitter instance to use
        timeout_ms: Timeout in milliseconds
        
    Returns:
        numpy array of the frame or None if failed
    """
    capturer = get_frame_capturer(frame_emitter)
    return capturer.capture_frame(camera_name, timeout_ms)

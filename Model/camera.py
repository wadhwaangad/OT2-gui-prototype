import cv2
import threading
import numpy as np
import time
from typing import Optional, Tuple, Union, List
from pygrabber.dshow_graph import FilterGraph
import paths
import json
import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker
from queue import Queue, Empty
import queue

CAMERA_LABELS_FILE = paths.CAM_CONFIGS_DIR + "/camera_labels.json"
CAMERA_CONFIG_DIR = paths.CAM_CONFIGS_DIR

class CameraManagerWindows:

    def __init__(self):
        self.graph = FilterGraph()
        self.refresh_devices()
        os.makedirs(CAMERA_CONFIG_DIR, exist_ok=True)
        self.label_map = self.load_labels()
    
    def refresh_devices(self):
        """Refresh the list of available devices and their indices."""
        try:
            # Recreate the graph to get fresh device list
            self.graph = FilterGraph()
            self.devices = self.graph.get_input_devices()
            self.device_to_index = {name: idx for idx, name in enumerate(self.devices)}
            print(f"Refreshed camera devices: {len(self.devices)} found")
            for i, device in enumerate(self.devices):
                print(f"  {i}: {device}")
        except Exception as e:
            print(f"Error refreshing camera devices: {e}")
            # Fallback to empty lists if refresh fails
            self.devices = []
            self.device_to_index = {}

    def load_labels(self):
        if os.path.exists(CAMERA_LABELS_FILE):
            with open(CAMERA_LABELS_FILE, "r") as f:
                return json.load(f)
        else:
            with open(CAMERA_LABELS_FILE, "w") as f:
                json.dump({}, f, indent=4)
            return {}

    def save_labels(self):
        with open(CAMERA_LABELS_FILE, "w") as f:
            json.dump(self.label_map, f, indent=4)

    def assign_label(self, device_name, label):
        if device_name not in self.devices:
            raise ValueError(f"Device '{device_name}' not found.")
        self.label_map[label] = device_name
        self.save_labels()
        self.load_resolution_config(label)

    def list_devices(self):
        return self.devices

    def list_labels(self):
        return self.label_map

    def get_camera_index_by_label(self, label):
        device_name = self.label_map.get(label)
        if device_name is None:
            raise ValueError(f"Label '{label}' not found.")
        index = self.device_to_index.get(device_name)
        if index is None:
            # Try refreshing devices in case the device was reconnected
            print(f"Device '{device_name}' not found in current list, refreshing...")
            self.refresh_devices()
            index = self.device_to_index.get(device_name)
            if index is None:
                raise RuntimeError(f"Device '{device_name}' is not connected.")
        return index

    def get_config_path(self, label):
        return os.path.join(CAMERA_CONFIG_DIR, f"{label}.json")

    def load_resolution_config(self, label):
        config_path = self.get_config_path(label)
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
        else:
            empty = {"resolutions": [], "default_resolution": None}
            with open(config_path, "w") as f:
                json.dump(empty, f, indent=4)
            return empty

    def save_resolution_config(self, label, resolutions):
        config_path = self.get_config_path(label)
        with open(config_path, "w") as f:
            json.dump({"resolutions": resolutions}, f, indent=4)

    def get_available_cameras(self) -> List[Tuple[str, int]]:
        """Get list of available cameras with their names and indices"""
        # Refresh device list before returning to ensure indices are current
        self.refresh_devices()
        
        cameras = []
        for device_name in self.devices:
            index = self.device_to_index.get(device_name)
            if index is not None:
                cameras.append((device_name, index))
        return cameras

class ThreadSafeVideoCapture(QObject):
    """
    A thread-safe video capture class that uses Qt threads and signals.
    Captures frames in a separate thread and emits them via Qt signals.
    """
    frame_ready = pyqtSignal(np.ndarray)  # Emitted when a new frame is available
    error_occurred = pyqtSignal(str)  # Emitted when an error occurs
    
    def __init__(self, camera_id: Union[int, str], width: int = 640, height: int = 480, fps: int = 30, focus: int = None):
        """
        Initialize the ThreadSafeVideoCapture.
        
        Args:
            camera_id: Camera index or path to video file
            width: Frame width
            height: Frame height
            fps: Desired frames per second
            focus: Focus value for camera
        """
        super().__init__()
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.focus = focus
        
        # Thread safety
        self.mutex = QMutex()
        self.capture_thread = None
        self.worker = None
        self.is_running = False
        
        # Current frame storage
        self.current_frame = None
        self.frame_available = False
        
    def start_capture(self) -> bool:
        """Start the capture in a separate thread."""
        if self.is_running:
            return True
            
        try:
            self.capture_thread = QThread()
            self.worker = CaptureWorker(self.camera_id, self.width, self.height, self.fps, self.focus)
            self.worker.moveToThread(self.capture_thread)
            
            # Connect signals
            self.worker.frame_captured.connect(self._on_frame_captured)
            self.worker.error_occurred.connect(self.error_occurred)
            self.capture_thread.started.connect(self.worker.start_capture)
            self.worker.finished.connect(self.capture_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.capture_thread.finished.connect(self.capture_thread.deleteLater)
            
            self.capture_thread.start()
            self.is_running = True
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to start capture: {str(e)}")
            return False
    
    def stop_capture(self):
        """Stop the capture thread."""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Signal worker to stop first
        if self.worker:
            self.worker.stop()
        
        # Wait for thread to finish gracefully
        if self.capture_thread and self.capture_thread.isRunning():
            # First try to quit gracefully
            self.capture_thread.quit()
            
            # Wait longer for graceful shutdown
            if not self.capture_thread.wait(8000):  # Wait up to 8 seconds
                print(f"Warning: Thread did not finish gracefully for camera {self.camera_id}, forcing termination")
                self.capture_thread.terminate()
                # Wait for termination to complete
                if not self.capture_thread.wait(3000):
                    print(f"Error: Thread termination failed for camera {self.camera_id}")
        
        # Disconnect all signals to prevent issues during cleanup
        try:
            if self.worker:
                self.worker.frame_captured.disconnect()
                self.worker.error_occurred.disconnect()
                self.worker.finished.disconnect()
        except:
            pass  # Ignore disconnect errors
        
        try:
            if self.capture_thread:
                self.capture_thread.started.disconnect()
                self.capture_thread.finished.disconnect()
        except:
            pass  # Ignore disconnect errors
        
        # Clean up references
        self.worker = None
        self.capture_thread = None
    
    def __del__(self):
        """Destructor to ensure proper cleanup."""
        try:
            self.stop_capture()
        except:
            pass  # Ignore errors during destruction
    
    def _on_frame_captured(self, frame: np.ndarray):
        """Handle frame captured from worker thread."""
        with QMutexLocker(self.mutex):
            self.current_frame = frame.copy()
            self.frame_available = True
        self.frame_ready.emit(frame)
    
    def get_current_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Get the most recent frame (thread-safe)."""
        with QMutexLocker(self.mutex):
            if self.frame_available and self.current_frame is not None:
                return True, self.current_frame.copy()
            return False, None
    
    def set_focus(self, focus_value: int):
        """Set the focus value for the camera (thread-safe)."""
        if self.worker:
            self.worker.set_focus(focus_value)
    
    def is_opened(self) -> bool:
        """Check if the capture is running."""
        return self.is_running and self.worker and self.worker.is_capturing
    
    def release(self):
        """Release the video capture resources."""
        self.stop_capture()


class CaptureWorker(QObject):
    """Worker class that runs in a separate thread to capture video frames."""
    frame_captured = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, camera_id: Union[int, str], width: int, height: int, fps: int, focus: int):
        super().__init__()
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.focus = focus
        
        self.cap = None
        self.is_capturing = False
        self.should_stop = False
        self.focus_mutex = QMutex()
        self.new_focus_value = None
        
    def start_capture(self):
        """Start capturing frames."""
        try:
            print(f"Attempting to open camera at index {self.camera_id}")
            self.cap = cv2.VideoCapture(self.camera_id)
            
            # Check if camera opened successfully
            if not self.cap.isOpened():
                error_msg = f"Could not open camera {self.camera_id} - camera may be in use or index is invalid"
                print(error_msg)
                self.error_occurred.emit(error_msg)
                self.finished.emit()
                return
            
            # Test if we can actually read from the camera
            test_ret, test_frame = self.cap.read()
            if not test_ret:
                error_msg = f"Camera {self.camera_id} opened but cannot read frames - camera may be in use"
                print(error_msg)
                self.cap.release()
                self.error_occurred.emit(error_msg)
                self.finished.emit()
                return
                
            # Set properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            if self.focus is not None:
                self.cap.set(cv2.CAP_PROP_FOCUS, self.focus)
            
            print(f"Successfully opened camera {self.camera_id}, resolution: {self.width}x{self.height}")
            self.is_capturing = True
            frame_time = 1.0 / self.fps
            
            while not self.should_stop:
                start_time = time.time()
                
                # Check for focus changes
                with QMutexLocker(self.focus_mutex):
                    if self.new_focus_value is not None:
                        self.cap.set(cv2.CAP_PROP_FOCUS, self.new_focus_value)
                        self.new_focus_value = None
                
                # Check should_stop before potentially blocking read operation
                if self.should_stop:
                    break
                    
                ret, frame = self.cap.read()
                if not ret:
                    if not self.should_stop:  # Only emit error if we're not stopping intentionally
                        self.error_occurred.emit("Failed to grab frame from camera")
                    break
                
                # Check should_stop again after read
                if self.should_stop:
                    break
                
                # Ensure frame size matches expected dimensions
                if frame.shape[:2] != (self.height, self.width):
                    frame = cv2.resize(frame, (self.width, self.height))
                
                self.frame_captured.emit(frame)
                
                # Sleep to maintain desired fps, but check for stop signal during sleep
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_time - elapsed)
                if sleep_time > 0:
                    # Sleep in smaller chunks to be more responsive to stop signals
                    sleep_chunks = max(1, int(sleep_time * 10))  # 10 checks per sleep period
                    chunk_time = sleep_time / sleep_chunks
                    for _ in range(sleep_chunks):
                        if self.should_stop:
                            break
                        time.sleep(chunk_time)
                    
        except Exception as e:
            error_msg = f"Exception in capture for camera {self.camera_id}: {str(e)}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
        finally:
            self.is_capturing = False
            if self.cap:
                self.cap.release()
            print(f"Camera {self.camera_id} capture stopped")
            self.finished.emit()
    
    def set_focus(self, focus_value: int):
        """Set focus value (thread-safe)."""
        with QMutexLocker(self.focus_mutex):
            self.new_focus_value = focus_value
    
    def stop(self):
        """Stop the capture."""
        self.should_stop = True

def open_capture(label: str, cam_manager: CameraManagerWindows, resolution: Union[list[int, int], str] = 'default', focus: int = None) -> ThreadSafeVideoCapture:
    index = cam_manager.get_camera_index_by_label(label)
    if resolution == 'default':
        resolution = cam_manager.load_resolution_config(label)['default_resolution']
    elif isinstance(resolution, list) and len(resolution) == 2:
        config = cam_manager.load_resolution_config(label)
        if resolution not in config['resolutions']:
            print(f"Warning: Resolution {resolution} not found in saved configurations for camera '{label}'. Using default resolution.")
            resolution = cam_manager.load_resolution_config(label)['default_resolution']
    return ThreadSafeVideoCapture(index, width=resolution[0], height=resolution[1], focus=focus)

class frameOperations():
    def __init__(self, width, height):
        self.camera_matrix = None
        self.distortion_coefficients = None
        self.new_camera_matrix = None
        self.w = width
        self.h = height

    def load_camera_intrinsics(self, config_profile: str, use_new_cam_mtx: bool = True) -> None:
        """
        Load camera intrinsics from a JSON configuration file.
        
        Args:
            config_profile: The name of the profile to load the camera intrinsics from.
            use_new_cam_mtx: Whether to compute a new camera matrix using cv2.getOptimalNewCameraMatrix.
        """
        config_path = os.path.join(paths.PROFILES_DIR, config_profile, 'camera_intrinsics.json')
        with open(config_path, 'r') as f:
            camera_data = json.load(f)

        if not camera_data:
            raise ValueError(f"No camera intrinsics found in {config_path}. Please calibrate the camera first.")
            return
        
        self.camera_matrix = np.array(camera_data['camera_mtx'])
        self.distortion_coefficients = np.array(camera_data['dist_coeffs'])
        
        if use_new_cam_mtx:
            self.new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(self.camera_matrix, self.distortion_coefficients, (self.w, self.h), 1, (self.w, self.h))
        else:
            self.new_camera_matrix = None

    def undistort_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Undistort a frame using the loaded camera intrinsics.
        
        Args:
            frame: The input frame to undistort.
        
        Returns:
            The undistorted frame.
        """
        if self.camera_matrix is None or self.distortion_coefficients is None:
            raise ValueError("Camera intrinsics not loaded. Please load camera intrinsics before undistorting frames.")
        
        if self.new_camera_matrix is not None:
            return cv2.undistort(frame, self.camera_matrix, self.distortion_coefficients, newCameraMatrix=self.new_camera_matrix)
        else:
            return cv2.undistort(frame, self.camera_matrix, self.distortion_coefficients)


class CameraFrameEmitter(QObject):
    """
    Manages camera frames and emits them via PyQt signals.
    This class is thread-safe and manages multiple cameras efficiently.
    Supports multiple simultaneous viewers for each camera.
    """
    frame_ready = pyqtSignal(str, np.ndarray)  # camera_name, frame
    
    def __init__(self):
        super().__init__()
        self.active_cameras = {}
        self.mutex = QMutex()
        # Keep track of individual camera connections for multi-viewer support
        self.camera_connections = {}
        # Track number of viewers per camera
        self.camera_viewer_counts = {}
        
    def add_camera(self, camera_name: str, capture: ThreadSafeVideoCapture):
        """Add a camera to the frame emitter (thread-safe)."""
        with QMutexLocker(self.mutex):
            if camera_name in self.active_cameras:
                # Camera already exists, just return (don't replace)
                return
            
            self.active_cameras[camera_name] = capture
            self.camera_viewer_counts[camera_name] = 0
            # Connect the camera's frame_ready signal to our emission
            # Use a lambda to capture the camera name for this specific connection
            connection = capture.frame_ready.connect(lambda frame, name=camera_name: self.frame_ready.emit(name, frame))
            self.camera_connections[camera_name] = connection
    
    def remove_camera(self, camera_name: str):
        """Remove a camera from the frame emitter (thread-safe)."""
        with QMutexLocker(self.mutex):
            self._remove_camera_internal(camera_name)
    
    def _remove_camera_internal(self, camera_name: str):
        """Internal method to remove camera (not thread-safe, caller must hold mutex)."""
        if camera_name in self.active_cameras:
            capture = self.active_cameras[camera_name]
            
            # Stop the capture first
            try:
                capture.stop_capture()
            except:
                pass  # Ignore errors during cleanup
            
            # Disconnect signals
            try:
                capture.frame_ready.disconnect()
            except:
                pass  # Signal might not be connected
            
            # Clean up connection tracking
            if camera_name in self.camera_connections:
                del self.camera_connections[camera_name]
            
            # Clean up viewer count tracking
            if camera_name in self.camera_viewer_counts:
                del self.camera_viewer_counts[camera_name]
            
            del self.active_cameras[camera_name]
    
    def connect_to_camera(self, camera_name: str, slot):
        """Connect a specific slot to a camera's frame signal (for multiple viewers)."""
        with QMutexLocker(self.mutex):
            if camera_name in self.active_cameras:
                capture = self.active_cameras[camera_name]
                connection = capture.frame_ready.connect(slot)
                if connection is not None:
                    # Increment viewer count
                    self.camera_viewer_counts[camera_name] = self.camera_viewer_counts.get(camera_name, 0) + 1
                return connection
            return None
    
    def disconnect_from_camera(self, camera_name: str, slot):
        """Disconnect a specific slot from a camera's frame signal."""
        with QMutexLocker(self.mutex):
            if camera_name in self.active_cameras:
                capture = self.active_cameras[camera_name]
                try:
                    capture.frame_ready.disconnect(slot)
                    # Decrement viewer count
                    self.camera_viewer_counts[camera_name] = max(0, self.camera_viewer_counts.get(camera_name, 0) - 1)
                    
                    # If no more viewers, consider stopping the camera (but don't auto-stop for now)
                    # The controller can check viewer count and decide when to stop
                    return True
                except:
                    pass
            return False
    
    def get_camera_frame(self, camera_name: str) -> Tuple[bool, Optional[np.ndarray]]:
        """Get the current frame from a specific camera (thread-safe)."""
        with QMutexLocker(self.mutex):
            if camera_name in self.active_cameras:
                return self.active_cameras[camera_name].get_current_frame()
            return False, None
    
    def set_camera_focus(self, camera_name: str, focus_value: int) -> bool:
        """Set focus for a specific camera (thread-safe)."""
        with QMutexLocker(self.mutex):
            if camera_name in self.active_cameras:
                self.active_cameras[camera_name].set_focus(focus_value)
                return True
            return False
    
    def is_camera_active(self, camera_name: str) -> bool:
        """Check if a camera is active (thread-safe)."""
        with QMutexLocker(self.mutex):
            return camera_name in self.active_cameras and self.active_cameras[camera_name].is_opened()
    
    def get_active_camera_names(self) -> List[str]:
        """Get list of active camera names (thread-safe)."""
        with QMutexLocker(self.mutex):
            return list(self.active_cameras.keys())
    
    def get_camera_viewer_count(self, camera_name: str) -> int:
        """Get the number of viewers connected to a camera (thread-safe)."""
        with QMutexLocker(self.mutex):
            return self.camera_viewer_counts.get(camera_name, 0)
    
    def stop_all_cameras(self):
        """Stop all cameras (thread-safe)."""
        with QMutexLocker(self.mutex):
            for camera_name in list(self.active_cameras.keys()):
                self._remove_camera_internal(camera_name)
    
    def stop(self):
        """Stop the frame emitter and all cameras."""
        self.stop_all_cameras()
    
    def __del__(self):
        """Destructor to ensure proper cleanup."""
        try:
            self.stop()
        except:
            pass  # Ignore errors during destruction


class CameraViewer(QObject):
    """
    A helper class that makes it easy to connect to and display camera streams.
    Multiple viewers can connect to the same camera stream simultaneously.
    
    Usage example:
        # In your controller or view:
        viewer1 = controller.create_camera_viewer("HD USB CAMERA")
        viewer2 = controller.create_camera_viewer("HD USB CAMERA")
        
        # Connect to your display widgets
        viewer1.frame_received.connect(display_widget1.set_frame)
        viewer2.frame_received.connect(display_widget2.set_frame)
        
        # Start viewing
        viewer1.connect_to_stream()
        viewer2.connect_to_stream()
        
        # Both widgets will now receive the same camera stream simultaneously
    """
    frame_received = pyqtSignal(np.ndarray)  # Emitted when this viewer receives a frame
    
    def __init__(self, camera_name: str, frame_emitter: CameraFrameEmitter):
        super().__init__()
        self.camera_name = camera_name
        self.frame_emitter = frame_emitter
        self.is_connected = False
        
    def connect_to_stream(self) -> bool:
        """Connect this viewer to the camera stream."""
        if self.is_connected:
            return True
            
        connection = self.frame_emitter.connect_to_camera(self.camera_name, self._on_frame_received)
        if connection is not None:
            self.is_connected = True
            return True
        return False
    
    def disconnect_from_stream(self):
        """Disconnect this viewer from the camera stream."""
        if self.is_connected:
            self.frame_emitter.disconnect_from_camera(self.camera_name, self._on_frame_received)
            self.is_connected = False
    
    def _on_frame_received(self, frame: np.ndarray):
        """Internal method to handle incoming frames and re-emit for this viewer."""
        self.frame_received.emit(frame)
    
    def get_current_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Get the current frame from the camera."""
        return self.frame_emitter.get_camera_frame(self.camera_name)
    
    def is_camera_active(self) -> bool:
        """Check if the camera is active."""
        return self.frame_emitter.is_camera_active(self.camera_name)

from PyQt6.QtCore import QObject, pyqtSignal
import numpy as np
import cv2

class CameraWorker(QObject):
    frame_ready = pyqtSignal(np.ndarray)
    finished = pyqtSignal()

    def __init__(self, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.running = False

    def start_capture(self):
        self.running = True
        cap = cv2.VideoCapture(self.camera_id)
        while self.running:
            ret, frame = cap.read()
            if not ret:
                break
            self.frame_ready.emit(frame)
        cap.release()
        self.finished.emit()

    def stop_capture(self):
        self.running = False

class FrameHub(QObject):
    new_frame = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.latest_frame = None

    def update_frame(self, frame):
        self.latest_frame = frame
        self.new_frame.emit(frame)

    def get_latest_frame(self):
        return self.latest_frame

class FrameHubManager:
    def __init__(self):
        self.hubs = {}  # {camera_name: FrameHub}

    def add_camera(self, camera_name):
        hub = FrameHub(camera_name)
        self.hubs[camera_name] = hub
        return hub

    def remove_camera(self, camera_name):
        if camera_name in self.hubs:
            del self.hubs[camera_name]

    def get_hub(self, camera_name):
        return self.hubs.get(camera_name)

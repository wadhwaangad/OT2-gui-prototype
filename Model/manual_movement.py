import Model.globals as globals
from Model.worker import Worker
from PyQt6.QtCore import QThread


class ManualMovementModel:
    """Placeholder model for manual movement controls."""
    def __init__(self):
        self.active_threads = []

    def run_in_thread(self, fn, *args, on_result=None, on_error=None, on_finished=None, **kwargs):
        """Run a function in a separate thread using Worker."""
        thread = QThread()
        worker = Worker(fn, *args, **kwargs)
        worker.moveToThread(thread)

        if on_result:
            worker.result.connect(on_result)
        if on_error:
            worker.error.connect(on_error)
        if on_finished:
            worker.finished.connect(on_finished)

        def cleanup():
            if thread in self.active_threads:
                self.active_threads.remove(thread)
            thread.quit()
            thread.wait()  # Wait for thread to finish
            worker.deleteLater()
            thread.deleteLater()

        worker.finished.connect(cleanup)
        thread.started.connect(worker.run)

        self.active_threads.append(thread)
        thread.start()
        return thread
    
    
    def drop_tip_in_place(self):
        """Placeholder for move up action."""
        if not globals.robot_api:
            print("Robot not initialized. Please initialize first.")
            return False
        globals.robot_api.drop_tip_in_place()
        return True
        

    def stop(self):
        """Placeholder for stop action."""
        if not globals.robot_api:
            print("Robot not initialized. Please initialize first.")
            return False
        globals.robot_api.control_run("stop")
        return True

    def move_robot(self, x: float, y: float, z: float) -> bool:
        if not globals.robot_initialized:
            print("Robot not initialized. Please initialize first.")
            return False
        globals.robot_api.move_relative(x,y,z)
        return True

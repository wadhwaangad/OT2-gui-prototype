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
        globals.robot_api.drop_tip_in_place()
        

    def stop(self):
        """Placeholder for stop action."""
        globals.robot_api.control_run("stop")

    def move_left(self):
        """Placeholder for move left action."""
        pass

    def move_right(self):
        """Placeholder for move right action."""
        pass

    def move_forward(self):
        """Placeholder for move forward action."""
        pass

    def move_backward(self):
        """Placeholder for move backward action."""
        pass

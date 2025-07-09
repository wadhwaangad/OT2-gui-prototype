from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        """Run the task."""
        try:
            res = self.fn(*self.args, **self.kwargs)
            # Only emit result if not interacting with Qt objects
            self.result.emit(res)
        except Exception as e:
            # Emit error as string
            self.error.emit(str(e))
        finally:
            # Always emit finished
            self.finished.emit()
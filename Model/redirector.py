
import sys
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import QObject, pyqtSignal, Qt


import threading

class StreamEmitter(QObject):
    text_written = pyqtSignal(str)


class StreamWrapper:
    def __init__(self, emitter, original_stream):
        self.emitter = emitter
        self.original_stream = original_stream
        self._buffer = ""
        self._lock = threading.Lock()

    def write(self, text):
        with self._lock:
            self.original_stream.write(text)
            self.original_stream.flush()
            self._buffer += str(text)
            # Emit only on newline or flush
            while '\n' in self._buffer:
                line, self._buffer = self._buffer.split('\n', 1)
                self.emitter.text_written.emit(line + '\n')

    def flush(self):
        with self._lock:
            if self._buffer:
                self.emitter.text_written.emit(self._buffer)
                self._buffer = ""
            self.original_stream.flush()


class StreamRedirector:
    _active = False

    def __init__(self, text_edit: QTextEdit):
        if StreamRedirector._active:
            # Prevent multiple global redirections
            print("Warning: StreamRedirector is already active. Skipping redirection setup.")
            self.text_edit = text_edit
            self.output_redirector = None
            return
            
        StreamRedirector._active = True
        self.text_edit = text_edit
        self.stdout_emitter = StreamEmitter()
        self.stderr_emitter = StreamEmitter()

        # Connect signals to GUI update using Qt QueuedConnection for thread safety
        self.stdout_emitter.text_written.connect(self._append_text, type=Qt.ConnectionType.QueuedConnection)
        self.stderr_emitter.text_written.connect(self._append_text, type=Qt.ConnectionType.QueuedConnection)

        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

        # Create wrapper instances for stdout and stderr
        self.stdout_wrapper = StreamWrapper(self.stdout_emitter, self._original_stdout)
        self.stderr_wrapper = StreamWrapper(self.stderr_emitter, self._original_stderr)

        sys.stdout = self.stdout_wrapper
        sys.stderr = self.stderr_wrapper

    def _append_text(self, text: str):
        # Only update if text_edit still exists
        if self.text_edit is not None:
            cursor = self.text_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(text)
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()

    def restore(self):
        if hasattr(self, 'stdout_wrapper') and hasattr(self, 'stderr_wrapper'):
            if StreamRedirector._active:
                sys.stdout = self._original_stdout
                sys.stderr = self._original_stderr
                StreamRedirector._active = False
        self.text_edit = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.restore()

"""
Progress monitoring bridge for real-time FSM updates.

This module provides a thread-safe bridge between the TissuePickerFSM running in its own thread
and the UI thread, enabling real-time updates of well progress and state changes.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QThread
from typing import Dict, Any, Optional


class ProgressMonitorBridge(QObject):
    """
    Thread-safe bridge for communicating FSM progress updates to the UI.
    
    This class runs in the main thread and receives signals from the FSM thread,
    then re-emits them as thread-safe signals that UI components can connect to.
    """
    
    # Signals for UI updates (emitted in main thread)
    well_started_signal = pyqtSignal(str)  # well_id
    well_completed_signal = pyqtSignal(str, int, bool)  # well_id, filled_count, success
    state_changed_signal = pyqtSignal(str, str)  # state_name, current_well
    picking_progress_signal = pyqtSignal(dict)  # {well_id: filled_count}
    fsm_finished_signal = pyqtSignal()  # FSM completed or stopped
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fsm = None
        self.connected = False
    
    def connect_to_fsm(self, fsm):
        """Connect to FSM signals for monitoring progress."""
        if self.connected:
            self.disconnect_from_fsm()
        
        self.fsm = fsm
        
        # Connect FSM signals to our bridge methods
        self.fsm.well_started.connect(self.on_well_started)
        self.fsm.well_completed.connect(self.on_well_completed)
        self.fsm.state_changed.connect(self.on_state_changed)
        self.fsm.picking_progress.connect(self.on_picking_progress)
        
        self.connected = True
        print("ProgressMonitorBridge connected to FSM")
    
    def disconnect_from_fsm(self):
        """Disconnect from FSM signals."""
        if self.fsm and self.connected:
            try:
                self.fsm.well_started.disconnect(self.on_well_started)
                self.fsm.well_completed.disconnect(self.on_well_completed)
                self.fsm.state_changed.disconnect(self.on_state_changed)
                self.fsm.picking_progress.disconnect(self.on_picking_progress)
            except Exception as e:
                print(f"Error disconnecting from FSM: {e}")
        
        self.connected = False
        self.fsm = None
        print("ProgressMonitorBridge disconnected from FSM")
    
    def on_well_started(self, well_id: str):
        """Handle well started signal from FSM."""
        print(f"Bridge: Well started - {well_id}")
        self.well_started_signal.emit(well_id)
    
    def on_well_completed(self, well_id: str, filled_count: int, success: bool):
        """Handle well completed signal from FSM."""
        print(f"Bridge: Well completed - {well_id}, count: {filled_count}, success: {success}")
        self.well_completed_signal.emit(well_id, filled_count, success)
    
    def on_state_changed(self, state_name: str, current_well: str):
        """Handle state changed signal from FSM."""
        print(f"Bridge: State changed - {state_name}, well: {current_well}")
        self.state_changed_signal.emit(state_name, current_well)
    
    def on_picking_progress(self, progress: Dict[str, int]):
        """Handle picking progress signal from FSM."""
        print(f"Bridge: Progress update - {progress}")
        self.picking_progress_signal.emit(progress)
    
    def notify_fsm_finished(self):
        """Notify that FSM has finished or been stopped."""
        print("Bridge: FSM finished")
        self.fsm_finished_signal.emit()
        self.disconnect_from_fsm()
    
    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """Get current FSM state if available."""
        if self.fsm:
            return {
                'state': self.fsm.state.value if hasattr(self.fsm.state, 'value') else str(self.fsm.state),
                'current_well': self.fsm.current_well,
                'filled_wells': dict(self.fsm.routine.filled_wells) if self.fsm.routine else {},
                'running': self.fsm.running,
                'paused': self.fsm.paused
            }
        return None
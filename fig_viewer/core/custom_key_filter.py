
import time


from PyQt6.QtCore import QObject, QTimer, QEvent, pyqtSignal as Signal

class KeyFilter(QObject):
    """
    An event filter that intercepts key presses to distinguish between
    single clicks and long presses. It emits the 'actionTriggered' signal.
    
    This class is compatible with both PyQt6 and PySide6.
    """
    
    # Define a custom signal that will carry the key code (integer).
    # 'Signal' is aliased to either pyqtSignal or Signal in the header.
    actionTriggered = Signal(int)

    # --- Constants for key event handling ---
    LONG_PRESS_THRESHOLD_MS = 500
    LONG_PRESS_INTERVAL_MS = 25
    
    def __init__(self, parent: QObject|None = None):
        super().__init__(parent)
        self._key_timers = {}
        self._key_press_times = {}

    def _handle_long_press(self, key: int):
        """
        Handles the logic for long presses.
        This method is called by the QTimer.
        """
        timer = self._key_timers.get(key)
        if not timer:
            return

        # Emit the signal to trigger the action.
        self.actionTriggered.emit(key)

        # If this is the first trigger, switch the timer to the repeating interval.
        if timer.interval() == self.LONG_PRESS_THRESHOLD_MS:
            timer.setInterval(self.LONG_PRESS_INTERVAL_MS)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """
        This method intercepts events from the object it's watching ('watched').
        """
        # We check the event type. In Qt6/PySide6, the event object passed
        # for KeyPress/KeyRelease is already a QKeyEvent instance, so we don't
        # need to cast it.
        
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if not event.isAutoRepeat() and key not in self._key_timers:
                self._key_press_times[key] = time.monotonic()
                
                timer = QTimer(self)
                self._key_timers[key] = timer
                timer.timeout.connect(lambda: self._handle_long_press(key))
                timer.start(self.LONG_PRESS_THRESHOLD_MS)
                
                # We return True to indicate that we have handled the event,
                # so it shouldn't be processed further.
                return True

        elif event.type() == QEvent.Type.KeyRelease:
            key = event.key()
            if not event.isAutoRepeat() and key in self._key_timers:
                timer = self._key_timers.pop(key)
                press_time = self._key_press_times.pop(key, None)
                
                is_single_click = timer.isActive()
                
                timer.stop()
                timer.deleteLater()
                
                if is_single_click:
                    # It's a single click, so we emit the signal.
                    self.actionTriggered.emit(key)
                
                # Event handled.
                return True

        # For all other events that we don't handle, we must return False
        # to allow them to be processed by the watched object.
        return super().eventFilter(watched, event)
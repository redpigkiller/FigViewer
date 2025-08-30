from typing import override

from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import QObject, Qt, QEvent, pyqtSignal as Signal

class KeyFilter(QObject):
    actionTriggered = Signal(object, object)

    def __init__(self, parent: QObject|None = None):
        super().__init__(parent)
        self._key_pressed = set()

    @override
    def eventFilter(self, a0: QObject|None, a1: QEvent|None) -> bool:
        if isinstance(a1, QKeyEvent) and a1.type() == QEvent.Type.KeyPress:
            if a1.key() not in (
                Qt.Key.Key_Control,
                Qt.Key.Key_Shift,
                Qt.Key.Key_Alt,
                Qt.Key.Key_Meta,
            ):
                self._key_pressed.add(a1.key())
            self.actionTriggered.emit(a1.modifiers(), self._key_pressed)
            return True

        elif isinstance(a1, QKeyEvent) and a1.type() == QEvent.Type.KeyRelease:
            self._key_pressed.discard(a1.key())
            return True

        else:
            return super().eventFilter(a0, a1)
        

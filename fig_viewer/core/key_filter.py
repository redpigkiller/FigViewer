from typing import override

from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import QObject, QEvent, pyqtSignal as Signal

class KeyFilter(QObject):
    actionTriggered = Signal(object, object)

    def __init__(self, parent: QObject|None = None):
        super().__init__(parent)
        self._key_pressed = set()

    @override
    def eventFilter(self, a0: QObject|None, a1: QEvent|None) -> bool:
        if isinstance(a1, QKeyEvent) and a1.type() == QEvent.Type.KeyPress:
            self._key_pressed.add(a1.key())

        elif isinstance(a1, QKeyEvent) and a1.type() == QEvent.Type.KeyRelease:
            self._key_pressed.discard(a1.key())

        else:
            return super().eventFilter(a0, a1)
        
        self.actionTriggered.emit(a1.modifiers(), self._key_pressed)
        return True

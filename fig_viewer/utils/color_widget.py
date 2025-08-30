
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QComboBox

from PyQt6.QtGui import QFont

class FontSizeWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        label = QLabel("Size:")
        layout.addWidget(label)
        
        text_size_range = (8, 72)
        # Set the current font size
        if not hasattr(self, '_current_font_size'):
            self._current_font_size = parent.pointSize() or 12  # Default to 12 if not set

        def set_font_size(size):
            """Set font size with proper validation and update"""
            try:
                if isinstance(size, str):
                    if size == "A-":
                        self._current_font_size -= 1
                    elif size == "A+":
                        self._current_font_size += 1
                    else:
                        self._current_font_size = int(size)
                else:
                    self._current_font_size = int(size)
                
                # Clamp the new size to the defined range
                self._current_font_size = min(self._current_font_size, text_size_range[1])
                self._current_font_size = max(self._current_font_size, text_size_range[0])

                # Create a new font with the updated size
                new_font = QFont(parent.font)
                new_font.setPointSize(self._current_font_size)
                parent.setFont(new_font)
                
                # Update the text item style
                size_selector.blockSignals(True)
                size_selector.setCurrentText(str(self._current_font_size))
                size_selector.blockSignals(False)
                
            except (ValueError, TypeError):
                # If conversion fails, keep the current font size
                size_selector.blockSignals(True)
                size_selector.setCurrentText(str(self._current_font_size))
                size_selector.blockSignals(False)

        # A- / A+ buttons
        btn_decrease = QPushButton("A-")
        btn_decrease.setMaximumWidth(30)
        btn_decrease.clicked.connect(lambda: set_font_size("A-"))
        layout.addWidget(btn_decrease)
        
        btn_increase = QPushButton("A+")
        btn_increase.setMaximumWidth(30)
        btn_increase.clicked.connect(lambda: set_font_size("A+"))
        layout.addWidget(btn_increase)
        
        # Font size combo box
        common_sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72]
        size_selector = QComboBox()
        size_selector.setEditable(True)  # allow manual typing
        size_selector.addItems([str(s) for s in common_sizes])
        size_selector.setCurrentText(str(self._current_font_size))

        # Connect the size selector to the set_font_size function
        size_selector.activated.connect(lambda _: set_font_size(size_selector.currentText()))
        size_selector.lineEdit().returnPressed.connect(lambda: set_font_size(size_selector.currentText())) # type: ignore

        layout.addWidget(size_selector)

from typing import Literal

import numpy as np

from PyQt6 import QtCore
from PyQt6 import QtWidgets
import pyqtgraph as pg

from .plot_core import PlotCore

# 線型對應
linestyle_map = {
    '-': QtCore.Qt.PenStyle.SolidLine,
    '--': QtCore.Qt.PenStyle.DashLine,
    ':': QtCore.Qt.PenStyle.DotLine,
    '-.': QtCore.Qt.PenStyle.DashDotLine
}

# 顏色處理（支持 'r', 'g' 等）
color_map = {
    'r': (255, 0, 0),
    'g': (0, 255, 0),
    'b': (0, 0, 255),
    'k': (0, 0, 0),
    'm': (255, 0, 255),
    'y': (255, 255, 0),
    'c': (0, 255, 255),
    'w': (255, 255, 255)
}

class PlotWidget():
    def __init__(self, *args, **kwargs):
        self._plot_widget = QtWidgets.QWidget(*args, **kwargs)

        layout = QtWidgets.QVBoxLayout(self._plot_widget)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self._reset_btn  = QtWidgets.QPushButton("Reset View")
        self._auto_btn   = QtWidgets.QPushButton("Auto Range")
        self._pan_btn    = QtWidgets.QPushButton("Pan")
        self._zoom_btn   = QtWidgets.QPushButton("Zoom")
        self._cursor_btn = QtWidgets.QPushButton("Cursor")
        self._grab_btn   = QtWidgets.QPushButton("Grab")
        self._save_btn   = QtWidgets.QPushButton("Save Image")
        self._open_btn   = QtWidgets.QPushButton("Open File")
        btn_layout.addWidget(self._reset_btn)
        btn_layout.addWidget(self._auto_btn)
        btn_layout.addWidget(self._pan_btn)
        btn_layout.addWidget(self._zoom_btn)
        btn_layout.addWidget(self._cursor_btn)
        btn_layout.addWidget(self._grab_btn)
        btn_layout.addWidget(self._save_btn)
        btn_layout.addWidget(self._open_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Graph afrea
        self._plot_core = PlotCore()

        self._plot_core.setBackground('w')
        pg.setConfigOptions(antialias=True)


        layout.addWidget(self._plot_core)

        # Callbacks
        # vb = self.plot_item.getViewBox()
        self._reset_btn.clicked.connect(lambda: self._plot_core.autoscale())
        self._auto_btn.clicked.connect(lambda: self._plot_core.autoscale())
        self._zoom_btn.clicked.connect(lambda: self._plot_core.set_mode('zoom'))
        self._pan_btn.clicked.connect(lambda: self._plot_core.set_mode('normal'))
        # self.save_btn.clicked.connect(self.save_image)
        # self.open_btn.clicked.connect(self.open_file)

    def as_widget(self):
        return self._plot_widget
    
    def subplot(self, row: int, col: int, rowspan=1, colspan=1) -> None:
        self._plot_core.subplot(row, col, rowspan, colspan)


    def plot(self, *args,
         linewidth: int = 1,
         color: Literal['r', 'g', 'b', 'k', 'm', 'y', 'c', 'w']|str|tuple = 'b',
         linestyle: Literal['-', '--', ':', '-.'] = '-',
         marker: Literal['o', 's', 'd', 't', '+', '*', 'x']|None = None,
         markersize: int = 6,
         hold: bool = False,
         grid: bool = False,
         label: str|None = None,
         title: str|None = None,
         xlabel: str|None = None,
         ylabel: str|None = None,
         xlim: tuple[float, float]|None = None,
         ylim: tuple[float, float]|None = None):
        """
        MATLAB-style plot function using pyqtgraph, with Literal type hints for IDE help.

        Parameters:
            *args: Either (y,) or (x, y)
            linewidth: Line width (default 1)
            color: Color (e.g., 'r', 'g', 'b', or RGB tuple)
            linestyle: '-', '--', ':', or '-.'
            marker: Marker symbol ('o', 's', 'd', etc.)
            markersize: Size of the marker
            label: Legend label
            hold: Whether to retain previous plots
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
        """
        if isinstance(color, str):
            color = color_map.get(color, color)

        
        pen = pg.mkPen(color=color, width=linewidth,
                       style=linestyle_map.get(linestyle, QtCore.Qt.PenStyle.SolidLine))

        self._plot_core.plot(*args, pen=pen)
        
        if title:
            self._plot_core.title(title)
        if xlabel:
            self._plot_core.xlabel(xlabel)
        if ylabel:
            self._plot_core.ylabel(ylabel)
        if hold:
            self._plot_core.hold = True
        # if label:
        #     self._plot_core.legend([label])
        if grid:
            self._plot_core.grid()
        if xlim:
            self._plot_core.xlim(*xlim)
        if ylim:
            self._plot_core.ylim(*ylim)





    def save_image(self):
        exporter = pg.exporters.ImageExporter(self.plot_item)
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Image", "", "PNG (*.png)")
        if fname:
            exporter.export(fname)

    def open_file(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open .npy File", "", "NumPy files (*.npy *.npz)")
        if fname:
            data = np.load(fname)
            try:
                if isinstance(data, np.lib.npyio.NpzFile):
                    keys = data.files
                    x, y = data[keys[0]], data[keys[1]]
                else:
                    x = np.arange(len(data))
                    y = data
                self.plot(x, y, pen='b')
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to load data:\n{e}")

# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     window = SinglePlotWindow()
#     window.show()
#     # 示範 plot
#     x = np.linspace(0, 10, 100)
#     y = np.sin(x)
#     window.plot(x, y)
#     sys.exit(app.exec_())
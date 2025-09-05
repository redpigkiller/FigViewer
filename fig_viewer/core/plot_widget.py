from typing import Literal

import numpy as np

from PyQt6 import QtCore
from PyQt6 import QtWidgets
import pyqtgraph as pg

from .plot_core import PlotCore


color_map_shorthand = {
    'r': (255, 0, 0),       # red
    'g': (0, 255, 0),       # green
    'b': (0, 0, 255),       # blue
    'c': (0, 255, 255),     # cyan
    'm': (255, 0, 255),     # magenta
    'y': (255, 255, 0),     # yellow
    'k': (0, 0, 0),         # black
    'w': (255, 255, 255)    # white
}

color_map_order = [
    (0.0000*255, 0.4470*255, 0.7410*255),  # blue
    (0.8500*255, 0.3250*255, 0.0980*255),  # orange/red
    (0.9290*255, 0.6940*255, 0.1250*255),  # yellow
    (0.4940*255, 0.1840*255, 0.5560*255),  # purple
    (0.4660*255, 0.6740*255, 0.1880*255),  # green
    (0.3010*255, 0.7450*255, 0.9330*255),  # light blue
    (0.6350*255, 0.0780*255, 0.1840*255)   # dark red
]

linestyle_map = {
    '-': QtCore.Qt.PenStyle.SolidLine,
    '--': QtCore.Qt.PenStyle.DashLine,
    ':': QtCore.Qt.PenStyle.DotLine,
    '-.': QtCore.Qt.PenStyle.DashDotLine
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

        # Graph area
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

        self._flag_initialized()

    def _flag_initialized(self):
        self._color_idx = 0

    def as_widget(self):
        return self._plot_widget
    
    def subplot(self, row: int, col: int, rowspan=1, colspan=1) -> None:
        self._plot_core.subplot(row, col, rowspan, colspan)

    def plot(self, *args,
        linewidth: int = 1,
        color: Literal['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w']|str|tuple|None = None,
        linestyle: Literal['-', '--', ':', '-.'] = '-',
        marker: Literal['o', 's', 't', 'd', '+', '*', 'x']|None = None,
        marker_size: int = 6,
        marker_facecolor: Literal['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w']|str|tuple|None = None,
        marker_edgecolor: Literal['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w']|str|tuple|None = None,
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
        color = self._check_color(color)
        marker_facecolor = self._check_color(marker_facecolor)
        marker_edgecolor = self._check_color(marker_edgecolor)

        line_style = linestyle_map.get(linestyle, None)
        if line_style is None:
            raise ValueError(f"Unsupported line style: {linestyle}")
        
        if marker is not None and marker not in ['o', 's', 't', 'd', '+', '*', 'x']:
            raise ValueError(f"Unsupported marker style: {marker}")

        if label is None:
            label = ''
        
        pen = pg.mkPen(color=color, width=linewidth, style=line_style)
        self._plot_core.plot(*args,
                             name=label,
                             pen=pen,
                             symbol=marker,
                             symbolBrush=marker_facecolor,
                             symbolPen=marker_edgecolor,
                             symbolSize=marker_size,
        )
        
        if title:
            self._plot_core.title(title)
        if xlabel:
            self._plot_core.xlabel(xlabel)
        if ylabel:
            self._plot_core.ylabel(ylabel)
        if hold:
            self._plot_core.hold('on')
        if grid:
            self._plot_core.grid()
        if xlim:
            self._plot_core.xlim(*xlim)
        if ylim:
            self._plot_core.ylim(*ylim)

    def legend(self, inputs: list[str]|Literal['on', 'off'] = 'on', offset=(10, 10), **kwargs) -> None:
        self._plot_core.legend(inputs, offset=offset, **kwargs)

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


    def _check_color(self, color):
        if isinstance(color, str):
            color = color_map_shorthand.get(color, None)
            if color is None:
                raise ValueError(f"Unsupported color shorthand: {color}")
        elif isinstance(color, tuple) and len(color) == 3:
            if any(not (0 <= c <= 255) for c in color):
                raise ValueError("Color RGB values must be in the range 0-255")
        elif color is None:
            color = color_map_order[self._color_idx % len(color_map_order)]
            self._color_idx += 1
        else:
            raise ValueError("Color must be a shorthand string, RGB tuple, or None")
        
        return color
    

# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     window = SinglePlotWindow()
#     window.show()
#     # 示範 plot
#     x = np.linspace(0, 10, 100)
#     y = np.sin(x)
#     window.plot(x, y)
#     sys.exit(app.exec_())
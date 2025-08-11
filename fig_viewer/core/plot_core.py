import os
from typing import Literal
from dataclasses import dataclass

import numpy as np

from PyQt6 import QtCore
import pyqtgraph as pg

from .plot_item import PlotItem

@dataclass
class SubplotSetting:
    row: int = 0
    col: int = 0
    rowspan: int = 1
    colspan: int = 1
    hold: bool = False


class PlotCore(pg.GraphicsLayoutWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Plotting configuration
        self._row: int = 0
        self._col: int = 0
        self._rowspan: int = 1
        self._colspan: int = 1

        # Plotting data
        self._plot_items: dict[tuple[int, int], PlotItem] = {}
        self._plot_item_settings: dict[PlotItem, SubplotSetting] = {}
        
        # Set focus policy
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def _get_plot_item(self, title: str='', **kwargs) -> PlotItem:
        p = self.getItem(self._row, self._col) # type: ignore
        if p is None:
            p = PlotItem(title=title, **kwargs)
            self.addItem(p, self._row, self._col, self._rowspan, self._colspan)
            self._plot_item_settings[p] = SubplotSetting()
            self._plot_items[(self._row, self._col)] = p
        return p
        
    def _remove_plot_item(self) -> None:
        p = self.getItem(self._row, self._col) # type: ignore
        if p is not None:
            self.removeItem(p)
            del self._plot_item_settings[p]
            del self._plot_items[(self._row, self._col)]

    # ########## User Interface Methods ##########
    def clear(self) -> None:
        for p in list(self._plot_items.values()):
            self.removeItem(p)
        self._plot_items.clear()
        self._plot_item_settings.clear()

        self._row = 0
        self._col = 0
        self._rowspan = 1
        self._colspan = 1

    def subplot(self, row: int, col: int, rowspan=1, colspan=1) -> None:
        self._row = row
        self._col = col
        self._rowspan = rowspan
        self._colspan = colspan

    def xlim(self, xmin=None, xmax=None) -> None:
        p = self._get_plot_item()
        p.setXRange(xmin, xmax) # type: ignore

    def ylim(self, ymin=None, ymax=None) -> None:
        p = self._get_plot_item()
        p.setYRange(ymin, ymax) # type: ignore

    def autoscale(self) -> None:
        p = self._get_plot_item()
        p.autoRange() # type: ignore

    def grid(self, status: Literal['on', 'off'] = 'on') -> None:
        p = self._get_plot_item()
        if status == 'on':
            p.showGrid(x=True, y=True)
        else:
            p.showGrid(x=False, y=False)

    def title(self, title: str) -> None:
        p = self._get_plot_item()
        p.setTitle(title)

    def xlabel(self, label: str) -> None:
        p = self._get_plot_item()
        p.setLabel('bottom', label)

    def ylabel(self, label: str) -> None:
        p = self._get_plot_item()
        p.setLabel('left', label)

    def hold(self, status: Literal['on', 'off'] = 'on') -> None:
        p = self._get_plot_item()
        if status == 'on':
            self._plot_item_settings[p].hold = True
        else:
            self._plot_item_settings[p].hold = False

    def legend(self, inputs: list[str]|Literal['on', 'off'] = 'on', offset=(10, 10), **kwargs) -> None:
        """
        Usage:
        1. Add legend when plotting: wp.plot(..., name="legend_name")
            a. To enable legend: wp.legend('on')
            b. To disable legend: wp.legend('off')
        2. Add legend after plotting:
            wp.legend(["legend_name1", "legend_name2"])
        """
        p = self._get_plot_item()
        
        if isinstance(inputs, list):
            # Add legend with multiple names
            p.add_legend(inputs, offset=offset, **kwargs)

        elif isinstance(inputs, str):
            if inputs.lower() == 'off':
                p.remove_legend()
            elif inputs.lower() == 'on':
                p.add_legend(offset=offset, **kwargs)

        else:
            raise ValueError("Invalid input for legend. Use a list of names or 'on'/'off'.")

    def plot(self, *args, title='', **kwargs) -> None:
        p = self._get_plot_item()
        if self._plot_item_settings[p].hold is False:
            self._remove_plot_item()
            p = self._get_plot_item()
        p.plot(title=title, *args, **kwargs)



if __name__ == '__main__':
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    # QApplication.setHighDpiScaleFactorRoundingPolicy(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    # pg.setConfigOption('useNumba', True)

    app = pg.mkQApp("Test")
    # win = pg.GraphicsLayoutWidget(show=True, title="Basic plotting examples")
    # win.resize(1000,600)
    # win.setWindowTitle('pyqtgraph example: Plotting')
    # win.setBackground('w')

    wp = PlotCore(show=True, title="Basic plotting examples")
    wp.resize(1000,600)
    wp.setWindowTitle('pyqtgraph example: Plotting')
    wp.setBackground('w')

    wp.subplot(0, 0)
    x = np.cos(np.linspace(0, 2*np.pi, 10))
    y = np.sin(np.linspace(0, 400*np.pi, 10))
    wp.xlim(-1, 14)
    wp.legend('off')
    wp.hold('on')
    wp.plot(x, y, name="0")
    wp.plot(2*y, name="1")
    wp.plot([ 2, 3, 4, 5, 6], name="2")
    wp.legend(['a', 'b', ])
    wp.legend()
    wp.subplot(0, 1)
    x = np.cos(np.linspace(0, 4*np.pi, 100))
    y = np.sin(np.linspace(0, 7*np.pi, 100))
    wp.plot(x, y)

    wp.subplot(0, 1)
    x = np.arange(1000)
    wp.plot(x, title='Cosine and Sine Waves')
    # wp.xlim(-1, 14)
    # wp.autoscale()
    wp.xlabel('Cosine Wave')
    wp.ylabel('s Wave')
    # wp.clear()

    # Enable antialiasing for prettier plots
    pg.setConfigOptions(antialias=True)
    pg.exec()
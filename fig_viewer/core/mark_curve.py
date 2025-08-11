from typing import TYPE_CHECKING

import numpy as np

import pyqtgraph as pg

if TYPE_CHECKING:
    from .plot_item import PlotItem


class MarkCurve(pg.GraphicsObject):
    def __init__(self, plot_data_item: pg.PlotDataItem, num_points: int = 100):
        super().__init__()

        self.plot_data_item = plot_data_item

        # Get the coordinates of the point
        pts = np.column_stack(plot_data_item.getData())     # shape (N, 2)

        self.scatter_items = []
        for i in np.linspace(0, pts.shape[0] - 1, num_points, dtype=int):
            point_coords = pts[i]  # Get the coordinates of the point
            scatter_item = pg.ScatterPlotItem([point_coords[0]], [point_coords[1]], size=5, pen=pg.mkPen('b'), brush=pg.mkBrush('gray'))

            # Add to scene
            scatter_item.setParentItem(self)

            self.scatter_items.append(scatter_item)

        # Define bounding rect for interaction
        self._boundingRect = self.scatter_items[0].boundingRect()
        for scatter_item in self.scatter_items[1:]:
            self._boundingRect = self._boundingRect.united(scatter_item.boundingRect())

    def boundingRect(self):
        return self._boundingRect

    def paint(self, painter, option=None, widget=None):
        pass


class HintCurve:
    def __init__(self, parent_win: 'PlotItem') -> None:
        self._parent_win = parent_win
        self.plot_data_item: pg.PlotDataItem | None = None
        self.scatter_items: list[pg.ScatterPlotItem] = []

    def update_hint_curve(self, plot_data_item: pg.PlotDataItem|None):
        if plot_data_item is None:
            # No hint curve to be shown
            self.clear_hint_curve()
            return
        
        elif self.plot_data_item == plot_data_item:
            # Current hint curve is the correct thing to be shown
            return
        
        self.clear_hint_curve()
        self.plot_data_item = plot_data_item

        # Get the coordinates of the point
        pts = np.column_stack(plot_data_item.getData())     # shape (N, 2)

        self.scatter_items = []
        for i in np.linspace(0, pts.shape[0] - 1, 100, dtype=int):
            point_coords = pts[i]  # Get the coordinates of the point
            scatter_item = pg.ScatterPlotItem([point_coords[0]], [point_coords[1]], size=5, pen=pg.mkPen('r'), brush=pg.mkBrush('r'))
            self.scatter_items.append(scatter_item)
            self._parent_win.addItem(scatter_item, ignoreBounds=True)

    def clear_hint_curve(self):
        for scatter_item in self.scatter_items:
            self._parent_win.removeItem(scatter_item)
        self.scatter_items = []
        self.plot_data_item = None



class MarkCurves:
    def __init__(self, parent_win: 'PlotItem') -> None:
        self._parent_win = parent_win
        self.mark_curves: dict[pg.PlotDataItem, MarkCurve] = {}

    def toggle_mark_curve(self, plot_data_item: pg.PlotDataItem|None):
        if plot_data_item is None:
            return
        
        if plot_data_item not in self.mark_curves:
            self.add_mark_curve(plot_data_item)
        else:
            self.discard_mark_curve(plot_data_item)

    def add_mark_curve(self, plot_data_item: pg.PlotDataItem|None):
        if plot_data_item is not None and plot_data_item not in self.mark_curves:
            mark_curve = MarkCurve(plot_data_item)
            self._parent_win.addItem(mark_curve, ignoreBounds=True)
            self.mark_curves[plot_data_item] = mark_curve

    def discard_mark_curve(self, plot_data_item: pg.PlotDataItem|None):
        if plot_data_item is not None and plot_data_item in self.mark_curves:
            self._parent_win.removeItem(self.mark_curves[plot_data_item])
            del self.mark_curves[plot_data_item]

    def clear_mark_curve(self):
        for mark_curve in self.mark_curves.values():
            self._parent_win.removeItem(mark_curve)
        self.mark_curves = {}

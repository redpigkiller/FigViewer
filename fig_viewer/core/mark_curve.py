from typing import TYPE_CHECKING

import numpy as np

import pyqtgraph as pg
from PyQt6.QtCore import QPointF

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

    def update(self, plot_data_item: pg.PlotDataItem|None):
        if plot_data_item is None:
            # No hint curve to be shown
            self.clear()
            return
        
        elif self.plot_data_item == plot_data_item:
            # Current hint curve is the correct thing to be shown
            return
        
        self.clear()
        self.plot_data_item = plot_data_item

        # Get the coordinates of the point
        pts = np.column_stack(plot_data_item.getData())     # shape (N, 2)

        for i in np.linspace(0, pts.shape[0] - 1, 2, dtype=int):
            point_coords = pts[i]  # Get the coordinates of the point
            scatter_item = pg.ScatterPlotItem([point_coords[0]], [point_coords[1]], size=5, pen=pg.mkPen('r'), brush=pg.mkBrush('r'))
            self.scatter_items.append(scatter_item)
            self._parent_win.addItem(scatter_item, ignoreBounds=True)

    def clear(self):
        for scatter_item in self.scatter_items:
            self._parent_win.removeItem(scatter_item)
        self.scatter_items = []
        self.plot_data_item = None



class MarkCurves:
    def __init__(self, parent_win: 'PlotItem') -> None:
        self._parent_win = parent_win
        self.mark_curves: dict[pg.PlotDataItem, MarkCurve] = {}

        self._hint_curve: HintCurve = HintCurve(self._parent_win)

        # Helper data
        self._seg_vec: dict[pg.PlotDataItem, dict] = {}         # For find nearest curve

    def add_mark_curve(self, plot_data_item: pg.PlotDataItem|None):
        if plot_data_item is not None and plot_data_item not in self.mark_curves:
            mark_curve = MarkCurve(plot_data_item)
            self._parent_win.addItem(mark_curve, ignoreBounds=True)
            self.mark_curves[plot_data_item] = mark_curve

    def remove_mark_curve(self, plot_data_item: pg.PlotDataItem|None):
        if plot_data_item is not None and plot_data_item in self.mark_curves:
            self._parent_win.removeItem(self.mark_curves[plot_data_item])
            del self.mark_curves[plot_data_item]

    def clear_mark_curve(self):
        for mark_curve in self.mark_curves.values():
            self._parent_win.removeItem(mark_curve)
        self.mark_curves = {}

    def update_hint_curve(self, view_pos, pixel_dist_threshold=20):
        plot_data_item = self.find_nearest_curve(view_pos, pixel_dist_threshold)
        self._hint_curve.update(plot_data_item)

    def update_mark_curve(self):
        self.add_mark_curve(self._hint_curve.plot_data_item)
        
    def discard_mark_curve(self):
        self.remove_mark_curve(self._hint_curve.plot_data_item)

    def toggle_mark_curve(self):
        if self._hint_curve.plot_data_item is None:
            return
        
        if self._hint_curve.plot_data_item not in self.mark_curves:
            self.add_mark_curve(self._hint_curve.plot_data_item)
        else:
            self.remove_mark_curve(self._hint_curve.plot_data_item)

    def clear_hint_curve(self):
        self._hint_curve.clear()

    def find_nearest_curve(self, coord_pos: QPointF, pixel_dist_threshold: float=-1) -> pg.PlotDataItem|None:
        min_dist = float('inf')
        min_plot_data_item = None

        #TODO: Need to exclude non-user-created-data items or particulity, hint curve items

        for plot_data_item in self._parent_win.listDataItems():
            if plot_data_item not in self._seg_vec:
                data = plot_data_item.getData()
                if any(d is None for d in data):
                    continue
                pts = np.column_stack(data)     # shape (N, 2)
                self._seg_vec[plot_data_item] = self._precompute_polyline(pts)

            closest_point = self._query_nearest_point(self._seg_vec[plot_data_item], (coord_pos.x(), coord_pos.y()))
            
            # Map the nearest data point to screen position
            view_point = pg.QtCore.QPointF(closest_point[0], closest_point[1])
            screen_point = self._parent_win.getViewBox().mapViewToScene(view_point) # type: ignore
            mouse_point = self._parent_win.getViewBox().mapViewToScene(coord_pos) # type: ignore

            square_pixel_dist = np.sqrt((screen_point.x() - mouse_point.x())**2 + (screen_point.y() - mouse_point.y())**2) # type: ignore
            
            if pixel_dist_threshold < 0 and square_pixel_dist < min_dist:
                min_dist = square_pixel_dist
                min_plot_data_item = plot_data_item

            elif square_pixel_dist < pixel_dist_threshold:
                return plot_data_item
        
        return min_plot_data_item

    def _precompute_polyline(self, data_points: np.ndarray) -> dict:
        if data_points.shape[0] == 1:
            return {"is_single_point": True, "point": data_points[0]}

        start = data_points[:-1]
        vec = data_points[1:] - start
        len_sq = np.einsum('ij,ij->i', vec, vec)  # dot product

        # avoid zero division in projection step
        len_sq[len_sq < 1e-12] = 1.0

        return {
            "is_single_point": False,
            "segments_start": start,
            "segment_vectors": vec,
            "segment_lengths_sq": len_sq
        }

    def _query_nearest_point(self, precomputed_data: dict, query_point: tuple|list) -> np.ndarray:
        qp = np.asarray(query_point, dtype=np.float64)

        if precomputed_data["is_single_point"]:
            return precomputed_data["point"]

        seg_start = precomputed_data["segments_start"]
        seg_vec = precomputed_data["segment_vectors"]
        seg_len_sq = precomputed_data["segment_lengths_sq"]

        v = qp - seg_start
        t = np.sum(v * seg_vec, axis=1) / seg_len_sq
        t = np.clip(t, 0.0, 1.0)
        p = seg_start + t[:, None] * seg_vec

        # use squared distance for efficiency
        d2 = np.sum((p - qp)**2, axis=1)
        return p[np.argmin(d2)]

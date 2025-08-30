from typing import NamedTuple, TYPE_CHECKING

import numpy as np

from PyQt6 import QtCore
from PyQt6.QtCore import QPointF, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPen, QAction
from PyQt6.QtWidgets import QApplication, QMenu, QWidget, QHBoxLayout, QLabel, QPushButton, QComboBox, QWidgetAction, QColorDialog, QFrame

import pyqtgraph as pg
from pyqtgraph.GraphicsScene.mouseEvents import MouseDragEvent

if TYPE_CHECKING:
    from .plot_item import PlotItem

DataPoint = NamedTuple('DataPoint', [('plot_data_item', pg.PlotDataItem), ('data_index', int), ('length', int)])




class AnchorDraggableTextItem(pg.TextItem):
    def __init__(self, text, anchor=(0, 1)):
        super().__init__(text, anchor=anchor)
        self._drag_start_pos = None
        self.setAnchor(anchor)

        # Default visual settings
        self.border_color = QColor("black")
        self.border_style = QtCore.Qt.PenStyle.SolidLine
        
        self.font = QFont("Arial", 12)
        self.setFont(self.font)
        self.setColor(QColor("black"))
        self.bg_color = QColor(255, 255, 255, 128)  # White semi-transparent
        self.auto_anchor = False
        self.updateStyle()

    def hoverEvent(self, ev):
        if self._drag_start_pos is None:
            if ev.isExit():
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)
            else:
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.OpenHandCursor)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            # Right-click to show context menu
            event.accept()
            self.create_context_menu(event)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        QApplication.setOverrideCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def mouseDragEvent(self, event: MouseDragEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if not self.getViewBox():
                event.ignore()
                return

            if event.isStart():
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ClosedHandCursor)

                # Start dragging
                self._drag_start_pos = self.pos()
                self.mouse_press_pos_in_item = event.pos() 
            
            if self._drag_start_pos is not None:
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ClosedHandCursor)

                # Current mouse position
                new_pos = self.getViewBox().mapSceneToView(event.scenePos()) # type: ignore
                new_anchor_x = int(new_pos.x() < self._drag_start_pos.x())
                new_anchor_y = int(new_pos.y() > self._drag_start_pos.y())
                self.setAnchor((new_anchor_x, new_anchor_y))

            if event.isFinish():
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ClosedHandCursor)

                self._drag_start_pos = None

            event.accept()

        else:
            event.ignore()

    def updateStyle(self):
        pen = QPen(self.border_color)
        pen.setStyle(self.border_style)
        self.border = pen
        self.fill = self.bg_color
        self.update()

    def create_context_menu(self, ev):
        """Create and show the right-click context menu"""
        menu = QMenu()
        
        # Show the menu
        pos = ev.screenPos()
        menu.exec(pos)


class DraggableScatterPlotItem(pg.ScatterPlotItem):
    drag_signal = pyqtSignal(QPointF)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self._is_dragged = False

    def hoverEvent(self, ev):
        if ev.isExit():
            QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)
        else:
            QApplication.setOverrideCursor(QtCore.Qt.CursorShape.CrossCursor)

    def mouseDragEvent(self, event: MouseDragEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if not self.getViewBox():
                event.ignore()
                return

            if event.isStart():
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.CrossCursor)

                # Start dragging
                self._is_dragged = True
                self.mouse_press_pos_in_item = event.pos() 
            
            if self._is_dragged:
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.CrossCursor)

                # Current mouse position and emit signal
                pos = self.getViewBox().mapSceneToView(event.scenePos()) # type: ignore
                self.drag_signal.emit(pos)

            if event.isFinish():
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)

                self._is_dragged = False

            event.accept()

        else:
            event.ignore()


class MarkSpot(pg.GraphicsObject):
    drag_signal = pyqtSignal(object, QPointF)

    def __init__(self, x, y, data_point: DataPoint, size=5, hit_size=15):
        super().__init__()
        self.data_point = data_point

        # Add hint spot for vision
        self.scatter_item = pg.ScatterPlotItem(
            [x], [y], size=size, 
            pen=pg.mkPen('b'), brush=pg.mkBrush('b'))
        
        # Add hint spot for dragging
        self.hitbox_scatter = DraggableScatterPlotItem(
            [x], [y], size=hit_size,
            pen=None, brush=pg.mkBrush(0, 0, 0, 0)  # Transparent
        )
        self.hitbox_scatter.drag_signal.connect(self._drag_event_callback)

        # Add mark spot
        mark_text = f"{x:.2f}, {y:.2f}"
        self.text_item = AnchorDraggableTextItem(mark_text)
        self.text_item.setPos(x, y)  #TODO for 3D

        # Add to scene
        self.scatter_item.setParentItem(self)
        self.hitbox_scatter.setParentItem(self)
        self.text_item.setParentItem(self)

        # Define bounding rect for interaction
        br1 = self.hitbox_scatter.boundingRect()
        br2 = self.text_item.boundingRect()
        self._boundingRect = br1.united(br2)

    def boundingRect(self):
        return self._boundingRect

    def paint(self, painter, option=None, widget=None):
        pass

    def _drag_event_callback(self, view_pos):
        self.drag_signal.emit(self, view_pos)

    def move_to_pos(self, data_point: DataPoint):
        self.data_point = data_point

        # Get the coordinates of the spot
        pts = np.column_stack(self.data_point.plot_data_item.getData())     # shape (N, 2)
        point_coords = pts[self.data_point.data_index]  # Get the coordinates of the point

        self.scatter_item.setData([point_coords[0]], [point_coords[1]])
        self.hitbox_scatter.setData([point_coords[0]], [point_coords[1]])

        mark_text = f"{point_coords[0]:.2f}, {point_coords[1]:.2f}"
        self.text_item.setPos(point_coords[0], point_coords[1])
        self.text_item.setText(mark_text)


class HintSpot:
    def __init__(self, parent_win: 'PlotItem') -> None:
        self._parent_win = parent_win
        self.data_point: DataPoint | None = None
        self.scatter_item: pg.ScatterPlotItem | None = None

    def update_hint_spot(self, data_point: DataPoint|None):
        """
            1. If new data_point is None: No hint spot -> clear and return
            2. If we have new data_point but it is the same as current one -> do nothing and return
            3. If we have new data_point and it is different from current one -> update hint spot and return
        """
        if data_point is None:
            self.clear_hint_spot()
            return

        elif self.data_point == data_point:
            return
        self.data_point = data_point
        
        # Get the coordinates of the point
        pts = np.column_stack(self.data_point.plot_data_item.getData())     # shape (N, 2)
        coords = pts[self.data_point.data_index]

        if self.scatter_item is None:
            self.scatter_item = pg.ScatterPlotItem([coords[0]], [coords[1]], size=5, pen=pg.mkPen('r'), brush=pg.mkBrush('r'))
            self._parent_win.addItem(self.scatter_item, ignoreBounds=True)
        else:
            self.scatter_item.setData([coords[0]], [coords[1]])
            
    def clear_hint_spot(self):
        if self.scatter_item is not None:
            self._parent_win.removeItem(self.scatter_item)
            self.scatter_item = None
        self.data_point = None


class MarkSpots:
    def __init__(self, parent_win: 'PlotItem') -> None:
        self._parent_win = parent_win
        self.mark_spots: list[MarkSpot] = []
        self.in_focus_mark_spot = None
    
    def update_mark_spot(self, data_point: DataPoint|None):
        if data_point is None:
            return

        self.in_focus_mark_spot = self._find_mark_spot_by_data_point(data_point)
        if self.in_focus_mark_spot is not None:
            return

        # Get the coordinates of the point
        pts = np.column_stack(data_point.plot_data_item.getData())     # shape (N, 2)
        coords = pts[data_point.data_index]

        mark_spot = MarkSpot(coords[0], coords[1], data_point)
        mark_spot.drag_signal.connect(self.drag_event)
        self._parent_win.addItem(mark_spot, ignoreBounds=True)
        self.mark_spots.append(mark_spot)
        self.in_focus_mark_spot = mark_spot
        
    def discard_mark_spot(self, data_point: DataPoint|None):
        if data_point is None:
            return
        
        mark_spot = self._find_mark_spot_by_data_point(data_point)
        if mark_spot is not None:
            self._parent_win.removeItem(mark_spot)
            self.mark_spots.remove(mark_spot)
            self.in_focus_mark_spot = None

    def clear_mark_spot(self):
        for mark_spot in self.mark_spots:
            self._parent_win.removeItem(mark_spot)
        self.mark_spots = []
        self.in_focus_mark_spot = None

    def move_mark_spot_forward(self):
        if self.in_focus_mark_spot is None:
            return
        
        data_point = self.in_focus_mark_spot.data_point
        plot_data_item = data_point.plot_data_item
        data_index = data_point.data_index
        data_length = data_point.length
        
        # Move the data point to the left
        data_index = max(data_index - 1, 0)
        self.in_focus_mark_spot.move_to_pos(DataPoint(plot_data_item, data_index, data_length))

    def move_mark_spot_backward(self):
        if self.in_focus_mark_spot is None:
            return
        
        data_point = self.in_focus_mark_spot.data_point
        plot_data_item = data_point.plot_data_item
        data_index = data_point.data_index
        data_length = data_point.length

        # Move the data point to the right
        data_index = min(data_index + 1, data_length - 1)
        self.in_focus_mark_spot.move_to_pos(DataPoint(plot_data_item, data_index, data_length))

    def drag_event(self, mark_spot: MarkSpot, pos: QPointF):
        new_data_point = self._parent_win._find_nearest_data_point(pos, specified_plot_data_item=mark_spot.data_point.plot_data_item)
        if new_data_point is None:
            return
        
        mark_spot.move_to_pos(new_data_point)

    def _find_mark_spot_by_data_point(self, data_point: DataPoint) -> MarkSpot|None:
        for mark_spot in self.mark_spots:
            if mark_spot.data_point == data_point:
                return mark_spot
        return None
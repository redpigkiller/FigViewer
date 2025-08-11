from typing import Literal, override

import numpy as np
from scipy.spatial import KDTree

import pyqtgraph as pg
from PyQt6 import QtCore
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtCore import QPointF, QTimer, Qt
from PyQt6.QtWidgets import QMenu, QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QWidgetAction, QDoubleSpinBox, QLabel, QRadioButton, QButtonGroup

from .custom_key_filter import KeyFilter
from .mark_spot import HintSpot, MarkSpots, AnchorDraggableTextItem, DataPoint
from .mark_curve import HintCurve, MarkCurves


class AxisMenu(QMenu):
    def __init__(self, axis_name, parent_plot):
        super().__init__(axis_name)
        self.axis_name = axis_name
        self.plot = parent_plot

        # --- Manual 選項 ---
        manual_widget = QWidget()
        manual_layout = QHBoxLayout(manual_widget)
        manual_layout.setContentsMargins(4, 2, 4, 2)

        self.manual_radio = QRadioButton("Manual")
        self.min_spin = QDoubleSpinBox()
        self.max_spin = QDoubleSpinBox()
        self.min_spin.setDecimals(3)
        self.max_spin.setDecimals(3)
        self.min_spin.setRange(-1e9, 1e9)
        self.max_spin.setRange(-1e9, 1e9)
        self.min_spin.setValue(0)
        self.max_spin.setValue(10)

        manual_layout.addWidget(self.manual_radio)
        manual_layout.addWidget(QLabel("Min"))
        manual_layout.addWidget(self.min_spin)
        manual_layout.addWidget(QLabel("Max"))
        manual_layout.addWidget(self.max_spin)

        manual_action = QWidgetAction(self)
        manual_action.setDefaultWidget(manual_widget)
        self.addAction(manual_action)

        # --- Auto 選項 ---
        auto_widget = QWidget()
        auto_layout = QHBoxLayout(auto_widget)
        auto_layout.setContentsMargins(4, 2, 4, 2)

        self.auto_radio = QRadioButton("Auto")
        self.padding_spin = QDoubleSpinBox()
        self.padding_spin.setDecimals(1)
        self.padding_spin.setRange(0, 100)
        self.padding_spin.setValue(10)
        self.padding_spin.setSuffix("%")

        auto_layout.addWidget(self.auto_radio)
        auto_layout.addWidget(QLabel("Padding"))
        auto_layout.addWidget(self.padding_spin)

        auto_action = QWidgetAction(self)
        auto_action.setDefaultWidget(auto_widget)
        self.addAction(auto_action)

        # --- 互斥組 ---
        group = QButtonGroup(self)
        group.addButton(self.manual_radio)
        group.addButton(self.auto_radio)
        self.auto_radio.setChecked(True)

        # --- Inverse axis ---
        inverse_action = QAction("Inverse axis", self)
        inverse_action.setCheckable(True)
        inverse_action.triggered.connect(self.toggle_inverse)
        self.addAction(inverse_action)

        # --- Log axis ---
        log_action = QAction("Log axis", self)
        log_action.setCheckable(True)
        log_action.triggered.connect(self.toggle_log)
        self.addAction(log_action)

        # --- 信號連接 ---
        self.manual_radio.toggled.connect(self.apply_manual)
        self.auto_radio.toggled.connect(self.apply_auto)

    def apply_manual(self, checked):
        if checked:
            min_val = self.min_spin.value()
            max_val = self.max_spin.value()
            if self.axis_name.lower().startswith("x"):
                self.plot.setXRange(min_val, max_val)
            else:
                self.plot.setYRange(min_val, max_val)

    def apply_auto(self, checked):
        if checked:
            padding = self.padding_spin.value() / 100
            if self.axis_name.lower().startswith("x"):
                self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
                self.plot.getViewBox().setRange(xRange=None, padding=padding)
            else:
                self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
                self.plot.getViewBox().setRange(yRange=None, padding=padding)

    def toggle_inverse(self, checked):
        if self.axis_name.lower().startswith("x"):
            self.plot.invertX(checked)
        else:
            self.plot.invertY(checked)

    def toggle_log(self, checked):
        if self.axis_name.lower().startswith("x"):
            self.plot.setLogMode(x=checked, y=self.plot.ctrl.logYCheck.isChecked() if hasattr(self.plot.ctrl, 'logYCheck') else False)
        else:
            self.plot.setLogMode(x=self.plot.ctrl.logXCheck.isChecked() if hasattr(self.plot.ctrl, 'logXCheck') else False, y=checked)




class InteractiveViewBox(pg.ViewBox):
    def __init__(self, **kwargs):
        super().__init__(enableMenu=False, **kwargs)
        self.setMouseEnabled(x=True, y=True)

    @override
    def wheelEvent(self, ev, axis=None):
        ev.accept()

        scale_factor = 1.001 ** -ev.delta()

        if ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.scaleBy((1., scale_factor)) # type: ignore
        elif ev.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.scaleBy((scale_factor, 1.)) # type: ignore
        else:
            self.scaleBy((scale_factor, scale_factor)) # type: ignore


class PlotItem(pg.PlotItem):
    def __init__(self, *args, **kwargs):
        super().__init__(viewBox=InteractiveViewBox(), *args, **kwargs)

        self._legend_item: pg.LegendItem | None = None
        self._legend_names: list[tuple[pg.PlotDataItem, str]] = []

        self.mouse_mode: Literal['pan', 'zoom', 'select', 'grab'] = "pan"
        self.toggle_type_state = False

        # Key press configuration
        self.key_filter = KeyFilter(self)   # Create an instance of the event filter
        self.installEventFilter(self.key_filter)    # Install the filter onto this widget
        self.key_filter.actionTriggered.connect(self._process_key_event)   # Connect the filter's signal

        self._hint_spot: HintSpot = HintSpot(self)
        self._mark_spots: MarkSpots = MarkSpots(self)

        self._hint_curve: HintCurve = HintCurve(self)
        self._mark_curves: MarkCurves = MarkCurves(self)

        # Helper data
        self._kd_tree: dict[pg.PlotDataItem, KDTree] = {}       # For find nearest data point
        self._seg_vec: dict[pg.PlotDataItem, dict] = {}         # For find nearest curve

        self._mouse_hover_lock: bool = False
        self._mouse_double_click_lock: bool = False

        # Initial values
        self._grid_on_x = False
        self._grid_on_y = False
    
    def plot(self, *args, name='', **kwargs):
        plot_data_item = super().plot(*args, **kwargs)
        self._legend_names.append((plot_data_item, name))
        return plot_data_item

    def add_legend(self, names: list[str]|None=None, offset=(10, 10), **kwargs):
        if self._legend_item is None:
            self._legend_item = pg.LegendItem(offset=offset, **kwargs)
            self._legend_item.setParentItem(self.getViewBox())
        
        if names is not None:
            for i, (plot_data_item, name) in enumerate(self._legend_names):
                if i < len(names):
                    self._legend_item.addItem(plot_data_item, names[i])
                else:
                    self._legend_item.addItem(plot_data_item, name)
        else:
            for plot_data_item, name in self._legend_names:
                self._legend_item.addItem(plot_data_item, name)
    
    def remove_legend(self):
        if self._legend_item is not None:
            self._legend_item.setParentItem(None)
            self._legend_item = None

    # ==================== Event Handler ====================
    @override
    def hoverEvent(self, event): # type: ignore
        if self._mouse_hover_lock:
            return
        self._mouse_hover_lock = True
        QTimer.singleShot(25, lambda: setattr(self, '_mouse_hover_lock', False))

        if event.exit:
            return
        
        self._process_hover_event(event)

    def mouseClickEvent(self, event):
        # When a double click event occurs, prevent the next single click event
        if self._mouse_double_click_lock:
            return
            
        if event.double():
            self._mouse_double_click_lock = True
            QTimer.singleShot(QApplication.doubleClickInterval() , lambda: setattr(self, '_mouse_double_click_lock', False))

        event.accept()
        self._process_click_event(event)

    def _process_key_event(self, key):
        # ==================== The key press event logic ====================
        #   (mouse_mode, clicked_button): action_description
        press_actions = {
            ('select', QtCore.Qt.Key.Key_Left):     "move_mark_spot_left",
            ('select', QtCore.Qt.Key.Key_Up):       "move_mark_spot_left",
            ('select', QtCore.Qt.Key.Key_Right):    "move_mark_spot_right",
            ('select', QtCore.Qt.Key.Key_Down):     "move_mark_spot_right",
        }

        press_action = press_actions.get((self.mouse_mode, key), None)
        
        # Start action
        if press_action is None:
            return

        if press_action == 'move_mark_spot_left':
            self._mark_spots.move_mark_spot_forward()
        elif press_action == 'move_mark_spot_right':
            self._mark_spots.move_mark_spot_backward()

    def _process_hover_event(self, event):
        # ==================== The mouse move event logic ====================
        #   (mouse_mode): action_description
        move_actions = {
            ('pan'):    "renew_hint_spot",
            ('select'): "renew_hint_spot",
            ('grab'):   "renew_hint_curve",
        }
        move_action = move_actions.get((self.mouse_mode), None)
        local_pos = event.pos()                 # Position relative to the current widget (plot_item)
        scene_pos = self.mapToScene(local_pos)  # Position in the global graphics scene

        # Start action
        if move_action is None:
            return
        
        elif move_action == 'renew_hint_spot':
            # Check covered items
            items_under_mouse = self.scene().items(scene_pos) # type: ignore
            if any(isinstance(item, (AnchorDraggableTextItem)) for item in items_under_mouse):
                data_point = None
            else:
                # Position in the data/view coordinate system
                view_pos = self.getViewBox().mapSceneToView(scene_pos) # type: ignore
                data_point = self._find_nearest_data_point(view_pos, pixel_dist_threshold=20)
            self._hint_spot.update_hint_spot(data_point)

        elif move_action == 'renew_hint_curve':
            # Position in the data/view coordinate system
            view_pos = self.getViewBox().mapSceneToView(scene_pos) # type: ignore
            plot_data_item = self._find_nearest_curve(view_pos, 20)
            self._hint_curve.update_hint_curve(plot_data_item)
    
    def _process_click_event(self, event) -> None:
        # ==================== The mouse click event logic ====================
        #   (mouse_mode, clicked_button, is_double, modifiers): action_description
        click_actions = {
            ('pan', QtCore.Qt.MouseButton.LeftButton, False, (Qt.KeyboardModifier.NoModifier)):                 "renew_mark_spot",
            ('pan', QtCore.Qt.MouseButton.LeftButton, True, (Qt.KeyboardModifier.NoModifier)):                  "discard_mark_spot",
            ('select', QtCore.Qt.MouseButton.LeftButton, False, (Qt.KeyboardModifier.NoModifier)):              "add_mark_spot",
            ('select', QtCore.Qt.MouseButton.LeftButton, True, (Qt.KeyboardModifier.NoModifier)):               "discard_mark_spot",
            ('grab', QtCore.Qt.MouseButton.LeftButton, False, (Qt.KeyboardModifier.NoModifier)):                "renew_selected_curve",
            ('grab', QtCore.Qt.MouseButton.LeftButton, False, (Qt.KeyboardModifier.ControlModifier)):           "update_selected_curve",
            ('pan', QtCore.Qt.MouseButton.RightButton, False, (Qt.KeyboardModifier.NoModifier)):                "raise_context_menu",
            ('zoom', QtCore.Qt.MouseButton.RightButton, False, (Qt.KeyboardModifier.NoModifier)):               "raise_context_menu",
            ('select', QtCore.Qt.MouseButton.RightButton, False, (Qt.KeyboardModifier.NoModifier)):             "raise_context_menu",
            ('grab', QtCore.Qt.MouseButton.RightButton, False, (Qt.KeyboardModifier.NoModifier)):               "raise_context_curve_menu",
        }

        click_action = click_actions.get((self.mouse_mode, event.button(), event.double(), event.modifiers()), None)
        
        # Start action
        if click_action is None:
            return
        
        elif click_action == 'renew_mark_spot':
            if self._hint_spot.data_point is not None:
                self._mark_spots.clear_mark_spot()
                self._mark_spots.update_mark_spot(self._hint_spot.data_point)

        elif click_action == 'add_mark_spot':
            self._mark_spots.update_mark_spot(self._hint_spot.data_point)

        elif click_action == 'discard_mark_spot':
            self._mark_spots.discard_mark_spot(self._hint_spot.data_point)

        elif click_action == 'renew_selected_curve':
            self._mark_curves.clear_mark_curve()
            self._mark_curves.add_mark_curve(self._hint_curve.plot_data_item)
        
        elif click_action == 'update_selected_curve':
            self._mark_curves.toggle_mark_curve(self._hint_curve.plot_data_item)

        elif click_action == 'raise_context_menu':
            self.getContextMenus(event)

        elif click_action == 'raise_context_curve_menu':
            self.getContextMenus(event)
        
    @override
    def getContextMenus(self, ev):
        def set_mouse_mode(mode):
            self.mouse_mode = mode
            if mode == "zoom":
                self.getViewBox().setMouseMode(self.getViewBox().RectMode) # type: ignore
            else:
                self.getViewBox().setMouseMode(self.getViewBox().PanMode) # type: ignore

        ev.accept()
        
        menu = QMenu()
        # menu = super().getContextMenus(ev)

        original_actions = menu.actions()
        actions_to_keep = {}
        for action in original_actions:
            action_text = action.text().replace('&', '') # 移除 '&' 以便比對
            if action_text == "View All":
                actions_to_keep["view_all"] = action
            elif action_text == "Export...":
                actions_to_keep["export"] = action
            # 如果您想保留 'Plot Options' 子選單，可以加上：
            # elif action_text == "Plot Options":
            #     actions_to_keep["plot_options"] = action
        # 4. 清空原始選單，準備重建
        menu.clear()

        # ########## Mouse mode region ##########
        mode_group = QActionGroup(menu)
        mode_group.setExclusive(True)
        
        pan_action = QAction("pan mode", menu)
        pan_action.setCheckable(True)
        pan_action.setChecked(self.mouse_mode == "pan")
        pan_action.triggered.connect(lambda: set_mouse_mode("pan"))
        mode_group.addAction(pan_action)
        menu.addAction(pan_action)
        
        zoom_action = QAction("zoom mode", menu)
        zoom_action.setCheckable(True)
        zoom_action.setChecked(self.mouse_mode == "zoom")
        zoom_action.triggered.connect(lambda: set_mouse_mode("zoom"))
        mode_group.addAction(zoom_action)
        menu.addAction(zoom_action)
        
        select_action = QAction("select mode", menu)
        select_action.setCheckable(True)
        select_action.setChecked(self.mouse_mode == "select")
        select_action.triggered.connect(lambda: set_mouse_mode("select"))
        mode_group.addAction(select_action)
        menu.addAction(select_action)
        
        grab_action = QAction("grab mode", menu)
        grab_action.setCheckable(True)
        grab_action.setChecked(self.mouse_mode == "grab")
        grab_action.triggered.connect(lambda: set_mouse_mode("grab"))
        mode_group.addAction(grab_action)
        menu.addAction(grab_action)
        
        menu.addSeparator()
        # ########## Common features ##########
        auto_range_action = QAction("Auto Range", menu)
        auto_range_action.triggered.connect(lambda: self.getViewBox().autoRange()) # type: ignore
        menu.addAction(auto_range_action)
        
        grid_on_menu = menu.addMenu("Grid")
        grid_all_action = QAction("All grid", grid_on_menu)
        grid_all_action.setCheckable(True)
        grid_all_action.setChecked(self._grid_on_x and self._grid_on_y)
        grid_all_action.triggered.connect(lambda: self.showGrid(x=not(self._grid_on_x and self._grid_on_y), y=not(self._grid_on_x and self._grid_on_y), alpha=0.5))
        grid_on_menu.addAction(grid_all_action) # type: ignore
        grid_x_action = QAction("X grid", grid_on_menu)
        grid_x_action.setCheckable(True)
        grid_x_action.setChecked(self._grid_on_x)
        grid_x_action.triggered.connect(lambda: self.showGrid(x=not self._grid_on_x, y=self._grid_on_y, alpha=0.5))
        grid_on_menu.addAction(grid_x_action) # type: ignore
        grid_y_action = QAction("Y grid", grid_on_menu)
        grid_y_action.setCheckable(True)
        grid_y_action.setChecked(self._grid_on_y)
        grid_y_action.triggered.connect(lambda: self.showGrid(x=self._grid_on_x, y=not self._grid_on_y, alpha=0.5))
        grid_on_menu.addAction(grid_y_action) # type: ignore

        menu.addSeparator()

        # ########## Axis features ##########
        axis_menu = menu.addMenu("Axis")
        axis_menu.addMenu(AxisMenu("X axis", self))
        axis_menu.addMenu(AxisMenu("Y axis", self))
        
        menu.addSeparator()
        
        # Single click
        auto_range_action = QAction("single click", menu)
        auto_range_action.triggered.connect(lambda: print("Single click triggered"))
        menu.addAction(auto_range_action)
        
        menu.addSeparator()
        
        # Toggle type
        grid_on_action = QAction("toggle type", menu)
        grid_on_action.setCheckable(True)
        grid_on_action.setChecked(self.toggle_type_state)
        grid_on_action.triggered.connect(self.toggle_type)
        menu.addAction(grid_on_action)
        
        # Show the menu at the mouse position
        pos = ev.screenPos()
        menu.exec(pos.toPoint())
    
    
    def toggle_type(self, checked):
        self.toggle_type_state = checked
        print(f"Toggle type: {'ON' if checked else 'OFF'}")

    @override
    def showGrid(self, x=None, y=None, alpha=None):
        self._grid_on_x = x if x is not None else self._grid_on_x
        self._grid_on_y = y if y is not None else self._grid_on_y
        super().showGrid(x=self._grid_on_x, y=self._grid_on_y, alpha=alpha)

    # ########## Helper Functions ##########
    def _find_nearest_data_point(self, coord_pos: QPointF, specified_plot_data_item: pg.PlotDataItem|None=None, pixel_dist_threshold: float=-1) -> DataPoint|None:
        min_dist = float('inf')
        min_data_point = None

        if specified_plot_data_item is not None:
            search_plot_data_items = [specified_plot_data_item]
        else:
            search_plot_data_items = self.listDataItems()
        
        for plot_data_item in search_plot_data_items:
            data = plot_data_item.getData()
            if any(d is None for d in data):
                continue

            pts = np.column_stack(data)     # shape (N, 2)

            # Check if KDTree is already created and create it for fast nearest neighbor search
            if plot_data_item not in self._kd_tree:
                self._kd_tree[plot_data_item] = KDTree(pts) # Create KDTree O(N log N)           

            # Query nearest neighbor O(log N)
            _, idx = self._kd_tree[plot_data_item].query([coord_pos.x(), coord_pos.y()], k=1, p=2)
            
            # Map the nearest data point to screen position
            view_point = pg.QtCore.QPointF(pts[idx][0], pts[idx][1])
            screen_point = self.getViewBox().mapViewToScene(view_point) # type: ignore
            mouse_point = self.getViewBox().mapViewToScene(coord_pos) # type: ignore

            square_pixel_dist = np.sqrt((screen_point.x() - mouse_point.x())**2 + (screen_point.y() - mouse_point.y())**2) # type: ignore
            
            if pixel_dist_threshold < 0 and square_pixel_dist < min_dist:
                min_dist = square_pixel_dist
                min_data_point = DataPoint(plot_data_item, int(idx), pts.shape[0])

            elif square_pixel_dist < pixel_dist_threshold:
                return DataPoint(plot_data_item, int(idx), pts.shape[0])
        
        return min_data_point

    def _find_nearest_curve(self, coord_pos: QPointF, pixel_dist_threshold: float=-1) -> pg.PlotDataItem|None:
        min_dist = float('inf')
        min_plot_data_item = None

        for plot_data_item in self.listDataItems():
            if plot_data_item not in self._seg_vec:
                data = plot_data_item.getData()
                if any(d is None for d in data):
                    continue
                pts = np.column_stack(data)     # shape (N, 2)
                self._seg_vec[plot_data_item] = self._precompute_polyline(pts)

            closest_point = self._query_nearest_point(self._seg_vec[plot_data_item], (coord_pos.x(), coord_pos.y()))
            
            # Map the nearest data point to screen position
            view_point = pg.QtCore.QPointF(closest_point[0], closest_point[1])
            screen_point = self.getViewBox().mapViewToScene(view_point) # type: ignore
            mouse_point = self.getViewBox().mapViewToScene(coord_pos) # type: ignore

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
        len_sq = np.einsum('ij,ij->i', vec, vec)  # faster dot product

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

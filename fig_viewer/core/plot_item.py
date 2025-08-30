from typing import Literal, override

import numpy as np

import pyqtgraph as pg
from PyQt6 import QtCore
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtCore import QPointF, QTimer, Qt
from PyQt6.QtWidgets import QMenu, QApplication, QWidget, QHBoxLayout, QSlider, QVBoxLayout, QPushButton, QWidgetAction, QDoubleSpinBox, QLabel, QRadioButton, QButtonGroup

from .key_filter import KeyFilter
from .mark_spot import MarkSpots
from .mark_curve import MarkCurves


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

        self._mark_spots: MarkSpots = MarkSpots(self)
        self._mark_curves: MarkCurves = MarkCurves(self)

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

    def _process_key_event(self, key_modifier, key):
        # ==================== The key press event logic ====================
        #   (mouse_mode, modifier, clicked_buttons): action_description
        press_actions = {
            ('select', Qt.KeyboardModifier.NoModifier,      frozenset([QtCore.Qt.Key.Key_Left])):     "move_mark_spot_left",
            ('select', Qt.KeyboardModifier.NoModifier,      frozenset([QtCore.Qt.Key.Key_Up])):       "move_mark_spot_left",
            ('select', Qt.KeyboardModifier.NoModifier,      frozenset([QtCore.Qt.Key.Key_Right])):    "move_mark_spot_right",
            ('select', Qt.KeyboardModifier.NoModifier,      frozenset([QtCore.Qt.Key.Key_Down])):     "move_mark_spot_right",
            ('grab',   Qt.KeyboardModifier.ControlModifier, frozenset([QtCore.Qt.Key.Key_C])):        "copy_mark_curve",
            ('grab',   Qt.KeyboardModifier.ControlModifier, frozenset([QtCore.Qt.Key.Key_V])):        "paste_mark_curve",
            ('grab',   Qt.KeyboardModifier.ControlModifier, frozenset([QtCore.Qt.Key.Key_X])):        "cut_mark_curve",
        }
        
        press_action = press_actions.get((self.mouse_mode, key_modifier, frozenset(key)), None)

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
            # Position in the data/view coordinate system
            view_pos = self.getViewBox().mapSceneToView(scene_pos) # type: ignore
            self._mark_spots.update_hint_spot(view_pos, pixel_dist_threshold=20)

        elif move_action == 'renew_hint_curve':
            # Position in the data/view coordinate system
            view_pos = self.getViewBox().mapSceneToView(scene_pos) # type: ignore
            self._mark_curves.update_hint_curve(view_pos, pixel_dist_threshold=20)
    
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
            self._mark_spots.clear_mark_spot()
            self._mark_spots.update_mark_spot()

        elif click_action == 'add_mark_spot':
            self._mark_spots.update_mark_spot()

        elif click_action == 'discard_mark_spot':
            self._mark_spots.discard_mark_spot()

        elif click_action == 'renew_selected_curve':
            self._mark_curves.clear_mark_curve()
            self._mark_curves.update_mark_curve()
        
        elif click_action == 'update_selected_curve':
            self._mark_curves.toggle_mark_curve()

        elif click_action == 'raise_context_menu':
            self.create_context_menu(event)

        elif click_action == 'raise_context_curve_menu':
            self.create_context_menu(event)
    
    def set_mouse_mode(self, mode):
        if self.mouse_mode == mode:
            return

        transition_actions = {
            ('pan', 'select'):      "keep_spots",
            ('select', 'pan'):      "keep_spots",
        }

        transition_action = transition_actions.get((self.mouse_mode, mode), "default")

        # Common actions
        self.mouse_mode = mode
        if mode == "zoom":
            self.getViewBox().setMouseMode(self.getViewBox().RectMode) # type: ignore
        else:
            self.getViewBox().setMouseMode(self.getViewBox().PanMode) # type: ignore
        
        if transition_action == "default":
            self._mark_spots.clear_hint_spot()
            self._mark_spots.clear_mark_spot()
            self._mark_curves.clear_hint_curve()
            self._mark_curves.clear_mark_curve()

    @override
    def showGrid(self, x=None, y=None, alpha=None):
        self._grid_on_x = x if x is not None else self._grid_on_x
        self._grid_on_y = y if y is not None else self._grid_on_y
        super().showGrid(x=self._grid_on_x, y=self._grid_on_y, alpha=alpha)

    def create_context_menu(self, ev):
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

        menu.clear()

        # ########## Mouse mode region ##########
        mode_group = QActionGroup(menu)
        mode_group.setExclusive(True)
        
        pan_action = QAction("pan mode", menu)
        pan_action.setCheckable(True)
        pan_action.setChecked(self.mouse_mode == "pan")
        pan_action.triggered.connect(lambda: self.set_mouse_mode("pan"))
        mode_group.addAction(pan_action)
        menu.addAction(pan_action)
        
        zoom_action = QAction("zoom mode", menu)
        zoom_action.setCheckable(True)
        zoom_action.setChecked(self.mouse_mode == "zoom")
        zoom_action.triggered.connect(lambda: self.set_mouse_mode("zoom"))
        mode_group.addAction(zoom_action)
        menu.addAction(zoom_action)
        
        select_action = QAction("select mode", menu)
        select_action.setCheckable(True)
        select_action.setChecked(self.mouse_mode == "select")
        select_action.triggered.connect(lambda: self.set_mouse_mode("select"))
        mode_group.addAction(select_action)
        menu.addAction(select_action)
        
        grab_action = QAction("grab mode", menu)
        grab_action.setCheckable(True)
        grab_action.setChecked(self.mouse_mode == "grab")
        grab_action.triggered.connect(lambda: self.set_mouse_mode("grab"))
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
        # axis_menu.addMenu(AxisMenu("X axis", self))
        # axis_menu.addMenu(AxisMenu("Y axis", self))
        
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



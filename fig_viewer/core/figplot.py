import sys
import time

from PyQt6 import QtWidgets
from PyQt6 import QtCore

from .plot_widget import PlotWidget


class SingleWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plot_widget = PlotWidget()
        self.setCentralWidget(self.plot_widget.as_widget())


class FigPlot:
    def __init__(self):
        self._app = None
        self._windows = {}

    def _ensure_app(self):
        if self._app is None:
            self._app = QtWidgets.QApplication(sys.argv)

    def figure(self, title: str|int|None = None) -> PlotWidget:
        """
        Create or retrieve a figure with specified title.
        Automatically shows the window if not already visible.
        """
        self._ensure_app()

        if title is None:
            title = len(self._windows)

        if title not in self._windows:
            window = SingleWindow()

            if isinstance(title, int):
                window.setWindowTitle(f"Figure {title}")
            else:
                window.setWindowTitle(title)

            self._windows[title] = window
            window.show()

            # Ensure GUI events are processed (so the window actually draws)
            assert self._app is not None
            self._app.processEvents()

        return self._windows[title].plot_widget

    def draw(self):
        """
        Force update/redraw of all visible windows.
        """
        if self._app:
            self._app.processEvents()
    
    def pause(self, seconds=None, only_focus: bool = False):
        """
        - pause(): Wait for user to press ESC (ignores mouse clicks).
                If all windows are closed, also quits.
        - pause(t): Pause for `t` seconds while allowing GUI refresh.
        """
        self._ensure_app()

        if seconds is not None:
            # Time-based pause
            end_time = time.time() + seconds
            while time.time() < end_time:
                assert self._app is not None
                self._app.processEvents()
                time.sleep(0.01)
        else:
            # Event-based pause
            loop = QtCore.QEventLoop()

            class PauseFilter(QtCore.QObject):
                def eventFilter(inner_self, a0, a1): # type: ignore
                    if a1.type() == QtCore.QEvent.Type.KeyPress:
                        if a1.key() == QtCore.Qt.Key.Key_Escape:
                            # When user press esc, close window

                            if only_focus:
                                # Close the widget that currently has focus
                                assert self._app is not None
                                focused_widget = self._app.focusWidget()
                                if focused_widget:
                                    # Get top-level window of the focused widget
                                    top_window = focused_widget.window()
                                    if top_window and top_window.isVisible():
                                        top_window.close()

                            else:
                                # Close all widgets
                                for win in list(self._windows.values()):
                                    if win.isVisible():
                                        win.close()

                            loop.quit()
                            return True
                    return False

            filter_obj = PauseFilter()

            assert self._app is not None
            self._app.installEventFilter(filter_obj)

            for win in self._windows.values():
                win.show()
            self._app.processEvents()

            # Timer to check if all windows are closed
            def check_windows_closed():
                if all(not win.isVisible() for win in self._windows.values()):
                    loop.quit()

            timer = QtCore.QTimer()
            timer.timeout.connect(check_windows_closed)
            timer.start(100)

            loop.exec()

            timer.stop()
            self._app.removeEventFilter(filter_obj)

    def close(self, title: str|int):
        """
        Close a specific figure by index.
        """
        if title in self._windows:
            self._windows[title].close()
            del self._windows[title]
    
    def close_all(self):
        """
        Close all opened figures.
        """
        for win in list(self._windows.values()):
            win.close()
        self._windows.clear()

    def show(self):
        """
        Block until all windows are closed by the user.
        Works like `plt.show()` in matplotlib.
        """
        self._ensure_app()

        # Don't call show() again — just check visible ones
        assert self._app is not None
        self._app.processEvents()

        loop = QtCore.QEventLoop()

        # Timer checks periodically if all windows are closed
        def check_windows():
            if all(not win.isVisible() for win in self._windows.values()):
                loop.quit()

        timer = QtCore.QTimer()
        timer.timeout.connect(check_windows)
        timer.start(100)

        loop.exec()
        timer.stop()


figplot = FigPlot()

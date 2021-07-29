import os
import time
import collections
from PyQt5 import QtCore, QtGui, QtWidgets

import todo
import qtawesome


class TodoWindow(QtWidgets.QMainWindow, object):
    def __init__(self, desk_widget, dock_widget, title=None, version=None):
        super(TodoWindow, self).__init__()
        self.title = title or "Todo"
        self.version = version or todo.version
        self.splash_screen = QtWidgets.QSplashScreen(
            QtGui.QPixmap(
                os.path.join(
                    os.path.dirname(__file__), "image", "splash.jpg"
                )
            ),
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.show_splash_screen()

        self.docked = None
        self.desk_widget = QtWidgets.QWidget()
        self.desk_widget.widget = desk_widget
        self.dock_widget = QtWidgets.QWidget()
        self.dock_widget.widget = dock_widget
        self.desk_toolbar = QtWidgets.QToolBar()
        self.dock_toolbar = QtWidgets.QToolBar()

        desk_layout = QtWidgets.QGridLayout()
        desk_spacer = QtWidgets.QWidget()
        desk_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        desk_layout.addWidget(desk_spacer, 0, 0)
        desk_layout.addWidget(self.desk_toolbar, 0, 1)
        desk_layout.addWidget(desk_widget, 1, 0, 1, 2)

        dock_layout = QtWidgets.QGridLayout()
        dock_layout.addWidget(dock_widget, 0, 0)
        dock_layout.addWidget(self.dock_toolbar, 0, 1)

        self.desk_widget.setLayout(desk_layout)
        self.dock_widget.setLayout(dock_layout)

        dock_toggle_action = QtWidgets.QAction(self.get_icon("dock"), "", self)
        dock_toggle_action.setCheckable(True)
        dock_toggle_action.setChecked(False)

        self.toolbar_actions = collections.OrderedDict((
            ("dock", (dock_toggle_action, self.toggle_dock)),
            (
                "font",
                (QtWidgets.QAction(self.get_icon("font"), "", self), self.change_font)
            ),
            (
                "color",
                (QtWidgets.QAction(self.get_icon("color"), "", self), self.change_color)
            ),
            (
                "close",
                (QtWidgets.QAction(self.get_icon("close"), "", self), self.deleteLater)
            ),
        ))
        for name, action_data in self.toolbar_actions.items():
            action, callback = action_data
            self.desk_toolbar.addAction(action)
            self.dock_toolbar.addAction(action)
            if action.isCheckable():
                action.toggled.connect(callback)
            else:
                action.triggered.connect(callback)

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.desk_widget)
        layout.addWidget(self.dock_widget)
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.setWindowTitle(self.title)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.desk()
        self.hide_splash_screen()

    def toggle_dock(self, docked):
        if docked:
            self.dock()
        else:
            self.desk()

    def dock(self):
        self.desk_widget.hide()
        self.dock_widget.show()

        self.adjustSize()
        self.docked = True

        desktop = QtWidgets.QApplication.desktop().screenGeometry(self.centralWidget())
        self.move(desktop.bottomRight())

    def desk(self):
        self.dock_widget.hide()
        self.desk_widget.show()

        self.adjustSize()
        self.docked = False

        desktop = QtWidgets.QApplication.desktop().screenGeometry(self)
        self.move(desktop.center())

    def change_font(self):
        font_dir = os.path.join(os.path.dirname(__file__), "font")
        selector = todo.FontSelector(font_dir)
        if selector.exec_() == QtWidgets.QDialog.Accepted:
            font = selector.selected_font
            if font:
                self.setFont(font)
                self.desk_widget.widget.current_font = font
                self.dock_widget.widget.current_font = font

    def change_color(self):
        color = QtWidgets.QColorDialog.getColor()

        if color and color.isValid():
            self.setStyleSheet("color: {}".format(color.name()))
            for name, action_data in self.toolbar_actions.items():
                action, callback = action_data
                action.setIcon(self.get_icon(name, color=color))

            self.desk_widget.widget.current_font_color = color
            self.dock_widget.widget.current_font_color = color

    def get_icon(self, name, color=None):
        iconmap = {
            "font": "fa5s.font",
            "color": "fa5s.palette",
            "dock": "fa5s.anchor",
            "close": "fa5.window-close"
        }
        if name not in iconmap:
            return

        if color:
            return qtawesome.icon(iconmap[name], color=color)
        else:
            return qtawesome.icon(iconmap[name])

    def show_splash_screen(self):
        self.splash_screen.show()
        self.splash_screen.showMessage(
            """
            <div style="align: center">
                <h1>
                    <font color='white'>{}</font>
                </h1>
                <h3>
                    <font color='white'>{}</font>
                </h3>
            </div>
            """.format(self.title, self.version),
            QtCore.Qt.AlignTop | QtCore.Qt.AlignCenter, QtCore.Qt.black
        )

    def hide_splash_screen(self, delay=None):
        time.sleep(delay or 0)
        self.splash_screen.finish(self)

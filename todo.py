import os
import functools
import sqlite3
import random
import inspect
import sys

from PyQt5 import QtCore, QtGui, QtSql, QtWidgets
import qtawesome

from todo import utils, constant


class TodoWidget(QtWidgets.QDialog, object):
    def __init__(self):
        super(TodoWidget, self).__init__()
        self.priorities = dict((
            (1, "Today"),
            (2, "Later"),
            (3, "Sometime"),
            (4, "Someday")
        ))

        # Item lifespans in seconds.
        # {priority: (active lifespan, completed lifespan)}
        self.lifespans = dict((
            (1, (8 * 60 * 60, 5 * 60)),
            (2, (12 * 60 * 60, 5 * 60)),
            (3, (5 * 24 * 60 * 60, 5 * 60)),
            (4, (None, 5 * 60))
        ))
        self.default_size = QtCore.QSize(600, 350)
        self._current_font = self.font()
        self._current_font_color = "black"
        self.views = {}
        self.toolbar_actions = dict((
            (
                "refresh",
                (
                    QtWidgets.QAction(
                        self.get_icon(
                            'refresh',
                            color=self._current_font_color
                        ),
                        "",
                        self
                    ),
                    self.refresh
                )
            ),
            (
                "add",
                (
                    QtWidgets.QAction(
                        self.get_icon(
                            "add",
                            color=self._current_font_color
                        ),
                        "",
                        self
                    ),
                    self.add
                )
            ),
        ))
        self.toolbar = QtWidgets.QToolBar()
        for action, callback in self.toolbar_actions.values():
            self.toolbar.addAction(action)
            if action.isCheckable():
                action.toggled.connect(callback)
            else:
                action.triggered.connect(callback)

        self.setLayout(QtWidgets.QGridLayout())
        self.setFixedSize(self.default_size)

    def get_icon(self, name, color=None):
        iconmap = {
            "refresh": "fa5s.sync-alt",
            "add": "fa5s.plus"
        }

        if name not in iconmap:
            return
        if color:
            return qtawesome.icon(iconmap[name], color=color)
        else:
            return qtawesome.icon(iconmap[name])

    @property
    def current_view(self):
        raise NotImplementedError

    def refresh(self):
        for view in self.views.values():
            view.model().select()

    @property
    def current_font(self):
        return self._current_font

    @current_font.setter
    def current_font(self, font):
        self._current_font = font
        for view in self.views.values():
            view.model().current_font = font

    @property
    def current_font_color(self):
        return self._current_font_color

    @current_font_color.setter
    def current_font_color(self, color):
        self._current_font_color = color
        for view in self.views.values():
            view.model().current_font_color = color
        for name, action_data in self.toolbar_actions.items():
            action, callback = action_data
            action.setIcon(self.get_icon(name, color=color))

    def add(self):
        if constant.DEBUG:
            print("Adding entry...")
        title, ok = QtWidgets.QInputDialog.getText(
            self, "Add todo", "What would you like to do?"
        )

        if not ok or not title:
            return

        title = str(title).strip()
        timestamp = utils.get_timestamp()
        item = {
            "title": title,
            "timestamp": timestamp,
        }

        if constant.DEBUG:
            print("add(), title: {}, timestamp: {}, item: {}".format(title, timestamp, item))

        self.current_view.model().add_entry(item)


class TodoDeskWidget(TodoWidget):
    def __init__(self):
        super(TodoDeskWidget, self).__init__()

        self.stack = QtWidgets.QTabWidget()
        self.views = {}
        self.layout().addWidget(self.toolbar, 0, 0)
        self.layout().addWidget(self.stack, 1, 0, 1, 2)

        for priority, label in self.priorities.items():
            view = TodoView(priority, self.lifespans[priority], self)
            self.views[priority] = view
            self.stack.addTab(view, label)
            view.viewchanged.connect(self.refresh)
        self.current_font = self._current_font
        self.current_font_color = self._current_font_color

    @property
    def current_view(self):
        return self.views[self.stack.currentIndex() + 1]


class TodoDockWidget(TodoWidget):
    def __init__(self):
        super(TodoDockWidget, self).__init__()
        self.default_size = QtCore.QSize(600, 50)
        self.priority = list(self.priorities.keys())[0]
        view = TodoView(self.priority, self.lifespans[self.priority], self)
        self.views[self.priority] = view
        view.viewchanged.connect(self.refresh)
        self.layout().addWidget(view, 0, 0)
        self.layout().addWidget(self.toolbar, 0, 1)
        self.layout().setColumnStretch(0, 575)
        self.setFixedSize(self.default_size)
        self.current_font = self._current_font
        self.current_font_color = self._current_font_color

    @property
    def current_view(self):
        return self.views[self.priority]


class TodoView(QtWidgets.QTableView, object):
    viewchanged = QtCore.pyqtSignal()

    def __init__(self, priority, lifespans, container):
        super(TodoView, self).__init__()
        self.menu = QtWidgets.QMenu()
        self.container = container
        self.lifespans = lifespans
        self.priority = priority

        self.database = QtSql.QSqlDatabase.addDatabase("QSQLITE")
        self.database.setDatabaseName(os.path.join(os.environ.get("HOME"), ".config", "todo", ".config"))
        self.database.open()

        model = TodoModel(self.database, priority, lifespans)
        self.setModel(model)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSortingEnabled(False)
        self.setCornerButtonEnabled(True)
        self.setSelectionMode(QtWidgets.QTableView.ExtendedSelection)
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.resizeColumnsToContents()
        self.horizontalHeader().setStretchLastSection(True)

        self.setColumnWidth(self.model().completed_column, 75)
        self.setColumnWidth(self.model().title_column, 300)
        self.setColumnWidth(self.model().timestamp_column, 150)

        self.hideColumn(0)
        self.hideColumn(len(self.model().fields()) - 1)
        self.model().datachanged.connect(self.viewchanged.emit)

        self.horizontalHeader().hide()
        self.verticalHeader().hide()

    def selectedRecords(self):
        rows = set([index.row() for index in self.selectedIndexes()])
        return map(lambda row: (row, self.model().get_record(row)), rows)

    def context_menu(self):
        self.menu.clear()
        promote_action = QtWidgets.QAction("Promote", self)
        demote_action = QtWidgets.QAction("Demote", self)
        mark_complete_action = QtWidgets.QAction("Mark completed", self)
        mark_active_action = QtWidgets.QAction("Mark active", self)

        def mark_complete():
            for row, record in self.selectedRecords():
                record.setValue(self.model().completed_column, 1)
                self.model().updateRowInTable(row, record)
                self.model().submit()

        def mark_active():
            for row, record in self.selectedRecords():
                record.setValue(self.model().completed_column, 0)
                self.model().updateRowInTable(row, record)
                self.model().submit()

        def promote():
            for row, record in self.selectedRecords():
                column = self.model().priority_column
                record.setValue(column, record.value(column) - 1)
                self.model().updateRowInTable(row, record)
                self.model().submit()

        def demote():
            for row, record in self.selectedRecords():
                column = self.model().priority_column
                record.setValue(column, record.value(column) + 1)
                self.model().updateRowInTable(row, record)
                self.model().submit()

        def move(priority):
            for row, record in self.selectedRecords():
                column = self.model().priority_column
                record.setValue(column, priority)
                self.model().updateRowInTable(row, record)
                self.model().submit()

        mark_complete_action.triggered.connect(mark_complete)
        mark_active_action.triggered.connect(mark_active)

        promote_action.triggered.connect(promote)
        demote_action.triggered.connect(demote)

        if self.priority != list(self.container.priorities.keys())[0]:
            self.menu.addAction(promote_action)

        if self.priority != list(self.container.priorities.keys())[-1]:
            self.menu.addAction(demote_action)

        self.menu.addAction(mark_complete_action)
        self.menu.addAction(mark_active_action)

        send_to_menu = self.menu.addMenu("Send to")
        for priority, priority_label in self.container.priorities.items():
            if priority == self.priority:
                continue
            action = QtWidgets.QAction(priority_label, self)
            action.triggered.connect(functools.partial(move, priority))
            send_to_menu.addAction(action)

        return self.menu

    def contextMenuEvent(self, event):
        self.context_menu().popup(QtGui.QCursor.pos())


class TodoDatabaseManager(object):
    def __init__(self):
        self.__dbname__ = "config"
        self.__dbdir__ = os.path.join(
            os.environ.get("HOME"), ".config", "todo"
        )
        self.__dbfile__ = os.path.join(self.__dbdir__, self.__dbname__)

        if not os.path.isdir(self.__dbdir__):
            os.makedirs(self.__dbdir__, mode=755)

        self.connection_name = u"todo_sql_connection"
        self.table = u"todos"
        self.connection = sqlite3.connect(self.__dbfile__)
        self.connection.row_factory = sqlite3.Row
        self.session = self.connection.cursor()

        if self.table not in self.tables:
            command = """CREATE TABLE {} (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, {})""".format(
                self.table,
                ", ".join(
                    "{} {}".format(field, datatype)
                    for field, datatype in self.fields
                )
            )
            self.session.execute(command)
            self.connection.commit()

        # if not self.session.execute(
        #     """select COUNT(*) from {}""".format(self.table)
        # ).fetchone()[0]:
        #     self.populate_test_data(5)

    @property
    def fields(self):
        return [
            ("completed", "INTEGER"),
            ("title", "TEXT"),
            ("timestamp", "TEXT"),
            ("priority", "INTEGER"),
        ]

    @property
    def tables(self):
        return [
            row["name"] for row in self.session.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        ]

    @property
    def table_info(self):
        return self.session.execute(
            "PRAGMA TABLE_INFO({})".format(self.table)
        ).fetchall()

    def get_connection(self, connection_name=None):
        self.connection_name = connection_name or self.connection_name
        if QtSql.QSqlDatabase.contains(self.connection_name):
            return QtSql.QSqlDatabase.database(self.connection_name)

        database = QtSql.QSqlDatabase.addDatabase(
            "QSQLITE", self.connection_name
        )
        database.setDatabaseName(self.__dbfile__)
        database.open()

        return database

    def add_entry(self, data):
        if constant.DEBUG:
            print("add_entry(), data: {}".format(data))
        command = (
            """
            INSERT INTO todos({}) VALUES ("{completed},"{title}", "{timestamp}, {priority})
            """.format(
                ", ".join([field for field, datatype in self.fields]),
                **data
            )
        )
        if constant.DEBUG:
            print(command)
        self.session.execute(command, data)
        self.connection.commit()
        return True

    def remove_entry(self, data):
        command = (
            """
            DELETE FROM {} WHERE id = {} 
            """.format(self.table, data["id"])
        )
        if constant.DEBUG:
            print(command)
        self.session.execute(command)
        self.connection.commit()

    def update_entry(self, data):
        command = (
            """0
            UPDATE {} SET {} WHERE id = {}
            """.format(
                self.table,
                ", ".join([
                    "{} = '{}'".format(field, value)
                    for field, value in data.items()
                    if value is not None and field != "id"
                ]),
                data["id"]
            )
        )
        if constant.DEBUG:
            print(command)
        self.session.execute(command)
        self.connection.commit()
        return True

    def populate_test_data(self, count=None):
        priorities = range(1, 5)
        for index in range(1, (count or 20) + 1):
            command = (
                """
                INSERT INTO todos({}) VALUES ({}, "test todo {}", "{}", {})
                """.format(
                    ", ".join([field for field, datatype in self.fields]),
                    random.choice([0, 1]),
                    index,
                    utils.get_timestamp(),
                    random.choice(priorities)
                )
            )
            self.session.execute(command)
        self.connection.commit()


class TodoModel(QtSql.QSqlTableModel):
    datachanged = QtCore.pyqtSignal()

    def __init__(self, database, priority, lifespans):
        super(TodoModel, self).__init__(None, database)
        self.database_manager = TodoDatabaseManager()
        self.priority = priority
        self.active_lifespan, self.completed_lifespan = lifespans
        self.title_column = self.fieldIndex("title")
        self.completed_column = self.fieldIndex("completed")
        self.timestamp_column = self.fieldIndex("timestamp")
        self.priority_column = self.fieldIndex("priority")
        self._current_font = None
        self._current_completed_font = None
        self._current_font_color = None
        self._current_completed_font_color = None

        self.setEditStrategy(QtSql.QSqlTableModel.OnFieldChange)
        self.select()

    @property
    def current_font(self):
        return self._current_font

    @current_font.setter
    def current_font(self, font):
        self._current_font = QtGui.QFont(font)
        self._current_font.setPointSize(self._current_font.pointSize() - 2)
        self._current_completed_font = QtGui.QFont(font)
        self._current_completed_font.setPointSize(self._current_font.pointSize())
        self._current_completed_font.setStrikeOut(True)

    @property
    def current_font_color(self):
        return self._current_font_color

    @current_font_color.setter
    def current_font_color(self, color):
        self._current_font_color = QtGui.QColor(color)
        h, s, v, a = self._current_font_color.getHsv()
        s *= 0.5
        a *= 0.75
        self._current_completed_font_color = QtGui.QColor.fromHsv(h, s, v, a)

    def populate_record(self, row, record, role=QtCore.Qt.EditRole):
        for column in range(record.count()):
            field = record.field(column)
            if field.isNull():
                if column == self.timestamp_column:
                    value = utils.get_timestamp()
                else:
                    value = self.data(
                        self.index(row, column), role
                    )
            else:

                value = field.value()

            record.setValue(column, value or field.value())

        return record

    # def insertRowIntoTable(self, record):
    #     return self.database_manager.add_entry(self.get_record_data(record))

    # def updateRowInTable(self, row, record):
    #     return self.database_manager.update_entry(
    #         self.get_record_data(self.populate_record(row, record))
    #     )

    # def deleteRowFromTable(self, record):
    #     return self.database_manager.remove_entry(self.get_record_data(record))

    def get_record_data(self, record):
        data = {}
        for index in range(record.count()):
            field = record.field(index)
            value = None if field.isNull() else str(field.value())
            data.update({
                str(field.name()): value
            })

        return data

    def submit(self):
        self.datachanged.emit()
        return True

    def print_record(self, record, prefix=None):
        if record.isEmpty():
            print("Empty record. Nothing to print.")
            return

        print("Record Data:")
        for index in range(record.count()):
            field = record.field(index)
            print(
                "{}{} : {}".format(
                    prefix or "",
                    field.name(),
                    "Null" if field.isNull() else field.value()
                )
            )

    def fields(self):
        return ["id"] + [
            field for field, datatype in self.database_manager.fields
        ]

    def table(self):
        return self.database_manager.table

    def selectStatement(self):
        return """
            SELECT {} from {} WHERE priority = {} ORDER BY completed 
        """.format(
            ", ".join(self.fields()),
            self.table(),
            self.priority,
        )

    @property
    def default_values(self):
        return {
            "id": None,
            "priority": self.priority,
            "completed": 0
        }

    def generate_record(self, data=None):
        data = data or {}
        record = QtSql.QSqlRecord()
        for field in self.fields():
            value = data.get(field, self.default_values.get(field))
            field = QtSql.QSqlField(field)
            field.setValue(value)
            field.setGenerated(True)
            record.append(field)
        return record

    def add_entry(self, data_dict):
        print("Adding entry in {}: {}".format(self.priority, data_dict))
        record = self.generate_record(data_dict)
        return self.insertRecord(-1, record)

    def insertRecord(self, row, record):
        print("insertRecord()")
        return super(TodoModel, self).insertRecord(row, record)

    def setRecord(self, row, record):
        print("setRecord()")
        return super(TodoModel, self).setRecord(row, record)

    def flags(self, index):
        if index.column() == self.title_column:
            completed = bool(
                self.data(
                    self.index(index.row(), self.completed_column),
                    QtCore.Qt.EditRole
                )
            )
            if not completed:
                return (
                        QtCore.Qt.ItemIsEditable
                        | QtCore.Qt.ItemIsEnabled
                        | QtCore.Qt.ItemIsSelectable
                )

        if index.column() == self.completed_column:
            return (
                    QtCore.Qt.ItemIsEnabled
                    | QtCore.Qt.ItemIsSelectable
                    | QtCore.Qt.ItemIsUserCheckable
            )

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def get_age(self, timestamp_index):
        value = str(self.data(timestamp_index, QtCore.Qt.EditRole))
        if not value:
            return 0

        return (
                utils.get_date(utils.get_timestamp())
                - utils.get_date(value)
        ).seconds

    def get_record(self, row):
        return self.populate_record(row, self.generate_record())

    def process_demotion(self, timestamp_index):
        if self.active_lifespan is None:
            return

        if self.get_age(timestamp_index) > self.active_lifespan:
            record = self.get_record(timestamp_index.row())
            value, _ = record.value(self.priority_column).toInt()
            record.setValue(
                self.priority_column,
                value + 1
            )
            self.updateRowInTable(timestamp_index.row, record)
            self.submit()

    def process_deletion(self, timestamp_index):
        if self.completed_lifespan is None:
            return

        if self.get_age(timestamp_index) > self.completed_lifespan:
            record = self.get_record(timestamp_index.row())
            self.deleteRowFromTable(record)
            self.submit()

    def process_lifespans(self, timestamp_index):
        completed = bool(
            super(TodoModel, self).data(
                self.index(timestamp_index.row(), self.completed_column),
                QtCore.Qt.EditRole
            )
        )

        if completed:
            self.process_deletion(timestamp_index)
        else:
            self.process_demotion(timestamp_index)

    def data(self, index, role):
        if not index.isValid():
            print("Invalid index.")
            return None

        column = index.column()
        value = super(TodoModel, self).data(index, role)

        if role == QtCore.Qt.CheckStateRole:
            if column != self.completed_column:
                return None
            completed = bool(
                super(TodoModel, self).data(
                    index, QtCore.Qt.EditRole
                )
            )
            return QtCore.Qt.Checked if completed else QtCore.Qt.Unchecked

        if role == QtCore.Qt.EditRole:
            return value

        if role == QtCore.Qt.DisplayRole:
            if column == self.completed_column:
                return None
            if column == self.timestamp_column:
                self.process_lifespans(index)
                str_value = str(value)
                if str_value:
                    return utils.get_date(str_value).humanize()

            return value

        completed = bool(
            super(TodoModel, self).data(
                self.index(index.row(), self.completed_column), QtCore.Qt.EditRole
            )
        )

        if role == QtCore.Qt.ToolTipRole:
            if column == self.timestamp_column:
                value = super(TodoModel, self).data(
                    index, QtCore.Qt.DisplayRole
                )
                return utils.get_formatted_date(str(value))
            if column == self.completed_column:
                return "Completed" if completed else "Active"

            return value

        if role == QtCore.Qt.TextAlignmentRole:
            if column == self.completed_column:
                return QtCore.Qt.AlignCenter
            else:
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        if role == QtCore.Qt.FontRole:
            return (
                self._current_completed_font
                if completed else self._current_font
            )

        if role == QtCore.Qt.ForegroundRole:
            return (
                self._current_completed_font_color
                if completed else self._current_font_color
            )

    def setData(self, index, value, role):
        if role == QtCore.Qt.CheckStateRole:
            if index.column() != self.completed_column:
                return None
            if value == QtCore.Qt.Checked:
                result = super(TodoModel, self).setData(
                    index, 1, QtCore.Qt.EditRole
                )
                print("1. Result: {}, Value: {}".format(result, value))
            else:
                result = super(TodoModel, self).setData(
                    index, 0, QtCore.Qt.EditRole
                )
                print("2. Result: {}, Value: {}".format(result, value))
        else:
            result = super(TodoModel, self).setData(index, value, role)
            print("3. Result: {}, Value: {}".format(result, value))

        if not result:
            self.print_last_error("setData()")

        return result

    def print_last_error(self, title=None):
        error_map = inspect.getmembers(
            QtSql.QSqlError, lambda member: isinstance(member, int)
        )
        db_error = self.database().lastError()
        error_type = [
            error for error, value in error_map if value == db_error.type()
        ][0]
        print(
            "{}: {} ({}): {}".format(
                title or "", error_type, db_error.number(), db_error.text()
            )
        )


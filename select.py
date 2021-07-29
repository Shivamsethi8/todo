import os
import collections
from glob import glob

from PyQt5 import QtCore, QtGui, QtWidgets


class FontSelector(QtWidgets.QDialog, object):
    def __init__(self, directory):
        super(FontSelector, self).__init__()
        self.font_dir = directory
        self.font_database = QtGui.QFontDatabase()
        self.font_map = collections.OrderedDict()
        self.selected_font = None
        self.sample_text = "A quick brown fox."
        self.build_font_map()

        layout = QtWidgets.QGridLayout()
        self.family_list = QtWidgets.QListWidget()
        self.family_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.style_list = QtWidgets.QListWidget()
        self.style_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.size_list = QtWidgets.QListWidget()
        self.size_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.font_sample = QtWidgets.QLabel()
        self.font_sample.setText(self.sample_text)
        self.font_sample.setAlignment(QtCore.Qt.AlignCenter)
        self.font_sample.setMinimumSize(100, 100)
        self.font_sample.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid black;
            }
        """)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.family_list.currentRowChanged.connect(self.populate_styles)
        self.style_list.currentRowChanged.connect(self.populate_sizes)
        self.size_list.currentRowChanged.connect(self.update_sample)

        layout.addWidget(self.family_list, 0, 0)
        layout.addWidget(self.style_list, 0, 1)
        layout.addWidget(self.size_list, 0, 2)
        layout.addWidget(self.font_sample, 1, 0, 1, 3)
        layout.addWidget(self.button_box, 2, 2)
        self.setLayout(layout)
        self.populate_families()

    def pause_updates(self, pause):
        self.family_list.setUpdatesEnabled(not pause)
        self.family_list.blockSignals(pause)
        self.style_list.setUpdatesEnabled(not pause)
        self.style_list.blockSignals(pause)
        self.size_list.setUpdatesEnabled(not pause)
        self.size_list.blockSignals(pause)
        self.font_sample.setUpdatesEnabled(not pause)
        self.font_sample.blockSignals(pause)

    def populate_families(self):
        self.pause_updates(True)
        self.family_list.clear()
        self.style_list.clear()
        self.size_list.clear()
        self.selected_font = None

        self.family_list.addItems(self.font_map.keys())
        self.pause_updates(False)
        self.family_list.setCurrentRow(0)

    def populate_styles(self, family_row):
        self.pause_updates(True)
        self.selected_font = None
        self.style_list.clear()
        self.size_list.clear()

        family = self.family_list.item(family_row).text()
        self.style_list.addItems(self.font_map[family].keys())
        self.pause_updates(False)
        self.style_list.setCurrentRow(0)

    def populate_sizes(self, style_row):
        self.pause_updates(True)
        self.selected_font = None
        family = self.family_list.item(self.family_list.currentRow()).text()
        style = self.style_list.item(style_row).text()
        self.size_list.addItems(self.font_map[family][style])

        self.pause_updates(False)
        self.size_list.setCurrentRow(self.size_list.count()/2.5)

    def update_sample(self):
        family = self.family_list.item(self.family_list.currentRow()).text()
        style = self.style_list.item(self.style_list.currentRow()).text()
        size = int(self.size_list.item(self.size_list.currentRow()).text())
        self.selected_font = self.font_database.font(family, style, size)
        self.font_sample.setText(self.sample_text)
        self.font_sample.setFont(self.selected_font)

    def get_font_files(self):
        extensions = ["*.ttf", "*.otf"]
        font_files = []

        for extension in extensions:
            font_files.extend(glob(os.path.join(self.font_dir, extension)))
            font_files.extend(
                glob(os.path.join(self.font_dir, extension.upper()))
            )

        return font_files

    def build_font_map(self):
        font_ids = map(
            self.font_database.addApplicationFont,
            self.get_font_files()
        )

        for font_id in font_ids:
            for family in sorted(
                self.font_database.applicationFontFamilies(font_id)
            ):
                self.font_map.setdefault(family, {})
                for style in sorted(self.font_database.styles(family)):
                    self.font_map[family].setdefault(style, [])
                    self.font_map[family][style] = map(
                        str,
                        sorted(self.font_database.smoothSizes(family, style))
                    )

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QListWidget, QListWidgetItem


class ComponentLibrary(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Components", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.list_widget = QListWidget()
        self.refresh_standard_components()
        self.refresh_custom_chips()

        self.list_widget.setDragEnabled(True)
        self.setWidget(self.list_widget)

    def refresh_standard_components(self):
        self.list_widget.addItem("AND")
        self.list_widget.addItem("OR")
        self.list_widget.addItem("NOT")
        self.list_widget.addItem("Input Switch")
        self.list_widget.addItem("Output Bulb")

    def refresh_custom_chips(self):
        self.list_widget.clear()
        self.refresh_standard_components()

        lib_path = os.path.join(os.path.dirname(__file__), "..", "..", "library")
        if not os.path.exists(lib_path):
            return

        for f in os.listdir(lib_path):
            if f.endswith(".json"):
                name = os.path.splitext(f)[0]
                item = QListWidgetItem(f"IC: {name}")

                item.setData(Qt.UserRole, os.path.join(lib_path, f))
                self.list_widget.addItem(item)

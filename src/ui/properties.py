from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDockWidget, QFormLayout, QLabel, QLineEdit,
                               QWidget)

from src.graphics.items.base import GateItem
from src.graphics.items.wire import WireItem


class PropertyInspector(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Properties", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.container = QWidget()
        self.layout = QFormLayout(self.container)
        self.setWidget(self.container)

        self.current_item = None

        self.name_edit = QLineEdit()
        self.name_edit.editingFinished.connect(self.on_name_changed)

        self.info_label = QLabel("Select an item")

        self._setup_ui()

    def _setup_ui(self):
        self.layout.addRow("Info", self.info_label)
        self.layout.addRow("Name", self.name_edit)
        self.name_edit.hide()

    def set_item(self, item):
        self.current_item = item
        self.name_edit.blockSignals(True)

        if isinstance(item, GateItem):
            self.info_label.setText(f"Type: {item.node.__class__.__name__}")
            self.name_edit.setText(item.node.name)
            self.name_edit.show()
            self.layout.labelForField(self.name_edit).show()
        elif isinstance(item, WireItem):
            self.info_label.setText("Wire")
            self.name_edit.hide()
            self.layout.labelForField(self.name_edit).hide()
        else:
            self.info_label.setText("No Selection")
            self.name_edit.hide()
            self.layout.labelForField(self.name_edit).hide()

        self.name_edit.blockSignals(False)

    def on_name_changed(self):
        if self.current_item and isinstance(self.current_item, GateItem):
            new_name = self.name_edit.text()
            self.current_item.node.name = new_name
            self.current_item.label.setPlainText(new_name)

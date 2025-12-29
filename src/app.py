import json
import os

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QAction, QUndoStack
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from src.commands.actions import AddGateCommand, DeleteGateCommand
from src.graphics.items.base import GateItem
from src.graphics.items.wire import WireItem
from src.graphics.scene import LogicScene
from src.graphics.view import LogicView
from src.model.circuit import Circuit
from src.model.gates import (
    AndGate,
    CustomGate,
    InputSwitch,
    NotGate,
    OrGate,
    OutputBulb,
)
from src.model.serializer import CircuitSerializer
from src.simulation.engine import SimulationEngine
from src.ui.library import ComponentLibrary
from src.ui.properties import PropertyInspector


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Logic Sim")
        self.resize(1200, 800)

        self.circuit = Circuit()
        self.undo_stack = QUndoStack(self)
        self.simulation = SimulationEngine(self.circuit)

        self.scene = LogicScene(self)
        self.view = LogicView(self.scene, self)
        self.setCentralWidget(self.view)

        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_docks()

        self.current_tool = "Select"
        self.temp_wire = None
        self.start_port = None

        self.scene.wire_connected.connect(self.on_wire_connected)
        self.scene.node_triggered.connect(self.on_node_triggered)
        self.simulation.start()

        self.startTimer(30)

    def timerEvent(self, event):
        self.scene.update()

    def on_node_triggered(self, node):
        self.simulation.trigger_update(node)

    def on_wire_connected(self, start_port, end_port):
        self.circuit.connect(start_port.pin, end_port.pin)

        self.simulation.trigger_update(start_port.pin.node)

    def _create_actions(self):
        self.exit_act = QAction("Exit", self)
        self.exit_act.setShortcut("Ctrl+Q")
        self.exit_act.triggered.connect(self.close)

        self.save_act = QAction("Save", self)
        self.save_act.setShortcut("Ctrl+S")
        self.save_act.triggered.connect(self.save_circuit)

        self.load_act = QAction("Open", self)
        self.load_act.setShortcut("Ctrl+O")
        self.load_act.triggered.connect(self.load_circuit)

        self.create_ic_act = QAction("Create IC", self)
        self.create_ic_act.triggered.connect(self.create_integrated_circuit)

        self.undo_act = self.undo_stack.createUndoAction(self, "Undo")
        self.undo_act.setShortcut("Ctrl+Z")

        self.redo_act = self.undo_stack.createRedoAction(self, "Redo")
        self.redo_act.setShortcut("Ctrl+Shift+Z")

        self.delete_act = QAction("Delete", self)
        self.delete_act.setShortcut("Del")
        self.delete_act.triggered.connect(self.delete_selection)

        self.zoom_in_act = QAction("Zoom In", self)
        self.zoom_in_act.triggered.connect(lambda: self.view.scale(1.2, 1.2))

        self.zoom_out_act = QAction("Zoom Out", self)
        self.zoom_out_act.triggered.connect(lambda: self.view.scale(1 / 1.2, 1 / 1.2))

    def _create_menus(self):
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.save_act)
        file_menu.addAction(self.load_act)
        file_menu.addAction(self.create_ic_act)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_act)

        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction(self.undo_act)
        edit_menu.addAction(self.redo_act)
        edit_menu.addSeparator()
        edit_menu.addAction(self.delete_act)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self.zoom_in_act)
        view_menu.addAction(self.zoom_out_act)

    def _create_toolbars(self):
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)

        toolbar.addAction("Select").triggered.connect(lambda: self.set_tool("Select"))
        toolbar.addAction("Wire").triggered.connect(lambda: self.set_tool("Wire"))
        toolbar.addSeparator()
        toolbar.addAction("AND").triggered.connect(lambda: self.add_gate("AND"))
        toolbar.addAction("OR").triggered.connect(lambda: self.add_gate("OR"))
        toolbar.addAction("NOT").triggered.connect(lambda: self.add_gate("NOT"))
        toolbar.addAction("Switch").triggered.connect(lambda: self.add_gate("Input"))
        toolbar.addAction("Bulb").triggered.connect(lambda: self.add_gate("Output"))

    def _create_docks(self):
        self.library = ComponentLibrary(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.library)
        self.library.list_widget.itemDoubleClicked.connect(self.on_library_double_click)

        self.props = PropertyInspector(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.props)

    def set_tool(self, tool):
        self.current_tool = tool
        self.scene.set_mode(tool)
        self.statusBar().showMessage(f"Tool: {tool}")
        if tool == "Select":
            self.view.setDragMode(LogicView.RubberBandDrag)
        else:
            self.view.setDragMode(LogicView.NoDrag)

    def add_gate(self, gate_type):
        node = None
        if gate_type == "AndGate" or gate_type == "AND":
            node = AndGate()
        elif gate_type == "OrGate" or gate_type == "OR":
            node = OrGate()
        elif gate_type == "NotGate" or gate_type == "NOT":
            node = NotGate()
        elif gate_type == "InputSwitch" or gate_type == "Input":
            node = InputSwitch()
        elif gate_type == "OutputBulb" or gate_type == "Output":
            node = OutputBulb()

        if node:
            cmd = AddGateCommand(self.scene, self.circuit, node, QPointF(100, 100))
            self.undo_stack.push(cmd)
            self.set_tool("Select")

    def save_circuit(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Circuit", "", "JSON Files (*.json)"
        )
        if path:
            data = CircuitSerializer.serialize(self.circuit, self.scene)
            try:
                with open(path, "w") as f:
                    json.dump(data, f, indent=4)
                self.statusBar().showMessage(f"Saved to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")

    def load_circuit(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Circuit", "", "JSON Files (*.json)"
        )
        if path:
            try:
                with open(path, "r") as f:
                    data = json.load(f)

                CircuitSerializer.deserialize(data, self.circuit, self.scene)
                self.undo_stack.clear()
                self.simulation.start()
                self.statusBar().showMessage(f"Loaded from {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load file: {e}")

    def create_integrated_circuit(self):
        name, ok = QInputDialog.getText(self, "Create IC", "Chip Name:")
        if ok and name:
            data = CircuitSerializer.serialize(self.circuit, self.scene)

            inputs = []
            outputs = []

            for node in self.circuit.nodes:
                if isinstance(node, InputSwitch):
                    inputs.append(node.name)
                elif isinstance(node, OutputBulb):
                    outputs.append(node.name)

            inputs.sort()
            outputs.sort()

            data["input_names"] = inputs
            data["output_names"] = outputs
            data["chip_name"] = name

            lib_path = os.path.join(os.path.dirname(__file__), "..", "library")
            os.makedirs(lib_path, exist_ok=True)

            filename = os.path.join(lib_path, f"{name}.json")
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)

            self.library.refresh_custom_chips()

            QMessageBox.information(self, "Success", f"Chip '{name}' created!")

    def on_library_double_click(self, item):
        text = item.text()
        if text.startswith("IC: "):
            chip_name = text[4:]

            lib_path = os.path.join(os.path.dirname(__file__), "..", "library")
            filename = os.path.join(lib_path, f"{chip_name}.json")

            if os.path.exists(filename):
                with open(filename, "r") as f:
                    chip_data = json.load(f)

                node = CustomGate(chip_name, chip_data)

                cmd = AddGateCommand(self.scene, self.circuit, node, QPointF(100, 100))
                self.undo_stack.push(cmd)
            else:
                QMessageBox.warning(self, "Error", f"Chip file not found: {filename}")

        else:
            type_map = {
                "Input Switch": "InputSwitch",
                "Output Bulb": "OutputBulb",
                "AND": "AndGate",
                "OR": "OrGate",
                "NOT": "NotGate",
            }
            gate_type = type_map.get(text, text)
            self.add_gate(gate_type)

    def delete_selection(self):
        for item in self.scene.selectedItems():
            if isinstance(item, GateItem):
                cmd = DeleteGateCommand(self.scene, self.circuit, item)
                self.undo_stack.push(cmd)
            elif isinstance(item, WireItem):
                self.circuit.disconnect(item.start_port.pin, item.end_port.pin)
                self.scene.removeItem(item)

    def on_selection_changed(self):
        items = self.scene.selectedItems()
        if items:
            self.props.set_item(items[0])
        else:
            self.props.set_item(None)

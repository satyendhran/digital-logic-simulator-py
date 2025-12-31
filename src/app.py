import json
import os

from PySide6.QtCore import QPointF, Qt, QSettings
from PySide6.QtGui import QAction, QUndoStack
from PySide6.QtWidgets import (QFileDialog, QInputDialog, QMainWindow,
                               QMessageBox, QToolBar)

from src.commands.actions import AddGateCommand, DeleteGateCommand
from src.graphics.items.base import GateItem
from src.graphics.items.wire import WireItem
from src.graphics.scene import LogicScene
from src.graphics.view import LogicView
from src.model.circuit import Circuit
from src.model.gates import (AndGate, CustomGate, InputSwitch, NotGate, OrGate,
                             OutputBulb, SevenSegmentDecoder,
                             SevenSegmentDisplay, TriStateBuffer)
from src.model.serializer import CircuitSerializer
from src.simulation.engine import SimulationEngine
from src.ui.library import ComponentLibrary
from src.ui.properties import PropertyInspector


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("DigitalSim", "DigitalLogicSim")
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
        self._apply_style()
        self._load_ui_settings()

        self.current_tool = "Select"
        self.temp_wire = None
        self.start_port = None

        self.scene.wire_connected.connect(self.on_wire_connected)
        self.scene.node_triggered.connect(self.on_node_triggered)
        self.scene.mode_changed.connect(self.on_scene_mode_changed)
        self.simulation.start()

        # Rendering cadence is controlled by LogicView's FPS timer

    def on_node_triggered(self, node):
        self.simulation.trigger_update(node)

    def on_wire_connected(self, start_port, end_port, control_points):
        from src.commands.actions import WireConnectCommand
        cmd = WireConnectCommand(self.scene, self.circuit, start_port, end_port, control_points)
        self.undo_stack.push(cmd)
        self.simulation.trigger_update(start_port.pin.node)
        self.set_tool("Select")

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
        self.backend_gpu_act = QAction("Renderer: GPU", self)
        self.backend_gpu_act.triggered.connect(lambda: self.view.set_backend("GPU"))
        self.backend_cpu_act = QAction("Renderer: CPU", self)
        self.backend_cpu_act.triggered.connect(lambda: self.view.set_backend("CPU"))
        self.fps_cap_act = QAction("Set FPS Cap…", self)
        self.fps_cap_act.triggered.connect(self._set_fps_cap)
        self.overlay_toggle_act = QAction("Toggle Performance Overlay", self)
        self.overlay_toggle_act.setCheckable(True)
        self.overlay_toggle_act.setChecked(True)
        self.overlay_toggle_act.triggered.connect(self._toggle_overlay)
        self.theme_toggle_act = QAction("Toggle Theme", self)
        self.theme_toggle_act.triggered.connect(self._toggle_theme)

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
        view_menu.addSeparator()
        view_menu.addAction(self.backend_gpu_act)
        view_menu.addAction(self.backend_cpu_act)
        view_menu.addSeparator()
        view_menu.addAction(self.fps_cap_act)
        view_menu.addAction(self.overlay_toggle_act)
        view_menu.addSeparator()
        view_menu.addAction(self.theme_toggle_act)

    def _create_toolbars(self):
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)
        toolbar.setMovable(False)
        toolbar.setObjectName("MainToolbar")

        toolbar.addAction("Select").triggered.connect(lambda: self.set_tool("Select"))
        toolbar.addAction("Wire").triggered.connect(lambda: self.set_tool("Wire"))
        toolbar.addSeparator()
        toolbar.addAction("AND").triggered.connect(lambda: self.add_gate("AND"))
        toolbar.addAction("OR").triggered.connect(lambda: self.add_gate("OR"))
        toolbar.addAction("XOR").triggered.connect(lambda: self.add_gate("XOR"))
        toolbar.addAction("NAND").triggered.connect(lambda: self.add_gate("NAND"))
        toolbar.addAction("NOR").triggered.connect(lambda: self.add_gate("NOR"))
        toolbar.addAction("NOT").triggered.connect(lambda: self.add_gate("NOT"))
        toolbar.addAction("Switch").triggered.connect(lambda: self.add_gate("Input"))
        toolbar.addAction("Bulb").triggered.connect(lambda: self.add_gate("Output"))
        toolbar.addAction("7-Seg").triggered.connect(lambda: self.add_gate("7SEG"))
        toolbar.addAction("7-Dec").triggered.connect(lambda: self.add_gate("7DEC"))
        toolbar.addAction("BUFZ").triggered.connect(lambda: self.add_gate("BUFZ"))

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
            self.view.setCursor(Qt.ArrowCursor)
        else:
            self.view.setDragMode(LogicView.NoDrag)
            if tool == "Wire":
                self.view.setCursor(Qt.CrossCursor)
            else:
                self.view.setCursor(Qt.ArrowCursor)
    def _set_fps_cap(self):
        val, ok = QInputDialog.getInt(self, "FPS Cap", "Frames per second:", 60, 10, 240, 1)
        if ok:
            self.view.set_fps_cap(val)
            self.settings.setValue("ui/fps_cap", val)
            self.statusBar().showMessage(f"FPS cap set to {val}")
    def _toggle_overlay(self, checked):
        self.scene.overlay_enabled = checked
        self.settings.setValue("ui/overlay", checked)
        self.scene.update()

    def _toggle_theme(self):
        cur = self.settings.value("ui/theme", "dark")
        nxt = "light" if cur == "dark" else "dark"
        self.settings.setValue("ui/theme", nxt)
        self._apply_style()

    def add_gate(self, gate_type):
        node = None
        if gate_type == "AndGate" or gate_type == "AND":
            node = AndGate()
        elif gate_type == "OrGate" or gate_type == "OR":
            node = OrGate()
        elif gate_type == "XorGate" or gate_type == "XOR":
            from src.model.gates import XorGate
            node = XorGate()
        elif gate_type == "NandGate" or gate_type == "NAND":
            from src.model.gates import NandGate
            node = NandGate()
        elif gate_type == "NorGate" or gate_type == "NOR":
            from src.model.gates import NorGate
            node = NorGate()
        elif gate_type == "NotGate" or gate_type == "NOT":
            node = NotGate()
        elif gate_type == "InputSwitch" or gate_type == "Input":
            node = InputSwitch()
        elif gate_type == "OutputBulb" or gate_type == "Output":
            node = OutputBulb()
        elif gate_type == "7SEG":
            node = SevenSegmentDisplay()
        elif gate_type == "7DEC":
            node = SevenSegmentDecoder()
        elif gate_type == "BUFZ":
            node = TriStateBuffer()

        if node:
            cmd = AddGateCommand(self.scene, self.circuit, node, QPointF(100, 100))
            self.undo_stack.push(cmd)
            self.set_tool("Select")

    def on_scene_mode_changed(self, mode):
        self.current_tool = mode
        self.statusBar().showMessage(f"Tool: {mode}")
        if mode == "Select":
            self.view.setDragMode(LogicView.RubberBandDrag)
            self.view.setCursor(Qt.ArrowCursor)
        elif mode == "Wire":
            self.view.setDragMode(LogicView.NoDrag)
            self.view.setCursor(Qt.CrossCursor)
        else:
            self.view.setDragMode(LogicView.NoDrag)
            self.view.setCursor(Qt.ArrowCursor)
    def _apply_style(self):
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
        except Exception:
            app = None
        theme = self.settings.value("ui/theme", "dark")
        if theme == "light":
            with open("src/light.qss", "r") as f:
                qss = f.read()
        else:
            with open("src/dark.qss", "r") as f:
                qss = f.read()
        if app:
            app.setStyleSheet(qss)

    def _load_ui_settings(self):
        fps = int(self.settings.value("ui/fps_cap", 60))
        self.view.set_fps_cap(fps)
        overlay = self.settings.value("ui/overlay", True)
        self.scene.overlay_enabled = bool(overlay) and str(overlay).lower() != "false"
        self.overlay_toggle_act.setChecked(self.scene.overlay_enabled)
        try:
            from src.constants import PORT_SIZE
            port_size = int(self.settings.value("ui/port_size", PORT_SIZE))
            for item in self.scene.items():
                if isinstance(item, GateItem):
                    for p in item.input_ports:
                        if hasattr(p, "set_port_size"):
                            p.set_port_size(port_size)
                    for p in item.output_ports:
                        if hasattr(p, "set_port_size"):
                            p.set_port_size(port_size)
        except Exception:
            pass
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
                "XOR": "XorGate",
                "NAND": "NandGate",
                "NOR": "NorGate",
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

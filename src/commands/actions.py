from PySide6.QtGui import QUndoCommand

from src.graphics.items.base import GateItem
from src.graphics.items.wire import WireItem
from src.graphics.scene import LogicScene
from src.model.circuit import Circuit
from src.model.node import Node, Pin


class AddGateCommand(QUndoCommand):
    def __init__(self, scene: LogicScene, circuit: Circuit, node: Node, pos):
        super().__init__(f"Add {node.name}")
        self.scene = scene
        self.circuit = circuit
        self.node = node
        self.pos = pos
        self.item = None

    def redo(self):
        if not self.item:
            self.item = GateItem(self.node)
            self.item.setPos(self.pos)

        if self.node not in self.circuit.nodes:
            self.circuit.add_node(self.node)

        if self.item.scene() != self.scene:
            self.scene.addItem(self.item)

    def undo(self):
        self.circuit.remove_node(self.node)
        self.scene.removeItem(self.item)


class DeleteGateCommand(QUndoCommand):
    def __init__(self, scene: LogicScene, circuit: Circuit, item: GateItem):
        super().__init__(f"Delete {item.node.name}")
        self.scene = scene
        self.circuit = circuit
        self.item = item
        self.node = item.node
        self.pos = item.pos()

    def redo(self):
        try:
            ports = list(getattr(self.item, "input_ports", [])) + list(getattr(self.item, "output_ports", []))
            for p in ports:
                for w in list(getattr(p, "wires", [])):
                    try:
                        a: Pin = w.start_port.pin
                        b: Pin = w.end_port.pin if w.end_port else None
                        if b:
                            a.disconnect(b)
                    except Exception:
                        pass
                    try:
                        if w in w.start_port.wires:
                            w.start_port.wires.remove(w)
                        if w.end_port and w in w.end_port.wires:
                            w.end_port.wires.remove(w)
                    except Exception:
                        pass
                    if w.scene():
                        self.scene.removeItem(w)
        except Exception:
            pass
        self.circuit.remove_node(self.node)
        self.scene.removeItem(self.item)

    def undo(self):
        self.circuit.add_node(self.node)
        self.scene.addItem(self.item)
        self.item.setPos(self.pos)


class WireConnectCommand(QUndoCommand):
    def __init__(
        self,
        scene: LogicScene,
        circuit: Circuit,
        start_port,
        end_port,
        control_points,
    ):
        super().__init__("Connect Wire")
        self.scene = scene
        self.circuit = circuit
        self.start_port = start_port
        self.end_port = end_port
        self.control_points = list(control_points or [])
        self.item = None

    def redo(self):
        if not self.item:
            self.item = WireItem(self.start_port, self.end_port)
            self.item.control_points = list(self.control_points)
            self.item.update_geometry()
        if self.item.scene() != self.scene:
            self.scene.addItem(self.item)
        a: Pin = self.start_port.pin
        b: Pin = self.end_port.pin
        a.connect(b)

    def undo(self):
        a: Pin = self.start_port.pin
        b: Pin = self.end_port.pin
        a.disconnect(b)
        if self.item and self.item.scene():
            self.scene.removeItem(self.item)

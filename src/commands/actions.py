from PySide6.QtGui import QUndoCommand

from src.graphics.items.base import GateItem
from src.graphics.scene import LogicScene
from src.model.circuit import Circuit
from src.model.node import Node


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
        self.circuit.remove_node(self.node)
        self.scene.removeItem(self.item)

    def undo(self):
        self.circuit.add_node(self.node)
        self.scene.addItem(self.item)
        self.item.setPos(self.pos)

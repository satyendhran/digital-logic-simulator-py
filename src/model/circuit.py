from typing import Dict, List

from src.model.node import Node, Pin


class Circuit:
    def __init__(self):
        self.nodes: List[Node] = []

        self.wires: List[Dict] = []

    def add_node(self, node: Node):
        self.nodes.append(node)

    def remove_node(self, node: Node):
        if node in self.nodes:
            for pin in node.inputs + node.outputs:
                for connected_pin in list(pin.connections):
                    pin.disconnect(connected_pin)
            self.nodes.remove(node)

    def connect(self, source_pin: Pin, target_pin: Pin):
        source_pin.connect(target_pin)

    def disconnect(self, source_pin: Pin, target_pin: Pin):
        source_pin.disconnect(target_pin)

    def clear(self):
        self.nodes.clear()
        self.wires.clear()

    def serialize(self):
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "wires": [],
        }

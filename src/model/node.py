import uuid
from enum import Enum
from typing import List


class PinType(Enum):
    INPUT = 0
    OUTPUT = 1


class LogicState(Enum):
    LOW = 0
    HIGH = 1
    UNDEFINED = 2


class Node:
    def __init__(self, name: str = "Node"):
        self.id = str(uuid.uuid4())
        self.name = name
        self.inputs: List["Pin"] = []
        self.outputs: List["Pin"] = []
        self.position = (0, 0)

    def compute(self):
        """Override this to implement gate logic."""
        pass

    def add_input(self):
        pin = Pin(self, PinType.INPUT, len(self.inputs))
        self.inputs.append(pin)
        return pin

    def add_output(self):
        pin = Pin(self, PinType.OUTPUT, len(self.outputs))
        self.outputs.append(pin)
        return pin

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.__class__.__name__,
            "x": self.position[0],
            "y": self.position[1],
            "inputs": len(self.inputs),
            "outputs": len(self.outputs),
        }


class Pin:
    def __init__(self, node: Node, pin_type: PinType, index: int):
        self.id = str(uuid.uuid4())
        self.node = node
        self.type = pin_type
        self.index = index
        self.connections: List["Pin"] = []
        self.value = LogicState.UNDEFINED

    def connect(self, other: "Pin"):
        if other not in self.connections:
            self.connections.append(other)
            other.connections.append(self)

    def disconnect(self, other: "Pin"):
        if other in self.connections:
            self.connections.remove(other)
            other.connections.remove(self)

    def set_value(self, value: LogicState):
        self.value = value

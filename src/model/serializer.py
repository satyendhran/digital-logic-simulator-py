import json
import os
from typing import Any, Dict

from src.graphics.items.base import GateItem
from src.graphics.items.wire import WireItem
from src.graphics.scene import LogicScene
from src.model.circuit import Circuit
from src.model.gates import (
    AndGate,
    CustomGate,
    InputSwitch,
    NotGate,
    OrGate,
    OutputBulb,
)


class CircuitSerializer:
    @staticmethod
    def serialize(circuit: Circuit, scene: LogicScene) -> Dict[str, Any]:
        data = {"nodes": [], "wires": []}

        node_items = {}
        for item in scene.items():
            if isinstance(item, GateItem):
                node_items[item.node.id] = item

        for node in circuit.nodes:
            item = node_items.get(node.id)
            pos = (item.pos().x(), item.pos().y()) if item else (0, 0)

            node_data = {
                "id": node.id,
                "type": node.__class__.__name__,
                "x": pos[0],
                "y": pos[1],
                "name": node.name,
                "inputs": len(node.inputs),
            }
            if node.__class__.__name__ == "CustomGate":
                node_data["source_chip_name"] = node.source_chip_name
            data["nodes"].append(node_data)

        visited_wires = set()

        for node in circuit.nodes:
            for pin in node.inputs:
                for connected_pin in pin.connections:
                    wire_key = tuple(sorted([pin.id, connected_pin.id]))
                    if wire_key not in visited_wires:
                        visited_wires.add(wire_key)
                        data["wires"].append(
                            {
                                "from_node": connected_pin.node.id,
                                "from_pin": connected_pin.index,
                                "to_node": pin.node.id,
                                "to_pin": pin.index,
                            }
                        )

        return data

    @staticmethod
    def deserialize(data: Dict[str, Any], circuit: Circuit, scene: LogicScene):
        circuit.clear()
        scene.clear()

        id_node_map = {}
        id_item_map = {}

        for node_data in data["nodes"]:
            cls_name = node_data["type"]
            node = None
            if cls_name == "AndGate":
                node = AndGate()
            elif cls_name == "OrGate":
                node = OrGate()
            elif cls_name == "NotGate":
                node = NotGate()
            elif cls_name == "InputSwitch":
                node = InputSwitch()
            elif cls_name == "OutputBulb":
                node = OutputBulb()
            elif cls_name == "CustomGate":
                from src.model.gates import CustomGate
                chip_name = node_data.get("source_chip_name", node_data.get("name"))
                if chip_name:
                    lib_path = os.path.join(
                        os.path.dirname(__file__), "..", "..", "library"
                    )
                    filename = os.path.join(lib_path, f"{chip_name}.json")
                    if os.path.exists(filename):
                        try:
                            with open(filename, "r") as f:
                                chip_data = json.load(f)
                            node = CustomGate(chip_name, chip_data)
                        except Exception as e:
                            print(f"Error loading custom gate {chip_name}: {e}")
                    else:
                        print(f"Custom gate file not found: {filename}")

            if node:
                old_id = node_data["id"]
                node.name = node_data.get("name", node.name)

                circuit.add_node(node)
                id_node_map[old_id] = node

                item = GateItem(node)
                item.setPos(node_data["x"], node_data["y"])
                scene.addItem(item)
                id_item_map[node] = item

        for wire_data in data["wires"]:
            from_node = id_node_map.get(wire_data["from_node"])
            to_node = id_node_map.get(wire_data["to_node"])

            if from_node and to_node:
                try:
                    from_pin = from_node.outputs[wire_data["from_pin"]]
                    to_pin = to_node.inputs[wire_data["to_pin"]]

                    circuit.connect(from_pin, to_pin)

                    start_item = id_item_map[from_node]
                    end_item = id_item_map[to_node]

                    start_port_item = start_item.output_ports[wire_data["from_pin"]]
                    end_port_item = end_item.input_ports[wire_data["to_pin"]]

                    wire_item = WireItem(start_port_item, end_port_item)
                    scene.addItem(wire_item)
                except IndexError:
                    print("Wire mapping error: Pin index out of range")
                except KeyError:
                    print("Wire mapping error: Node not found")
                    end_item = id_item_map[to_node]

                    start_port_item = start_item.output_ports[wire_data["from_pin"]]
                    end_port_item = end_item.input_ports[wire_data["to_pin"]]

                    wire_item = WireItem(start_port_item, end_port_item)
                    scene.addItem(wire_item)
                except IndexError:
                    print("Wire mapping error: Pin index out of range")
                except KeyError:
                    print("Wire mapping error: Node not found")

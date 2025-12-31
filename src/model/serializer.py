import json
import os
from typing import Any, Dict

from src.graphics.items.base import GateItem
from src.graphics.items.wire import WireItem
from src.graphics.scene import LogicScene
from src.model.circuit import Circuit
from src.model.gates import AndGate, InputSwitch, NotGate, OrGate, OutputBulb
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor


class CircuitSerializer:
    @staticmethod
    def serialize(circuit: Circuit, scene: LogicScene) -> Dict[str, Any]:
        data = {"nodes": [], "wires": []}

        node_items = {}
        for item in scene.items():
            if isinstance(item, GateItem):
                node_items[item.node.id] = item
        wire_items = []
        for item in scene.items():
            if isinstance(item, WireItem) and item.start_port and item.end_port:
                wire_items.append(item)

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
            # Persist component body color
            if item is not None and hasattr(item, "body_color"):
                c = item.body_color
                node_data["body_color"] = [c.red(), c.green(), c.blue(), c.alpha()]
            # Persist pin names and colors (inputs/outputs)
            pin_inputs = []
            pin_outputs = []
            if item is not None:
                for i, port_item in enumerate(getattr(item, "input_ports", []) or []):
                    name = node.inputs[i].name if i < len(node.inputs) else f"In{i+1}"
                    col = port_item.base_color
                    pin_inputs.append(
                        {"name": name, "color": [col.red(), col.green(), col.blue(), col.alpha()]}
                    )
                for i, port_item in enumerate(getattr(item, "output_ports", []) or []):
                    name = node.outputs[i].name if i < len(node.outputs) else f"Out{i+1}"
                    col = port_item.base_color
                    pin_outputs.append(
                        {"name": name, "color": [col.red(), col.green(), col.blue(), col.alpha()]}
                    )
            else:
                # Fallback when no item is present in the scene
                for i, pin in enumerate(node.inputs):
                    col = getattr(pin, "color", None)
                    if isinstance(col, QColor):
                        rgba = [col.red(), col.green(), col.blue(), col.alpha()]
                    else:
                        rgba = None
                    pin_inputs.append({"name": pin.name, "color": rgba})
                for i, pin in enumerate(node.outputs):
                    col = getattr(pin, "color", None)
                    if isinstance(col, QColor):
                        rgba = [col.red(), col.green(), col.blue(), col.alpha()]
                    else:
                        rgba = None
                    pin_outputs.append({"name": pin.name, "color": rgba})
            node_data["pin_inputs"] = pin_inputs
            node_data["pin_outputs"] = pin_outputs
            data["nodes"].append(node_data)

        visited_wires = set()

        def _match_wire(from_node_id, from_pin_idx, to_node_id, to_pin_idx):
            for w in wire_items:
                a_node = w.start_port.pin.node.id
                a_idx = w.start_port.pin.index
                b_node = w.end_port.pin.node.id if w.end_port else None
                b_idx = w.end_port.pin.index if w.end_port else None
                if a_node == from_node_id and a_idx == from_pin_idx and b_node == to_node_id and b_idx == to_pin_idx:
                    return w
            return None

        for node in circuit.nodes:
            for pin in node.inputs:
                for connected_pin in pin.connections:
                    wire_key = tuple(sorted([pin.id, connected_pin.id]))
                    if wire_key not in visited_wires:
                        visited_wires.add(wire_key)
                        entry = {
                            "from_node": connected_pin.node.id,
                            "from_pin": connected_pin.index,
                            "to_node": pin.node.id,
                            "to_pin": pin.index,
                        }
                        w = _match_wire(connected_pin.node.id, connected_pin.index, pin.node.id, pin.index)
                        if w and w.control_points:
                            entry["points"] = [(p.x(), p.y()) for p in w.control_points]
                        data["wires"].append(entry)

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
            elif cls_name == "XorGate":
                from src.model.gates import XorGate
                node = XorGate()
            elif cls_name == "NandGate":
                from src.model.gates import NandGate
                node = NandGate()
            elif cls_name == "NorGate":
                from src.model.gates import NorGate
                node = NorGate()
            elif cls_name == "SevenSegmentDisplay":
                from src.model.gates import SevenSegmentDisplay
                node = SevenSegmentDisplay()
            elif cls_name == "SevenSegmentDecoder":
                from src.model.gates import SevenSegmentDecoder
                node = SevenSegmentDecoder()
            elif cls_name == "TriStateBuffer":
                from src.model.gates import TriStateBuffer
                node = TriStateBuffer()
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
                # Apply pin names and colors before creating graphics items
                pin_inputs = node_data.get("pin_inputs", [])
                pin_outputs = node_data.get("pin_outputs", [])
                for i, info in enumerate(pin_inputs):
                    if i < len(node.inputs):
                        nm = info.get("name")
                        if isinstance(nm, str):
                            node.inputs[i].name = nm
                        col = info.get("color")
                        if isinstance(col, (list, tuple)) and len(col) == 4:
                            try:
                                node.inputs[i].color = QColor(int(col[0]), int(col[1]), int(col[2]), int(col[3]))
                            except Exception:
                                pass
                for i, info in enumerate(pin_outputs):
                    if i < len(node.outputs):
                        nm = info.get("name")
                        if isinstance(nm, str):
                            node.outputs[i].name = nm
                        col = info.get("color")
                        if isinstance(col, (list, tuple)) and len(col) == 4:
                            try:
                                node.outputs[i].color = QColor(int(col[0]), int(col[1]), int(col[2]), int(col[3]))
                            except Exception:
                                pass

                circuit.add_node(node)
                id_node_map[old_id] = node

                item = GateItem(node)
                item.setPos(node_data["x"], node_data["y"])
                # Apply persisted body color if present
                body = node_data.get("body_color")
                if isinstance(body, (list, tuple)) and len(body) == 4:
                    try:
                        bc = QColor(int(body[0]), int(body[1]), int(body[2]), int(body[3]))
                        item.body_color = bc
                        item.setBrush(bc)
                    except Exception:
                        pass
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
                    pts = wire_data.get("points", [])
                    if pts:
                        wire_item.control_points = [QPointF(x, y) for (x, y) in pts]
                        wire_item.update_geometry()
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

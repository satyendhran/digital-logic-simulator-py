from typing import Any, Dict

from src.model.node import LogicState, Node


class CustomGate(Node):
    def __init__(self, name: str, internal_data: Dict[str, Any]):
        super().__init__(name)
        self.source_chip_name = name
        self.internal_data = internal_data

        for inp_name in internal_data.get("input_names", []):
            self.add_input()

        for out_name in internal_data.get("output_names", []):
            self.add_output()

        from src.graphics.scene import LogicScene
        from src.model.circuit import Circuit
        from src.model.serializer import CircuitSerializer

        self.internal_circuit = Circuit()

        dummy_scene = LogicScene()
        CircuitSerializer.deserialize(internal_data, self.internal_circuit, dummy_scene)

        self.input_nodes = []
        self.output_nodes = []

        all_inputs = [
            n for n in self.internal_circuit.nodes if isinstance(n, InputSwitch)
        ]
        all_outputs = [
            n for n in self.internal_circuit.nodes if isinstance(n, OutputBulb)
        ]

        all_inputs.sort(key=lambda n: n.name)
        all_outputs.sort(key=lambda n: n.name)

        self.input_nodes = all_inputs
        self.output_nodes = all_outputs

        if len(self.input_nodes) != len(self.inputs):
            print(f"Warning: CustomGate {name} input count mismatch")

        if len(self.output_nodes) != len(self.outputs):
            print(f"Warning: CustomGate {name} output count mismatch")

    def compute(self):
        for i, pin in enumerate(self.inputs):
            if i < len(self.input_nodes):
                val = pin.value
                switch = self.input_nodes[i]
                switch.state = val

        max_steps = 100
        for _ in range(max_steps):
            changes = False
            for node in self.internal_circuit.nodes:
                old_outs = [p.value for p in node.outputs]
                node.compute()
                for idx, p in enumerate(node.outputs):
                    if p.value != old_outs[idx]:
                        changes = True

                        for conn in p.connections:
                            conn.set_value(p.value)
            if not changes:
                break

        for i, bulb in enumerate(self.output_nodes):
            if i < len(self.outputs):
                if bulb.inputs and bulb.inputs[0].value == LogicState.HIGH:
                    self.outputs[i].set_value(LogicState.HIGH)
                else:
                    self.outputs[i].set_value(LogicState.LOW)


class AndGate(Node):
    def __init__(self):
        super().__init__("AND")
        self.add_input()
        self.add_input()
        self.add_output()

    def compute(self):
        all_high = True
        for pin in self.inputs:
            if pin.value == LogicState.UNDEFINED:
                self.outputs[0].set_value(LogicState.LOW)

            if pin.value == LogicState.LOW:
                all_high = False

        result = LogicState.HIGH if all_high else LogicState.LOW

        self.outputs[0].set_value(result)


class OrGate(Node):
    def __init__(self):
        super().__init__("OR")
        self.add_input()
        self.add_input()
        self.add_output()

    def compute(self):
        any_high = False
        for pin in self.inputs:
            if pin.value == LogicState.HIGH:
                any_high = True
            elif pin.value == LogicState.UNDEFINED:
                self.outputs[0].set_value(LogicState.LOW)

        result = LogicState.HIGH if any_high else LogicState.LOW
        self.outputs[0].set_value(result)


class NotGate(Node):
    def __init__(self):
        super().__init__("NOT")
        self.add_input()
        self.add_output()

    def compute(self):
        inp = self.inputs[0].value
        if inp == LogicState.HIGH:
            self.outputs[0].set_value(LogicState.LOW)
        elif inp == LogicState.LOW:
            self.outputs[0].set_value(LogicState.HIGH)
        else:
            self.outputs[0].set_value(LogicState.HIGH)


class InputSwitch(Node):
    def __init__(self):
        super().__init__("Input")
        self.add_output()
        self.state = LogicState.LOW
        self.outputs[0].set_value(self.state)

    def toggle(self):
        if self.state == LogicState.LOW:
            self.state = LogicState.HIGH
        else:
            self.state = LogicState.LOW

    def compute(self):
        self.outputs[0].set_value(self.state)


class OutputBulb(Node):
    def __init__(self):
        super().__init__("Output")
        self.add_input()
        self.active = False

    def compute(self):
        self.active = self.inputs[0].value == LogicState.HIGH

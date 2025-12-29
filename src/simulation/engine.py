import queue
import threading
import time

from src.model.circuit import Circuit
from src.model.node import Node, PinType


class SimulationEngine:
    def __init__(self, circuit: Circuit):
        self.circuit = circuit
        self.event_queue = queue.PriorityQueue()
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.simulation_time = 0
        self.sequence = 0
        self.stop_event = threading.Event()

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()
        if self.thread:
            self.thread.join()

    def queue_update(self, node: Node, delay: int = 0):
        """Schedule a node update."""
        with self.lock:
            self.sequence += 1
            self.event_queue.put((self.simulation_time + delay, self.sequence, node))

    def run(self):
        while self.running and not self.stop_event.is_set():
            try:
                if self.event_queue.empty():
                    time.sleep(0.01)
                    continue

                with self.lock:
                    target_time, _, node = self.event_queue.get_nowait()

                self.simulation_time = max(self.simulation_time, target_time)

                old_outputs = [p.value for p in node.outputs]
                node.compute()

                for i, out_pin in enumerate(node.outputs):
                    if out_pin.value != old_outputs[i]:
                        for conn in out_pin.connections:
                            conn.set_value(out_pin.value)

                            if conn.type == PinType.INPUT:
                                self.queue_update(conn.node, delay=1)

            except queue.Empty:
                pass
            except Exception as e:
                print(f"Simulation Error: {e}")

    def trigger_update(self, node: Node):
        """Manually trigger an update (e.g. from UI click)."""
        self.queue_update(node)

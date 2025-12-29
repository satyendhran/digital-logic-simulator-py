from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem

from src.constants import *
from src.graphics.items.port import PortItem
from src.model.node import LogicState


class WireItem(QGraphicsPathItem):
    def __init__(self, start_port: PortItem, end_port: PortItem = None):
        super().__init__()
        self.start_port = start_port
        self.end_port = end_port

        self.setZValue(Z_VAL_WIRE)
        self.setFlags(QGraphicsItem.ItemIsSelectable)

        self.start_port.wires.append(self)
        if self.end_port:
            self.end_port.wires.append(self)

        self.current_state = LogicState.UNDEFINED
        self.update_geometry()

    def set_end_pos(self, pos: QPointF):
        self.end_pos = pos
        self.update_geometry(use_end_pos=True)

    def update_geometry(self, use_end_pos=False):
        start_pos = self.start_port.get_scene_pos()
        if use_end_pos:
            end_pos = self.end_pos
        elif self.end_port:
            end_pos = self.end_port.get_scene_pos()
        else:
            return

        path = QPainterPath()
        path.moveTo(start_pos)

        mid_x = (start_pos.x() + end_pos.x()) / 2
        path.lineTo(mid_x, start_pos.y())
        path.lineTo(mid_x, end_pos.y())
        path.lineTo(end_pos)

        self.setPath(path)
        self._update_color()

    def _update_color(self):
        color = WIRE_COLOR_UNDEFINED
        if self.isSelected():
            color = WIRE_COLOR_SELECTED
        else:
            state = self.start_port.pin.value
            if state == LogicState.HIGH:
                color = WIRE_COLOR_ON
            elif state == LogicState.LOW:
                color = WIRE_COLOR_OFF
            elif state == LogicState.UNDEFINED:
                color = WIRE_COLOR_UNDEFINED

        self.setPen(QPen(color, WIRE_WIDTH))

    def paint(self, painter, option, widget):
        self._update_color()
        super().paint(painter, option, widget)

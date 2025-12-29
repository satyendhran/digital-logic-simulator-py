from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem

from src.constants import *
from src.model.node import Pin


class PortItem(QGraphicsPathItem):
    def __init__(self, pin: Pin, parent: QGraphicsItem):
        super().__init__(parent)
        self.pin = pin
        self.radius = PORT_SIZE / 2
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)

        path = QPainterPath()
        path.addEllipse(-self.radius, -self.radius, PORT_SIZE, PORT_SIZE)
        self.setPath(path)

        self.setBrush(QBrush(PORT_COLOR))
        self.setPen(QPen(Qt.NoPen))
        self.setZValue(Z_VAL_PORT)

        self.hovered = False

        self.wires = []

    def hoverEnterEvent(self, event):
        self.hovered = True
        self.setBrush(QBrush(PORT_HOVER_COLOR))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hovered = False
        self.setBrush(QBrush(PORT_COLOR))
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            for wire in self.wires:
                wire.update_geometry()
        return super().itemChange(change, value)

    def get_scene_pos(self):
        return self.mapToScene(0, 0)

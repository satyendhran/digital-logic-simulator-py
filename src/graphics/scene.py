from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen, QTransform
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent

from src.constants import *
from src.graphics.items.port import PortItem
from src.graphics.items.wire import WireItem


class LogicScene(QGraphicsScene):
    wire_connected = Signal(object, object)
    node_triggered = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_size = GRID_SIZE
        self.setBackgroundBrush(BACKGROUND_COLOR)
        self.setItemIndexMethod(QGraphicsScene.NoIndex)

        self.mode = "Select"
        self.temp_wire = None
        self.start_port = None

    def set_mode(self, mode):
        self.mode = mode

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if self.mode == "Wire":
            if event.button() == Qt.LeftButton:
                item = self.itemAt(event.scenePos(), QTransform())
                if isinstance(item, PortItem):
                    self.start_port = item
                    self.temp_wire = WireItem(item)
                    self.addItem(self.temp_wire)
                    self.temp_wire.set_end_pos(event.scenePos())
                    return

        if self.mode == "Select" and event.button() == Qt.LeftButton:
            pass

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self.mode == "Wire" and self.temp_wire:
            pos = self.snap_to_grid(event.scenePos())
            self.temp_wire.set_end_pos(pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.mode == "Wire" and self.temp_wire:
            item = self.itemAt(event.scenePos(), QTransform())
            if isinstance(item, PortItem) and item != self.start_port:
                self.wire_connected.emit(self.start_port, item)

                self.temp_wire.end_port = item
                self.temp_wire.update_geometry()
                self.temp_wire = None
                self.start_port = None
            else:
                self.removeItem(self.temp_wire)
                self.temp_wire = None
                self.start_port = None
        super().mouseReleaseEvent(event)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)

        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)

        lines_light = []
        lines_dark = []

        x = left
        while x < rect.right():
            if x % (self.grid_size * 5) == 0:
                lines_dark.append(QLineF(x, rect.top(), x, rect.bottom()))
            else:
                lines_light.append(QLineF(x, rect.top(), x, rect.bottom()))
            x += self.grid_size

        y = top
        while y < rect.bottom():
            if y % (self.grid_size * 5) == 0:
                lines_dark.append(QLineF(rect.left(), y, rect.right(), y))
            else:
                lines_light.append(QLineF(rect.left(), y, rect.right(), y))
            y += self.grid_size

        painter.setPen(QPen(GRID_COLOR_LIGHT, 0.5))
        painter.drawLines(lines_light)

        painter.setPen(QPen(GRID_COLOR_DARK, 1.0))
        painter.drawLines(lines_dark)

    def snap_to_grid(self, pos: QPointF) -> QPointF:
        x = round(pos.x() / self.grid_size) * self.grid_size
        y = round(pos.y() / self.grid_size) * self.grid_size
        return QPointF(x, y)

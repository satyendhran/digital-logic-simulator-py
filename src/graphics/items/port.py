from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPainterPath, QPen, QColor
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem

from src.constants import *
from src.model.node import Pin, LogicState


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

        self.base_color = getattr(self.pin, "color", None) or SIGNAL_HIGH_COLOR
        self._current_color = QColor(SIGNAL_UNDEFINED_COLOR)
        self.setBrush(QBrush(self._current_color))
        self.setPen(QPen(Qt.NoPen))
        self.setZValue(Z_VAL_PORT)

        self.hovered = False

        self.wires = []

    def hoverEnterEvent(self, event):
        self.hovered = True
        self.setBrush(QBrush(PORT_HOVER_COLOR))
        state = self.pin.value.name if hasattr(self.pin.value, "name") else str(self.pin.value)
        ptype = "Input" if self.pin.type.name == "INPUT" else "Output"
        self.setToolTip(f"{ptype} pin\nName: {self.pin.name}\nState: {state}")
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hovered = False
        self.setBrush(QBrush(self._current_color))
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            for wire in self.wires:
                wire.update_geometry()
        return super().itemChange(change, value)

    def get_scene_pos(self):
        return self.mapToScene(0, 0)

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu, QInputDialog, QColorDialog
        menu = QMenu()
        rename_act = menu.addAction("Rename Pin")
        color_act = menu.addAction("Change Color")
        chosen = menu.exec_(event.screenPos())
        if chosen == rename_act:
            text, ok = QInputDialog.getText(None, "Rename Pin", "New pin label:")
            if ok and text:
                self.pin.name = text
                state = self.pin.value.name if hasattr(self.pin.value, "name") else str(self.pin.value)
                self.setToolTip(f"Pin: {self.pin.name}\nType: {self.pin.type.name}\nState: {state}")
        elif chosen == color_act:
            col = QColorDialog.getColor(self.base_color, None, "Pin Color")
            if col.isValid():
                self.base_color = col
                self.pin.color = col

    def paint(self, painter, option, widget):
        target = SIGNAL_UNDEFINED_COLOR
        if self.pin.value == LogicState.HIGH:
            target = self.base_color
        elif self.pin.value == LogicState.LOW:
            target = SIGNAL_LOW_COLOR

        scene = self.scene()
        dt = scene.get_frame_ms() if scene and hasattr(scene, "get_frame_ms") else 16.0
        t = max(0.0, min(1.0, dt / 120.0))
        self._current_color.setRed(int(self._current_color.red() + (target.red() - self._current_color.red()) * t))
        self._current_color.setGreen(int(self._current_color.green() + (target.green() - self._current_color.green()) * t))
        self._current_color.setBlue(int(self._current_color.blue() + (target.blue() - self._current_color.blue()) * t))
        self._current_color.setAlpha(255)

        if self.hovered:
            self.setBrush(QBrush(PORT_HOVER_COLOR))
        else:
            self.setBrush(QBrush(self._current_color))

        if self.pin.value == LogicState.HIGH:
            painter.save()
            painter.setPen(Qt.NoPen)
            pulse = scene.get_pulse() if scene and hasattr(scene, "get_pulse") else 0.5
            glow = QColor(self._current_color)
            glow.setAlpha(int(100 + 100 * pulse))
            r = self.radius + 4 + int(3 * pulse)
            painter.setBrush(glow)
            painter.drawEllipse(-r, -r, r * 2, r * 2)
            painter.restore()
        super().paint(painter, option, widget)

    def set_port_size(self, size: int):
        self.radius = size / 2
        path = QPainterPath()
        path.addEllipse(-self.radius, -self.radius, size, size)
        self.setPath(path)

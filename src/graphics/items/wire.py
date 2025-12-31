from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainterPath, QPen, QColor
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                               QGraphicsPathItem)

from src.constants import *
from src.graphics.items.port import PortItem
from src.model.node import LogicState


class WireItem(QGraphicsPathItem):
    def __init__(self, start_port: PortItem, end_port: PortItem = None):
        super().__init__()
        self.start_port = start_port
        self.end_port = end_port
        self.control_points = []
        self.handles = []
        self.end_pos = None
        self.preview_valid = False
        self._current_color = QColor(WIRE_COLOR_UNDEFINED)

        self.setZValue(Z_VAL_WIRE)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)

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

        points = [start_pos] + self.control_points + [end_pos]
        for p in points[1:]:
            path.lineTo(p)

        self.setPath(path)
        self._update_color()
        self._refresh_handles()

    def _update_color(self):
        target = SIGNAL_UNDEFINED_COLOR
        if self.isSelected():
            target = WIRE_COLOR_SELECTED
        else:
            # Use the source (OUTPUT) pin value for coloring
            src_pin = self.start_port.pin
            if self.end_port and self.end_port.pin.type.name == "OUTPUT":
                src_pin = self.end_port.pin
            state = src_pin.value
            if state == LogicState.HIGH:
                target = SIGNAL_HIGH_COLOR
            elif state == LogicState.LOW:
                target = SIGNAL_LOW_COLOR
            elif state == LogicState.UNDEFINED:
                target = SIGNAL_UNDEFINED_COLOR

        scene = self.scene()
        dt = scene.get_frame_ms() if scene and hasattr(scene, "get_frame_ms") else 16.0
        t = max(0.0, min(1.0, dt / 140.0))
        self._current_color.setRed(int(self._current_color.red() + (target.red() - self._current_color.red()) * t))
        self._current_color.setGreen(int(self._current_color.green() + (target.green() - self._current_color.green()) * t))
        self._current_color.setBlue(int(self._current_color.blue() + (target.blue() - self._current_color.blue()) * t))
        self._current_color.setAlpha(255)

        pen = QPen(self._current_color, WIRE_WIDTH)
        if self.end_port is None:
            if self.preview_valid:
                pen.setStyle(Qt.SolidLine)
            else:
                pen.setStyle(Qt.DashLine)
        self.setPen(pen)

    def paint(self, painter, option, widget):
        self._update_color()
        super().paint(painter, option, widget)
        # Draw glow and directional arrow based on source pin value
        # Determine source (OUTPUT) and destination (INPUT) ports to orient arrow correctly
        src_port = self.start_port
        dst_port = self.end_port if self.end_port else None
        if self.end_port:
            if self.start_port.pin.type.name == "INPUT" and self.end_port.pin.type.name == "OUTPUT":
                src_port = self.end_port
                dst_port = self.start_port
        src_val = src_port.pin.value if src_port else LogicState.UNDEFINED
        if src_val == LogicState.HIGH:
            scene = self.scene()
            pulse = scene.get_pulse() if scene and hasattr(scene, "get_pulse") else 0.5
            glow = QPen(self._current_color)
            a = int(80 + 100 * pulse)
            c = glow.color()
            c.setAlpha(a)
            glow.setColor(c)
            glow.setWidth(WIRE_WIDTH + 2)
            painter.setPen(glow)
            painter.drawPath(self.path())

    def add_control_point(self, pos: QPointF):
        snapped = self._snap_to_grid(pos)
        self.control_points.append(snapped)
        self.update_geometry(use_end_pos=self.end_pos is not None)

    def mouseDoubleClickEvent(self, event):
        self.add_control_point(event.scenePos())
        event.accept()
        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self._refresh_handles(force=True)
        return super().itemChange(change, value)

    def _refresh_handles(self, force=False):
        selected = self.isSelected()
        if not selected and not force:
            return

        for h in self.handles:
            if h.scene():
                h.scene().removeItem(h)
        self.handles.clear()

        if not selected or not self.control_points:
            return

        for idx, pt in enumerate(self.control_points):
            handle = _ControlHandle(self, idx, pt)
            self.handles.append(handle)
            if self.scene():
                self.scene().addItem(handle)

    def _snap_to_grid(self, pos: QPointF) -> QPointF:
        scene = self.scene()
        if not scene or not hasattr(scene, "grid_size"):
            return pos
        grid = getattr(scene, "wire_grid_size", scene.grid_size)
        x = round(pos.x() / grid) * grid
        y = round(pos.y() / grid) * grid
        return QPointF(x, y)

    def set_preview_valid(self, valid: bool):
        self.preview_valid = valid
        self.update()


class _ControlHandle(QGraphicsEllipseItem):
    def __init__(self, wire: WireItem, index: int, scene_pos: QPointF):
        size = max(4, int(PORT_SIZE / 3))
        super().__init__(-size / 2, -size / 2, size, size)
        self.wire = wire
        self.index = index
        self.setZValue(wire.zValue() + 0.1)
        self.setBrush(Qt.white)
        self.setPen(QPen(Qt.black, 1))
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsScenePositionChanges
        )
        self.setPos(scene_pos)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            snapped = self.wire._snap_to_grid(self.scenePos())
            self.wire.control_points[self.index] = snapped
            self.wire.update_geometry(use_end_pos=self.wire.end_pos is not None)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        if 0 <= self.index < len(self.wire.control_points):
            del self.wire.control_points[self.index]
            self.wire.update_geometry(use_end_pos=self.wire.end_pos is not None)
            if self.scene():
                self.scene().removeItem(self)
        event.accept()
        super().mouseDoubleClickEvent(event)

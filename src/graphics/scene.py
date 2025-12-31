from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QKeyEvent, QPainter, QPen, QTransform, QPolygonF, QColor
import math
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent

from src.constants import *
from src.graphics.items.port import PortItem
from src.graphics.items.wire import WireItem


class LogicScene(QGraphicsScene):
    wire_connected = Signal(object, object, object)
    node_triggered = Signal(object)
    mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_size = GRID_SIZE
        self.wire_grid_size = WIRE_GRID_SIZE
        self.setBackgroundBrush(BACKGROUND_COLOR)
        self.setItemIndexMethod(QGraphicsScene.NoIndex)

        self.mode = "Select"
        self.temp_wire = None
        self.start_port = None
        self.hover_port = None
        self.active_draw = False
        self.overlay_enabled = True
        self._fps = 0.0
        self._frame_ms = 0.0
        self._time_ms = 0.0

    def set_mode(self, mode):
        self.mode = mode
        self.mode_changed.emit(mode)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.LeftButton:
            raw_pos = event.scenePos()
            pos = self.wire_snap_to_grid(raw_pos)
            item = self._find_port_near(raw_pos)
            if isinstance(item, PortItem):
                if not self.active_draw:
                    if self.mode != "Wire":
                        self.set_mode("Wire")
                    self.start_port = item
                    self.temp_wire = WireItem(item)
                    self.addItem(self.temp_wire)
                    self.temp_wire.set_end_pos(pos)
                    self.active_draw = True
                    return
                else:
                    if self._is_valid_endpoint(item):
                        control_points = list(self.temp_wire.control_points)
                        self.removeItem(self.temp_wire)
                        self.wire_connected.emit(self.start_port, item, control_points)
                        self._reset_draw_state()
                        self.set_mode("Select")
                        return
            else:
                if self.mode == "Wire" and self.active_draw and self.temp_wire:
                    snapped = self._orthogonal_snap(self._current_anchor(), pos)
                    self.temp_wire.add_control_point(snapped)
                    self.temp_wire.set_end_pos(snapped)
                    return

        if self.mode == "Select" and event.button() == Qt.LeftButton:
            pass

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self.mode == "Wire" and self.temp_wire and self.active_draw:
            raw_pos = event.scenePos()
            pos = self.wire_snap_to_grid(raw_pos)
            snapped = self._orthogonal_snap(self._current_anchor(), pos)
            self.temp_wire.set_end_pos(snapped)
            item = self._find_port_near(raw_pos)
            self.hover_port = item if isinstance(item, PortItem) else None
            if self.hover_port and self._is_valid_endpoint(self.hover_port):
                self.temp_wire.set_preview_valid(True)
            else:
                self.temp_wire.set_preview_valid(False)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        super().mouseReleaseEvent(event)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)

        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)

        dots_minor = []
        dots_major = []
        scale = 1.0
        try:
            views = self.views()
            if views:
                t = views[0].transform()
                scale = max(0.1, t.m11())
        except Exception:
            scale = 1.0

        step = self.grid_size
        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                if (x // step) % 5 == 0 and (y // step) % 5 == 0:
                    dots_major.append(QPointF(x, y))
                else:
                    dots_minor.append(QPointF(x, y))
                y += step
            x += step

        c_light = GRID_COLOR_LIGHT
        c_dark = GRID_COLOR_DARK
        cl = QColor(c_light)
        cd = QColor(c_dark)
        fade = max(0.12, min(1.0, scale))
        cl.setAlphaF(fade)
        cd.setAlphaF(min(1.0, fade * 1.2))
        painter.setPen(QPen(cl, 0))
        if dots_minor:
            painter.setBrush(cl)
            painter.drawPoints(QPolygonF(dots_minor))
        painter.setPen(QPen(cd, 0))
        if dots_major:
            painter.setBrush(cd)
            painter.drawPoints(QPolygonF(dots_major))

        # Performance overlay
        if self.overlay_enabled:
            painter.save()
            painter.setRenderHint(QPainter.TextAntialiasing, True)
            painter.setPen(Qt.NoPen)
            painter.setBrush(OVERLAY_BG)
            panel_rect = QRectF(rect.right() - 220, rect.top() + 10, 210, 80)
            painter.drawRoundedRect(panel_rect, 6, 6)
            painter.setPen(QPen(OVERLAY_TEXT))
            nodes = len(getattr(self.parent(), "circuit", None).nodes) if getattr(self.parent(), "circuit", None) else 0
            lines = [
                f"FPS: {self._fps:.1f}",
                f"Frame: {self._frame_ms:.2f} ms",
                f"Nodes: {nodes}",
            ]
            x = panel_rect.x() + 10
            y = panel_rect.y() + 22
            for s in lines:
                painter.drawText(QPointF(x, y), s)
                y += 20
            painter.restore()

    def snap_to_grid(self, pos: QPointF) -> QPointF:
        x = round(pos.x() / self.grid_size) * self.grid_size
        y = round(pos.y() / self.grid_size) * self.grid_size
        return QPointF(x, y)

    def wire_snap_to_grid(self, pos: QPointF) -> QPointF:
        x = round(pos.x() / self.wire_grid_size) * self.wire_grid_size
        y = round(pos.y() / self.wire_grid_size) * self.wire_grid_size
        return QPointF(x, y)

    def keyPressEvent(self, event: QKeyEvent):
        if self.mode == "Wire" and self.active_draw and self.temp_wire:
            if event.key() in (Qt.Key_Escape,):
                self.removeItem(self.temp_wire)
                self._reset_draw_state()
                self.set_mode("Select")
                event.accept()
                return
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if self.hover_port and self._is_valid_endpoint(self.hover_port):
                    control_points = list(self.temp_wire.control_points)
                    self.removeItem(self.temp_wire)
                    self.wire_connected.emit(self.start_port, self.hover_port, control_points)
                else:
                    self.removeItem(self.temp_wire)
                self._reset_draw_state()
                self.set_mode("Select")
                event.accept()
                return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        if self.mode == "Wire" and self.active_draw and self.temp_wire:
            self.removeItem(self.temp_wire)
            self._reset_draw_state()
            self.set_mode("Select")
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _reset_draw_state(self):
        self.temp_wire = None
        self.start_port = None
        self.hover_port = None
        self.active_draw = False

    def _current_anchor(self) -> QPointF:
        if self.temp_wire and self.temp_wire.control_points:
            return self.temp_wire.control_points[-1]
        if self.start_port:
            return self.start_port.get_scene_pos()
        return QPointF(0, 0)

    def _orthogonal_snap(self, anchor: QPointF, pos: QPointF) -> QPointF:
        dx = abs(pos.x() - anchor.x())
        dy = abs(pos.y() - anchor.y())
        if dx > dy:
            return QPointF(pos.x(), anchor.y())
        else:
            return QPointF(anchor.x(), pos.y())

    def _is_valid_endpoint(self, port: PortItem) -> bool:
        if not self.start_port or not port or port == self.start_port:
            return False
        a = self.start_port.pin
        b = port.pin
        return a.node != b.node and a.type != b.type

    def _find_port_near(self, pos: QPointF, radius: float = 8.0):
        rect = QRectF(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2)
        candidates = [it for it in self.items(rect) if isinstance(it, PortItem)]
        if not candidates:
            return None
        best = None
        best_d = None
        for it in candidates:
            sp = it.get_scene_pos()
            d = (sp.x() - pos.x()) ** 2 + (sp.y() - pos.y()) ** 2
            if best is None or d < best_d:
                best = it
                best_d = d
        return best

    def update_metrics(self, frame_ms: float, fps: float):
        self._frame_ms = frame_ms
        self._fps = fps
        self._time_ms += frame_ms

    def get_pulse(self) -> float:
        return 0.5 + 0.5 * math.sin(self._time_ms * 0.01)

    def get_frame_ms(self) -> float:
        return self._frame_ms

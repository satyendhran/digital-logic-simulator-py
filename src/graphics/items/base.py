from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QFont, QPen
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsRectItem,
                               QGraphicsTextItem, QMenu, QInputDialog,
                               QColorDialog, QGraphicsDropShadowEffect)

from src.constants import *
from src.graphics.items.port import PortItem
from src.model.gates import SevenSegmentDisplay, InputSwitch, OutputBulb
from src.model.node import LogicState, Node




class GateItem(QGraphicsRectItem):
    def __init__(self, node: Node):
        super().__init__()
        self.node = node
        self.width = 60
        self.height = 60
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)

        self.body_color = GATE_BODY_COLOR
        self.setBrush(QBrush(self.body_color))
        self.setPen(QPen(GATE_BORDER_COLOR, 2))
        self.setZValue(Z_VAL_GATE)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(Qt.black)
        self.setGraphicsEffect(shadow)

        self.label = QGraphicsTextItem(node.name, self)
        self.label.setDefaultTextColor(Qt.white)
        font = QFont("Segoe UI", 10, QFont.Bold)
        self.label.setFont(font)
        if not SHOW_DISPLAY_LABELS and isinstance(node, (InputSwitch, OutputBulb, SevenSegmentDisplay)):
            self.label.setVisible(False)

        self.input_ports = []
        self.output_ports = []
        self._create_ports()
        self._layout()

    def _create_ports(self):
        for pin in self.node.inputs:
            port = PortItem(pin, self)
            self.input_ports.append(port)

        for pin in self.node.outputs:
            port = PortItem(pin, self)
            self.output_ports.append(port)

    def _layout(self):
        max_ports = max(len(self.input_ports), len(self.output_ports))
        self.height = max(40, max_ports * 20 + 20)

        self.setRect(0, 0, self.width, self.height)

        brect = self.label.boundingRect()
        self.label.setPos(
            (self.width - brect.width()) / 2, (self.height - brect.height()) / 2
        )

        y_step = self.height / (len(self.input_ports) + 1)
        for i, port in enumerate(self.input_ports):
            port.setPos(0, y_step * (i + 1))

        y_step = self.height / (len(self.output_ports) + 1)
        for i, port in enumerate(self.output_ports):
            port.setPos(self.width, y_step * (i + 1))

    def mouseDoubleClickEvent(self, event):
        if hasattr(self.node, "toggle"):
            self.node.toggle()

            self.scene().node_triggered.emit(self.node)
            self.update()
        super().mouseDoubleClickEvent(event)

    def paint(self, painter, option, widget):
        if isinstance(self.node, (InputSwitch, OutputBulb)):
            painter.save()
            painter.setPen(Qt.NoPen)
            if isinstance(self.node, InputSwitch):
                color = Qt.green if self.node.state == LogicState.HIGH else Qt.red
                painter.setBrush(QBrush(color))
            else:
                v = self.node.inputs[0].value if self.node.inputs else LogicState.UNDEFINED
                if v == LogicState.HIGH:
                    painter.setBrush(QBrush(Qt.yellow))
                elif v == LogicState.LOW:
                    painter.setBrush(QBrush(Qt.black))
                else:
                    painter.setBrush(QBrush(QColor(90, 90, 90)))
            r = min(self.width, self.height) - 20
            r = max(16, int(r))
            cx = self.width / 2
            cy = self.height / 2
            painter.drawEllipse(QPointF(cx, cy), r / 2, r / 2)
            painter.restore()
            if self.isSelected():
                scene = self.scene()
                pulse = scene.get_pulse() if scene and hasattr(scene, "get_pulse") else 0.5
                sel = QPen(GATE_SELECTED_COLOR, 2 + pulse * 2)
                painter.setPen(sel)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(cx, cy), r / 2 + 2, r / 2 + 2)
            return
        else:
            if self.isSelected():
                self.setPen(QPen(GATE_SELECTED_COLOR, 2))
            else:
                self.setPen(QPen(GATE_BORDER_COLOR, 2))
            super().paint(painter, option, widget)

        if isinstance(self.node, SevenSegmentDisplay):
            seg_w = self.width - 16
            seg_h = self.height - 16
            base_x = 8
            base_y = 8
            segs = []
            segs.append(QRectF(base_x + 10, base_y, seg_w - 20, 6))  # A top
            segs.append(QRectF(base_x + seg_w - 6, base_y + 10, 6, seg_h / 2 - 20))  # B upper-right
            segs.append(QRectF(base_x + seg_w - 6, base_y + seg_h / 2 + 10, 6, seg_h / 2 - 20))  # C lower-right
            segs.append(QRectF(base_x + 10, base_y + seg_h / 2 - 3, seg_w - 20, 6))  # D middle
            segs.append(QRectF(base_x, base_y + seg_h / 2 + 10, 6, seg_h / 2 - 20))  # E lower-left
            segs.append(QRectF(base_x, base_y + 10, 6, seg_h / 2 - 20))  # F upper-left
            segs.append(QRectF(base_x + 10, base_y + seg_h - 6, seg_w - 20, 6))  # G bottom
            painter.setPen(Qt.NoPen)
            for i, rect in enumerate(segs):
                val = self.node.inputs[i].value if i < len(self.node.inputs) else LogicState.LOW
                painter.setBrush(QBrush(SEGMENT_ON_COLOR if val == LogicState.HIGH else SEGMENT_OFF_COLOR))
                painter.drawRoundedRect(rect, 2, 2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_pos = value
            grid_size = GRID_SIZE
            x = round(new_pos.x() / grid_size) * grid_size
            y = round(new_pos.y() / grid_size) * grid_size
            return QPointF(x, y)
        return super().itemChange(change, value)

    def contextMenuEvent(self, event):
        menu = QMenu()
        rename_act = menu.addAction("Rename")
        color_act = menu.addAction("Change Color")
        chosen = menu.exec_(event.screenPos())
        if chosen == rename_act:
            text, ok = QInputDialog.getText(None, "Rename Component", "New name:", text=self.node.name)
            if ok and text:
                self.node.name = text
                self.label.setPlainText(text)
        elif chosen == color_act:
            col = QColorDialog.getColor(self.body_color, None, "Component Color")
            if col.isValid():
                self.body_color = col
                self.setBrush(QBrush(self.body_color))

from PySide6.QtCore import Qt, QSize, QTimer, QPointF, QRectF
from PySide6.QtGui import QMouseEvent, QPainter, QSurfaceFormat, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView
from time import perf_counter
from src.constants import DEFAULT_FPS_CAP
from src.graphics.items.base import GateItem
from src.model.gates import OutputBulb


class LogicView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)

        try:
            fmt = QSurfaceFormat()
            fmt.setSamples(4)
            self.setViewport(QOpenGLWidget())
            self.viewport().setFormat(fmt)
            print("OpenGL Activated")
        except Exception as e:
            print(f"OpenGL acceleration failed, falling back to raster: {e}")

        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        self._zoom_factor = 1.15
        self._current_zoom = 1.0

        self._panning = False
        self._pan_start = None
        self._pan_last = None
        self._pan_vel = QPointF(0, 0)
        self._pan_inertia = QTimer(self)
        self._pan_inertia.timeout.connect(self._tick_inertia)
        self._renderer_backend = "GPU"
        self._last_paint = perf_counter()
        self._fps_cap = DEFAULT_FPS_CAP
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._tick_frame)
        self._update_timer_interval()
        self._frame_timer.start()

        self._target_zoom = 1.0
        self._zoom_anim = QTimer(self)
        self._zoom_anim.timeout.connect(self._tick_zoom)
        self._zoom_anchor_pos = None
        self.setOptimizationFlags(
            QGraphicsView.DontSavePainterState | QGraphicsView.DontAdjustForAntialiasing
        )
        # self.setCacheMode(QGraphicsView.NoCache)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.scale(self._zoom_factor, self._zoom_factor)
                self._current_zoom *= self._zoom_factor
            else:
                inv = 1.0 / self._zoom_factor
                self.scale(inv, inv)
                self._current_zoom *= inv
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def set_backend(self, backend: str):
        backend = backend.upper()
        if backend == self._renderer_backend:
            return
        if backend == "GPU":
            try:
                fmt = QSurfaceFormat()
                fmt.setSamples(4)
                self.setViewport(QOpenGLWidget())
                self.viewport().setFormat(fmt)
                self._renderer_backend = "GPU"
            except Exception as e:
                print(f"Failed to switch to GPU: {e}")
        elif backend == "CPU":
            from PySide6.QtWidgets import QWidget
            self.setViewport(QWidget())
            self._renderer_backend = "CPU"
        else:
            print(f"Unknown backend: {backend}")

    def set_fps_cap(self, fps: int):
        if fps <= 0:
            return
        self._fps_cap = fps
        self._update_timer_interval()

    def _update_timer_interval(self):
        interval_ms = int(1000 / max(1, self._fps_cap))
        self._frame_timer.setInterval(interval_ms)

    def _tick_frame(self):
        scene = self.scene()
        if scene:
            try:
                rect = scene.sceneRect()
            except Exception:
                rect = None
            if rect:
                scene.invalidate(rect, QGraphicsScene.AllLayers)
            else:
                scene.invalidate(QRectF(), QGraphicsScene.AllLayers)
            try:
                for it in scene.items():
                    if isinstance(it, GateItem) and isinstance(getattr(it, "node", None), OutputBulb):
                        br = it.sceneBoundingRect()
                        scene.invalidate(br, QGraphicsScene.ItemLayer)
                        it.update()
            except Exception:
                pass
        self.viewport().update()

    def paintEvent(self, event):
        now = perf_counter()
        dt = (now - self._last_paint) * 1000.0
        self._last_paint = now
        fps = 1000.0 / dt if dt > 0 else 0.0
        scene = self.scene()
        if hasattr(scene, "update_metrics"):
            scene.update_metrics(dt, fps)
        super().paintEvent(event)

    def _tick_inertia(self):
        vx = self._pan_vel.x()
        vy = self._pan_vel.y()
        vx *= 0.88
        vy *= 0.88
        self._pan_vel = QPointF(vx, vy)
        if abs(vx) < 0.3 and abs(vy) < 0.3:
            self._pan_inertia.stop()
            return
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(vx))
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(vy))

    def _tick_zoom(self):
        cur = self._current_zoom
        target = self._target_zoom
        if abs(target - cur) < 0.002:
            self._zoom_anim.stop()
            return
        step = (target - cur) * 0.18
        new_zoom = cur + step
        factor = new_zoom / max(0.0001, cur)
        if self._zoom_anchor_pos is not None:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            before = self.mapToScene(int(self._zoom_anchor_pos.x()), int(self._zoom_anchor_pos.y()))
            self.scale(factor, factor)
            after = self.mapToScene(int(self._zoom_anchor_pos.x()), int(self._zoom_anchor_pos.y()))
            delta = after - before
            self.translate(delta.x(), delta.y())
            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        else:
            self.scale(factor, factor)
        self._current_zoom = new_zoom

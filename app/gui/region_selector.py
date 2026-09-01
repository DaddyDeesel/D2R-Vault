"""Full-screen click/drag capture-region selector for Manual Selection mode."""
from __future__ import annotations
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

class RegionSelector(QWidget):
    region_selected = Signal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start = QPoint()
        self.end = QPoint()
        self.selected_region: dict | None = None
        screens = QGuiApplication.screens()
        geom = screens[0].geometry()
        for screen in screens[1:]:
            geom = geom.united(screen.geometry())
        self.setGeometry(geom)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start = event.position().toPoint()
            self.end = self.start
            self.update()
        elif event.button() == Qt.RightButton:
            self.close()

    def mouseMoveEvent(self, event):
        self.end = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.end = event.position().toPoint()
        rect = QRect(self.start, self.end).normalized()
        if rect.width() >= 20 and rect.height() >= 20:
            g = self.geometry()
            self.selected_region = {
                "x": rect.x() + g.x(), "y": rect.y() + g.y(),
                "width": rect.width(), "height": rect.height(),
            }
            self.region_selected.emit(self.selected_region)
        self.close()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 105))
        if not self.start.isNull() or not self.end.isNull():
            rect = QRect(self.start, self.end).normalized()
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.fillRect(rect, Qt.transparent)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.setPen(QPen(QColor("#d9b85f"), 2))
            p.drawRect(rect)

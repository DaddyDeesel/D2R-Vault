"""D2R Vault — grid-based inventory view (spec §5)."""
from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QDrag, QPainter, QColor, QMouseEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QTabWidget, QVBoxLayout, QWidget

from app.config import CONTAINERS, GRID_SIZES
from app.gui.theme import quality_color

CELL_SIZE = 40


class ItemCell(QFrame):
    """A single item's visual representation, sized to its grid footprint."""

    item_clicked = Signal(int)
    item_moved = Signal(int, int, int)  # item_id, new_x, new_y

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setFixedSize(item.width * CELL_SIZE - 2, item.height * CELL_SIZE - 2)
        color = quality_color(item.quality)
        self.setStyleSheet(
            f"QFrame {{ background-color: #26232d; border: 2px solid {color}; border-radius: 3px; }}"
            f"QFrame:hover {{ border: 2px solid #e8c874; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        label = QLabel(item.name)
        label.setStyleSheet(f"color: {color}; font-size: 10px; border: none; background: transparent;")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setToolTip(self._build_tooltip())
        self.setCursor(Qt.PointingHandCursor)

    def _build_tooltip(self) -> str:
        lines = [self.item.name]
        if self.item.base_name:
            lines.append(self.item.base_name)
        if self.item.defense:
            lines.append(f"Defense: {self.item.defense}")
        if self.item.damage_min:
            lines.append(f"Damage: {self.item.damage_min}-{self.item.damage_max}")
        for skill in (self.item.skills or []):
            lines.append(f"+{skill.get('amount')} To {skill.get('skill')}")
        lines.append(self.item.quality)
        return "\n".join(lines)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.item_clicked.emit(self.item.id)
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(str(self.item.id))
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction)
        super().mousePressEvent(event)


class GridContainer(QWidget):
    """A single container's grid (e.g. Inventory, Stash)."""

    item_clicked = Signal(int)
    item_dropped = Signal(int, int, int)  # item_id, x, y

    def __init__(self, container_name: str, parent=None):
        super().__init__(parent)
        self.container_name = container_name
        self.cols, self.rows = GRID_SIZES.get(container_name, (10, 4))
        self.setAcceptDrops(True)
        self.setFixedSize(self.cols * CELL_SIZE, self.rows * CELL_SIZE)
        self._cells: dict[int, ItemCell] = {}

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(QColor("#3a3542"))
        for col in range(self.cols + 1):
            x = col * CELL_SIZE
            painter.drawLine(x, 0, x, self.rows * CELL_SIZE)
        for row in range(self.rows + 1):
            y = row * CELL_SIZE
            painter.drawLine(0, y, self.cols * CELL_SIZE, y)

    def dragEnterEvent(self, event) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        item_id = int(event.mimeData().text())
        pos: QPoint = event.position().toPoint() if hasattr(event, "position") else event.pos()
        grid_x = max(0, min(self.cols - 1, pos.x() // CELL_SIZE))
        grid_y = max(0, min(self.rows - 1, pos.y() // CELL_SIZE))
        self.item_dropped.emit(item_id, grid_x, grid_y)
        event.acceptProposedAction()

    def render_items(self, items: list) -> None:
        for cell in self._cells.values():
            cell.setParent(None)
        self._cells.clear()
        for item in items:
            cell = ItemCell(item, parent=self)
            cell.move(item.x * CELL_SIZE + 1, item.y * CELL_SIZE + 1)
            cell.item_clicked.connect(self.item_clicked.emit)
            cell.show()
            self._cells[item.id] = cell


class InventoryView(QWidget):
    """Tabbed view across all containers (spec §5)."""

    item_clicked = Signal(int)
    item_dropped = Signal(str, int, int, int)  # container, item_id, x, y

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.grids: dict[str, GridContainer] = {}
        for container in CONTAINERS:
            grid = GridContainer(container)
            grid.item_clicked.connect(self.item_clicked.emit)
            grid.item_dropped.connect(
                lambda item_id, x, y, c=container: self.item_dropped.emit(c, item_id, x, y)
            )
            self.grids[container] = grid

            wrapper = QWidget()
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.addWidget(grid)
            wrapper_layout.addStretch()
            self.tabs.addTab(wrapper, container)
        layout.addWidget(self.tabs)

    def render_container(self, container: str, items: list) -> None:
        if container in self.grids:
            self.grids[container].render_items(items)

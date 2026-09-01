"""D2R Vault — transient 'CAPTURING...' overlay shown during F9 (spec §7)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CaptureOverlay(QWidget):
    """A small, frameless, always-on-top toast. Auto-hides itself so the
    user barely notices it, matching the "nearly instantaneous" UX goal
    (spec §45)."""

    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(220, 80)

        layout = QVBoxLayout(self)
        self.container = QWidget(self)
        self.container.setStyleSheet(
            "background-color: rgba(20, 18, 24, 220); border: 1px solid #c9a24b; border-radius: 8px;"
        )
        inner = QVBoxLayout(self.container)
        self.title_label = QLabel("CAPTURING...")
        self.title_label.setStyleSheet("color: #e8c874; font-weight: 700; font-size: 13px;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("🔍 Reading Item")
        self.status_label.setStyleSheet("color: #e8e3d8; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        inner.addWidget(self.title_label)
        inner.addWidget(self.status_label)
        layout.addWidget(self.container)

    def show_status(self, status: str, *, auto_hide_ms: int | None = None) -> None:
        self.status_label.setText(status)
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen is not None:
            self.move(screen.right() - self.width() - 24, screen.top() + 24)
        self.show()
        if auto_hide_ms:
            QTimer.singleShot(auto_hide_ms, self.hide)

    def show_success(self, item_name: str) -> None:
        self.title_label.setText("✓ ITEM ADDED")
        self.status_label.setText(item_name)
        self.show_status(item_name, auto_hide_ms=1800)

    def show_failure(self, message: str = "Couldn't confidently read this item.") -> None:
        self.title_label.setText("⚠ CAPTURE ISSUE")
        self.status_label.setText(message)
        self.show_status(message, auto_hide_ms=2500)

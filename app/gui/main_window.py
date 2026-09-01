"""D2R Vault — main window: navigation shell, F9 capture wiring, system tray."""
from __future__ import annotations

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox, QPushButton,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from app import config
from app.capture.hotkey_listener import HotkeyListener
from app.capture.screen_capture import MSSScreenCapture
from app.database.database import get_session_factory
from app.gui.capture_overlay import CaptureOverlay
from app.gui.character_view import CharacterVaultView, CreateCharacterDialog
from app.gui.inventory_view import InventoryView
from app.gui.item_view import ItemConfirmationDialog, ManualItemEntryDialog
from app.gui.settings_view import SettingsView
from app.gui.theme import STYLESHEET
from app.ocr.ocr_engine import TesseractOCREngine
from app.services.capture_service import CaptureService
from app.services.character_service import CharacterService
from app.services.inventory_service import InventoryService
from app.services.item_service import ItemService


class _CaptureBridge(QObject):
    """Marshals hotkey-thread callbacks onto the Qt event loop via a
    signal, since pynput fires callbacks on a background thread and Qt
    widgets must only be touched from the main thread."""

    capture_requested = Signal()
    rapid_toggle_requested = Signal()
    pause_toggle_requested = Signal()
    open_vault_requested = Signal()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME}")
        self.resize(1100, 720)
        self.setStyleSheet(STYLESHEET)

        self.settings = config.get_settings()
        self.session_factory = get_session_factory()
        self.session = self.session_factory()

        self.current_character_id: int | None = None
        self.rapid_scan_enabled = False

        self._build_ui()
        self._build_tray()
        self._build_hotkeys()
        self.refresh_vault()

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        nav = QHBoxLayout()
        self.back_btn = QPushButton("← Vault")
        self.back_btn.clicked.connect(self.show_vault)
        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        self.rapid_scan_btn = QPushButton("⚡ Rapid Scan: OFF")
        self.rapid_scan_btn.clicked.connect(self.toggle_rapid_scan)
        self.manual_entry_btn = QPushButton("+ Manual Entry")
        self.manual_entry_btn.clicked.connect(self.open_manual_entry)
        nav.addWidget(self.back_btn)
        nav.addStretch()
        nav.addWidget(self.rapid_scan_btn)
        nav.addWidget(self.manual_entry_btn)
        nav.addWidget(self.settings_btn)
        outer.addLayout(nav)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        self.vault_view = CharacterVaultView()
        self.vault_view.character_selected.connect(self.open_character)
        self.vault_view.create_character_requested.connect(self.open_create_character)
        self.stack.addWidget(self.vault_view)

        self.character_header = QLabel("")
        self.character_header.setObjectName("Title")
        self.inventory_view = InventoryView()
        self.inventory_view.item_dropped.connect(self._on_item_dropped)

        character_page = QWidget()
        char_layout = QVBoxLayout(character_page)
        char_layout.addWidget(self.character_header)
        char_layout.addWidget(self.inventory_view)
        self.stack.addWidget(character_page)

        self.settings_view = SettingsView(self.settings)
        self.settings_view.test_capture_btn.clicked.connect(self.test_capture)
        self.settings_view.backup_now_btn.clicked.connect(self.backup_now)
        self.stack.addWidget(self.settings_view)

        self.overlay = CaptureOverlay()

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip(config.APP_NAME)
        menu = QMenu()
        menu.addAction("Open D2R Vault", self.show_vault)
        menu.addAction("Capture Item", self.perform_capture)
        menu.addAction("Toggle Rapid Scan", self.toggle_rapid_scan)
        menu.addAction("Pause Hotkeys", self.toggle_pause)
        menu.addAction("Backup Database", self.backup_now)
        menu.addSeparator()
        menu.addAction("Exit", self.close)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def _build_hotkeys(self) -> None:
        self.bridge = _CaptureBridge()
        self.bridge.capture_requested.connect(self.perform_capture)
        self.bridge.rapid_toggle_requested.connect(self.toggle_rapid_scan)
        self.bridge.pause_toggle_requested.connect(self.toggle_pause)
        self.bridge.open_vault_requested.connect(self.show_vault)

        self.hotkeys = HotkeyListener()
        hk = self.settings.hotkeys
        self.hotkeys.register(hk["capture"], self.bridge.capture_requested.emit)
        self.hotkeys.register(hk["rapid_scan"], self.bridge.rapid_toggle_requested.emit)
        self.hotkeys.register(hk["pause"], self.bridge.pause_toggle_requested.emit)
        self.hotkeys.register(hk["open_vault"], self.bridge.open_vault_requested.emit)
        try:
            self.hotkeys.start()
        except Exception:
            # No display/input backend available (e.g. headless CI) —
            # the app still runs, just without global hotkeys.
            pass

    # -- navigation -----------------------------------------------------

    def show_vault(self) -> None:
        self.refresh_vault()
        self.stack.setCurrentIndex(0)

    def show_settings(self) -> None:
        self.stack.setCurrentIndex(2)

    def refresh_vault(self) -> None:
        char_service = CharacterService(self.session)
        characters = char_service.list_characters()
        stats = {c.id: char_service.dashboard_stats(c.id) for c in characters}
        self.vault_view.refresh(characters, stats)

    def open_create_character(self) -> None:
        dialog = CreateCharacterDialog(self)
        if dialog.exec():
            values = dialog.values()
            if not values["name"]:
                QMessageBox.warning(self, "Missing Name", "Please enter a character name.")
                return
            CharacterService(self.session).create_character(**values)
            self.refresh_vault()

    def open_character(self, character_id: int) -> None:
        self.current_character_id = character_id
        char_service = CharacterService(self.session)
        char = char_service.characters.get(character_id)
        if char is None:
            return
        self.character_header.setText(f"{char.name} — {char.char_class}, Level {char.level}")
        self._refresh_inventory()
        self.stack.setCurrentIndex(1)

    def _refresh_inventory(self) -> None:
        if self.current_character_id is None:
            return
        inv_service = InventoryService(self.session)
        for container in config.CONTAINERS:
            items = inv_service.items.for_character(self.current_character_id, container)
            self.inventory_view.render_container(container, items)

    # -- capture ----------------------------------------------------------

    def _build_capture_service(self) -> CaptureService:
        ocr = TesseractOCREngine(language=self.settings.ocr_language)
        return CaptureService(MSSScreenCapture(), ocr, self.settings)

    def perform_capture(self) -> None:
        if self.hotkeys.is_paused:
            return
        self.overlay.show_status("🔍 Reading Item")
        try:
            outcome = self._build_capture_service().capture_and_parse()
        except Exception as exc:
            self.overlay.show_failure(f"Capture failed: {exc}")
            return

        if self.rapid_scan_enabled:
            self._save_item(outcome.parsed_item, silent=True)
            return

        dialog = ItemConfirmationDialog(outcome.parsed_item, outcome.low_confidence, self)
        result = dialog.exec()
        if result in (10, 11):
            edited = dialog.edited_fields()
            for key, value in edited.items():
                setattr(outcome.parsed_item, key, value)
            self._save_item(outcome.parsed_item, screenshot_path=outcome.screenshot_path)
            if result == 11:
                self.perform_capture()

    def _save_item(self, parsed_item, screenshot_path: str | None = None, silent: bool = False) -> None:
        if self.current_character_id is None:
            if not silent:
                QMessageBox.information(self, "Select a Character", "Open a character before saving items.")
            return
        parsed_item.raw_ocr_text = parsed_item.raw_ocr_text or ""
        item_service = ItemService(self.session)
        result = item_service.save_parsed_item(parsed_item, self.current_character_id)
        if result.is_duplicate:
            if silent:
                return
            choice = QMessageBox.question(
                self, "Possible Duplicate",
                f"'{parsed_item.name}' looks like a duplicate of an item already stored.\n\nSave anyway?",
            )
            if choice == QMessageBox.Yes:
                result = item_service.save_parsed_item(parsed_item, self.current_character_id, force=True)
            else:
                return
        if screenshot_path and result.item:
            result.item.screenshot_path = screenshot_path
            self.session.commit()
        self.overlay.show_success(parsed_item.name)
        self._refresh_inventory()
        self.refresh_vault()

    def open_manual_entry(self) -> None:
        if self.current_character_id is None:
            QMessageBox.information(self, "Select a Character", "Open a character before adding items.")
            return
        dialog = ManualItemEntryDialog(self)
        if dialog.exec():
            from app.parser.item_parser import parse_item

            parsed = parse_item(dialog.raw_text(), ocr_confidence=100.0)
            self._save_item(parsed)

    def test_capture(self) -> None:
        try:
            outcome = self._build_capture_service().capture_and_parse()
            QMessageBox.information(
                self, "Test Capture",
                f"OCR confidence: {outcome.ocr_result.confidence:.0f}%\n\n"
                f"Detected: {outcome.parsed_item.name}\n\nRaw text:\n{outcome.ocr_result.text[:400]}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Test Capture Failed", str(exc))

    def _on_item_dropped(self, container: str, item_id: int, x: int, y: int) -> None:
        try:
            InventoryService(self.session).move_item(item_id, container, x, y)
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot Move Item", str(exc))
        self._refresh_inventory()

    # -- misc actions -----------------------------------------------------

    def toggle_rapid_scan(self) -> None:
        self.rapid_scan_enabled = not self.rapid_scan_enabled
        self.rapid_scan_btn.setText(f"⚡ Rapid Scan: {'ON' if self.rapid_scan_enabled else 'OFF'}")

    def toggle_pause(self) -> None:
        if self.hotkeys.is_paused:
            self.hotkeys.resume()
        else:
            self.hotkeys.pause()

    def backup_now(self) -> None:
        from app.services.backup_service import BackupService

        path = BackupService().backup_now()
        if path:
            QMessageBox.information(self, "Backup Complete", f"Database backed up to:\n{path}")
        else:
            QMessageBox.information(self, "Nothing to Back Up", "No database file exists yet.")

    def closeEvent(self, event) -> None:
        # Minimize to tray instead of quitting, so F9 keeps working
        # while the user keeps playing (spec §38).
        event.ignore()
        self.hide()
        self.tray.showMessage(config.APP_NAME, "Still running in the system tray. F9 keeps working.", QSystemTrayIcon.Information, 2000)

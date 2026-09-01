"""D2R Vault — main window, navigation, capture workflow and system tray."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox,
    QPushButton, QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from app import config
from app.capture.hotkey_listener import HotkeyListener
from app.capture.screen_capture import MSSScreenCapture
from app.database.database import get_session_factory, reset_session_factory
from app.database.repositories import ItemRepository
from app.gui.capture_overlay import CaptureOverlay
from app.gui.character_view import CharacterVaultView, CreateCharacterDialog
from app.gui.inventory_view import InventoryView
from app.gui.item_view import ItemConfirmationDialog, ItemDetailsDialog, ManualItemEntryDialog
from app.gui.region_selector import RegionSelector
from app.gui.settings_view import SettingsView
from app.gui.theme import STYLESHEET
from app.ocr.ocr_engine import TesseractOCREngine
from app.services.backup_service import BackupService
from app.services.capture_service import CaptureService
from app.services.character_service import CharacterService
from app.services.export_service import ExportService
from app.services.inventory_service import InventoryService
from app.services.item_service import ItemService


class _CaptureBridge(QObject):
    capture_requested = Signal()
    rapid_toggle_requested = Signal()
    pause_toggle_requested = Signal()
    open_vault_requested = Signal()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.resize(1100, 720)
        self.setStyleSheet(STYLESHEET)
        self.settings = config.get_settings()
        self.session_factory = get_session_factory()
        self.session = self.session_factory()
        self.current_character_id = None
        self.rapid_scan_enabled = False
        self._last_rapid_capture = 0.0
        self._really_quit = False
        self._region_selector = None
        self._build_ui()
        self._build_tray()
        self._build_hotkeys()
        self._maybe_auto_backup()
        self.refresh_vault()

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central); outer = QVBoxLayout(central)
        nav = QHBoxLayout()
        self.back_btn = QPushButton("← Vault"); self.back_btn.clicked.connect(self.show_vault)
        self.settings_btn = QPushButton("⚙ Settings"); self.settings_btn.clicked.connect(self.show_settings)
        self.rapid_scan_btn = QPushButton("⚡ Rapid Scan: OFF"); self.rapid_scan_btn.clicked.connect(self.toggle_rapid_scan)
        self.manual_entry_btn = QPushButton("+ Manual Entry"); self.manual_entry_btn.clicked.connect(self.open_manual_entry)
        nav.addWidget(self.back_btn); nav.addStretch(); nav.addWidget(self.rapid_scan_btn); nav.addWidget(self.manual_entry_btn); nav.addWidget(self.settings_btn)
        outer.addLayout(nav)
        self.stack = QStackedWidget(); outer.addWidget(self.stack)
        self.vault_view = CharacterVaultView(); self.vault_view.character_selected.connect(self.open_character); self.vault_view.create_character_requested.connect(self.open_create_character); self.stack.addWidget(self.vault_view)
        self.character_header = QLabel(""); self.character_header.setObjectName("Title")
        self.inventory_view = InventoryView(); self.inventory_view.item_dropped.connect(self._on_item_dropped); self.inventory_view.item_clicked.connect(self.open_item_details)
        character_page = QWidget(); char_layout = QVBoxLayout(character_page); char_layout.addWidget(self.character_header); char_layout.addWidget(self.inventory_view); self.stack.addWidget(character_page)
        self.settings_view = SettingsView(self.settings)
        self.settings_view.test_capture_btn.clicked.connect(self.test_capture)
        self.settings_view.backup_now_btn.clicked.connect(self.backup_now)
        self.settings_view.restore_btn.clicked.connect(self.restore_backup)
        self.settings_view.export_btn.clicked.connect(self.export_inventory)
        self.settings_view.import_btn.clicked.connect(self.import_database)
        self.settings_view.settings_saved.connect(self._on_settings_saved)
        self.settings_view.select_region_requested.connect(self.select_capture_region)
        self.stack.addWidget(self.settings_view)
        self.overlay = CaptureOverlay()

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self); self.tray.setToolTip(config.APP_NAME)
        menu = QMenu(); menu.addAction("Open D2R Vault", self.show_vault); menu.addAction("Capture Item", self.perform_capture)
        menu.addAction("Toggle Rapid Scan", self.toggle_rapid_scan); menu.addAction("Pause Hotkeys", self.toggle_pause); menu.addAction("Backup Database", self.backup_now)
        menu.addSeparator(); menu.addAction("Exit", self.quit_app); self.tray.setContextMenu(menu); self.tray.activated.connect(self._tray_activated); self.tray.show()

    def _build_hotkeys(self):
        self.bridge = getattr(self, "bridge", _CaptureBridge())
        if not hasattr(self, "_bridge_connected"):
            self.bridge.capture_requested.connect(self.perform_capture); self.bridge.rapid_toggle_requested.connect(self.toggle_rapid_scan)
            self.bridge.pause_toggle_requested.connect(self.toggle_pause); self.bridge.open_vault_requested.connect(self.show_vault); self._bridge_connected = True
        old = getattr(self, "hotkeys", None)
        if old: old.stop()
        self.hotkeys = HotkeyListener(); hk = self.settings.hotkeys
        self.hotkeys.register(hk["capture"], self.bridge.capture_requested.emit); self.hotkeys.register(hk["rapid_scan"], self.bridge.rapid_toggle_requested.emit)
        self.hotkeys.register(hk["pause"], self.bridge.pause_toggle_requested.emit); self.hotkeys.register(hk["open_vault"], self.bridge.open_vault_requested.emit)
        try: self.hotkeys.start()
        except Exception: pass

    def _on_settings_saved(self):
        self.settings = self.settings_view.settings
        self._build_hotkeys()
        self.overlay.show_status("✓ Settings saved")

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick: self.show_vault()

    def show_vault(self):
        self.refresh_vault(); self.stack.setCurrentIndex(0); self.show(); self.raise_(); self.activateWindow()

    def show_settings(self):
        self.stack.setCurrentIndex(2); self.show(); self.raise_()

    def refresh_vault(self):
        cs = CharacterService(self.session); chars = cs.list_characters(); stats = {c.id: cs.dashboard_stats(c.id) for c in chars}; self.vault_view.refresh(chars, stats)

    def open_create_character(self):
        d = CreateCharacterDialog(self)
        if d.exec():
            values = d.values()
            if not values["name"]: QMessageBox.warning(self, "Missing Name", "Please enter a character name."); return
            char = CharacterService(self.session).create_character(**values)
            self.refresh_vault()
            # A newly-created character should immediately become the active scan target.
            self.open_character(char.id)

    def open_character(self, character_id):
        self.current_character_id = character_id; char = CharacterService(self.session).characters.get(character_id)
        if char is None: return
        self.character_header.setText(f"{char.name} — {char.char_class}, Level {char.level}"); self._refresh_inventory(); self.stack.setCurrentIndex(1)

    def _refresh_inventory(self):
        if self.current_character_id is None: return
        inv = InventoryService(self.session)
        for container in config.CONTAINERS: self.inventory_view.render_container(container, inv.items.for_character(self.current_character_id, container))

    def _build_capture_service(self):
        ocr = TesseractOCREngine(language=self.settings.ocr_language, tesseract_cmd=self.settings.tesseract_cmd)
        return CaptureService(MSSScreenCapture(), ocr, self.settings)

    def _ensure_active_character(self) -> bool:
        """Resolve the active scan target from the Vault selection when possible."""
        if self.current_character_id is not None:
            return True
        selected = self.vault_view.list_widget.currentItem()
        if selected is not None:
            character_id = selected.data(1000)
            if character_id is not None:
                self.open_character(character_id)
        return self.current_character_id is not None

    def perform_capture(self):
        if self.hotkeys.is_paused: return
        if not self._ensure_active_character():
            self.overlay.show_failure("Select a character in the Vault before scanning")
            return
        if self.rapid_scan_enabled:
            now = time.monotonic()
            if now - self._last_rapid_capture < self.settings.rapid_scan_delay_seconds: return
            self._last_rapid_capture = now
        self.overlay.show_status("🔍 Reading Item")
        try: outcome = self._build_capture_service().capture_and_parse()
        except Exception as exc: self.overlay.show_failure(f"Capture failed: {exc}"); return
        if self.rapid_scan_enabled:
            self._save_item(outcome.parsed_item, screenshot_path=outcome.screenshot_path, silent=True); return
        dialog = ItemConfirmationDialog(outcome.parsed_item, outcome.low_confidence, self)
        result = dialog.exec()
        if result in (10, 11):
            for key, value in dialog.edited_fields().items(): setattr(outcome.parsed_item, key, value)
            self._save_item(outcome.parsed_item, screenshot_path=outcome.screenshot_path)
            if result == 11: self.perform_capture()

    def _save_item(self, parsed_item, screenshot_path=None, silent=False):
        if self.current_character_id is None:
            if not silent: QMessageBox.information(self, "Select a Character", "Open a character before saving items.")
            return
        parsed_item.raw_ocr_text = parsed_item.raw_ocr_text or ""
        svc = ItemService(self.session); result = svc.save_parsed_item(parsed_item, self.current_character_id)
        if result.is_duplicate:
            if silent:
                self.overlay.show_status(f"↺ Duplicate skipped: {parsed_item.name}"); return
            choice = QMessageBox.question(self, "Possible Duplicate", f"'{parsed_item.name}' looks like a duplicate.\n\nSave anyway?")
            if choice == QMessageBox.Yes: result = svc.save_parsed_item(parsed_item, self.current_character_id, force=True)
            else: return
        if screenshot_path and result.item:
            result.item.screenshot_path = screenshot_path; self.session.commit()
        self.overlay.show_success(parsed_item.name); self._refresh_inventory(); self.refresh_vault()

    def open_item_details(self, item_id):
        repo = ItemRepository(self.session); item = repo.get(item_id)
        if item is None: return
        d = ItemDetailsDialog(item, self)
        if not d.exec(): return
        if d.delete_requested:
            if QMessageBox.question(self, "Delete Item", f"Delete '{item.name}' from D2R Vault?") == QMessageBox.Yes: repo.delete(item_id)
        else: repo.update(item_id, **d.values())
        self._refresh_inventory(); self.refresh_vault()

    def open_manual_entry(self):
        if not self._ensure_active_character():
            QMessageBox.information(self, "Select a Character", "Select a character in the Vault before adding items.")
            return
        d = ManualItemEntryDialog(self)
        if d.exec():
            from app.parser.item_parser import parse_item
            self._save_item(parse_item(d.raw_text(), ocr_confidence=100.0))

    def test_capture(self):
        try:
            outcome = self._build_capture_service().capture_and_parse()
            QMessageBox.information(self, "Test Capture", f"OCR confidence: {outcome.ocr_result.confidence:.0f}%\nPass: {outcome.ocr_result.pass_name}\n\nDetected: {outcome.parsed_item.name}\n\nRaw text:\n{outcome.ocr_result.text[:500]}")
        except Exception as exc: QMessageBox.warning(self, "Test Capture Failed", str(exc))

    def select_capture_region(self):
        self.hide()
        selector = RegionSelector(); self._region_selector = selector
        selector.region_selected.connect(self._region_selected); selector.destroyed.connect(lambda: self.show())
        selector.show()

    def _region_selected(self, region):
        self.settings.fixed_region = region; self.settings.tooltip_capture_mode = "Manual Selection"; self.settings.save()
        self.settings_view.set_region(region); self.show(); self.raise_(); self.activateWindow()

    def _on_item_dropped(self, container, item_id, x, y):
        try: InventoryService(self.session).move_item(item_id, container, x, y)
        except ValueError as exc: QMessageBox.warning(self, "Cannot Move Item", str(exc))
        self._refresh_inventory()

    def toggle_rapid_scan(self):
        self.rapid_scan_enabled = not self.rapid_scan_enabled; self.rapid_scan_btn.setText(f"⚡ Rapid Scan: {'ON' if self.rapid_scan_enabled else 'OFF'}")
        self.overlay.show_status(f"Rapid Scan {'enabled' if self.rapid_scan_enabled else 'disabled'}")

    def toggle_pause(self):
        if self.hotkeys.is_paused: self.hotkeys.resume(); self.overlay.show_status("Hotkeys resumed")
        else: self.hotkeys.pause(); self.overlay.show_status("Hotkeys paused")

    def _maybe_auto_backup(self):
        svc = BackupService(keep=self.settings.backups_to_keep)
        if svc.is_backup_due(self.settings): svc.backup_now()

    def backup_now(self):
        path = BackupService(keep=self.settings.backups_to_keep).backup_now()
        QMessageBox.information(self, "Backup", f"Database backed up to:\n{path}" if path else "No database file exists yet.")

    def _reset_session(self):
        try: self.session.close()
        except Exception: pass
        self.session_factory = get_session_factory(); self.session = self.session_factory(); self.refresh_vault()
        if self.current_character_id is not None: self._refresh_inventory()

    def restore_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore D2R Vault Backup", str(config.BACKUP_DIR), "SQLite Database (*.db);;All Files (*)")
        if not path: return
        if QMessageBox.question(self, "Restore Backup", "This replaces the current database after creating a safety backup. Continue?") != QMessageBox.Yes: return
        try:
            self.session.close(); reset_session_factory(); BackupService(keep=self.settings.backups_to_keep).restore(Path(path)); self.session_factory = get_session_factory(); self.session = self.session_factory(); self.refresh_vault(); self.current_character_id = None; self.show_vault()
            QMessageBox.information(self, "Restore Complete", "Backup restored successfully.")
        except Exception as exc: QMessageBox.critical(self, "Restore Failed", str(exc))

    def import_database(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import D2R Vault Database", "", "SQLite Database (*.db);;All Files (*)")
        if not path: return
        if QMessageBox.question(self, "Import Database", "Replace the current database with this file? A safety backup will be created first.") != QMessageBox.Yes: return
        try:
            self.session.close(); reset_session_factory(); BackupService(keep=self.settings.backups_to_keep).backup_now(); shutil.copy2(path, config.DB_PATH); self.session_factory = get_session_factory(); self.session = self.session_factory(); self.current_character_id = None; self.show_vault()
            QMessageBox.information(self, "Import Complete", "Database imported successfully.")
        except Exception as exc: QMessageBox.critical(self, "Import Failed", str(exc))

    def export_inventory(self):
        path, selected = QFileDialog.getSaveFileName(self, "Export Inventory", str(Path.home()/"d2r_vault_inventory.xlsx"), "Excel (*.xlsx);;CSV (*.csv);;JSON (*.json)")
        if not path: return
        try:
            svc = ExportService(self.session); p = Path(path); suffix = p.suffix.lower()
            if suffix == ".csv": svc.export_csv(p)
            elif suffix == ".json": svc.export_json(p)
            else:
                if suffix != ".xlsx": p = p.with_suffix(".xlsx")
                svc.export_excel(p)
            QMessageBox.information(self, "Export Complete", f"Inventory exported to:\n{p}")
        except Exception as exc: QMessageBox.critical(self, "Export Failed", str(exc))

    def quit_app(self):
        self._really_quit = True
        try: self.hotkeys.stop(); self.session.close()
        except Exception: pass
        self.tray.hide()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        if self._really_quit: event.accept(); return
        event.ignore(); self.hide(); self.tray.showMessage(config.APP_NAME, "Still running in the system tray. F9 keeps working.", QSystemTrayIcon.Information, 2000)

"""D2R Vault — settings screen (spec §40)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QLabel, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from app.config import DEFAULT_HOTKEYS, Settings, TOOLTIP_CAPTURE_MODES


class SettingsView(QWidget):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        layout = QVBoxLayout(self)

        title = QLabel("Settings")
        title.setObjectName("Title")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_capture_tab(), "Capture")
        tabs.addTab(self._build_ocr_tab(), "OCR")
        tabs.addTab(self._build_hotkeys_tab(), "Hotkeys")
        tabs.addTab(self._build_backup_tab(), "Backups")
        layout.addWidget(tabs)

        save_btn = QPushButton("SAVE SETTINGS")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self.apply_and_save)
        layout.addWidget(save_btn)

    def _build_capture_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(TOOLTIP_CAPTURE_MODES)
        self.mode_combo.setCurrentText(self.settings.tooltip_capture_mode)
        form.addRow("Tooltip Capture Mode:", self.mode_combo)

        region = self.settings.fixed_region
        self.region_x = QSpinBox(); self.region_x.setRange(0, 10000); self.region_x.setValue(region["x"])
        self.region_y = QSpinBox(); self.region_y.setRange(0, 10000); self.region_y.setValue(region["y"])
        self.region_w = QSpinBox(); self.region_w.setRange(10, 4000); self.region_w.setValue(region["width"])
        self.region_h = QSpinBox(); self.region_h.setRange(10, 4000); self.region_h.setValue(region["height"])
        form.addRow("Region X:", self.region_x)
        form.addRow("Region Y:", self.region_y)
        form.addRow("Region Width:", self.region_w)
        form.addRow("Region Height:", self.region_h)

        test_btn = QPushButton("TEST CAPTURE")
        form.addRow(test_btn)
        self.test_capture_btn = test_btn

        self.save_screenshots_check = QCheckBox("Save screenshots")
        self.save_screenshots_check.setChecked(self.settings.save_screenshots)
        form.addRow("", self.save_screenshots_check)

        return widget

    def _build_ocr_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.ocr_engine_combo = QComboBox()
        self.ocr_engine_combo.addItems(["tesseract"])
        self.ocr_engine_combo.setCurrentText(self.settings.ocr_engine)
        form.addRow("OCR Engine:", self.ocr_engine_combo)

        self.ocr_lang_combo = QComboBox()
        self.ocr_lang_combo.addItems(["eng"])
        self.ocr_lang_combo.setCurrentText(self.settings.ocr_language)
        form.addRow("Language:", self.ocr_lang_combo)

        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0, 100)
        self.confidence_spin.setValue(self.settings.ocr_confidence_threshold)
        form.addRow("Confidence Threshold:", self.confidence_spin)

        return widget

    def _build_hotkeys_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.hotkey_edits: dict[str, QComboBox] = {}
        f_keys = [f"F{i}" for i in range(1, 13)]
        labels = {"capture": "Capture:", "rapid_scan": "Rapid Scan:", "open_vault": "Open Vault:", "pause": "Pause:"}
        for action, label in labels.items():
            combo = QComboBox()
            combo.addItems(f_keys)
            combo.setCurrentText(self.settings.hotkeys.get(action, DEFAULT_HOTKEYS[action]))
            form.addRow(label, combo)
            self.hotkey_edits[action] = combo
        return widget

    def _build_backup_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.auto_backup_check = QCheckBox("Automatic backups")
        self.auto_backup_check.setChecked(self.settings.automatic_backups)
        form.addRow("", self.auto_backup_check)

        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["Daily", "Weekly"])
        self.frequency_combo.setCurrentText(self.settings.backup_frequency)
        form.addRow("Frequency:", self.frequency_combo)

        self.keep_spin = QSpinBox()
        self.keep_spin.setRange(1, 100)
        self.keep_spin.setValue(self.settings.backups_to_keep)
        form.addRow("Keep:", self.keep_spin)

        self.backup_now_btn = QPushButton("BACKUP NOW")
        self.restore_btn = QPushButton("RESTORE BACKUP")
        self.export_btn = QPushButton("EXPORT DATABASE")
        self.import_btn = QPushButton("IMPORT DATABASE")
        form.addRow(self.backup_now_btn)
        form.addRow(self.restore_btn)
        form.addRow(self.export_btn)
        form.addRow(self.import_btn)

        return widget

    def apply_and_save(self) -> Settings:
        self.settings.tooltip_capture_mode = self.mode_combo.currentText()
        self.settings.fixed_region = {
            "x": self.region_x.value(), "y": self.region_y.value(),
            "width": self.region_w.value(), "height": self.region_h.value(),
        }
        self.settings.save_screenshots = self.save_screenshots_check.isChecked()
        self.settings.ocr_engine = self.ocr_engine_combo.currentText()
        self.settings.ocr_language = self.ocr_lang_combo.currentText()
        self.settings.ocr_confidence_threshold = self.confidence_spin.value()
        self.settings.hotkeys = {k: combo.currentText() for k, combo in self.hotkey_edits.items()}
        self.settings.automatic_backups = self.auto_backup_check.isChecked()
        self.settings.backup_frequency = self.frequency_combo.currentText()
        self.settings.backups_to_keep = self.keep_spin.value()
        self.settings.save()
        return self.settings

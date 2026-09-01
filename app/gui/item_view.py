"""D2R Vault — item confirmation window (spec §7/§13) and manual entry (spec §42)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout,
)

from app.config import ITEM_QUALITIES
from app.gui.theme import quality_color


class ItemConfirmationDialog(QDialog):
    """Shown right after an F9 capture. Never auto-saves — the user
    always confirms (spec §13: 'Never blindly trust OCR')."""

    def __init__(self, parsed_item, low_confidence: bool, parent=None):
        super().__init__(parent)
        self.parsed_item = parsed_item
        self.setWindowTitle("Item Detected")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        header = QLabel(parsed_item.name)
        header.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {quality_color(parsed_item.quality)};"
        )
        layout.addWidget(header)

        if parsed_item.base_name:
            base_label = QLabel(parsed_item.base_name)
            base_label.setStyleSheet("color: #a49d8f;")
            layout.addWidget(base_label)

        if low_confidence:
            warn = QLabel("⚠ Some fields may be inaccurate — OCR confidence is low. Please review.")
            warn.setStyleSheet("color: #e8a34b;")
            warn.setWordWrap(True)
            layout.addWidget(warn)

        form = QFormLayout()
        self.name_edit = QLineEdit(parsed_item.name)
        form.addRow("Item Name:", self.name_edit)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(ITEM_QUALITIES)
        self.quality_combo.setCurrentText(parsed_item.quality)
        form.addRow("Quality:", self.quality_combo)

        self.base_edit = QLineEdit(parsed_item.base_name or "")
        form.addRow("Base:", self.base_edit)

        self.defense_spin = QSpinBox()
        self.defense_spin.setRange(0, 9999)
        self.defense_spin.setValue(parsed_item.defense or 0)
        form.addRow("Defense:", self.defense_spin)

        self.level_spin = QSpinBox()
        self.level_spin.setRange(0, 99)
        self.level_spin.setValue(parsed_item.required_level or 0)
        form.addRow("Required Level:", self.level_spin)

        self.ethereal_check = QCheckBox("Ethereal")
        self.ethereal_check.setChecked(parsed_item.ethereal)
        form.addRow("", self.ethereal_check)

        layout.addLayout(form)

        stats_label = QLabel("Stats:")
        stats_label.setStyleSheet("color: #c9a24b; font-weight: 600; margin-top: 8px;")
        layout.addWidget(stats_label)

        stat_lines = self._build_stat_lines(parsed_item)
        self.stats_text = QPlainTextEdit("\n".join(stat_lines))
        self.stats_text.setReadOnly(False)
        self.stats_text.setMaximumHeight(140)
        layout.addWidget(self.stats_text)

        raw_label = QLabel(f"Raw OCR confidence: {parsed_item.ocr_confidence or 0:.0f}%")
        raw_label.setStyleSheet("color: #a49d8f; font-size: 11px;")
        layout.addWidget(raw_label)

        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("CANCEL")
        self.edit_btn = QPushButton("EDIT RAW TEXT")
        self.save_next_btn = QPushButton("SAVE & CAPTURE NEXT")
        self.save_btn = QPushButton("SAVE")
        self.save_btn.setObjectName("Primary")

        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(lambda: self.done(10))
        self.save_next_btn.clicked.connect(lambda: self.done(11))
        self.edit_btn.clicked.connect(self._toggle_raw_edit)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.save_next_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _build_stat_lines(parsed_item) -> list[str]:
        lines = []
        if parsed_item.plus_to_skills:
            lines.append(f"+{parsed_item.plus_to_skills} To All Skills")
        for skill in parsed_item.skills:
            lines.append(f"+{skill.amount} To {skill.skill}" + (f" ({skill.tab} Only)" if skill.tab else ""))
        if parsed_item.enhanced_defense:
            lines.append(f"+{parsed_item.enhanced_defense}% Enhanced Defense")
        if parsed_item.enhanced_damage:
            lines.append(f"+{parsed_item.enhanced_damage}% Enhanced Damage")
        for element, value in (parsed_item.resistances or {}).items():
            lines.append(f"{element.title()} Resist +{value}%")
        if parsed_item.all_resistances:
            lines.append(f"+{parsed_item.all_resistances} All Resistances")
        if parsed_item.faster_cast_rate:
            lines.append(f"+{parsed_item.faster_cast_rate}% Faster Cast Rate")
        if parsed_item.faster_hit_recovery:
            lines.append(f"+{parsed_item.faster_hit_recovery}% Faster Hit Recovery")
        if parsed_item.magic_find:
            lines.append(f"+{parsed_item.magic_find}% Better Chance of Getting Magic Items")
        if parsed_item.socket_count:
            lines.append(f"Socketed ({parsed_item.socket_count})")
        for key in (parsed_item.extra_mods or {}):
            lines.append(key)
        return lines or ["(no stats parsed — edit raw text or enter manually)"]

    def _toggle_raw_edit(self) -> None:
        self.stats_text.setPlainText(self.parsed_item.raw_ocr_text)

    def edited_fields(self) -> dict:
        return {
            "name": self.name_edit.text().strip() or self.parsed_item.name,
            "quality": self.quality_combo.currentText(),
            "base_name": self.base_edit.text().strip() or None,
            "defense": self.defense_spin.value() or None,
            "required_level": self.level_spin.value() or None,
            "ethereal": self.ethereal_check.isChecked(),
        }


class ManualItemEntryDialog(QDialog):
    """Manual fallback entry (spec §42) — uses the same save path as OCR."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Item Entry")
        self.setMinimumWidth(360)
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow("Item Name:", self.name_edit)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(ITEM_QUALITIES)
        layout.addRow("Quality:", self.quality_combo)

        self.base_edit = QLineEdit()
        layout.addRow("Base:", self.base_edit)

        self.stats_text = QPlainTextEdit()
        self.stats_text.setPlaceholderText("One stat per line, e.g.\n+2 To All Skills\nDefense: 98")
        layout.addRow("Stats:", self.stats_text)

        self.sockets_spin = QSpinBox()
        self.sockets_spin.setRange(0, 6)
        layout.addRow("Sockets:", self.sockets_spin)

        self.ethereal_check = QCheckBox("Ethereal")
        layout.addRow("", self.ethereal_check)

        self.level_spin = QSpinBox()
        self.level_spin.setRange(0, 99)
        layout.addRow("Required Level:", self.level_spin)

        self.notes_edit = QLineEdit()
        layout.addRow("Notes:", self.notes_edit)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("SAVE")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addRow(btn_row)

    def raw_text(self) -> str:
        """Reconstructs pseudo-OCR text so it can flow through the same
        parser as a real capture, per spec §42's requirement to reuse
        the exact same database service."""
        lines = [self.name_edit.text().strip()]
        if self.base_edit.text().strip():
            lines.append(self.base_edit.text().strip())
        lines.append(self.quality_combo.currentText())
        if self.level_spin.value():
            lines.append(f"Required Level: {self.level_spin.value()}")
        if self.sockets_spin.value():
            lines.append(f"Socketed ({self.sockets_spin.value()})")
        if self.ethereal_check.isChecked():
            lines.append("Ethereal (Cannot Be Repaired)")
        lines.extend(self.stats_text.toPlainText().splitlines())
        return "\n".join(l for l in lines if l.strip())

class ItemDetailsDialog(QDialog):
    """Inspect/edit a stored item after clicking it in the inventory grid."""
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.delete_requested = False
        self.setWindowTitle(item.name)
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        header = QLabel(item.name)
        header.setStyleSheet(f"font-size:20px;font-weight:700;color:{quality_color(item.quality)};")
        layout.addWidget(header)
        form = QFormLayout()
        self.name_edit = QLineEdit(item.name); form.addRow("Name:", self.name_edit)
        self.quality_combo = QComboBox(); self.quality_combo.addItems(ITEM_QUALITIES); self.quality_combo.setCurrentText(item.quality); form.addRow("Quality:", self.quality_combo)
        self.base_edit = QLineEdit(item.base_name or ""); form.addRow("Base:", self.base_edit)
        self.favorite = QCheckBox("Favorite"); self.favorite.setChecked(bool(item.is_favorite)); form.addRow("", self.favorite)
        self.tags_edit = QLineEdit(", ".join(item.tags or [])); self.tags_edit.setPlaceholderText("keep, trade, grail"); form.addRow("Tags:", self.tags_edit)
        self.notes_edit = QPlainTextEdit(item.notes or ""); self.notes_edit.setMaximumHeight(90); form.addRow("Notes:", self.notes_edit)
        layout.addLayout(form)

        stat_lines = []
        for label, value in [
            ("Defense", item.defense), ("Damage", f"{item.damage_min}-{item.damage_max}" if item.damage_min is not None else None),
            ("Required level", item.required_level), ("Sockets", item.socket_count or None),
            ("FCR", f"{item.faster_cast_rate}%" if item.faster_cast_rate else None),
            ("FHR", f"{item.faster_hit_recovery}%" if item.faster_hit_recovery else None),
            ("Magic Find", f"{item.magic_find}%" if item.magic_find else None),
        ]:
            if value is not None: stat_lines.append(f"{label}: {value}")
        if item.ethereal: stat_lines.append("Ethereal")
        for k,v in (item.resistances or {}).items(): stat_lines.append(f"{k.title()} Resist: {v:+d}%")
        for skill in (item.skills or []): stat_lines.append(f"+{skill.get('amount')} {skill.get('skill')}")
        if item.screenshot_path: stat_lines.append(f"Screenshot: {item.screenshot_path}")
        stats = QPlainTextEdit("\n".join(stat_lines) or "No structured stats parsed."); stats.setReadOnly(True); stats.setMaximumHeight(150)
        layout.addWidget(stats)

        if item.raw_ocr_text:
            raw = QPlainTextEdit(item.raw_ocr_text); raw.setReadOnly(True); raw.setMaximumHeight(120)
            layout.addWidget(QLabel(f"Raw OCR ({item.ocr_confidence or 0:.0f}%):")); layout.addWidget(raw)

        row = QHBoxLayout()
        delete_btn = QPushButton("DELETE ITEM"); delete_btn.clicked.connect(self._delete)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        save = QPushButton("SAVE CHANGES"); save.setObjectName("Primary"); save.clicked.connect(self.accept)
        row.addWidget(delete_btn); row.addStretch(); row.addWidget(cancel); row.addWidget(save); layout.addLayout(row)

    def _delete(self):
        self.delete_requested = True
        self.accept()

    def values(self):
        return {
            "name": self.name_edit.text().strip() or self.item.name,
            "quality": self.quality_combo.currentText(),
            "base_name": self.base_edit.text().strip() or None,
            "is_favorite": self.favorite.isChecked(),
            "tags": [x.strip() for x in self.tags_edit.text().split(",") if x.strip()],
            "notes": self.notes_edit.toPlainText().strip() or None,
        }

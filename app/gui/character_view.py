"""D2R Vault — character vault (dashboard) and create/edit dialog."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from app.config import CHARACTER_CLASSES, DIFFICULTIES
from app.gui.theme import GOLD_BRIGHT

CLASS_ICONS = {
    "Amazon": "🏹", "Assassin": "🗡️", "Barbarian": "⚔️", "Druid": "🐺",
    "Necromancer": "💀", "Paladin": "🛡️", "Sorceress": "🧙",
}


class CreateCharacterDialog(QDialog):
    def __init__(self, parent=None, character=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Character" if character else "Create Character")
        self.setMinimumWidth(340)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit(character.name if character else "")
        layout.addRow("Character Name:", self.name_edit)

        self.class_combo = QComboBox()
        self.class_combo.addItems(CHARACTER_CLASSES)
        if character:
            self.class_combo.setCurrentText(character.char_class)
        layout.addRow("Class:", self.class_combo)

        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 99)
        self.level_spin.setValue(character.level if character else 1)
        layout.addRow("Level:", self.level_spin)

        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(DIFFICULTIES)
        if character:
            self.difficulty_combo.setCurrentText(character.difficulty)
        layout.addRow("Difficulty:", self.difficulty_combo)

        self.season_edit = QLineEdit(character.season if character and character.season else "")
        self.season_edit.setPlaceholderText("optional")
        layout.addRow("Season:", self.season_edit)

        self.hardcore_check = QCheckBox("Hardcore")
        self.hardcore_check.setChecked(bool(character.hardcore) if character else False)
        layout.addRow("", self.hardcore_check)

        self.ladder_check = QCheckBox("Ladder")
        self.ladder_check.setChecked(bool(character.ladder) if character else True)
        layout.addRow("", self.ladder_check)

        btn_row = QHBoxLayout()
        create_btn = QPushButton("SAVE CHARACTER" if character else "CREATE CHARACTER")
        create_btn.setObjectName("Primary")
        create_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(create_btn)
        layout.addRow(btn_row)

    def values(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "char_class": self.class_combo.currentText(),
            "level": self.level_spin.value(),
            "difficulty": self.difficulty_combo.currentText(),
            "season": self.season_edit.text().strip() or None,
            "hardcore": self.hardcore_check.isChecked(),
            "ladder": self.ladder_check.isChecked(),
        }


class CharacterVaultView(QWidget):
    """Dashboard listing all characters (spec §2)."""

    character_selected = Signal(int)
    create_character_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("D2R VAULT")
        title.setObjectName("Title")
        header.addWidget(title)
        header.addStretch()
        create_btn = QPushButton("+ Create Character")
        create_btn.setObjectName("Primary")
        create_btn.clicked.connect(self.create_character_requested.emit)
        header.addWidget(create_btn)
        layout.addLayout(header)

        subtitle = QLabel("Character Vault")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(subtitle)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("Panel")
        # Treat a normal single click as selecting/opening the character.
        # itemActivated alone requires double-click/Enter on many platforms, which
        # made the UI look selected while MainWindow still had no active character.
        self.list_widget.itemClicked.connect(self._on_item_activated)
        self.list_widget.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self.list_widget)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        character_id = item.data(1000)
        if character_id is not None:
            self.character_selected.emit(character_id)

    def refresh(self, characters: list, stats_by_id: dict[int, dict] | None = None) -> None:
        self.list_widget.clear()
        stats_by_id = stats_by_id or {}
        for char in characters:
            icon = CLASS_ICONS.get(char.char_class, "🎮")
            stats = stats_by_id.get(char.id, {})
            item_count = stats.get("total_items", 0)
            label = f"{icon}  {char.name}    {char.char_class}\n     Level {char.level}          {item_count} items"
            item = QListWidgetItem(label)
            item.setData(1000, char.id)
            self.list_widget.addItem(item)

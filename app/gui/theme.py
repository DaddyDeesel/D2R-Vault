"""
D2R Vault — visual theme.

Dark charcoal background, subtle gold accents, stone/metal panel
styling — "Diablo II stash management meets modern desktop software"
(spec §43), implemented as a single Qt stylesheet so it's easy to
retheme later.
"""

GOLD = "#c9a24b"
GOLD_BRIGHT = "#e8c874"
CHARCOAL = "#15141a"
PANEL = "#1f1d26"
PANEL_LIGHT = "#2a2732"
BORDER = "#3a3542"
TEXT = "#e8e3d8"
TEXT_DIM = "#a49d8f"

QUALITY_COLORS = {
    "Normal": "#c9c9c9",
    "Superior": "#c9c9c9",
    "Magic": "#6c6cf0",
    "Rare": "#e8d24b",
    "Set": "#4be86c",
    "Unique": "#c99a3a",
    "Crafted": "#e8a34b",
    "Rune": "#e88f4b",
    "Gem": "#4bc9e8",
    "Charm": "#e84bd8",
    "Jewel": "#e84bd8",
    "Runeword": "#c99a3a",
    "Quest": "#e8e34b",
    "Miscellaneous": "#a49d8f",
}

STYLESHEET = f"""
QWidget {{
    background-color: {CHARCOAL};
    color: {TEXT};
    font-family: 'Segoe UI', 'Cinzel', sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {CHARCOAL};
}}

#Panel {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}

QLabel#Title {{
    color: {GOLD_BRIGHT};
    font-size: 22px;
    font-weight: 600;
    letter-spacing: 1px;
}}

QLabel#Subtitle {{
    color: {TEXT_DIM};
    font-size: 12px;
}}

QPushButton {{
    background-color: {PANEL_LIGHT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 14px;
}}

QPushButton:hover {{
    background-color: {BORDER};
    border: 1px solid {GOLD};
    color: {GOLD_BRIGHT};
}}

QPushButton#Primary {{
    background-color: {GOLD};
    color: {CHARCOAL};
    font-weight: 600;
    border: none;
}}

QPushButton#Primary:hover {{
    background-color: {GOLD_BRIGHT};
}}

QListWidget, QTreeWidget, QTableWidget {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    alternate-background-color: {PANEL_LIGHT};
}}

QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {BORDER};
    color: {GOLD_BRIGHT};
}}

QLineEdit, QComboBox, QSpinBox {{
    background-color: {PANEL_LIGHT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    color: {TEXT};
}}

QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {GOLD};
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {PANEL};
}}

QTabBar::tab {{
    background-color: {PANEL_LIGHT};
    color: {TEXT_DIM};
    padding: 6px 16px;
    border: 1px solid {BORDER};
    border-bottom: none;
}}

QTabBar::tab:selected {{
    background-color: {PANEL};
    color: {GOLD_BRIGHT};
    border-bottom: 2px solid {GOLD};
}}

QScrollBar:vertical {{
    background: {PANEL};
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
}}

QToolTip {{
    background-color: {PANEL_LIGHT};
    color: {GOLD_BRIGHT};
    border: 1px solid {GOLD};
    padding: 4px;
}}
"""


def quality_color(quality: str) -> str:
    return QUALITY_COLORS.get(quality, TEXT)

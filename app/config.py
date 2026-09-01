"""D2R Vault application configuration."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

APP_NAME = "D2R Vault"
APP_VERSION = "0.2.0"
BASE_DIR = Path(__file__).resolve().parent.parent

# PyInstaller one-file apps are extracted into a temporary _MEIPASS folder.
# Never put mutable user data there: it may disappear on exit. Assets are read
# from the bundle, while DB/settings/captures live in a persistent user folder.
if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    if os.name == "nt":
        USER_DATA_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "D2R Vault"
    else:
        USER_DATA_ROOT = Path.home() / ".local" / "share" / "d2r-vault"
else:
    RESOURCE_DIR = BASE_DIR
    USER_DATA_ROOT = BASE_DIR

DATA_DIR = USER_DATA_ROOT / "data"
BACKUP_DIR = DATA_DIR / "backups"
CAPTURES_DIR = DATA_DIR / "captures"
LOG_DIR = USER_DATA_ROOT / "logs"
ASSETS_DIR = RESOURCE_DIR / "assets"
DB_PATH = DATA_DIR / "d2r_vault.db"
SETTINGS_PATH = DATA_DIR / "settings.json"
LOG_PATH = LOG_DIR / "d2r_vault.log"

for d in (DATA_DIR, BACKUP_DIR, CAPTURES_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

CHARACTER_CLASSES = ["Amazon", "Assassin", "Barbarian", "Druid", "Necromancer", "Paladin", "Sorceress"]
DIFFICULTIES = ["Normal", "Nightmare", "Hell"]
ITEM_QUALITIES = [
    "Normal", "Superior", "Magic", "Rare", "Set", "Unique", "Crafted",
    "Rune", "Gem", "Charm", "Jewel", "Runeword", "Quest", "Miscellaneous",
]
CONTAINERS = ["Equipped", "Inventory", "Personal Stash", "Shared Stash", "Cube", "Mercenary"]
EQUIPMENT_SLOTS = ["Helm", "Amulet", "Weapon", "Shield", "Armor", "Gloves", "Belt", "Boots", "Ring1", "Ring2"]
GRID_SIZES = {
    "Equipped": (4, 4), "Inventory": (10, 4), "Personal Stash": (10, 10),
    "Shared Stash": (10, 10), "Cube": (3, 4), "Mercenary": (2, 3),
}
DEFAULT_HOTKEYS = {"capture": "F9", "rapid_scan": "F10", "open_vault": "F11", "pause": "F12"}
TOOLTIP_CAPTURE_MODES = ["Automatic", "Fixed Region", "Manual Selection"]

@dataclass
class Settings:
    hotkeys: dict = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))
    tooltip_capture_mode: str = "Fixed Region"
    fixed_region: dict = field(default_factory=lambda: {"x": 0, "y": 0, "width": 400, "height": 300})
    save_screenshots: bool = True
    ocr_engine: str = "tesseract"
    ocr_language: str = "eng"
    tesseract_cmd: str = ""
    ocr_confidence_threshold: float = 60.0
    rapid_scan_delay_seconds: float = 0.5
    automatic_backups: bool = True
    backup_frequency: str = "Daily"
    backups_to_keep: int = 10
    theme: str = "dark_fantasy"

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> "Settings":
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                base = asdict(cls())
                base.update(data)
                return cls(**base)
            except (json.JSONDecodeError, TypeError, OSError):
                return cls()
        return cls()

    def save(self, path: Path = SETTINGS_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

def get_settings() -> Settings:
    return Settings.load()

"""D2R Vault — backup service (spec §29)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from app import config
from app.database.database import backup_database, restore_backup


class BackupService:
    def __init__(self, db_path: Path = config.DB_PATH, backup_dir: Path = config.BACKUP_DIR):
        self.db_path = db_path
        self.backup_dir = backup_dir

    def backup_now(self) -> Path | None:
        return backup_database(self.db_path, self.backup_dir)

    def list_backups(self) -> list[Path]:
        if not self.backup_dir.exists():
            return []
        return sorted(self.backup_dir.glob("d2r_vault_*.db"), reverse=True)

    def restore(self, backup_path: Path) -> None:
        # Snapshot the current state first so a bad restore is itself
        # recoverable.
        backup_database(self.db_path, self.backup_dir)
        restore_backup(backup_path, self.db_path)

    def is_backup_due(self, settings: config.Settings) -> bool:
        if not settings.automatic_backups:
            return False
        backups = self.list_backups()
        if not backups:
            return True
        latest = backups[0]
        age = dt.datetime.now() - dt.datetime.fromtimestamp(latest.stat().st_mtime)
        if settings.backup_frequency == "Daily":
            return age >= dt.timedelta(days=1)
        if settings.backup_frequency == "Weekly":
            return age >= dt.timedelta(weeks=1)
        return age >= dt.timedelta(days=1)

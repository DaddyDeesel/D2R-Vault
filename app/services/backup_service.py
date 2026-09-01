"""D2R Vault — backup service."""
from __future__ import annotations
import datetime as dt
from pathlib import Path
from app import config
from app.database.database import backup_database, restore_backup

class BackupService:
    def __init__(self, db_path: Path = config.DB_PATH, backup_dir: Path = config.BACKUP_DIR, keep: int | None = None):
        self.db_path = db_path; self.backup_dir = backup_dir; self.keep = keep
    def backup_now(self) -> Path | None:
        path = backup_database(self.db_path, self.backup_dir)
        if path and self.keep:
            backups = sorted(self.list_backups(), key=lambda p:p.stat().st_mtime, reverse=True)
            for old in backups[self.keep:]: old.unlink(missing_ok=True)
        return path
    def list_backups(self):
        return sorted(self.backup_dir.glob("d2r_vault_*.db"), reverse=True) if self.backup_dir.exists() else []
    def restore(self, backup_path: Path):
        backup_database(self.db_path, self.backup_dir); restore_backup(backup_path, self.db_path)
    def is_backup_due(self, settings: config.Settings) -> bool:
        if not settings.automatic_backups: return False
        backups = self.list_backups()
        if not backups: return True
        age = dt.datetime.now() - dt.datetime.fromtimestamp(backups[0].stat().st_mtime)
        return age >= (dt.timedelta(weeks=1) if settings.backup_frequency == "Weekly" else dt.timedelta(days=1))

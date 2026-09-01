"""
D2R Vault — database engine/session management.

Handles engine creation, schema creation, lightweight version tracking,
and "backup before migration" (spec §53).
"""
from __future__ import annotations

import shutil
import datetime as dt
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app import config
from app.database.models import Base, CURRENT_SCHEMA_VERSION, SchemaVersion


def make_engine(db_path: Path = config.DB_PATH, *, echo: bool = False):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=echo, future=True)
    return engine


def backup_database(db_path: Path = config.DB_PATH, backup_dir: Path = config.BACKUP_DIR) -> Path | None:
    """Copy the current DB file into the backups folder with a timestamp."""
    if not db_path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")
    dest = backup_dir / f"d2r_vault_{stamp}.db"
    shutil.copy2(db_path, dest)
    _prune_backups(backup_dir)
    return dest


def _prune_backups(backup_dir: Path, keep: int = 10) -> None:
    backups = sorted(backup_dir.glob("d2r_vault_*.db"), key=lambda p: p.stat().st_mtime)
    while len(backups) > keep:
        oldest = backups.pop(0)
        oldest.unlink(missing_ok=True)


def restore_backup(backup_path: Path, db_path: Path = config.DB_PATH) -> None:
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    shutil.copy2(backup_path, db_path)


def _get_or_create_schema_version(session: Session) -> SchemaVersion:
    row = session.execute(select(SchemaVersion).limit(1)).scalar_one_or_none()
    if row is None:
        row = SchemaVersion(version=CURRENT_SCHEMA_VERSION)
        session.add(row)
        session.commit()
    return row


def init_db(db_path: Path = config.DB_PATH, *, echo: bool = False):
    """Create tables if needed, back up before applying any future migration,
    and return a sessionmaker bound to the engine."""
    db_existed = db_path.exists()

    if db_existed:
        # Always snapshot before we touch schema, in case a migration runs.
        backup_database(db_path)

    engine = make_engine(db_path, echo=echo)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    with SessionLocal() as session:
        version_row = _get_or_create_schema_version(session)
        if version_row.version < CURRENT_SCHEMA_VERSION:
            # Placeholder for future migration steps. Each step should be
            # additive (ALTER TABLE ADD COLUMN, new tables) and never drop
            # existing item data.
            version_row.version = CURRENT_SCHEMA_VERSION
            session.commit()

    return SessionLocal


_SessionLocal = None


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = init_db()
    return _SessionLocal


def reset_session_factory():
    """Dispose pooled SQLite connections and clear the cached session factory.

    The next call to get_session_factory() recreates the engine/factory. Keeping
    disposal and recreation separate is important when replacing the DB file on
    Windows, where an open SQLite handle can lock or retain the old file.
    """
    global _SessionLocal
    if _SessionLocal is not None:
        bind = _SessionLocal.kw.get("bind")
        if bind is not None:
            bind.dispose()
    _SessionLocal = None

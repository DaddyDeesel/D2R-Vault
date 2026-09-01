# D2R Vault

A companion inventory-management tool for **Diablo II: Resurrected**. Hover over
an item in-game, press **F9**, and D2R Vault captures the tooltip, reads it with
OCR, parses it into structured stats, and — after you confirm — saves it into a
searchable local database of your characters' gear.

D2R Vault **never** touches the game itself: no memory reads, no file
modification, no code injection, no automated clicks or keypresses sent into
D2R. Everything happens externally via screen capture and a global hotkey.

```
PLAY D2R → Hover Item → F9 → OCR → Confirm → SAVE → Continue Playing
```

## Status: Phases 1–5 complete, Phase 6/7 partial

This is a real, running application — not a mockup — built in the phased order
the spec calls for.

| Phase | Status |
|---|---|
| 1. Foundation (project setup, DB, models, character CRUD) | ✅ Done |
| 2. Inventory (grid view, drag/drop placement, collision detection) | ✅ Done |
| 3. Capture (global F9 hotkey, screen capture, region config) | ✅ Done |
| 4. OCR (multi-pass preprocessing, Tesseract, confidence scoring) | ✅ Done |
| 5. Parser (name/quality/base detection, stat parsing, fuzzy matching) | ✅ Done |
| 6. Advanced (Rapid Scan, duplicates, favorites, search, Grail tracking, demo mode) | ✅ Core done, wishlists/build planner/comparison UI not yet built |
| 7. Polish (tray, notifications, backups, export, settings) | ✅ Core done, installer/icons not yet built |

Not yet implemented (models exist where noted, but no UI): item comparison
view, build planner calculations, wishlist UI, roll-percentage tracking,
"God Roll"/"Charsi This?"/"Stash Cleanup" extras, OCR-correction feedback loop
wired into the live parse path (the `ocr_corrections` table and repository
exist and are ready to be wired in), and a real icon asset pipeline (folders
exist under `assets/items/`, empty by design — see spec §25, no copyrighted
assets are bundled).

## Requirements

- Windows 10/11 (target platform — screen capture, global hotkeys, and the
  packaged `.exe` are all Windows-oriented)
- Python 3.12+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed and
  on your `PATH`

## Setup

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bat
python -m app.main
```

On first launch the app creates `data\d2r_vault.db` and opens an empty
Character Vault. Create a character, open it, then set your capture region in
**Settings → Capture** (start with **Fixed Region** — draw a box around where
D2R tooltips usually appear on your screen — then try **Test Capture**).
**Automatic** tooltip detection is also implemented as a best-effort heuristic
you can switch to once Fixed Region is working reliably, per the spec's own
guidance to get a reliable configurable region working first.

To try the UI without D2R running:

```python
from app.database.database import get_session_factory
from app.services.demo_data import load_demo_data

session = get_session_factory()()
load_demo_data(session)
```

## Tests

```bat
pip install -r requirements-dev.txt
pytest
```

`tests/test_normalize.py`, `test_stat_parser.py`, and `test_item_parser.py`
cover the OCR-tolerant parsing pipeline directly (no GUI/DB/OCR-engine
dependencies — these were verified to pass during development).
`tests/test_services.py` covers character/item/inventory CRUD, duplicate
detection, collision detection, and search, using an in-memory SQLite DB via
`tests/conftest.py`.

## Building the Windows executable

```bat
build_windows.bat
```

Produces `dist\D2R-Vault.exe` via PyInstaller. Tesseract itself is **not**
bundled — it must be installed separately on the machine running the `.exe`
(see Requirements above), or you can point
`pytesseract.pytesseract.tesseract_cmd` in `app/ocr/ocr_engine.py` at a
portable Tesseract binary you ship alongside the app.

## Architecture

```
app/
  main.py              entry point
  config.py            paths, constants, persisted Settings
  database/            SQLAlchemy models, engine/session, repositories
  gui/                 PySide6 views (dark-fantasy themed)
  capture/             screen capture, global hotkeys, tooltip region detection
  ocr/                 image preprocessing + Tesseract wrapper (swappable engine)
  parser/              OCR-tolerant text → structured ParsedItem
  services/            business logic layer (character/item/inventory/search/
                        export/backup/capture orchestration)
tests/                 pytest suite
data/                  SQLite DB, backups, saved capture screenshots
assets/                item icon folders (bring your own, see spec §25)
```

Every layer is swappable by design (spec §50): `OCREngine`, `ScreenCapture`,
and `ItemParser`-equivalent logic are all defined as small interfaces with a
mock implementation used in tests, so Tesseract can later be replaced with a
different OCR engine or an AI vision model without touching the GUI or
database code.

## Privacy

All data is local. No cloud account, no telemetry, no Battle.net interaction,
no network connection required to run the core application.

---

## v0.2 quick start on Windows

The easiest source-code launch is now:

```bat
setup_and_run_windows.bat
```

It creates `.venv`, installs `requirements.txt`, and launches the app. You still
need the **Tesseract OCR engine** installed separately. If Tesseract is not on
PATH, open **Settings → OCR → Browse** and select `tesseract.exe` (commonly
`C:\Program Files\Tesseract-OCR\tesseract.exe`).

For a packaged build, run:

```bat
build_windows.bat
```

The one-file build stores your mutable data outside the temporary PyInstaller
bundle under:

```text
%LOCALAPPDATA%\D2R Vault\data
```

That folder contains the SQLite database, settings, backups, and saved capture
screenshots. See `CHANGELOG-v0.2.md` for the fixes added in this release.

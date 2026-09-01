# D2R Vault v0.2 changes

## Reliability / Windows packaging
- Version bumped to 0.2.0.
- Packaged one-file builds now store mutable data in `%LOCALAPPDATA%\D2R Vault` instead of PyInstaller's temporary extraction folder.
- `build_windows.bat` no longer fails just because a custom `.ico` file is missing.
- Build script uses `python -m PyInstaller`, cleans old build state, and stops on dependency/build failures.
- System-tray **Exit** now actually exits instead of being intercepted by the minimize-to-tray close handler.
- Automatic backup is checked at startup, and the configured backup retention count is honored.

## Capture / OCR
- Added a real full-screen drag selector for **Manual Selection** capture mode.
- Added configurable Tesseract executable path under Settings → OCR.
- Tesseract detection now checks the configured path, PATH, and the common Windows install location.
- Rapid Scan now honors its configured cooldown.
- Rapid Scan saves the capture screenshot path onto the item record instead of leaving orphaned screenshots.
- Rapid Scan reports skipped duplicates.

## Settings / data management
- Saving changed hotkeys now restarts/re-registers the global hotkey listener immediately.
- Restore Backup, Import Database, and Export Inventory buttons are wired up.
- Export supports XLSX, CSV, and JSON.
- Restore/import dispose and rebuild SQLite connections around database replacement.

## Inventory UX
- Clicking an inventory item now opens a details window.
- Stored items can be renamed, reclassified, favorited, tagged, annotated, or deleted.
- Raw OCR text, OCR confidence, parsed stats, and screenshot path are visible in item details.

## Tests
- Corrected the collision test whose assertion contradicted `exclude_item_id` semantics: an item's own occupied cells must be ignored while testing a move of that same item.

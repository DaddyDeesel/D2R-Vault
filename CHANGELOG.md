# Changelog

## v0.2 — 2026-09-02

D2R Treasure Vault v0.2 is the first full portable release of the stash browser and d2jsp sales workflow.

### Added

- Diablo II-themed, searchable inventory browser backed by a user-selected D2R Manager `items.db`.
- Account, character, stash tab, carried-inventory, materials-tab, and grid-position item locator.
- Mule selection for personal stash and carried inventory.
- Collection, character, item-type, and quality filtering.
- Gear subtype filters for Sets, Uniques, and Bases.
- Charm-size and Charm/Jewel quality filtering.
- Stash-only Inventory Log with optional carried-inventory tracking.
- Per-collection Inventory Log preferences with All / None controls.
- Added, removed, quantity, moved, and changed activity entries with before/after locations.
- Manual FG pricing and targeted d2jsp price searches.
- Editable BBCode composer, formatted preview, browser autosave, copy, and text export.
- Automatic read-only refresh when the selected stash table changes.
- Portable Windows x64 package with first-run database selection and local shutdown helper.

### Inventory behavior

- Excludes equipped items, mercenary items, and `drop_log` records.
- Combines material stack quantities.
- Orders runes El through Zod and gems by gem and quality tier.
- Omits unverified empty material records.
- Shows important variable rolls for Sets, Uniques, and Runewords.

### Validation

The packaged ZIP was tested from a fresh extraction using synthetic inventory. Checks cover first-run setup, settings persistence, artwork, item-type data, live database refresh, shutdown/restart, inventory scope, change matching, log collection preferences, subtype filters, pricing, and post generation.

## v0.1.0-test2 — 2026-09-02

Tester package with the first Item Locator and readable inventory activity log.

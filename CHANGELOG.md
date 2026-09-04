# Changelog

## v0.3.1 — 2026-09-04

D2R Treasure Vault v0.3.1 expands search and sale-post customization while making account and mule boundaries explicit.

### Added

- Fuzzy D2R shorthand and structured stat searches, including `hoz`, `hoto`, `pcomb`, `35 spirit`, `3os armor`, `FCR >= 10`, socket comparisons, resistance comparisons, and ethereal filters.
- Blizzard Sorceress, Nova Sorceress, and Hammerdin package builders with custom saved build templates, ranked alternatives, item locations, retrieval checklists, and sale-selection support.
- Conservative unidentified unique inference. An unidentified item receives a unique name only when its base has one valid unique definition, and the visible name retains `(Unid)`.
- Persistent JSP Post Template Editor for main headings, main subtext, category headings, subtitles, BBCode previews, quick inserts, identifiers, and custom categories.
- Sanitized inventory, package-builder, and JSP-template screenshots in the project README.

### Changed

- Package searches use account shared stashes and only the personal stashes and carried inventories enabled under **Select Mules**.
- Shared locations are labeled by account, shared page, or account material section without attributing account-wide stock to a character.
- The organizer selects one deterministic latest shared snapshot per account. Equal-timestamp observations from another character are audit records and never additional sale quantity.

### Fixed

- Restored the **Add selected vault items** handler after adding the JSP template controls.
- Prevented the `arach` alias from fuzzily matching unrelated items such as Godstrike Arch.
- Prevented the Eth rune from matching the `ethereal` item filter.

### Validation

- Browser checks cover mule-scoped package counts, shared locator labels, unidentified Arachnid Mesh search, custom post headings, and browser persistence.
- A synthetic duplicate-snapshot test added 214 equal-timestamp shared rows under a second character; output remained 715 listings and 7,663 units.

## v0.3 — 2026-09-02

D2R Treasure Vault v0.3 adds portable trade-list backups and reusable smart searches without crowding the main inventory view.

### Added

- Saved searches for reusable query, collection, character, item-type, quality, and live priced/unpriced filter combinations.
- JSON and CSV trade-list backups containing selected listings, asking prices, and recorded locations.
- Trade-list import that restores available selections and prices, with stable identity fallback and a clear count of unavailable items.

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

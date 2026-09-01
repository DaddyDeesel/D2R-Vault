# D2R Vault v0.2.2

- Rejects stash/UI labels such as `Gems`, `Runes`, `Personal`, `Shared`, `Inventory`, and `Stash` instead of saving them as items.
- Adds item-tooltip evidence validation after OCR, while still allowing real gems/runes and unknown items.
- Automatic capture now uses the foreground Windows client area, supporting D2R fullscreen, borderless, and windowed modes.
- Automatic tooltip detection now merges text glyphs into tooltip-sized blocks and favors blocks near the mouse cursor.
- Automatic fallback region is cursor-centered and clipped to the D2R client area rather than assuming a fixed desktop center.
- New installs default to Automatic capture mode; existing saved settings are preserved.

# BL2-F7 v0.4 — Per-game configuration import/export

Adds a dedicated submenu inside Borderlands 2 per-game settings:

- **Importar configuração** — imports a `.ini` and replaces only the BL2 per-game profile.
- **Exportar configuração** — saves the current BL2 per-game profile as `010096F00FF22000.ini`.

The global Eden/BL2-F7 config is never replaced. Import uses a temporary file, validates a small INI payload, keeps a rollback backup during replacement, unloads/reloads `NativeConfig`, and refreshes the settings list. Import is disabled while emulation is running to avoid partially applying non-runtime-modifiable options.

The implementation uses Android's Storage Access Framework (`OpenDocument` / `CreateDocument`), so it does not require broad storage permission.

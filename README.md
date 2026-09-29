# BL2-F7 v0.4 — Single-Title + Turnip V36 + 60 FPS built-in

Fork/patch kit for **Eden v0.2.1** targeting **Borderlands 2** on **POCO F7 / Snapdragon 8s Gen 4 / Adreno 825**.

Base Eden revision:

`58c1e20ee58efa3900ba616207d460886214480b`

## What v0.3 changes

- BL2-only library filtering and native boot guard.
- Borderlands 2 title ID: `010096F00FF22000`.
- Pinned Turnip Gen8 V36 downloaded during GitHub Actions and verified by SHA-256.
- V36 is staged automatically on POCO F7 before Vulkan initialization.
- Built-in 60 FPS IPS32 patch: no external `load/` mod folder is required.
- Three BL2 Build IDs from the supplied `Borderlands2GOTY60FPS.zip` are supported.
- F7 preset: NCE, Vulkan, 1x, GPU Fast, shader cache ON, Vulkan pipeline cache ON,
  Sync Memory Operations ON, Force Max Clock ON, 6 pipeline workers, touch overlay OFF.
- Pipeline and DMA-sync profiling remain in the instrumented build.
- The earlier `nice(+10)` background-priority experiment is **not applied** in v0.3.

## Built-in 60 FPS Build IDs

- `B5EA86B6AEFEEB73E61BC385C1E77F17`
- `F367DE313B111EFF909C2A5C5D43E3F8`
- `F7C233469F20EE3F2383F3CD5BCF775A`

If the BL2 `main` NSO has one of these Build IDs, BL2-F7 applies the matching 19-byte IPS32 patch directly from the emulator core.

## Turnip V36

The workflow downloads:

`https://github.com/StevenMXZ/Adreno-Tools-Drivers/releases/download/v36/Turnip_Gen8_V36.zip`

Expected archive SHA-256:

`a7b1209e9cd4e87aac70e46991d7f07465810ef667fcead24ae82bfa68d7388a`

Only `libvulkan_freedreno.so` and `meta.json` are embedded into the `bl2F7` flavor assets.

## Build on GitHub

1. Replace the contents of your `AmzHook/BL2-F7` repository with this package.
2. Keep `.github/workflows/build-bl2-f7.yml` at exactly that path.
3. Open **Actions → Build BL2-F7 Android → Run workflow**.
4. First choose `instrumented`.
5. After validating 60 FPS / shader behavior, build `release`.

The workflow installs Android SDK 36, NDK 28.2, CMake 3.22.1 and `glslang-tools`, then checks out the exact Eden v0.2.1 commit and applies this patch kit.

## Logs to look for

Successful built-in mod:

`[BL2-F7] Applying built-in 60 FPS IPS32 patch for Build ID ...`

Unsupported BL2 build:

`[BL2-F7] No built-in 60 FPS patch for Build ID ...`

Shader/pipeline stall:

`[BL2-F7] runtime graphics pipeline build: ...`

Sync-memory stall:

`[BL2-F7] DMA sync fence wait: ...`

## Important

This package does not include Borderlands 2 game data, firmware, keys or copyrighted game assets. It only modifies the Eden runtime and incorporates the tiny user-supplied IPS32 frame-rate patches.


## v0.4 config transfer

BL2 per-game settings now include a dedicated **Importar / Exportar configuração** submenu. See `docs/V04-CONFIG-TRANSFER.md`.

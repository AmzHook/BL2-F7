# BL2-F7 test protocol

Use the **same save, driver, game version, resolution and route** for every run.

## Baseline route

Pick a repeatable 2-3 minute section that includes the traversal area where the game drops from ~60 FPS and then recovers. Start each run from the same save/location.

## Runs

1. Eden v0.2.1 unmodified, same driver.
2. BL2-F7 v0.2, workers = 4 (default).
3. BL2-F7 v0.2, workers = 2.
4. BL2-F7 v0.2, workers = 6.
5. BL2-F7 v0.2, workers = 8 only if thermals/frametime remain good.

Restart the emulator between runs. The first run may populate caches; perform a cold-cache pass and then a warm-cache pass if possible.

## What to capture

- Average FPS and visible minimum FPS.
- Frame-time graph/screen recording if available.
- Temperature before/after.
- Driver name/version.
- Eden log lines containing `[BL2-F7]`.

Important log lines:

- `runtime graphics pipeline build` = a new graphics pipeline blocked the slow path for at least 0.5 ms.
- `runtime compute pipeline build` = compute-pipeline build cost.
- `DMA sync fence wait` = time spent waiting for Sync Memory Operations fences.

## Interpretation

If FPS drops line up with long `runtime ... pipeline build` entries, the next patch should focus on pipeline prewarming/cache behavior.

If drops line up with `DMA sync fence wait`, the next patch should investigate narrowing the BL2 synchronization workaround rather than disabling it globally.

If neither spikes while FPS falls, the next focus is GPU load/driver, texture streaming, or presentation rather than CPU pipeline work.

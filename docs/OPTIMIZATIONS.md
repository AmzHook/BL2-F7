# BL2-F7 v0.2 performance changes

## Applied

- Dedicated `bl2F7` Android flavor and package id.
- Profile activates only for Borderlands 2 Program ID `010096F00FF22000` on POCO F7 / SM8735 markers.
- NCE when compiled and available; multicore enabled.
- Vulkan, disk shader cache and Vulkan driver pipeline cache enabled.
- ASTC decode on GPU.
- Sync Memory Operations forced on because the target setup needs it to pass the intro.
- Adreno Force Maximum Clocks enabled.
- Async GPU and Async Presentation kept off to match Eden 0.2.1's Android stability choice.
- Pipeline worker control widened from 4..8 to 2..8; F7 default = 4.
- Pipeline build/serialization helper threads receive Android nice +10 so they are less likely to steal CPU time from NCE/GPU critical work.
- Runtime graphics/compute pipeline builds >=0.5 ms are timed and logged.
- Sync Memory Operations fence waits >=0.5 ms are timed and logged for BL2.
- Touch overlay/touchscreen disabled in the BL2-F7 target profile; physical gamepads remain enabled.

## Deliberately not forced

- Extended Dynamic State: driver-sensitive; benchmark before forcing.
- Async shaders: can reduce stalls but can produce rendering errors; not a safe default.
- Aggressive VRAM mode: can improve residency on some devices but increases crash risk.
- GPU Accuracy changes: left at Eden/per-game value to avoid introducing graphics regressions.
- Experimental synchronization removal: BL2 currently relies on Sync Memory Operations to boot on the target setup.
- Hard CPU affinity: not added in v0.2; incorrect cluster pinning can reduce performance on Android governors.

## Why this is not called “100% optimized”

No static patch can prove the optimum without measurements on the actual phone, driver and game route. v0.2 changes the most defensible bottlenecks and adds measurements that identify what remains. The next revision should be driven by those logs rather than guesses.

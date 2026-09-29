# BL2-F7 v0.2 Performance changelog

Base: Eden v0.2.1 `58c1e20ee58efa3900ba616207d460886214480b`.

- Dedicated `bl2F7` flavor and package `dev.bl2f7.runtime`.
- BL2 + POCO F7/SM8735 guarded performance profile.
- NCE/multicore/Vulkan/cache/ASTC GPU baseline.
- Sync Memory Operations ON and Force Maximum Clocks ON.
- Async GPU / Async Presentation OFF.
- Pipeline workers: 2..8 UI/runtime range; BL2-F7 default 4.
- Added Android background-priority helper using nice +10.
- Pipeline build and serialization workers use background priority.
- Added runtime graphics/compute pipeline timing logs >= 0.5 ms.
- Added BL2 DMA sync-fence timing logs >= 0.5 ms.
- Added static verifier and reproducible test protocol.

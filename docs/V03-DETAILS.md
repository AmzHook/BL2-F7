# BL2-F7 v0.3 technical notes

## Why the previous BL2-F7 build ran at 30 FPS

The BL2-F7 flavor uses a different Android application ID from the user's normal Eden install, so Eden's external `load/<title-id>/...` mod directory is not automatically shared. A 60 FPS patch installed in normal Eden therefore does not automatically exist in BL2-F7.

v0.3 removes that dependency by applying the supplied IPS32 data inside `PatchManager::PatchNSO()`.

## IPS32 integration

The supplied ZIP contained these exact files:

- `B5EA86B6AEFEEB73E61BC385C1E77F1700000000000000000000000000000000.ips`
- `F367DE313B111EFF909C2A5C5D43E3F800000000000000000000000000000000.ips`
- `F7C233469F20EE3F2383F3CD5BCF775A00000000000000000000000000000000.ips`

Each is 19 bytes and uses the `IPS32` format already supported by Eden's `PatchIPS()` implementation.

The built-in path also patches `HasNSOPatch()` so the NSO loader invokes `PatchNSO()` even when no external mod directory exists.

## V36 behavior

The driver is not stored in this repository. GitHub Actions fetches the official release archive, validates the pinned SHA-256 and extracts only:

- `libvulkan_freedreno.so`
- `meta.json`

The `bl2F7` flavor packages them as Android assets. On a detected POCO F7 / SM8735, `GpuDriverHelper` stages them into Eden's private custom-driver directory before native Vulkan initialization. If staging or loading fails, Eden's existing AdrenoTools path can fall back to the system driver.

## Performance philosophy

The user's normal Eden + V36 already performs well after shader compilation. Therefore v0.3 deliberately removes the previous experiment that lowered pipeline-worker priority with `nice(+10)`. The baseline keeps Eden v0.2.1 timing behavior and focuses on:

- 60 FPS patch guaranteed inside the runtime for known builds;
- persistent disk shader cache;
- Vulkan pipeline cache;
- six pipeline workers as the initial F7 preset;
- NCE and Vulkan;
- Sync Memory Operations enabled because BL2 requires it on this setup;
- profiling for remaining first-run shader and DMA stalls.

Aggressive EDS / GPU-unswizzle changes are not forced in the baseline because they can change graphics behavior and are not needed to reproduce the already-stable original Eden + V36 result.

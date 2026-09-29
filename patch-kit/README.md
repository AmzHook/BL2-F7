# BL2-F7 v0.2 Performance

Target: **Eden v0.2.1** commit `58c1e20ee58efa3900ba616207d460886214480b`, Android ARM64, POCO F7 / Snapdragon 8s Gen 4 / Adreno 825, Borderlands 2 Program ID `010096F00FF22000`.

This is a **source patch kit**, not Borderlands 2 and not an APK containing game data. It contains no game files, firmware, keys or proprietary assets.

## What changed from v0.1

v0.1 only applied a safe BL2/F7 boot profile. v0.2 also changes the pipeline-worker scheduling path and adds low-overhead bottleneck instrumentation:

- worker range 2..8, default 4 on BL2-F7;
- pipeline-builder and pipeline-serialization threads use Android nice +10;
- runtime graphics/compute pipeline build time is logged when >= 0.5 ms;
- DMA fence wait time from Sync Memory Operations is logged when >= 0.5 ms;
- exact v0.2.1 revision checking remains mandatory.

See `docs/OPTIMIZATIONS.md` for rationale and `docs/TEST-PROTOCOL.md` for A/B testing.

## Apply

Clone Eden recursively, then checkout the exact base:

```bash
git clone --recursive https://git.eden-emu.dev/eden-emu/eden.git
cd eden
git checkout 58c1e20ee58efa3900ba616207d460886214480b
git submodule update --init --recursive
```

From the Eden repository root:

```bash
python3 /path/to/BL2-F7-v0.2-performance-kit/scripts/apply_bl2_f7.py
python3 /path/to/BL2-F7-v0.2-performance-kit/scripts/verify_bl2_f7.py
```

The apply script refuses a dirty tree by default and refuses any revision other than the exact Eden v0.2.1 commit.

## Build

Eden v0.2.1 specifies Android 36 and NDK `28.2.13676358`. Use the project's Android setup plus Java 17.

Instrumented / test build:

```bash
cd src/android
./build-bl2-f7.sh
```

Equivalent:

```bash
./gradlew assembleBl2F7RelWithDebInfo
```

Release build after testing:

```bash
./build-bl2-f7-release.sh
```

To locate the APK:

```bash
find app/build/outputs/apk -type f -name '*.apk' -print
```

## Logs

Filter Android logs for:

```text
[BL2-F7]
```

The most useful lines are:

```text
[BL2-F7] Performance profile applied ...
[BL2-F7] runtime graphics pipeline build: ... us
[BL2-F7] runtime compute pipeline build: ... us
[BL2-F7] DMA sync fence wait: ... us
```

These distinguish pipeline/shader stalls from Sync Memory fence stalls, which is essential before making a more aggressive v0.3 patch.

## Expected performance effect

The patch is designed primarily to improve traversal smoothness and 1% lows by reducing CPU contention during pipeline work. It may also improve average FPS if the game was CPU/pipeline limited. If the scene is purely GPU-bound, average FPS may change little; in that case the next optimization target is the Vulkan driver/render path rather than more CPU tweaks.

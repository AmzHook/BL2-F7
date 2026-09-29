#!/usr/bin/env python3
"""Static verification after BL2-F7 v0.3 patch application."""

from pathlib import Path
import sys

root = Path.cwd()
checks = {
    "src/android/app/build.gradle.kts": [
        'create("bl2F7")',
        "-DBL2_F7=ON",
        "dev.bl2f7.runtime",
    ],
    "src/android/app/src/main/jni/CMakeLists.txt": [
        "bl2_f7_profile.cpp",
        "target_compile_definitions(video_core PRIVATE BL2_F7=1)",
        "target_compile_definitions(core PRIVATE BL2_F7=1)",
    ],
    "src/android/app/src/main/jni/native.cpp": [
        "BL2F7::TryApply",
        "Blocking non-Borderlands 2 launch",
    ],
    "src/android/app/src/main/java/org/yuzu/yuzu_emu/features/settings/model/Settings.kt": [
        "SECTION_BL2_CONFIG_TRANSFER",
    ],
    "src/android/app/src/main/java/org/yuzu/yuzu_emu/features/settings/ui/SettingsViewModel.kt": [
        "shouldImportGameConfig",
        "shouldExportGameConfig",
    ],
    "src/android/app/src/main/java/org/yuzu/yuzu_emu/features/settings/ui/SettingsFragmentPresenter.kt": [
        "addBl2ConfigTransferSettings",
        "Importar / Exportar configuração",
    ],
    "src/android/app/src/main/java/org/yuzu/yuzu_emu/features/settings/ui/SettingsFragment.kt": [
        "importBl2ConfigLauncher",
        "exportBl2ConfigLauncher",
        "SettingsFile.getCustomSettingsFile",
    ],
    "src/android/app/src/main/java/org/yuzu/yuzu_emu/utils/GameHelper.kt": [
        "BL2_PROGRAM_ID_DECIMAL",
        "isSupportedBl2ProgramId",
    ],
    "src/android/app/src/main/java/org/yuzu/yuzu_emu/model/GamesViewModel.kt": [
        "72223551841771520L",
        'dev.bl2f7.runtime',
    ],
    "src/android/app/src/main/java/org/yuzu/yuzu_emu/utils/GpuDriverHelper.kt": [
        "BL2_F7_TURNIP_V36_SHA256",
        "installBundledBl2F7DriverIfNeeded",
        "libvulkan_freedreno.so",
    ],
    "src/android/app/src/bl2F7/assets/bl2f7_driver/meta.json": [],
    "src/android/app/src/bl2F7/assets/bl2f7_driver/libvulkan_freedreno.so": [],
    "src/android/app/src/bl2F7/assets/bl2f7_driver/SOURCE.txt": [
        "Turnip Gen8 V36",
        "a7b1209e9cd4e87aac70e46991d7f07465810ef667fcead24ae82bfa68d7388a",
    ],
    "src/video_core/renderer_vulkan/vk_pipeline_cache.cpp": [
        "std::clamp(configured, 2, 8)",
        "runtime graphics pipeline build",
    ],
    "src/video_core/dma_pusher.cpp": [
        "DMA sync fence wait",
    ],
    "src/core/file_sys/patch_manager.cpp": [
        "BL2_F7_60FPS_B5EA86B6AEFEEB73",
        "BL2_F7_60FPS_F367DE313B111EFF",
        "BL2_F7_60FPS_F7C233469F20EE3F",
        "Applying built-in 60 FPS IPS32 patch",
        "B5EA86B6AEFEEB73E61BC385C1E77F17",
        "F367DE313B111EFF909C2A5C5D43E3F8",
        "F7C233469F20EE3F2383F3CD5BCF775A",
    ],
}

failed = False
for rel, needles in checks.items():
    p = root / rel
    if not p.exists():
        print(f"MISSING {rel}")
        failed = True
        continue
    if not needles:
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = ""
    for needle in needles:
        if needle not in text:
            print(f"MISSING ANCHOR {rel}: {needle}")
            failed = True

if failed:
    sys.exit(1)
print("BL2-F7 v0.4 static verification: OK")

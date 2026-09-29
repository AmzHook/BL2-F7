#!/usr/bin/env python3
"""Apply BL2-F7 v0.4 Single-Title + V36 + built-in 60 FPS + per-game config transfer to Eden v0.2.1.

Run from the Eden repository root:
    python3 /path/to/BL2-F7-v0.3/patch-kit/scripts/apply_bl2_f7.py

The patch is intentionally strict. It refuses unknown revisions and refuses to
patch a dirty tree unless --allow-dirty is supplied.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path.cwd()
KIT = Path(__file__).resolve().parents[1]
EXPECTED_SHA = "58c1e20ee58efa3900ba616207d460886214480b"
TURNIP_V36_SHA256 = "a7b1209e9cd4e87aac70e46991d7f07465810ef667fcead24ae82bfa68d7388a"
TURNIP_V36_ZIP = KIT / "vendor" / "Turnip_Gen8_V36.zip"


def die(msg: str) -> None:
    raise SystemExit(f"BL2-F7: {msg}")


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        die(f"expected exactly one patch anchor in {path}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def check_base(allow_dirty: bool) -> None:
    if not (ROOT / "src/android/app/build.gradle.kts").exists():
        die("run this script from the Eden repository root")
    try:
        sha = run("git", "rev-parse", "HEAD")
    except (FileNotFoundError, subprocess.CalledProcessError):
        die("git is required and HEAD must be readable")
    if sha != EXPECTED_SHA:
        die(f"expected Eden v0.2.1 {EXPECTED_SHA}, got {sha}")

    if not allow_dirty:
        status = run("git", "status", "--porcelain")
        if status:
            die("working tree is not clean; commit/stash changes or rerun with --allow-dirty")


def patch_gradle() -> None:
    path = ROOT / "src/android/app/build.gradle.kts"
    anchor = '''        create("genshinSpoof") {\n'''
    flavor = '''        create("bl2F7") {\n            dimension = "version"\n            manifestPlaceholders += mapOf("appNameBase" to "BL2-F7")\n            resValue("string", "app_name_suffixed", "BL2-F7")\n            applicationId = "dev.bl2f7.runtime"\n\n            externalNativeBuild {\n                cmake {\n                    arguments.add("-DBL2_F7=ON")\n                }\n            }\n\n            ndk {\n                abiFilters += listOf("arm64-v8a")\n            }\n        }\n\n'''
    replace_once(path, anchor, flavor + anchor)



def bundle_turnip_v36() -> None:
    if not TURNIP_V36_ZIP.exists():
        die(f"missing pinned Turnip V36 archive: {TURNIP_V36_ZIP}")

    digest = hashlib.sha256(TURNIP_V36_ZIP.read_bytes()).hexdigest()
    if digest != TURNIP_V36_SHA256:
        die(f"Turnip V36 checksum mismatch: expected {TURNIP_V36_SHA256}, got {digest}")

    asset_dir = ROOT / "src/android/app/src/bl2F7/assets/bl2f7_driver"
    asset_dir.mkdir(parents=True, exist_ok=True)

    required = {"libvulkan_freedreno.so", "meta.json"}
    with zipfile.ZipFile(TURNIP_V36_ZIP) as zf:
        by_basename = {
            Path(info.filename).name: info
            for info in zf.infolist()
            if not info.is_dir()
        }
        missing = required - set(by_basename)
        if missing:
            die(f"Turnip V36 archive missing: {sorted(missing)}")
        for name in sorted(required):
            (asset_dir / name).write_bytes(zf.read(by_basename[name]))

    (asset_dir / "SOURCE.txt").write_text(
        "Turnip Gen8 V36\\n"
        "https://github.com/StevenMXZ/Adreno-Tools-Drivers/releases/tag/v36\\n"
        f"archive_sha256={TURNIP_V36_SHA256}\\n",
        encoding="utf-8",
    )


def patch_android_single_title_and_driver() -> None:
    game_helper = ROOT / "src/android/app/src/main/java/org/yuzu/yuzu_emu/utils/GameHelper.kt"
    games_vm = ROOT / "src/android/app/src/main/java/org/yuzu/yuzu_emu/model/GamesViewModel.kt"
    driver_helper = ROOT / "src/android/app/src/main/java/org/yuzu/yuzu_emu/utils/GpuDriverHelper.kt"

    replace_once(
        game_helper,
        '''object GameHelper {\n    private const val KEY_OLD_GAME_PATH = "game_path"\n''',
        '''object GameHelper {\n    private const val BL2_F7_APPLICATION_ID_PREFIX = "dev.bl2f7.runtime"\n    private const val BL2_PROGRAM_ID_DECIMAL = 72223551841771520L\n    private const val KEY_OLD_GAME_PATH = "game_path"\n\n    private fun isBl2F7Build(): Boolean =\n        YuzuApplication.appContext.packageName.startsWith(BL2_F7_APPLICATION_ID_PREFIX)\n\n    private fun isSupportedBl2ProgramId(programId: String): Boolean =\n        programId.toLongOrNull() == BL2_PROGRAM_ID_DECIMAL\n''',
    )
    replace_once(
        game_helper,
        '''        if (programId.isEmpty()) {\n            programId = name.substring(0, name.lastIndexOf("."))\n        }\n\n        val newGame = Game(\n''',
        '''        if (programId.isEmpty()) {\n            programId = name.substring(0, name.lastIndexOf("."))\n        }\n\n        if (isBl2F7Build() && !isSupportedBl2ProgramId(programId)) {\n            return null\n        }\n\n        val newGame = Game(\n''',
    )

    replace_once(
        games_vm,
        '''    fun setGames(games: List<Game>) {\n        val sortedList = games.sortedWith(\n''',
        '''    fun setGames(games: List<Game>) {\n        val visibleGames = if (YuzuApplication.appContext.packageName.startsWith("dev.bl2f7.runtime")) {\n            games.filter { it.programId.toLongOrNull() == 72223551841771520L }\n        } else {\n            games\n        }\n        val sortedList = visibleGames.sortedWith(\n''',
    )

    replace_once(
        driver_helper,
        '''object GpuDriverHelper {\n    private const val META_JSON_FILENAME = "meta.json"\n''',
        '''object GpuDriverHelper {\n    private const val META_JSON_FILENAME = "meta.json"\n    private const val BL2_F7_APPLICATION_ID_PREFIX = "dev.bl2f7.runtime"\n    private const val BL2_F7_DRIVER_ASSET_DIR = "bl2f7_driver"\n    private const val BL2_F7_TURNIP_V36_SHA256 = "a7b1209e9cd4e87aac70e46991d7f07465810ef667fcead24ae82bfa68d7388a"\n    private const val BL2_F7_DRIVER_MARKER = ".bl2f7-turnip-v36"\n''',
    )
    replace_once(
        driver_helper,
        '''        initializeDirectories()\n        hookLibPath = YuzuApplication.appContext.applicationInfo.nativeLibraryDir + "/"\n''',
        '''        initializeDirectories()\n        installBundledBl2F7DriverIfNeeded()\n        hookLibPath = YuzuApplication.appContext.applicationInfo.nativeLibraryDir + "/"\n''',
    )
    replace_once(
        driver_helper,
        '''    fun getDrivers(): MutableList<Pair<String, GpuDriverMetadata>> {\n''',
        '''    private fun isBl2F7TargetDevice(): Boolean {\n        if (!YuzuApplication.appContext.packageName.startsWith(BL2_F7_APPLICATION_ID_PREFIX)) {\n            return false\n        }\n        val soc = Build.SOC_MODEL ?: ""\n        val model = Build.MODEL ?: ""\n        val device = Build.DEVICE ?: ""\n        val socMatch =\n            soc.contains("SM8735", ignoreCase = true) ||\n                soc.contains("Snapdragon 8s Gen 4", ignoreCase = true)\n        val deviceMatch =\n            model.contains("POCO F7", ignoreCase = true) ||\n                model.contains("25053PC47", ignoreCase = true) ||\n                device.contains("onyx", ignoreCase = true)\n        return socMatch && deviceMatch\n    }\n\n    private fun installBundledBl2F7DriverIfNeeded() {\n        if (!isBl2F7TargetDevice()) {\n            return\n        }\n\n        val installDir = File(driverInstallationPath ?: return)\n        val markerFile = File(installDir, BL2_F7_DRIVER_MARKER)\n        val libraryFile = File(installDir, "libvulkan_freedreno.so")\n        val metadataFile = File(installDir, META_JSON_FILENAME)\n\n        if (markerFile.exists() &&\n            markerFile.readText().trim() == BL2_F7_TURNIP_V36_SHA256 &&\n            libraryFile.exists() && metadataFile.exists()) {\n            return\n        }\n\n        try {\n            installDir.deleteRecursively()\n            installDir.mkdirs()\n\n            val assets = YuzuApplication.appContext.assets\n            listOf("libvulkan_freedreno.so", META_JSON_FILENAME).forEach { name ->\n                assets.open("$BL2_F7_DRIVER_ASSET_DIR/$name").use { input ->\n                    File(installDir, name).outputStream().use { output ->\n                        input.copyTo(output)\n                    }\n                }\n            }\n            markerFile.writeText(BL2_F7_TURNIP_V36_SHA256)\n        } catch (_: Exception) {\n            installDir.deleteRecursively()\n            installDir.mkdirs()\n        }\n    }\n\n    fun getDrivers(): MutableList<Pair<String, GpuDriverMetadata>> {\n''',
    )


def patch_android_jni() -> None:
    cmake = ROOT / "src/android/app/src/main/jni/CMakeLists.txt"
    native = ROOT / "src/android/app/src/main/jni/native.cpp"
    jni_dir = native.parent

    replace_once(
        cmake,
        '''    native.cpp\n    native.h\n''',
        '''    native.cpp\n    native.h\n    bl2_f7_profile.cpp\n    bl2_f7_profile.h\n''',
    )

    replace_once(
        cmake,
        '''target_link_libraries(yuzu-android PRIVATE OpenSSL::SSL cpp-jwt::cpp-jwt)\nif (ENABLE_UPDATE_CHECKER)\n''',
        '''target_link_libraries(yuzu-android PRIVATE OpenSSL::SSL cpp-jwt::cpp-jwt)\nif (BL2_F7)\n    target_compile_definitions(yuzu-android PRIVATE BL2_F7=1)\n    target_compile_definitions(video_core PRIVATE BL2_F7=1)\n    target_compile_definitions(core PRIVATE BL2_F7=1)\nendif()\nif (ENABLE_UPDATE_CHECKER)\n''',
    )

    replace_once(
        native,
        '''#include "jni/native.h"\n''',
        '''#include "jni/native.h"\n#ifdef BL2_F7\n#include "jni/bl2_f7_profile.h"\n#endif\n''',
    )

    replace_once(
        native,
        '''    m_system.SetShuttingDown(false);\n    m_system.ApplySettings();\n''',
        '''    m_system.SetShuttingDown(false);\n#ifdef BL2_F7\n    const auto bl2_f7_profile = BL2F7::TryApply(m_system, filepath);\n    if (!bl2_f7_profile.title_detected) {\n        LOG_ERROR(Frontend, "[BL2-F7] Blocking non-Borderlands 2 launch");\n        return Core::SystemResultStatus::ErrorLoader;\n    }\n#endif\n    m_system.ApplySettings();\n''',
    )

    for name in ("bl2_f7_profile.h", "bl2_f7_profile.cpp"):
        shutil.copy2(KIT / "files/src/android/app/src/main/jni" / name, jni_dir / name)


def patch_worker_range() -> None:
    settings_item = ROOT / (
        "src/android/app/src/main/java/org/yuzu/yuzu_emu/features/settings/model/view/SettingsItem.kt"
    )
    replace_once(
        settings_item,
        '''                    IntSetting.ANDROID_PIPELINE_WORKERS,\n                    titleId = R.string.pipeline_worker_cores,\n                    descriptionId = R.string.pipeline_worker_cores_description,\n                    min = 4,\n                    max = 8,\n                    units = "cores"\n''',
        '''                    IntSetting.ANDROID_PIPELINE_WORKERS,\n                    titleId = R.string.pipeline_worker_cores,\n                    descriptionId = R.string.pipeline_worker_cores_description,\n                    min = 2,\n                    max = 8,\n                    units = "cores"\n''',
    )

    pipeline = ROOT / "src/video_core/renderer_vulkan/vk_pipeline_cache.cpp"
    replace_once(
        pipeline,
        '''    const int clamped = std::clamp(configured, 4, 8);\n''',
        '''    const int clamped = std::clamp(configured, 2, 8);\n''',
    )


def patch_pipeline_profiling() -> None:
    pipeline = ROOT / "src/video_core/renderer_vulkan/vk_pipeline_cache.cpp"

    replace_once(
        pipeline,
        '''#include <algorithm>\n#include <cstddef>\n''',
        '''#include <algorithm>\n#include <chrono>\n#include <cstddef>\n''',
    )

    replace_once(
        pipeline,
        '''    auto& pipeline{pair->second};\n    if (is_new) {\n        pipeline = CreateGraphicsPipeline();\n    }\n    if (!pipeline) {\n''',
        '''    auto& pipeline{pair->second};\n    if (is_new) {\n#ifdef BL2_F7\n        const auto bl2_f7_begin = std::chrono::steady_clock::now();\n#endif\n        pipeline = CreateGraphicsPipeline();\n#ifdef BL2_F7\n        const auto bl2_f7_us = std::chrono::duration_cast<std::chrono::microseconds>(\n                                   std::chrono::steady_clock::now() - bl2_f7_begin)\n                                   .count();\n        if (bl2_f7_us >= 500) {\n            LOG_INFO(Render_Vulkan,\n                     "[BL2-F7] runtime graphics pipeline build: {} us, hash=0x{:016x}",\n                     bl2_f7_us, graphics_key.Hash());\n        }\n#endif\n    }\n    if (!pipeline) {\n''',
    )

    replace_once(
        pipeline,
        '''    if (!is_new) {\n        return pipeline.get();\n    }\n    pipeline = CreateComputePipeline(key, shader);\n    return pipeline.get();\n''',
        '''    if (!is_new) {\n        return pipeline.get();\n    }\n#ifdef BL2_F7\n    const auto bl2_f7_begin = std::chrono::steady_clock::now();\n#endif\n    pipeline = CreateComputePipeline(key, shader);\n#ifdef BL2_F7\n    const auto bl2_f7_us = std::chrono::duration_cast<std::chrono::microseconds>(\n                               std::chrono::steady_clock::now() - bl2_f7_begin)\n                               .count();\n    if (bl2_f7_us >= 500) {\n        LOG_INFO(Render_Vulkan,\n                 "[BL2-F7] runtime compute pipeline build: {} us, hash=0x{:016x}",\n                 bl2_f7_us, key.Hash());\n    }\n#endif\n    return pipeline.get();\n''',
    )


def patch_sync_profiling() -> None:
    dma = ROOT / "src/video_core/dma_pusher.cpp"

    replace_once(
        dma,
        '''#include "common/settings.h"\n''',
        '''#include <chrono>\n\n#include "common/logging.h"\n#include "common/settings.h"\n''',
    )

    replace_once(
        dma,
        '''    if (signal_sync && !synced) {\n        std::unique_lock lk(sync_mutex);\n        sync_cv.wait(lk, [this]() { return synced; });\n        signal_sync = false;\n        synced = false;\n    }\n''',
        '''    if (signal_sync && !synced) {\n#ifdef BL2_F7\n        const auto bl2_f7_sync_begin = std::chrono::steady_clock::now();\n#endif\n        std::unique_lock lk(sync_mutex);\n        sync_cv.wait(lk, [this]() { return synced; });\n#ifdef BL2_F7\n        const auto bl2_f7_sync_us = std::chrono::duration_cast<std::chrono::microseconds>(\n                                        std::chrono::steady_clock::now() - bl2_f7_sync_begin)\n                                        .count();\n        if (system.GetApplicationProcessProgramID() == 0x010096F00FF22000ULL &&\n            bl2_f7_sync_us >= 500) {\n            LOG_INFO(HW_GPU, "[BL2-F7] DMA sync fence wait: {} us", bl2_f7_sync_us);\n        }\n#endif\n        signal_sync = false;\n        synced = false;\n    }\n''',
    )



def patch_builtin_60fps() -> None:
    patch_manager = ROOT / "src/core/file_sys/patch_manager.cpp"

    replace_once(
        patch_manager,
        '''constexpr std::array<const char*, 14> EXEFS_FILE_NAMES{\n''',
        '''#ifdef BL2_F7\nconstexpr u64 BL2_F7_TITLE_ID = 0x010096F00FF22000ULL;\n\nconstexpr std::array<u8, 19> BL2_F7_60FPS_B5EA86B6AEFEEB73{\n    0x49, 0x50, 0x53, 0x33, 0x32, 0x01, 0x2A, 0xA8, 0xBC, 0x00,\n    0x04, 0x21, 0x00, 0x80, 0x52, 0x45, 0x45, 0x4F, 0x46,\n};\nconstexpr std::array<u8, 19> BL2_F7_60FPS_F367DE313B111EFF{\n    0x49, 0x50, 0x53, 0x33, 0x32, 0x01, 0x2A, 0xF1, 0x3C, 0x00,\n    0x04, 0x21, 0x00, 0x80, 0x52, 0x45, 0x45, 0x4F, 0x46,\n};\nconstexpr std::array<u8, 19> BL2_F7_60FPS_F7C233469F20EE3F{\n    0x49, 0x50, 0x53, 0x33, 0x32, 0x01, 0x2A, 0xF2, 0x2C, 0x00,\n    0x04, 0x21, 0x00, 0x80, 0x52, 0x45, 0x45, 0x4F, 0x46,\n};\n\nVirtualFile GetBuiltInBl2F760FpsPatch(std::string_view build_id) {\n    if (build_id == "B5EA86B6AEFEEB73E61BC385C1E77F17") {\n        return MakeArrayFile(BL2_F7_60FPS_B5EA86B6AEFEEB73, "BL2-F7-60FPS.ips");\n    }\n    if (build_id == "F367DE313B111EFF909C2A5C5D43E3F8") {\n        return MakeArrayFile(BL2_F7_60FPS_F367DE313B111EFF, "BL2-F7-60FPS.ips");\n    }\n    if (build_id == "F7C233469F20EE3F2383F3CD5BCF775A") {\n        return MakeArrayFile(BL2_F7_60FPS_F7C233469F20EE3F, "BL2-F7-60FPS.ips");\n    }\n    return nullptr;\n}\n#endif\n\nconstexpr std::array<const char*, 14> EXEFS_FILE_NAMES{\n''',
    )

    replace_once(
        patch_manager,
        '''    LOG_INFO(Loader, "Patching NSO for name={}, build_id={}", name, build_id);\n\n    const auto load_dir = fs_controller.GetModificationLoadRoot(title_id);\n    if (load_dir == nullptr) {\n        LOG_ERROR(Loader, "Cannot load mods for invalid title_id={:016X}", title_id);\n        return nso;\n    }\n\n    auto patch_dirs = load_dir->GetSubdirectories();\n''',
        '''    LOG_INFO(Loader, "Patching NSO for name={}, build_id={}", name, build_id);\n\n    auto out = nso;\n#ifdef BL2_F7\n    if (title_id == BL2_F7_TITLE_ID && name == "main") {\n        const auto built_in_patch = GetBuiltInBl2F760FpsPatch(build_id);\n        if (built_in_patch != nullptr) {\n            LOG_INFO(Loader, "[BL2-F7] Applying built-in 60 FPS IPS32 patch for Build ID {}",\n                     build_id);\n            const auto patched = PatchIPS(std::make_shared<VectorVfsFile>(out), built_in_patch);\n            if (patched != nullptr) {\n                out = patched->ReadAllBytes();\n            } else {\n                LOG_ERROR(Loader, "[BL2-F7] Built-in 60 FPS IPS32 patch failed");\n            }\n        } else {\n            LOG_WARNING(Loader,\n                        "[BL2-F7] No built-in 60 FPS patch for Build ID {}. Game will use its "\n                        "native frame-rate behavior.",\n                        build_id);\n        }\n    }\n#endif\n\n    const auto load_dir = fs_controller.GetModificationLoadRoot(title_id);\n    if (load_dir == nullptr) {\n        LOG_INFO(Loader, "No external mod directory for title_id={:016X}", title_id);\n        return out;\n    }\n\n    auto patch_dirs = load_dir->GetSubdirectories();\n''',
    )

    replace_once(
        patch_manager,
        '''    const auto patches = CollectPatches(patch_dirs, build_id);\n\n    auto out = nso;\n    for (const auto& patch_file : patches) {\n''',
        '''    const auto patches = CollectPatches(patch_dirs, build_id);\n\n    for (const auto& patch_file : patches) {\n''',
    )

    replace_once(
        patch_manager,
        '''bool PatchManager::HasNSOPatch(const BuildID& build_id_, std::string_view name) const {\n    const auto build_id_raw = Common::HexToString(build_id_);\n    const auto build_id = build_id_raw.substr(0, build_id_raw.find_last_not_of('0') + 1);\n\n    LOG_INFO(Loader, "Querying NSO patch existence for build_id={}, name={}", build_id, name);\n\n    const auto load_dir = fs_controller.GetModificationLoadRoot(title_id);\n''',
        '''bool PatchManager::HasNSOPatch(const BuildID& build_id_, std::string_view name) const {\n    const auto build_id_raw = Common::HexToString(build_id_);\n    const auto build_id = build_id_raw.substr(0, build_id_raw.find_last_not_of('0') + 1);\n\n    LOG_INFO(Loader, "Querying NSO patch existence for build_id={}, name={}", build_id, name);\n\n#ifdef BL2_F7\n    if (title_id == BL2_F7_TITLE_ID && name == "main" &&\n        GetBuiltInBl2F760FpsPatch(build_id) != nullptr) {\n        return true;\n    }\n#endif\n\n    const auto load_dir = fs_controller.GetModificationLoadRoot(title_id);\n''',
    )



def patch_bl2_config_transfer_ui() -> None:
    # Dedicated BL2 per-game INI import/export submenu for Android settings.
    settings_model = ROOT / (
        "src/android/app/src/main/java/org/yuzu/yuzu_emu/features/settings/model/Settings.kt"
    )
    settings_vm = ROOT / (
        "src/android/app/src/main/java/org/yuzu/yuzu_emu/features/settings/ui/SettingsViewModel.kt"
    )
    presenter = ROOT / (
        "src/android/app/src/main/java/org/yuzu/yuzu_emu/features/settings/ui/SettingsFragmentPresenter.kt"
    )
    fragment = ROOT / (
        "src/android/app/src/main/java/org/yuzu/yuzu_emu/features/settings/ui/SettingsFragment.kt"
    )

    replace_once(
        settings_model,
        "        SECTION_ROOT(R.string.advanced_settings),\n",
        "        SECTION_ROOT(R.string.advanced_settings),\n        SECTION_BL2_CONFIG_TRANSFER,\n",
    )

    replace_once(
        settings_vm,
        "    private val _shouldShowPathResetDialog = MutableStateFlow(false)\n    val shouldShowPathResetDialog = _shouldShowPathResetDialog.asStateFlow()\n\n    private val _pathSettingPosition = MutableStateFlow(-1)\n",
        "    private val _shouldShowPathResetDialog = MutableStateFlow(false)\n    val shouldShowPathResetDialog = _shouldShowPathResetDialog.asStateFlow()\n\n    private val _shouldImportGameConfig = MutableStateFlow(false)\n    val shouldImportGameConfig = _shouldImportGameConfig.asStateFlow()\n\n    private val _shouldExportGameConfig = MutableStateFlow(false)\n    val shouldExportGameConfig = _shouldExportGameConfig.asStateFlow()\n\n    private val _pathSettingPosition = MutableStateFlow(-1)\n",
    )
    replace_once(
        settings_vm,
        "    fun setShouldShowPathResetDialog(value: Boolean) {\n        _shouldShowPathResetDialog.value = value\n    }\n\n    fun setPathSettingPosition(value: Int) {\n",
        "    fun setShouldShowPathResetDialog(value: Boolean) {\n        _shouldShowPathResetDialog.value = value\n    }\n\n    fun setShouldImportGameConfig(value: Boolean) {\n        _shouldImportGameConfig.value = value\n    }\n\n    fun setShouldExportGameConfig(value: Boolean) {\n        _shouldExportGameConfig.value = value\n    }\n\n    fun setPathSettingPosition(value: Int) {\n",
    )

    replace_once(
        presenter,
        "            MenuTag.SECTION_ROOT -> addConfigSettings(sl)\n            MenuTag.SECTION_SYSTEM -> addSystemSettings(sl)\n",
        "            MenuTag.SECTION_ROOT -> addConfigSettings(sl)\n            MenuTag.SECTION_BL2_CONFIG_TRANSFER -> addBl2ConfigTransferSettings(sl)\n            MenuTag.SECTION_SYSTEM -> addSystemSettings(sl)\n",
    )

    replace_once(
        presenter,
        "            add(\n                RunnableSetting(\n                    titleId = R.string.reset_to_default,\n                    descriptionId = R.string.reset_to_default_description,\n                    isRunnable = !NativeLibrary.isRunning(),\n                    iconId = R.drawable.ic_restore\n                ) { settingsViewModel.setShouldShowResetSettingsDialog(true) }\n            )\n        }\n    }\n\n    private fun addSystemSettings(sl: ArrayList<SettingsItem>) {\n",
        "            if (NativeConfig.isPerGameConfigLoaded()) {\n                add(\n                    SubmenuSetting(\n                        titleString = \"Importar / Exportar configuração\",\n                        descriptionString = \"Perfil individual do Borderlands 2 (.ini)\",\n                        iconId = R.drawable.ic_import,\n                        menuKey = MenuTag.SECTION_BL2_CONFIG_TRANSFER\n                    )\n                )\n            }\n            add(\n                RunnableSetting(\n                    titleId = R.string.reset_to_default,\n                    descriptionId = R.string.reset_to_default_description,\n                    isRunnable = !NativeLibrary.isRunning(),\n                    iconId = R.drawable.ic_restore\n                ) { settingsViewModel.setShouldShowResetSettingsDialog(true) }\n            )\n        }\n    }\n\n    private fun addBl2ConfigTransferSettings(sl: ArrayList<SettingsItem>) {\n        sl.apply {\n            add(\n                RunnableSetting(\n                    titleId = R.string.import_config,\n                    descriptionString = \"Substitui somente o perfil individual do BL2. As configurações globais não são alteradas.\",\n                    isRunnable = !NativeLibrary.isRunning(),\n                    iconId = R.drawable.ic_import\n                ) { settingsViewModel.setShouldImportGameConfig(true) }\n            )\n            add(\n                RunnableSetting(\n                    titleId = R.string.export_config,\n                    descriptionString = \"Salva o perfil atual do BL2 como um arquivo .ini portátil.\",\n                    isRunnable = true,\n                    iconId = R.drawable.ic_export\n                ) { settingsViewModel.setShouldExportGameConfig(true) }\n            )\n        }\n    }\n\n    private fun addSystemSettings(sl: ArrayList<SettingsItem>) {\n",
    )

    replace_once(
        fragment,
        "import android.content.Intent\n",
        "import android.content.Intent\nimport android.net.Uri\n",
    )

    replace_once(
        fragment,
        "import org.yuzu.yuzu_emu.features.settings.model.view.PathSetting\n",
        "import org.yuzu.yuzu_emu.features.settings.model.view.PathSetting\nimport org.yuzu.yuzu_emu.features.settings.utils.SettingsFile\nimport org.yuzu.yuzu_emu.model.TaskState\n",
    )

    replace_once(
        fragment,
        "    private val requestAllFilesPermissionLauncher = registerForActivityResult(\n        ActivityResultContracts.StartActivityForResult()\n    ) {\n        if (hasAllFilesPermission()) {\n            showPathPickerDialog()\n        } else {\n            Toast.makeText(\n                requireContext(),\n                R.string.all_files_permission_required,\n                Toast.LENGTH_LONG\n            ).show()\n        }\n    }\n\n    override fun onCreate(savedInstanceState: Bundle?) {\n",
        "    private val requestAllFilesPermissionLauncher = registerForActivityResult(\n        ActivityResultContracts.StartActivityForResult()\n    ) {\n        if (hasAllFilesPermission()) {\n            showPathPickerDialog()\n        } else {\n            Toast.makeText(\n                requireContext(),\n                R.string.all_files_permission_required,\n                Toast.LENGTH_LONG\n            ).show()\n        }\n    }\n\n    private val importBl2ConfigLauncher = registerForActivityResult(\n        ActivityResultContracts.OpenDocument()\n    ) { uri ->\n        if (uri == null) return@registerForActivityResult\n        importBl2Config(uri)\n    }\n\n    private val exportBl2ConfigLauncher = registerForActivityResult(\n        ActivityResultContracts.CreateDocument(\"text/ini\")\n    ) { uri ->\n        if (uri == null) return@registerForActivityResult\n        exportBl2Config(uri)\n    }\n\n    override fun onCreate(savedInstanceState: Bundle?) {\n",
    )

    replace_once(
        fragment,
        "        settingsViewModel.shouldShowPathResetDialog.collect(\n            viewLifecycleOwner,\n            resetState = { settingsViewModel.setShouldShowPathResetDialog(false) }\n        ) {\n            if (it) {\n                showPathResetDialog()\n            }\n        }\n\n        if (args.menuTag == Settings.MenuTag.SECTION_ROOT) {\n",
        "        settingsViewModel.shouldShowPathResetDialog.collect(\n            viewLifecycleOwner,\n            resetState = { settingsViewModel.setShouldShowPathResetDialog(false) }\n        ) {\n            if (it) {\n                showPathResetDialog()\n            }\n        }\n\n        settingsViewModel.shouldImportGameConfig.collect(\n            viewLifecycleOwner,\n            resetState = { settingsViewModel.setShouldImportGameConfig(false) }\n        ) {\n            if (it) {\n                importBl2ConfigLauncher.launch(arrayOf(\"text/ini\", \"text/plain\", \"application/octet-stream\"))\n            }\n        }\n\n        settingsViewModel.shouldExportGameConfig.collect(\n            viewLifecycleOwner,\n            resetState = { settingsViewModel.setShouldExportGameConfig(false) }\n        ) {\n            if (it) {\n                val game = settingsViewModel.game\n                if (game != null) {\n                    exportBl2ConfigLauncher.launch(game.settingsName + \".ini\")\n                }\n            }\n        }\n\n        if (args.menuTag == Settings.MenuTag.SECTION_ROOT) {\n",
    )

    replace_once(
        fragment,
        "    private fun resolveToolbarTitle(): String {\n        if (args.menuTag == Settings.MenuTag.SECTION_ROOT && args.game != null) {\n            return args.game!!.title\n        }\n        return when (args.menuTag) {\n",
        "    private fun resolveToolbarTitle(): String {\n        if (args.menuTag == Settings.MenuTag.SECTION_ROOT && args.game != null) {\n            return args.game!!.title\n        }\n        if (args.menuTag == Settings.MenuTag.SECTION_BL2_CONFIG_TRANSFER) {\n            return \"Importar / Exportar configuração\"\n        }\n        return when (args.menuTag) {\n",
    )

    replace_once(
        fragment,
        "    private fun configureToolbar(title: String) {\n        binding.toolbarSettings.title = title\n    }\n\n    private fun setInsets() {\n",
        "    private fun configureToolbar(title: String) {\n        binding.toolbarSettings.title = title\n    }\n\n    private fun importBl2Config(uri: Uri) {\n        val game = settingsViewModel.game ?: return\n        val cacheDirectory = File(requireContext().cacheDir, \"bl2_f7_config_import\")\n        cacheDirectory.mkdirs()\n        val temp = FileUtil.copyUriToInternalStorage(\n            sourceUri = uri,\n            destinationParentPath = cacheDirectory.absolutePath + \"/\",\n            destinationFilename = \"import.ini\"\n        )\n\n        val valid = temp != null && temp.exists() && temp.length() in 1..(2L * 1024L * 1024L) &&\n            runCatching { temp.readText().contains(\"[\") }.getOrDefault(false)\n        if (!valid) {\n            temp?.delete()\n            Toast.makeText(requireContext(), R.string.import_failed, Toast.LENGTH_SHORT).show()\n            return\n        }\n\n        val destination = SettingsFile.getCustomSettingsFile(game)\n        val backup = File(destination.parentFile, destination.name + \".bl2f7.bak\")\n        try {\n            destination.parentFile?.mkdirs()\n            if (destination.exists()) {\n                destination.copyTo(backup, overwrite = true)\n            }\n            if (NativeConfig.isPerGameConfigLoaded()) {\n                NativeConfig.unloadPerGameConfig()\n            }\n            temp!!.copyTo(destination, overwrite = true)\n            SettingsFile.loadCustomConfig(game)\n            backup.delete()\n            settingsViewModel.setReloadListAndNotifyDataset(true)\n            Toast.makeText(requireContext(), R.string.import_success, Toast.LENGTH_SHORT).show()\n        } catch (_: Exception) {\n            if (backup.exists()) {\n                backup.copyTo(destination, overwrite = true)\n            }\n            if (!NativeConfig.isPerGameConfigLoaded()) {\n                SettingsFile.loadCustomConfig(game)\n            }\n            Toast.makeText(requireContext(), R.string.import_failed, Toast.LENGTH_SHORT).show()\n        } finally {\n            temp?.delete()\n            backup.delete()\n        }\n    }\n\n    private fun exportBl2Config(uri: Uri) {\n        val game = settingsViewModel.game ?: return\n        if (NativeConfig.isPerGameConfigLoaded()) {\n            NativeConfig.savePerGameConfig()\n        }\n        val config = SettingsFile.getCustomSettingsFile(game)\n        if (!config.exists()) {\n            Toast.makeText(requireContext(), R.string.export_failed, Toast.LENGTH_SHORT).show()\n            return\n        }\n        when (FileUtil.copyToExternalStorage(sourcePath = config.absolutePath, destUri = uri)) {\n            TaskState.Completed ->\n                Toast.makeText(requireContext(), R.string.export_success, Toast.LENGTH_SHORT).show()\n            TaskState.Cancelled, TaskState.Failed ->\n                Toast.makeText(requireContext(), R.string.export_failed, Toast.LENGTH_SHORT).show()\n        }\n    }\n\n    private fun setInsets() {\n",
    )

def write_build_scripts() -> None:
    build = ROOT / "src/android/build-bl2-f7.sh"
    build.write_text(
        '''#!/usr/bin/env bash\nset -euo pipefail\ncd "$(dirname "$0")"\n./gradlew assembleBl2F7RelWithDebInfo\n''',
        encoding="utf-8",
    )
    build.chmod(0o755)

    release = ROOT / "src/android/build-bl2-f7-release.sh"
    release.write_text(
        '''#!/usr/bin/env bash\nset -euo pipefail\ncd "$(dirname "$0")"\n./gradlew assembleBl2F7Release\n''',
        encoding="utf-8",
    )
    release.chmod(0o755)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    check_base(args.allow_dirty)
    patch_gradle()
    bundle_turnip_v36()
    patch_android_single_title_and_driver()
    patch_android_jni()
    patch_worker_range()
    patch_pipeline_profiling()
    patch_sync_profiling()
    patch_builtin_60fps()
    patch_bl2_config_transfer_ui()
    write_build_scripts()

    print("BL2-F7 v0.4 Single-Title + V36 + built-in 60 FPS + per-game config transfer applied successfully.")
    print("Build instrumented: cd src/android && ./build-bl2-f7.sh")
    print("Build release:      cd src/android && ./build-bl2-f7-release.sh")
    print("Only Borderlands 2 title ID 010096F00FF22000 is exposed/accepted.")
    print("POCO F7 stages pinned Turnip Gen8 V36 automatically.")
    print("60 FPS IPS32 is built into the core for three supported BL2 Build IDs.")
    print("Per-game BL2 .ini import/export submenu is enabled.")
    print("Search runtime logs for: [BL2-F7]")


if __name__ == "__main__":
    main()

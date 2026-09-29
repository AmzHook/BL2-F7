#!/usr/bin/env python3
"""Apply BL2-F7 v0.2 Performance to an exact Eden v0.2.1 checkout.

Run from the Eden repository root:
    python3 /path/to/BL2-F7-v0.2-performance-kit/scripts/apply_bl2_f7.py

The patch is intentionally strict. It refuses unknown revisions and refuses to
patch a dirty tree unless --allow-dirty is supplied.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path.cwd()
KIT = Path(__file__).resolve().parents[1]
EXPECTED_SHA = "58c1e20ee58efa3900ba616207d460886214480b"


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
        '''target_link_libraries(yuzu-android PRIVATE OpenSSL::SSL cpp-jwt::cpp-jwt)\nif (BL2_F7)\n    target_compile_definitions(yuzu-android PRIVATE BL2_F7=1)\n    target_compile_definitions(video_core PRIVATE BL2_F7=1)\nendif()\nif (ENABLE_UPDATE_CHECKER)\n''',
    )

    replace_once(
        native,
        '''#include "jni/native.h"\n''',
        '''#include "jni/native.h"\n#ifdef BL2_F7\n#include "jni/bl2_f7_profile.h"\n#endif\n''',
    )

    replace_once(
        native,
        '''    m_system.SetShuttingDown(false);\n    m_system.ApplySettings();\n''',
        '''    m_system.SetShuttingDown(false);\n#ifdef BL2_F7\n    const auto bl2_f7_profile = BL2F7::TryApply(m_system, filepath);\n    (void)bl2_f7_profile;\n#endif\n    m_system.ApplySettings();\n''',
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


def patch_background_pipeline_workers() -> None:
    # v0.2.1's generic SCHED_OTHER priority path does not meaningfully lower Android
    # worker priority. Add a dedicated Android nice(+10) helper and use it only for
    # pipeline-builder/serialization workers.
    thread_h = ROOT / "src/common/thread.h"
    thread_cpp = ROOT / "src/common/thread.cpp"
    worker_h = ROOT / "src/common/thread_worker.h"
    pipeline = ROOT / "src/video_core/renderer_vulkan/vk_pipeline_cache.cpp"

    replace_once(
        thread_h,
        '''void SetCurrentThreadPriority(ThreadPriority new_priority);\nvoid SetCurrentThreadName(const char* name);\nvoid PinCurrentThreadToPerformanceCore(size_t core_id);\n''',
        '''void SetCurrentThreadPriority(ThreadPriority new_priority);\n// Low-impact background priority for expensive helper workers. On Android this uses\n// a positive nice value, which does not require elevated privileges.\nvoid SetCurrentThreadBackgroundPriority();\nvoid SetCurrentThreadName(const char* name);\nvoid PinCurrentThreadToPerformanceCore(size_t core_id);\n''',
    )

    replace_once(
        thread_cpp,
        '''#ifndef _WIN32\n#include <unistd.h>\n#endif\n''',
        '''#ifndef _WIN32\n#include <unistd.h>\n#endif\n#ifdef __ANDROID__\n#include <sys/resource.h>\n#endif\n''',
    )

    replace_once(
        thread_cpp,
        '''void SetCurrentThreadName(const char* name) {\n''',
        '''void SetCurrentThreadBackgroundPriority() {\n#ifdef __ANDROID__\n    // Raising niceness (lowering priority) is permitted to ordinary app processes.\n    // Keep shader/pipeline helper work from stealing time from NCE/GPU critical paths.\n    constexpr int background_nice = 10;\n    if (setpriority(PRIO_PROCESS, static_cast<id_t>(gettid()), background_nice) != 0) {\n        LOG_DEBUG(Common, "Could not lower background worker priority: {}", GetLastErrorMsg());\n    }\n#else\n    SetCurrentThreadPriority(ThreadPriority::Low);\n#endif\n}\n\nvoid SetCurrentThreadName(const char* name) {\n''',
    )

    replace_once(
        worker_h,
        '''    explicit StatefulThreadWorker(size_t num_workers, std::string name, StateMaker func = {})\n        : workers_queued{num_workers}, thread_name{std::move(name)} {\n        const auto lambda = [this, func](std::stop_token stop_token) {\n            Common::SetCurrentThreadName(thread_name.c_str());\n            {\n''',
        '''    explicit StatefulThreadWorker(size_t num_workers, std::string name, StateMaker func = {},\n                                  bool background_priority = false)\n        : workers_queued{num_workers}, thread_name{std::move(name)} {\n        const auto lambda = [this, func, background_priority](std::stop_token stop_token) {\n            Common::SetCurrentThreadName(thread_name.c_str());\n            if (background_priority) {\n                Common::SetCurrentThreadBackgroundPriority();\n            }\n            {\n''',
    )

    replace_once(
        pipeline,
        '''      workers(device.HasBrokenParallelShaderCompiling() ? 1ULL : GetTotalPipelineWorkers(),\n              "VkPipelineBuilder"),\n      serialization_thread(1, "VkPipelineSerialization") {\n''',
        '''      workers(device.HasBrokenParallelShaderCompiling() ? 1ULL : GetTotalPipelineWorkers(),\n              "VkPipelineBuilder", {}, true),\n      serialization_thread(1, "VkPipelineSerialization", {}, true) {\n''',
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
    patch_android_jni()
    patch_worker_range()
    patch_background_pipeline_workers()
    patch_pipeline_profiling()
    patch_sync_profiling()
    write_build_scripts()

    print("BL2-F7 v0.2 Performance applied successfully.")
    print("Build instrumented: cd src/android && ./build-bl2-f7.sh")
    print("Build release:      cd src/android && ./build-bl2-f7-release.sh")
    print("Search runtime logs for: [BL2-F7]")


if __name__ == "__main__":
    main()

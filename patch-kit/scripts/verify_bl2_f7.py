#!/usr/bin/env python3
"""Static verification after apply_bl2_f7.py (does not compile the project)."""
from pathlib import Path
import sys

root = Path.cwd()
checks = {
    "src/android/app/build.gradle.kts": ["create(\"bl2F7\")", "-DBL2_F7=ON", "dev.bl2f7.runtime"],
    "src/android/app/src/main/jni/CMakeLists.txt": ["bl2_f7_profile.cpp", "target_compile_definitions(video_core PRIVATE BL2_F7=1)"],
    "src/android/app/src/main/jni/native.cpp": ["BL2F7::TryApply"],
    "src/common/thread.h": ["SetCurrentThreadBackgroundPriority"],
    "src/common/thread.cpp": ["background_nice = 10"],
    "src/common/thread_worker.h": ["background_priority"],
    "src/video_core/renderer_vulkan/vk_pipeline_cache.cpp": ["std::clamp(configured, 2, 8)", "runtime graphics pipeline build"],
    "src/video_core/dma_pusher.cpp": ["DMA sync fence wait"],
}
failed = False
for rel, needles in checks.items():
    p = root / rel
    if not p.exists():
        print(f"MISSING {rel}")
        failed = True
        continue
    txt = p.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in txt:
            print(f"MISSING ANCHOR {rel}: {needle}")
            failed = True
if failed:
    sys.exit(1)
print("BL2-F7 static verification: OK")

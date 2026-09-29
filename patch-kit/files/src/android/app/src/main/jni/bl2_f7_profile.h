// SPDX-FileCopyrightText: 2026 BL2-F7 contributors
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <string>
#include "common/common_types.h"

namespace Core {
class System;
}

namespace BL2F7 {

constexpr u64 kBorderlands2ProgramId = 0x010096F00FF22000ULL;
// Eden 0.2.1 lowered the Android default to 4 to reduce heat/CPU contention.
// On the POCO F7 this is the conservative performance baseline; the patched UI allows 2..8.
constexpr int kInitialPipelineWorkers = 4;

struct ProfileResult {
    bool title_detected{};
    bool poco_f7_detected{};
    bool applied{};
    u64 program_id{};
    std::string model;
    std::string device;
    std::string soc_model;
};

// Detect Borderlands 2 from the selected game file and the target POCO F7/SM8735
// from Android system properties. The performance profile is applied only if both match.
ProfileResult TryApply(Core::System& system, const std::string& filepath);

} // namespace BL2F7

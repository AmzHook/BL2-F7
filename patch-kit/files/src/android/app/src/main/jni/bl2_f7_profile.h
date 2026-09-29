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
constexpr int kInitialPipelineWorkers = 6;

struct ProfileResult {
    bool title_detected{};
    bool poco_f7_detected{};
    bool applied{};
    u64 program_id{};
    std::string model;
    std::string device;
    std::string soc_model;
};

ProfileResult TryApply(Core::System& system, const std::string& filepath);

} // namespace BL2F7

// SPDX-FileCopyrightText: 2026 BL2-F7 contributors
// SPDX-License-Identifier: GPL-3.0-or-later

#include "bl2_f7_profile.h"

#include <algorithm>
#include <cctype>
#include <optional>
#include <string>
#include <sys/system_properties.h>

#include "android_settings.h"
#include "common/logging.h"
#include "common/settings.h"
#include "core/core.h"
#include "core/file_sys/vfs/vfs.h"
#include "core/loader/loader.h"

namespace BL2F7 {
namespace {

std::string GetSystemProperty(const char* key) {
    char value[PROP_VALUE_MAX]{};
    const int length = __system_property_get(key, value);
    if (length <= 0) {
        return {};
    }
    return std::string{value, static_cast<std::size_t>(length)};
}

std::string Lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

bool ContainsInsensitive(const std::string& value, const std::string& needle) {
    return Lower(value).find(Lower(needle)) != std::string::npos;
}

std::optional<u64> ReadProgramId(Core::System& system, const std::string& filepath) {
    const auto file = system.GetFilesystem()->OpenFile(filepath, FileSys::OpenMode::Read);
    if (!file) {
        return std::nullopt;
    }

    auto loader = Loader::GetLoader(system, file);
    if (!loader) {
        return std::nullopt;
    }

    u64 program_id{};
    if (loader->ReadProgramId(program_id) != Loader::ResultStatus::Success) {
        return std::nullopt;
    }
    return program_id;
}

bool IsPocoF7(const std::string& model, const std::string& device, const std::string& soc_model) {
    const bool soc_match = ContainsInsensitive(soc_model, "SM8735") ||
                           ContainsInsensitive(soc_model, "Snapdragon 8s Gen 4");
    const bool device_match = ContainsInsensitive(model, "POCO F7") ||
                              ContainsInsensitive(model, "25053PC47") ||
                              ContainsInsensitive(device, "onyx");
    return soc_match && device_match;
}

void ApplyStable60Preset() {
#ifdef HAS_NCE
    Settings::values.cpu_backend.SetValue(Settings::CpuBackend::Nce);
#endif
    Settings::values.use_multi_core.SetValue(true);

    Settings::values.renderer_backend.SetValue(Settings::RendererBackend::Vulkan);
    Settings::values.resolution_setup.SetValue(Settings::ResolutionSetup::Res1X);
    Settings::values.gpu_accuracy.SetValue(Settings::GpuAccuracy::Low);

    Settings::values.use_disk_shader_cache.SetValue(true);
    Settings::values.use_vulkan_driver_pipeline_cache.SetValue(true);
    Settings::values.accelerate_astc.SetValue(Settings::AstcDecodeMode::Gpu);
    Settings::values.astc_recompression.SetValue(Settings::AstcRecompression::Uncompressed);

    // Required on the target setup to pass Borderlands 2's Gearbox intro reliably.
    Settings::values.sync_memory_operations.SetValue(true);

    // The target POCO F7 is used with active cooling.
    Settings::values.renderer_force_max_clock.SetValue(true);

    // Preserve the stable Eden v0.2.1 Android timing model.
    Settings::values.use_asynchronous_gpu_emulation.SetValue(false);
    Settings::values.async_presentation.SetValue(false);
    Settings::values.use_asynchronous_shaders.SetValue(false);
    Settings::values.use_reactive_flushing.SetValue(false);

    // Do not force experimental EDS/unswizzle paths in the baseline build. The user's
    // original Eden + V36 is already stable outside first-time shader compilation.
    Settings::values.dyna_state.SetValue(Settings::ExtendedDynamicState::Disabled);
    Settings::values.gpu_unswizzle_enabled.SetValue(false);

    // Six workers gives the 8s Gen 4 more shader/pipeline parallelism without the previous
    // BL2-F7 nice(+10) priority demotion. UI still exposes 2..8 for A/B testing.
    AndroidSettings::values.pipeline_worker_count.SetValue(kInitialPipelineWorkers);

    // Gamepad-only target.
    AndroidSettings::values.show_input_overlay.SetValue(false);
    AndroidSettings::values.touchscreen.SetValue(false);
}

} // namespace

ProfileResult TryApply(Core::System& system, const std::string& filepath) {
    ProfileResult result{};
    result.model = GetSystemProperty("ro.product.model");
    result.device = GetSystemProperty("ro.product.device");
    result.soc_model = GetSystemProperty("ro.soc.model");
    result.poco_f7_detected = IsPocoF7(result.model, result.device, result.soc_model);

    const auto program_id = ReadProgramId(system, filepath);
    if (!program_id) {
        LOG_WARNING(Frontend, "[BL2-F7] Could not read Program ID before boot");
        return result;
    }

    result.program_id = *program_id;
    result.title_detected = result.program_id == kBorderlands2ProgramId;

    LOG_INFO(Frontend,
             "[BL2-F7] Probe: program_id={:016X}, model='{}', device='{}', soc='{}', f7={}",
             result.program_id, result.model, result.device, result.soc_model,
             result.poco_f7_detected);

    if (!result.title_detected) {
        LOG_ERROR(Frontend, "[BL2-F7] Unsupported title blocked: {:016X}", result.program_id);
        return result;
    }

    if (!result.poco_f7_detected) {
        LOG_WARNING(Frontend,
                    "[BL2-F7] Borderlands 2 detected outside POCO F7/SM8735; "
                    "single-title boot allowed, F7 preset not applied");
        return result;
    }

    ApplyStable60Preset();
    result.applied = true;

    LOG_INFO(Frontend,
             "[BL2-F7] Stable60 preset applied: NCE(if available), Vulkan, 1x, GPU-fast, "
             "caches=on, sync-memory=on, max-clock=on, workers={}",
             kInitialPipelineWorkers);
    return result;
}

} // namespace BL2F7

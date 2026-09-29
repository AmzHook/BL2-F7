#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EDEN_DIR="${ROOT_DIR}/eden"
EDEN_SHA="${EDEN_SHA:-58c1e20ee58efa3900ba616207d460886214480b}"

rm -rf "${EDEN_DIR}"

# Prefer the upstream Eden server used by the requested v0.2.1 release.
# The public GitHub mirror is a fallback in case the upstream host is unavailable from CI.
if ! git clone --recursive https://git.eden-emu.dev/eden-emu/eden.git "${EDEN_DIR}"; then
  echo "Upstream clone failed; using the Eden public GitHub mirror."
  git clone --recursive https://github.com/eden-emulator/mirror.git "${EDEN_DIR}"
fi

cd "${EDEN_DIR}"
git checkout "${EDEN_SHA}"
git submodule sync --recursive
git submodule update --init --recursive --jobs 4

ACTUAL_SHA="$(git rev-parse HEAD)"
if [[ "${ACTUAL_SHA}" != "${EDEN_SHA}" ]]; then
  echo "Unexpected Eden revision: ${ACTUAL_SHA}" >&2
  exit 1
fi

python3 "${ROOT_DIR}/patch-kit/scripts/apply_bl2_f7.py"
python3 "${ROOT_DIR}/patch-kit/scripts/verify_bl2_f7.py"

echo "BL2-F7 source prepared at ${EDEN_DIR}"

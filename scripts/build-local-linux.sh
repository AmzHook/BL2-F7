#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VARIANT="${1:-instrumented}"

"${ROOT_DIR}/scripts/prepare-eden.sh"
cd "${ROOT_DIR}/eden/src/android"
chmod +x gradlew

case "${VARIANT}" in
  instrumented)
    ./gradlew assembleBl2F7RelWithDebInfo --no-daemon --stacktrace
    ;;
  release)
    ./gradlew assembleBl2F7Release --no-daemon --stacktrace
    ;;
  *)
    echo "Usage: $0 [instrumented|release]" >&2
    exit 2
    ;;
esac

find app/build/outputs/apk -type f -name '*.apk' -print

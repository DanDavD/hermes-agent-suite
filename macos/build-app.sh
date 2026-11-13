#!/usr/bin/env bash
# ==============================================================================
# Hermes Studio v2 - Native macOS Application Compiler & Bundler
# Compiles Swift Cocoa entrypoint and packages standalone .app bundle
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BUILD_DIR="${SCRIPT_DIR}/build"
APP_BUNDLE="${BUILD_DIR}/Hermes Studio.app"
CONTENTS_DIR="${APP_BUNDLE}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

echo "=================================================================="
echo "Compiling Hermes Studio Native macOS Desktop Application"
echo "=================================================================="

# 1. Clean previous build directory
rm -rf "${BUILD_DIR}"
mkdir -p "${MACOS_DIR}" "${RESOURCES_DIR}"

# 2. Compile Swift binary with optimizations
echo "[1/4] Compiling Swift source (Cocoa + WebKit)..."
swiftc -O \
    -target arm64-apple-macosx12.0 \
    -framework Cocoa \
    -framework WebKit \
    "${SCRIPT_DIR}/Sources/main.swift" \
    -o "${MACOS_DIR}/Hermes Studio"

# 3. Copy Plist and App Icon
echo "[2/4] Assembling .app bundle contents..."
cp "${SCRIPT_DIR}/Resources/Info.plist" "${CONTENTS_DIR}/Info.plist"
if [[ -f "${SCRIPT_DIR}/Resources/HermesStudio.icns" ]]; then
    cp "${SCRIPT_DIR}/Resources/HermesStudio.icns" "${RESOURCES_DIR}/HermesStudio.icns"
fi

# 4. Sign binary with ad-hoc signature for local execution
echo "[3/4] Applying local ad-hoc code signature..."
codesign -s - --force --deep "${APP_BUNDLE}"

# 5. Optional install to /Applications
if [[ "${1:-}" == "--install" ]] || [[ "${INSTALL_APP:-false}" == "true" ]]; then
    echo "[4/4] Installing to /Applications/Hermes Studio.app ..."
    rm -rf "/Applications/Hermes Studio.app"
    cp -R "${APP_BUNDLE}" "/Applications/"
    echo "[OK] Installed to /Applications/Hermes Studio.app"
else
    echo "[4/4] Build complete: ${APP_BUNDLE}"
    echo "Tip: Run with --install to copy directly into /Applications."
fi

echo "=================================================================="
echo "Hermes Studio.app built successfully!"
echo "=================================================================="

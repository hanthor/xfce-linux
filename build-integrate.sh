#!/bin/bash
# XFCE Linux BuildStream Build Script
# Integrates pre-built XFCE binaries and builds the OCI image

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
BINARIES_DIR="$PROJECT_ROOT/files/xfce-binaries/install"
TEMP_EXTRACT_DIR="${XDG_RUNTIME_DIR:-/tmp}/xfce-extract-$$"

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║           XFCE Linux BuildStream - Integration & Build Script            ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"

# Cleanup on exit
cleanup() {
    if [[ -d "$TEMP_EXTRACT_DIR" ]]; then
        echo "[CLEANUP] Removing temporary directory: $TEMP_EXTRACT_DIR"
        rm -rf "$TEMP_EXTRACT_DIR"
    fi
}
trap cleanup EXIT

# Step 1: Verify binaries are extracted
echo ""
echo "=== Step 1: Verifying XFCE binaries ==="
if [[ ! -d "$BINARIES_DIR" ]]; then
    echo "[ERROR] Binaries directory not found: $BINARIES_DIR"
    echo "[INFO] Extracting from tarball..."
    mkdir -p "$PROJECT_ROOT/files/xfce-binaries"
    cd "$PROJECT_ROOT/files/xfce-binaries"
    tar -xzf "$PROJECT_ROOT/files/sources/xfce-binaries.tar.gz"
    echo "[✓] Binaries extracted"
fi

BINARIES_COUNT=$(find "$BINARIES_DIR/bin" -type f -executable 2>/dev/null | wc -l)
PLUGINS_COUNT=$(find "$BINARIES_DIR/lib64/xfce4/panel/plugins" -type f 2>/dev/null | wc -l || echo 0)

echo "[✓] Found $BINARIES_COUNT binaries"
echo "[✓] Found $PLUGINS_COUNT panel plugins"

# Step 2: Show element resolution
echo ""
echo "=== Step 2: Validating BuildStream elements ==="
cd "$PROJECT_ROOT"
timeout 180 just bst show oci/xfce-linux.bst > /dev/null 2>&1 && \
    echo "[✓] All elements resolve correctly" || \
    (echo "[ERROR] Element resolution failed"; exit 1)

# Step 3: Show build information
echo ""
echo "=== Step 3: Build Information ==="
TOTAL_ELEMENTS=$(timeout 180 just bst show oci/xfce-linux.bst 2>/dev/null | grep -E '(cached|buildable|waiting|fetch needed)' | wc -l)
echo "[INFO] Total elements: $TOTAL_ELEMENTS"

# Step 4: Ready for build
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║                         READY FOR BUILD                                   ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "To build the OCI image, run:"
echo "  cd $PROJECT_ROOT"
echo "  just build"
echo ""
echo "To boot the image in QEMU, run:"
echo "  just boot-vm"
echo ""

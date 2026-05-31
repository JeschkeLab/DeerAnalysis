#!/usr/bin/env bash
#
# Build a distributable single-file Flatpak bundle of DeerAnalysis.
#
# Output: DeerAnalysis.flatpak in the repo root.
# Install on a target machine with:
#   flatpak install --user DeerAnalysis.flatpak
#
set -euo pipefail

APP_ID="io.github.JeschkeLab.DeerAnalysis"
MANIFEST="packaging/flatpak/${APP_ID}.yml"
REPO_DIR="repo"
BUILD_DIR="build-dir"
BUNDLE="DeerAnalysis.flatpak"
RUNTIME_REPO="https://flathub.org/repo/flathub.flatpakrepo"

# Run from the repo root (this script lives in packaging/flatpak/), so the
# repo/, build-dir/ and DeerAnalysis.flatpak outputs land at the top level.
cd "$(dirname "$0")/../.."

# 1. Build the app and export it into a local OSTree repo.
flatpak-builder --force-clean --repo="${REPO_DIR}" "${BUILD_DIR}" "${MANIFEST}"

# 2. Pack the repo into one self-contained .flatpak file. --runtime-repo
#    embeds where to fetch org.gnome.Platform so users without it can pull
#    the runtime from Flathub automatically on install.
flatpak build-bundle "${REPO_DIR}" "${BUNDLE}" "${APP_ID}" \
    --runtime-repo="${RUNTIME_REPO}"

echo "Created ${BUNDLE}"

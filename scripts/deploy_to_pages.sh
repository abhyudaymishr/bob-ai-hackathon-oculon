#!/usr/bin/env bash
# ==============================================================================
# Deploy Static Maps to GitHub Pages (tesseractthou-code/tessracting-oculon)
# Usage:
#   ./scripts/deploy_to_pages.sh [TARGET_REPO] [BRANCH]
# Example:
#   ./scripts/deploy_to_pages.sh tesseractthou-code/tessracting-oculon main
# ==============================================================================

set -euo pipefail

TARGET_REPO="${1:-tesseractthou-code/tessracting-oculon}"
BRANCH="${2:-main}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Oculon Static Web Portal Deployment ==="
echo "Target Repo: https://github.com/${TARGET_REPO}"
echo "Branch:      ${BRANCH}"

# 1. Build the pages payload
echo "--> Building static pages..."
python3 "${ROOT_DIR}/scripts/build_pages_site.py"

TEMP_DIR="$(mktemp -d -t oculon_pages_deploy_XXXXXX)"
echo "--> Staging directory: ${TEMP_DIR}"

# 2. Clone or initialize target repo
if git clone "git@github.com:${TARGET_REPO}.git" "${TEMP_DIR}" 2>/dev/null || \
   git clone "https://github.com/${TARGET_REPO}.git" "${TEMP_DIR}" 2>/dev/null; then
  echo "Target repository cloned successfully."
else
  echo "Target repo not cloneable via default git credentials. Initializing new repo..."
  cd "${TEMP_DIR}"
  git init -b "${BRANCH}"
  git remote add origin "https://github.com/${TARGET_REPO}.git"
  cd - >/dev/null
fi

# 3. Sync files
rm -rf "${TEMP_DIR}"/*
cp -R "${ROOT_DIR}/dist_pages"/* "${TEMP_DIR}/"
cp "${ROOT_DIR}/dist_pages/.nojekyll" "${TEMP_DIR}/" 2>/dev/null || touch "${TEMP_DIR}/.nojekyll"

# 4. Commit and push
cd "${TEMP_DIR}"
git add -A
if git diff --staged --quiet; then
  echo "No changes to deploy. Everything is already up to date!"
else
  git commit -m "Deploy Oculon live web maps portal"
  echo "--> Pushing to https://github.com/${TARGET_REPO} (${BRANCH})..."
  git push -u origin "${BRANCH}"
  echo "Deployment complete! Live at: https://tesseractthou-code.github.io/tessracting-oculon/"
fi

# 5. Cleanup
rm -rf "${TEMP_DIR}"

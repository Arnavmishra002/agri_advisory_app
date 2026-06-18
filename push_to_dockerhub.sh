#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# push_to_dockerhub.sh — Build, tag, and push KrishiMitra to Docker Hub
# Usage:  bash push_to_dockerhub.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DOCKER_USER="arnavmishra002"
IMAGE_NAME="krishimitra-ai"
SHORT_SHA=$(git -C "$(dirname "$0")" rev-parse --short HEAD 2>/dev/null || echo "latest")

echo "══════════════════════════════════════════"
echo " KrishiMitra — Docker Hub Push"
echo " Tag: ${DOCKER_USER}/${IMAGE_NAME}:${SHORT_SHA}"
echo "══════════════════════════════════════════"

# 1. Ensure we're logged in
if ! docker info 2>/dev/null | grep -q "Username"; then
  echo "🔑 Not logged in. Logging in to Docker Hub..."
  docker login -u "$DOCKER_USER"
fi

# 2. Re-tag the locally built image (avoids a full rebuild)
echo "📦 Tagging krishimitra-api:latest → ${DOCKER_USER}/${IMAGE_NAME}:latest"
docker tag "krishimitra-api:latest" "${DOCKER_USER}/${IMAGE_NAME}:latest"
docker tag "krishimitra-api:latest" "${DOCKER_USER}/${IMAGE_NAME}:${SHORT_SHA}"

# 3. Push both tags
echo "🚀 Pushing ${DOCKER_USER}/${IMAGE_NAME}:latest..."
docker push "${DOCKER_USER}/${IMAGE_NAME}:latest"

echo "🚀 Pushing ${DOCKER_USER}/${IMAGE_NAME}:${SHORT_SHA}..."
docker push "${DOCKER_USER}/${IMAGE_NAME}:${SHORT_SHA}"

echo ""
echo "✅ Done! Pushed:"
echo "   docker.io/${DOCKER_USER}/${IMAGE_NAME}:latest"
echo "   docker.io/${DOCKER_USER}/${IMAGE_NAME}:${SHORT_SHA}"

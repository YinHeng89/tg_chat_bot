#!/bin/bash
set -e

# ==================== 配置 ====================
DOCKER_USER="yinheng1989"
IMAGE_NAME="tg-chat-bot"
VERSION=$(date +%Y%m%d-%H%M)

cd "$(dirname "$0")"

echo "========================================"
echo "  TG Chat Bot 打包发布"
echo "  镜像: ${DOCKER_USER}/${IMAGE_NAME}"
echo "  版本: ${VERSION}"
echo "========================================"

# ---- 1. 登录 ----
echo ""
echo "[1/5] 检查 Docker Hub 登录状态..."
DOCKER_CONFIG="${DOCKER_CONFIG:-$HOME/.docker}"
if ! grep -q '"https://index.docker.io/v1/"' "$DOCKER_CONFIG/config.json" 2>/dev/null; then
  echo "⚠️  未登录 Docker Hub，请登录："
  docker login
fi

# ---- 2. 创建/使用 buildx builder ----
echo ""
echo "[2/5] 检查 buildx builder..."
if ! docker buildx ls | grep -q "tg-chat-bot-builder"; then
  docker buildx create --name tg-chat-bot-builder --use
else
  docker buildx use tg-chat-bot-builder
fi
docker buildx inspect --bootstrap

# ---- 3. 构建并推送（多架构） ----
echo ""
echo "[3/5] 构建并推送多架构镜像 (amd64 + arm64)..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ${DOCKER_USER}/${IMAGE_NAME}:latest \
  -t ${DOCKER_USER}/${IMAGE_NAME}:${VERSION} \
  --push \
  .

# ---- 4. 摘要 ----
echo ""
echo "[4/5] ✅ 发布完成！"
echo ""
echo "  镜像地址:"
echo "    ${DOCKER_USER}/${IMAGE_NAME}:latest"
echo "    ${DOCKER_USER}/${IMAGE_NAME}:${VERSION}"
echo ""
echo "  docker-compose 引用:"
echo "    image: ${DOCKER_USER}/${IMAGE_NAME}:latest"

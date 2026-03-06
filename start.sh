#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE_FILE="$ROOT_DIR/.env.example"

usage() {
  cat <<'EOF'
用法:
  ./start.sh [--detach|-d]

说明:
  使用 Docker Compose 启动项目依赖与服务（postgres/redis/backend/frontend）。

选项:
  -d, --detach  后台启动（等同 docker compose up -d）
  -h, --help    显示帮助
EOF
}

COMPOSE_ARGS=("up" "--build")
if [[ "${1:-}" == "-d" || "${1:-}" == "--detach" ]]; then
  COMPOSE_ARGS+=("-d")
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
elif [[ $# -gt 0 ]]; then
  echo "未知参数: $1"
  echo
  usage
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ENV_EXAMPLE_FILE" ]]; then
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
    echo "未找到 .env，已从 .env.example 自动创建。请按需修改 .env 后重新执行脚本。"
    exit 0
  else
    echo "未找到 .env 文件，且不存在 .env.example。"
    exit 1
  fi
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "未检测到 Docker Compose，请先安装 docker compose 或 docker-compose。"
  exit 1
fi

echo "执行: ${COMPOSE_CMD[*]} ${COMPOSE_ARGS[*]}"
"${COMPOSE_CMD[@]}" "${COMPOSE_ARGS[@]}"

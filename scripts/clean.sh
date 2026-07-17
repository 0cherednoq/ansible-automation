#!/usr/bin/env bash
# Освободить место на серверах: неиспользуемые контейнеры, образы, build-кэш.
# Volumes НЕ трогает (данные сохраняются).
set -euo pipefail

ansible app -m shell -a 'df -h / && echo "---" && docker system df'
echo "=== очистка ==="
ansible app -m shell -a 'docker container prune -f && docker image prune -af && docker builder prune -af'
echo "=== после ==="
ansible app -m shell -a 'df -h /'

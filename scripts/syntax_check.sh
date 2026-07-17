#!/usr/bin/env bash
# Проверить синтаксис всех плейбуков.
set -euo pipefail

for pb in playbooks/*.yml; do
  echo "== $pb =="
  ansible-playbook "$pb" --syntax-check
done

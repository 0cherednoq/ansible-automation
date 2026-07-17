#!/usr/bin/env bash
# Деплой/редеплой. Vault-пароль подхватывается автоматически, если есть.
# Доп. аргументы прокидываются в ansible-playbook: scripts/deploy.sh --limit srv1
set -euo pipefail

vault=""
[ -f "$VAULT_PASS_FILE" ] && vault="--vault-password-file $VAULT_PASS_FILE"
ansible-playbook playbooks/04-deploy.yml $vault "$@"

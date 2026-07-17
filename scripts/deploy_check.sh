#!/usr/bin/env bash
# Dry-run деплоя (--check --diff): ничего не меняет на серверах.
set -euo pipefail

vault=""
[ -f "$VAULT_PASS_FILE" ] && vault="--vault-password-file $VAULT_PASS_FILE"
ansible-playbook playbooks/04-deploy.yml --check --diff $vault "$@"

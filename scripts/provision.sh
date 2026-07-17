#!/usr/bin/env bash
# Полный цикл подготовки и деплоя по порядку.
set -euo pipefail

vault=""
[ -f "$VAULT_PASS_FILE" ] && vault="--vault-password-file $VAULT_PASS_FILE"
ansible-galaxy collection install -r requirements.yml
ansible-playbook playbooks/01-bootstrap-ssh.yml --ask-pass
ansible-playbook playbooks/02-harden-ssh.yml
ansible-playbook playbooks/03-prepare-server.yml
ansible-playbook playbooks/04-deploy.yml $vault

#!/usr/bin/env bash
# Сохранить git-токен в зашифрованный Ansible Vault.
# Использование: scripts/save_token.sh <ТОКЕН>
# Переменные VAULT_PASS_FILE / VAULT_FILE приходят из окружения mise.
set -euo pipefail

TOKEN="${1:-}"
if [ -z "$TOKEN" ]; then
  echo "Использование: mise run secrets:token <ТОКЕН>" >&2
  exit 1
fi

# Пароль Vault: создаётся один раз случайным, лежит локально (в .gitignore).
if [ ! -f "$VAULT_PASS_FILE" ]; then
  openssl rand -base64 32 > "$VAULT_PASS_FILE"
  chmod 600 "$VAULT_PASS_FILE"
  echo "Создан $VAULT_PASS_FILE (пароль Vault)."
fi

# Записать токен во временный файл и зашифровать его в VAULT_FILE.
umask 077
printf 'app_git_token: "%s"\n' "$TOKEN" > .vault.tmp
ansible-vault encrypt --vault-password-file "$VAULT_PASS_FILE" --output "$VAULT_FILE" .vault.tmp
rm -f .vault.tmp
echo "Токен сохранён и зашифрован в $VAULT_FILE."

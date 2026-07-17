# Шпаргалка по командам

Запускать с Linux/macOS или из WSL (Ansible на Windows напрямую не работает).
Все команды выполняются из корня проекта.

## 0. Подготовка (один раз)

```bash
# Установить коллекции Ansible
ansible-galaxy collection install -r requirements.yml
```

## 1. Bootstrap SSH — первый вход по паролю, установка ключа root

```bash
ansible-playbook playbooks/01-bootstrap-ssh.yml --ask-pass
```

- `--ask-pass` — спросит пароль root на сервере.
- Пароль на этом шаге ещё НЕ отключается.
- Разные пароли на серверах → бутстрапить по одному: добавить `--limit srv1`.

## 2. Harden SSH + базовые утилиты — отключить пароль, поставить curl/git/архиваторы

```bash
ansible-playbook playbooks/02-harden-ssh.yml
```

- Запускать только после успешного шага 1 (вход по ключу проверен).
- После него вход по паролю запрещён, root — только по ключу.

## 3. Подготовка сервера — Docker, локаль ru_RU.UTF-8

```bash
ansible-playbook playbooks/03-prepare-server.yml
```

## 4. Деплой / редеплой

```bash
# Первый деплой (клон) или обновление до ветки по умолчанию (main)
ansible-playbook playbooks/04-deploy.yml

# Редеплой конкретной версии (тег/коммит/ветка)
ansible-playbook playbooks/04-deploy.yml -e app_version=v1.2.3

# Приватный репозиторий Gitea (токен в Vault)
ansible-playbook playbooks/04-deploy.yml --ask-vault-pass

# Деплой только на один сервер
ansible-playbook playbooks/04-deploy.yml --limit srv2
```

- Раскатка идёт по одному серверу (`serial: 1`); при падении — стоп.

## 5. Языковые рантаймы (опционально) — uv, Node.js, pm2, Go, Rust, PHP

```bash
# Всё сразу
ansible-playbook playbooks/05-install-runtimes.yml

# Выборочно по тегам (uv, node, pm2, go, rust, php)
ansible-playbook playbooks/05-install-runtimes.yml --tags node,go

# Переопределить версию на запуске
ansible-playbook playbooks/05-install-runtimes.yml --tags go -e go_version=1.22.5
```

## Полезные флаги (к любому плейбуку)

```bash
--check                       # dry-run, ничего не меняет
--diff                        # показать изменения в файлах
--limit srv1                  # только указанный(е) сервер(ы)
-e ssh_proxy_enabled=true     # подключаться через Tor/SOCKS-прокси
--syntax-check                # проверка синтаксиса (нужен Ansible)
-vvv                          # подробный вывод для отладки
--ask-vault-pass              # если используется Vault (токен Gitea)
```

## Типовой первый запуск (весь цикл)

```bash
ansible-galaxy collection install -r requirements.yml
ansible-playbook playbooks/01-bootstrap-ssh.yml --ask-pass
ansible-playbook playbooks/02-harden-ssh.yml
ansible-playbook playbooks/03-prepare-server.yml
ansible-playbook playbooks/04-deploy.yml --ask-vault-pass
# при необходимости:
ansible-playbook playbooks/05-install-runtimes.yml
```

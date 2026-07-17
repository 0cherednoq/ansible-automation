# Ansible: подготовка, SSH и Docker-деплой

Плейбуки рассчитаны на Debian/Ubuntu и запускаются с Linux/macOS или из WSL.
Всё выполняется под пользователем **root**.

1. Установите коллекции:

   `ansible-galaxy collection install -r requirements.yml`

2. Заполните `inventories/production/hosts.yml` и
   `inventories/production/group_vars/all.yml` (как минимум `ansible_host`,
   `app_repo` и `docker_compose_files`). Compose-файлы должны храниться в Git.
   Для нескольких серверов перечислите их в группах `bootstrap` и `app`
   (пример на 3 хоста уже в `hosts.yml`). Все шаги применяются ко всем
   серверам группы `app`.

3. Первый вход по логину/паролю, генерация ключа и отключение пароля:

   `ansible-playbook playbooks/01-bootstrap-ssh.yml --ask-pass`

   Приватный ключ останется только на управляющей машине по пути
   `ssh_private_key_path`; на сервер копируется лишь публичный ключ (в
   `authorized_keys` root). Пароль на этом шаге ещё не отключается.

4. Отключить вход по паролю и установить базовые утилиты (curl, git,
   архиваторы и т.д. — список в `base_utils`):

   `ansible-playbook playbooks/02-harden-ssh.yml`

   После этого вход по паролю запрещён, root пускается только по ключу
   (`PermitRootLogin prohibit-password`).

5. Подготовка сервера и ru_RU.UTF-8:

   `ansible-playbook playbooks/03-prepare-server.yml`

6. Деплой (первый запуск — клонирование Git, последующие — обновление):

   `ansible-playbook playbooks/04-deploy.yml`

   Редеплой конкретной версии:

   `ansible-playbook playbooks/04-deploy.yml -e app_version=<tag-or-commit>`

   Раскатка идёт по одному серверу за раз (`serial: 1`). Если на сервере
   деплой упал (например, `--wait` не дождался healthcheck), раскатка
   останавливается и остальные серверы не трогаются (`max_fail_percentage: 0`).
   Ускорить: `serial: 2` или `"50%"` в `playbooks/04-deploy.yml`.
   Ограничить одним сервером: `--limit srv2`.

7. (Опционально) Языковые рантаймы на хост — uv, Node.js, pm2, Go, Rust, PHP:

   `ansible-playbook playbooks/05-install-runtimes.yml`

   Выборочно по тегам: `--tags node,go` (теги: `uv`, `node`, `pm2`, `go`,
   `rust`, `php`). Версии задаются в `roles/dev_runtimes/defaults/main.yml`.
   Так как приложение работает в Docker, эти рантаймы нужны на хосте лишь как
   инструментарий (сборка, вспомогательные скрипты, pm2 для не-докеризованных
   процессов), а не для самого приложения.

Код разворачивается в домашнем каталоге пользователя подключения
(`{{ ansible_env.HOME }}/myapp`, для root — `/root/myapp`) и создаётся самим
git при клонировании: никаких каталогов релизов,
Python virtualenv или генерируемого `.env` нет. Образы собираются на сервере
(`--build`). Деплой ждёт готовности контейнеров (`--wait`): если healthcheck не
проходит, деплой завершается ошибкой, а не ложным успехом. После запуска
неиспользуемые образы удаляются (`docker image prune`).

## Подключение через прокси (Tor)

Все SSH-подключения (bootstrap, подготовка, деплой) можно пустить через один
SOCKS-прокси — например локальный Tor.

1. На управляющей машине должны быть запущен Tor (SOCKS5 на `127.0.0.1:9050`)
   и установлен `netcat-openbsd` (даёт `nc` с поддержкой `-X`).
2. Включите прокси на запуске любого плейбука:

   `ansible-playbook playbooks/04-deploy.yml -e ssh_proxy_enabled=true`

   Либо выставьте `ssh_proxy_enabled: true` в `group_vars/all.yml`, чтобы
   прокси применялся всегда.

Параметры прокси (`ssh_proxy_host`, `ssh_proxy_port`, `ssh_proxy_command`)
задаются в `group_vars/all.yml`. Механизм — `ProxyCommand` через `nc -X 5`
(SOCKS5); при `ssh_proxy_enabled: false` подключение идёт напрямую.
Если серверы доступны как `.onion`, укажите такой адрес в `ansible_host` —
Tor резолвит имя сам.

## Приватные репозитории Gitea

SSH в Gitea отключён — клонируем по HTTPS с токеном доступа.

1. В Gitea создайте токен: Settings → Applications → Generate Token,
   scope `read:repository` (достаточно для клона/pull).
2. Укажите `app_repo` в формате `https://gitea.example.com/OWNER/REPO.git`.
3. Токен положите в зашифрованный Vault, а не в `all.yml`:

   ```bash
   ansible-vault create inventories/production/group_vars/vault.yml
   # внутри:  app_git_token: "<ваш-токен>"
   ansible-playbook playbooks/04-deploy.yml --ask-vault-pass
   ```

Токен передаётся git через HTTP-заголовок `Authorization: token ...`
(переменные окружения `GIT_CONFIG_*`), поэтому он **не сохраняется** в
`.git/config` на сервере. Для публичных репозиториев оставьте
`app_git_token` пустым — авторизация не применяется.

Если приватные образы требуют авторизации, выполните `docker login` на сервере
заранее либо добавьте отдельную Vault-защищённую задачу. Секреты приложения и
`.env` этот набор плейбуков намеренно не создаёт и не изменяет.

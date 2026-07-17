#!/usr/bin/env python3
"""Интерактивная разметка .env.example аннотациями dotenver.

Проходит по переменным без аннотации, для каждой предлагает тип генерации
(с умным дефолтом по имени переменной). Пользователь жмёт Enter (принять
дефолт) или вводит номер типа. В конце дописывает `## dotenver:...` в файл.

Запуск:  python scripts/annotate_env.py            # env/.env.example
         python scripts/annotate_env.py -t path
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VAR_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<val>.*)$")
HAS_ANNOTATION = re.compile(r"##\s*dotenver:")

# Меню типов: номер -> (подпись, функция построения аннотации).
# Функции могут спрашивать доп. параметры (длину и т.п.).
MANUAL_RE = re.compile(
    r"(API[_-]?KEY|APIKEY|ACCESS[_-]?TOKEN|CLIENT[_-]?ID|CLIENT[_-]?SECRET"
    r"|OAUTH|WEBHOOK|DSN|(?<!SECRET_)TOKEN)", re.IGNORECASE)
SECRETKEY_RE = re.compile(r"SECRET[_-]?KEY|PRIVATE[_-]?KEY", re.IGNORECASE)
PASSWORD_RE = re.compile(r"PASSWORD|PASSWD|SECRET|SALT", re.IGNORECASE)
BOOL_RE = re.compile(r"DEBUG|ENABLE|DISABLE|_BOOL|IS_|USE_", re.IGNORECASE)
EMAIL_RE = re.compile(r"EMAIL|MAIL(?!_)", re.IGNORECASE)


def ask(prompt: str, default: str = "") -> str:
    try:
        s = input(prompt).strip()
    except EOFError:
        return default
    return s or default


def build_password(length_default: int) -> str:
    n = ask(f"    длина [{length_default}]: ", str(length_default))
    try:
        n = int(n)
    except ValueError:
        n = length_default
    return f"password(length={n}, special_chars=False)"


# Пункты меню: (подпись, builder или строковая аннотация)
def menu_items():
    return [
        ("пропустить (заполнить вручную / оставить как есть)", None),
        ("пароль (буквы+цифры)", lambda: build_password(32)),
        ("секретный ключ (длинный)", lambda: build_password(60)),
        ("boolean (true/false)", lambda: "boolean(chance_of_getting_true=50)"),
        ("uuid4", lambda: "uuid4()"),
        ("email", lambda: "email()"),
        ("имя (name)", lambda: "name()"),
        ("слово (word)", lambda: "word()"),
        ("своё выражение dotenver", lambda: ask("    dotenver: ").strip()),
    ]


def suggest_index(key: str) -> int:
    if MANUAL_RE.search(key):
        return 0                       # внешний ключ — вручную
    if SECRETKEY_RE.search(key):
        return 2
    if PASSWORD_RE.search(key):
        return 1
    if BOOL_RE.search(key):
        return 3
    if EMAIL_RE.search(key):
        return 5
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Интерактивная разметка .env.example для dotenver")
    ap.add_argument("-t", "--template", default="env/.env.example")
    args = ap.parse_args()

    path = Path(args.template)
    if not path.exists():
        print(f"[ОШИБКА] Файл не найден: {path}", file=sys.stderr)
        return 1
    if not sys.stdin.isatty():
        print("[ОШИБКА] Нужен интерактивный терминал.", file=sys.stderr)
        return 1

    lines = path.read_text(encoding="utf-8").splitlines()
    items = menu_items()

    menu_text = "\n".join(f"      {i}. {label}" for i, (label, _) in enumerate(items))
    print(f"Разметка {path}. Для каждой переменной: Enter — принять дефолт, "
          f"номер — выбрать тип.\nТипы:\n{menu_text}\n")

    changed = 0
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        m = VAR_RE.match(line)
        if not m or HAS_ANNOTATION.search(line):
            continue

        key, val = m.group("key"), m.group("val")
        default = suggest_index(key)
        cur = f"  (текущее значение: {val})" if val.strip() else ""
        print(f"• {key}{cur}")
        choice = ask(f"    тип [{default}. {items[default][0]}]: ", str(default))
        try:
            choice = int(choice)
        except ValueError:
            choice = default
        if not 0 <= choice < len(items):
            choice = default

        builder = items[choice][1]
        if builder is None:
            print("    → пропущено\n")
            continue
        annotation = builder()
        if not annotation:
            print("    → пусто, пропущено\n")
            continue
        lines[idx] = f"{key}= ## dotenver:{annotation}"
        changed += 1
        print(f"    → {key}= ## dotenver:{annotation}\n")

    if changed == 0:
        print("Ничего не размечено — изменений нет.")
        return 0

    if ask(f"Записать {changed} аннотаций в {path}? [Y/n]: ", "y").lower() not in ("y", "yes", "д", "да"):
        print("Отменено, файл не изменён.")
        return 0

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Готово. Теперь сгенерируйте .env:  mise run env:gen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

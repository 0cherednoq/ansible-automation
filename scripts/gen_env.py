#!/usr/bin/env python3
"""Локальная генерация .env из аннотированного .env.example через dotenver.

Не ходит в git (это делает scripts/fetch_env_example.py). Работает с локальным
шаблоном: генерирует секреты по аннотациям `## dotenver:...`, сохраняет уже
заполненные значения (идемпотентность dotenver), печатает поля для ручного ввода.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

VAR_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<val>.*)$")


def manual_fields(text: str) -> list[str]:
    """Ключи с пустым значением — их нужно заполнить вручную (внешние ключи/токены)."""
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = VAR_RE.match(line)
        if m and m.group("val").strip() in ("", '""', "''"):
            out.append(m.group("key"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Генерация .env из .env.example (dotenver)")
    ap.add_argument("-t", "--template", default="env/.env.example",
                    help="локальный шаблон (по умолчанию env/.env.example)")
    args = ap.parse_args()

    template = Path(args.template)
    if not template.exists():
        print(f"[ОШИБКА] Шаблон не найден: {template}\n"
              f"Сначала скачайте его: mise run env:fetch", file=sys.stderr)
        return 1
    if shutil.which("dotenver") is None:
        print("[ОШИБКА] dotenver не найден. Установка: uv tool install dotenver "
              "(или mise install).", file=sys.stderr)
        return 1

    # dotenver создаёт .env рядом с шаблоном (.env.example -> .env),
    # сохраняя значения уже существующего .env.
    res = subprocess.run(["dotenver", "-r"], cwd=template.parent,
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ОШИБКА] dotenver: {res.stderr.strip()}", file=sys.stderr)
        return 1

    output = template.with_name(template.name.replace(".example", ""))
    if not output.is_file():
        print(f"[ОШИБКА] dotenver не создал {output}", file=sys.stderr)
        return 1
    try:
        output.chmod(0o600)
    except OSError:
        pass

    print(f"Записано: {output}")
    manual = manual_fields(output.read_text(encoding="utf-8"))
    if manual:
        print(f"\n⚠ Заполните вручную ({len(manual)}) — внешние ключи/токены "
              f"(пусто = функция выключена, если необязательна):")
        for k in manual:
            print(f"    {k}=")
        print(f"\n  Откройте {output} и впишите значения.")
    else:
        print("\nВсё готово — ручных значений не требуется.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

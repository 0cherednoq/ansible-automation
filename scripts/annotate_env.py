#!/usr/bin/env python3
"""Интерактивная разметка .env.example аннотациями dotenver.

TUI (curses): список переменных, навигация стрелками, выбор типа генерации,
редактирование параметров, сохранение. Если curses недоступен (напр. Windows
без WSL) — откат на простой построчный режим.

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

MANUAL_RE = re.compile(
    r"(API[_-]?KEY|APIKEY|ACCESS[_-]?TOKEN|CLIENT[_-]?ID|CLIENT[_-]?SECRET"
    r"|OAUTH|WEBHOOK|DSN|(?<!SECRET_)TOKEN)", re.IGNORECASE)
SECRETKEY_RE = re.compile(r"SECRET[_-]?KEY|PRIVATE[_-]?KEY", re.IGNORECASE)
PASSWORD_RE = re.compile(r"PASSWORD|PASSWD|SECRET|SALT", re.IGNORECASE)
BOOL_RE = re.compile(r"DEBUG|ENABLE|DISABLE|_BOOL|IS_|USE_", re.IGNORECASE)
EMAIL_RE = re.compile(r"EMAIL|MAIL(?!_)", re.IGNORECASE)

# (подпись, kind, дефолтный параметр). kind=None — пропустить.
TYPES = [
    ("пропустить (вручную)", None, None),
    ("пароль", "password", 32),
    ("секретный ключ", "password", 60),
    ("boolean", "boolean", None),
    ("uuid4", "uuid4", None),
    ("email", "email", None),
    ("имя", "name", None),
    ("слово", "word", None),
    ("своё выражение", "custom", ""),
]


def suggest_choice(key: str) -> int:
    if MANUAL_RE.search(key):
        return 0
    if SECRETKEY_RE.search(key):
        return 2
    if PASSWORD_RE.search(key):
        return 1
    if BOOL_RE.search(key):
        return 3
    if EMAIL_RE.search(key):
        return 5
    return 0


def build_annotation(choice: int, param) -> str | None:
    label, kind, _ = TYPES[choice]
    if kind is None:
        return None
    if kind == "password":
        return f"password(length={param}, special_chars=False)"
    if kind == "boolean":
        return "boolean(chance_of_getting_true=50)"
    if kind == "custom":
        return str(param).strip() or None
    return f"{kind}()"


def collect_rows(lines: list[str]):
    """Строки-переменные без готовой аннотации — их можно размечать."""
    rows = []
    annotated = 0
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        m = VAR_RE.match(line)
        if not m:
            continue
        if HAS_ANNOTATION.search(line):
            annotated += 1
            continue
        c = suggest_choice(m.group("key"))
        rows.append({
            "idx": idx,
            "key": m.group("key"),
            "value": m.group("val").strip(),
            "choice": c,
            "param": TYPES[c][2],
        })
    return rows, annotated


def type_label(row) -> str:
    label, kind, _ = TYPES[row["choice"]]
    if kind == "password":
        return f"{label} (len={row['param']})"
    if kind == "custom":
        return f"{label}: {row['param'] or '—'}"
    return label


def apply_and_write(path: Path, lines: list[str], rows) -> int:
    changed = 0
    for r in rows:
        ann = build_annotation(r["choice"], r["param"])
        if ann is None:
            continue
        lines[r["idx"]] = f"{r['key']}= ## dotenver:{ann}"
        changed += 1
    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


# --------------------------------------------------------------------------
# TUI (curses)
# --------------------------------------------------------------------------
def run_tui(path: Path, lines: list[str], rows) -> int:
    import curses

    def safe_addstr(win, y, x, text, attr=0):
        h, w = win.getmaxyx()
        if 0 <= y < h and x < w:
            win.addstr(y, x, text[: max(0, w - x - 1)], attr)

    def prompt(win, msg: str) -> str:
        curses.echo()
        curses.curs_set(1)
        h, w = win.getmaxyx()
        win.move(h - 1, 0)
        win.clrtoeol()
        safe_addstr(win, h - 1, 0, msg)
        win.refresh()
        try:
            s = win.getstr(h - 1, len(msg) + 1, 60).decode("utf-8", "ignore")
        except Exception:
            s = ""
        curses.noecho()
        curses.curs_set(0)
        return s.strip()

    def _main(stdscr):
        curses.curs_set(0)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
        sel = 0
        top = 0
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            safe_addstr(stdscr, 0, 0,
                        f" Разметка {path}  —  переменных: {len(rows)}",
                        curses.A_BOLD | (curses.color_pair(1) if curses.has_colors() else 0))
            safe_addstr(stdscr, 1, 0,
                        " ↑/↓ выбор · ←/→ тип · 0-8 быстрый выбор · e параметр · s сохранить · q выход",
                        curses.A_DIM)
            list_h = h - 4
            if sel < top:
                top = sel
            if sel >= top + list_h:
                top = sel - list_h + 1
            for i in range(top, min(len(rows), top + list_h)):
                r = rows[i]
                y = 3 + (i - top)
                marker = "▶ " if i == sel else "  "
                kind = TYPES[r["choice"]][1]
                col = 0
                if curses.has_colors():
                    col = curses.color_pair(2) if kind else curses.color_pair(3)
                val = f"={r['value']}" if r["value"] else "="
                line = f"{marker}{r['key']:<28} {val:<16} → {type_label(r)}"
                attr = curses.A_REVERSE if i == sel else col
                safe_addstr(stdscr, y, 0, line, attr)
            safe_addstr(stdscr, h - 1, 0,
                        " green = будет сгенерировано · yellow = пропущено (вручную)",
                        curses.A_DIM)
            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (curses.KEY_UP, ord("k")):
                sel = (sel - 1) % len(rows)
            elif ch in (curses.KEY_DOWN, ord("j")):
                sel = (sel + 1) % len(rows)
            elif ch in (curses.KEY_RIGHT, ord("l")):
                r = rows[sel]
                r["choice"] = (r["choice"] + 1) % len(TYPES)
                r["param"] = TYPES[r["choice"]][2]
            elif ch in (curses.KEY_LEFT, ord("h")):
                r = rows[sel]
                r["choice"] = (r["choice"] - 1) % len(TYPES)
                r["param"] = TYPES[r["choice"]][2]
            elif ord("0") <= ch <= ord("8"):
                idx = ch - ord("0")
                if idx < len(TYPES):
                    rows[sel]["choice"] = idx
                    rows[sel]["param"] = TYPES[idx][2]
            elif ch in (ord("e"), ord("E")):
                r = rows[sel]
                kind = TYPES[r["choice"]][1]
                if kind == "password":
                    s = prompt(stdscr, f"Длина для {r['key']} [{r['param']}]:")
                    if s.isdigit():
                        r["param"] = int(s)
                elif kind == "custom":
                    s = prompt(stdscr, f"dotenver для {r['key']}:")
                    if s:
                        r["param"] = s
            elif ch in (ord("s"), ord("S")):
                return "save"
            elif ch in (ord("q"), ord("Q"), 27):
                return "quit"

    action = curses.wrapper(_main)
    if action != "save":
        print("Отменено, файл не изменён.")
        return 0
    changed = apply_and_write(path, lines, rows)
    print(f"Записано аннотаций: {changed} в {path}")
    if changed:
        print("Теперь сгенерируйте .env:  mise run env:gen")
    return 0


# --------------------------------------------------------------------------
# Фолбэк: построчный режим без curses
# --------------------------------------------------------------------------
def run_line_mode(path: Path, lines: list[str], rows) -> int:
    menu = "\n".join(f"      {i}. {lbl}" for i, (lbl, _, _) in enumerate(TYPES))
    print(f"Разметка {path} (построчно). Enter — дефолт, номер — тип.\n{menu}\n")
    for r in rows:
        cur = f"  (значение: {r['value']})" if r["value"] else ""
        print(f"• {r['key']}{cur}")
        d = r["choice"]
        s = input(f"    тип [{d}. {TYPES[d][0]}]: ").strip()
        c = int(s) if s.isdigit() and int(s) < len(TYPES) else d
        r["choice"] = c
        r["param"] = TYPES[c][2]
        if TYPES[c][1] == "password":
            ln = input(f"    длина [{r['param']}]: ").strip()
            if ln.isdigit():
                r["param"] = int(ln)
        elif TYPES[c][1] == "custom":
            r["param"] = input("    dotenver: ").strip()
    if input("Записать изменения? [Y/n]: ").strip().lower() in ("", "y", "yes", "д", "да"):
        changed = apply_and_write(path, lines, rows)
        print(f"Записано аннотаций: {changed} в {path}")
        return 0
    print("Отменено.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Разметка .env.example для dotenver")
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
    rows, annotated = collect_rows(lines)
    if annotated:
        print(f"(уже размечено ранее: {annotated} — не трогаю)")
    if not rows:
        print("Нет переменных для разметки.")
        return 0

    try:
        import curses  # noqa: F401
        return run_tui(path, lines, rows)
    except ImportError:
        return run_line_mode(path, lines, rows)


if __name__ == "__main__":
    raise SystemExit(main())

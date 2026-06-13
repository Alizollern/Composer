#!/usr/bin/env python3
"""
Читалка журнала «мыслей» агента — по-человечески, без JSON.

Показывает, на чём ИИ основывал ответы и почему отказывал. Это инструмент
КОНТРОЛЯ: руководитель видит каждый шаг бота.

  python3 scripts/agent_log.py            — показать весь журнал
  python3 scripts/agent_log.py -n 20      — последние 20 записей
  python3 scripts/agent_log.py -f         — следить вживую (как tail -f)

Путь к журналу — env EVERGREEN_AGENT_LOG (по умолчанию var/logs/agent.jsonl).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path


def _path() -> Path:
    return Path(os.environ.get("EVERGREEN_AGENT_LOG", "var/logs/agent.jsonl"))


def render(rec: dict) -> str:
    ts = rec.get("ts", "")
    kind = rec.get("kind", "")
    if kind == "chat.retrieval":
        cands = ", ".join(f"{x['title']}={x['score']}" for x in rec.get("candidates", []))
        return (f"[{ts}] 🔎 ПОИСК по базе → лучшее совпадение {rec.get('best_score')} "
                f"(порог {rec.get('min_score')})\n        кандидаты: {cands or '—'}")
    if kind == "chat.decision":
        d = rec.get("decision")
        mark = "✅ ОТВЕТИЛ" if d == "answered" else "🚫 ОТКАЗАЛ"
        extra = ""
        if rec.get("sources"):
            extra = "  источники: " + ", ".join(rec["sources"])
        return f"[{ts}] {mark} (гейт «{rec.get('gate')}»){extra}"
    if kind == "llm.complete":
        out = (rec.get("output") or "").replace("\n", " ")
        return (f"[{ts}] 🤖 ВЫЗОВ МОДЕЛИ «{rec.get('operation')}» "
                f"({rec.get('elapsed_ms')} мс)\n        ответ: {out[:160]}")
    if kind in ("agent.run", "agent.orchestrate"):
        out = (rec.get("output") or "").replace("\n", " ")
        who = rec.get("agent") or rec.get("orchestrator") or "оркестратор"
        return f"[{ts}] 🧩 АГЕНТ {who} ({rec.get('elapsed_ms')} мс)\n        итог: {out[:160]}"
    return f"[{ts}] {kind}: {json.dumps(rec, ensure_ascii=False)[:200]}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=0, help="показать только последние N записей")
    ap.add_argument("-f", action="store_true", help="следить вживую (tail -f)")
    args = ap.parse_args()

    path = _path()
    if not path.exists():
        print(f"Журнал пуст или не создан: {path}\n"
              f"Подсказка: задай вопрос боту — и записи появятся.")
        return

    lines = path.read_text(encoding="utf-8").splitlines()
    if args.n:
        lines = lines[-args.n:]
    for ln in lines:
        try:
            print(render(json.loads(ln)))
        except Exception:
            print(ln)

    if args.f:
        print("\n— слежу за новыми записями (Ctrl+C чтобы выйти) —")
        with path.open("r", encoding="utf-8") as fh:
            fh.seek(0, os.SEEK_END)
            try:
                while True:
                    line = fh.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    try:
                        print(render(json.loads(line)))
                    except Exception:
                        print(line.rstrip())
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()

"""Единая конфигурация Composer AI (пути, модель). Меняется через env."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # ~/composer-ai
AGENTS_DIR = ROOT / "agents"                     # определения агентов (папки = данные)
WORKSPACE = ROOT / "workspace"                   # общая доска для обмена между агентами
PIPELINE_FILE = ROOT / "pipeline.txt"            # порядок агентов в пайплайне
MEMORY_FILE = ROOT / "memory.json"

WORKSPACE.mkdir(exist_ok=True)
AGENTS_DIR.mkdir(exist_ok=True)

# Модель и лимиты (можно переопределить переменными окружения)
MODEL = os.environ.get("COMPOSER_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = int(os.environ.get("COMPOSER_MAX_TOKENS", "4096"))
MAX_STEPS = int(os.environ.get("COMPOSER_MAX_STEPS", "20"))

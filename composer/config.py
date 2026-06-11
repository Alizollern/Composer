"""Единая конфигурация Composer AI (пути, модель). Меняется через env."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # ~/composer-ai
AGENTS_DIR = ROOT / "agents"                     # определения агентов (папки = данные)
KNOWLEDGE_DIR = ROOT / "knowledge"               # общий склад знаний (домены = подпапки)
WORKSPACE = ROOT / "workspace"                   # общая доска для обмена между агентами
PIPELINE_FILE = ROOT / "pipeline.txt"            # порядок агентов в пайплайне
MEMORY_FILE = ROOT / "memory.json"

RUNS_DIR = WORKSPACE / ".runs"                   # история прогонов (персист для API)
KV_FILE = WORKSPACE / ".kv.json"                 # key-value стор интеграции
COMPANIES_DIR = WORKSPACE / "companies"          # папка на каждую компанию (мульти-тенант)

WORKSPACE.mkdir(exist_ok=True)
AGENTS_DIR.mkdir(exist_ok=True)
KNOWLEDGE_DIR.mkdir(exist_ok=True)
RUNS_DIR.mkdir(exist_ok=True)
COMPANIES_DIR.mkdir(exist_ok=True)

# Провайдер LLM: claude (по умолчанию) или gemini (бесплатный тариф для тестов).
PROVIDER = os.environ.get("COMPOSER_PROVIDER", "claude")
# Модель Gemini (бесплатный тариф Google AI Studio). Ключ — в GEMINI_API_KEY.
# На бесплатном тарифе живут Flash/Flash-Lite. gemini-2.0-flash отключён (01.06.2026).
# Текущие бесплатные: gemini-3-flash-preview (дефолт), gemini-3.1-flash-lite (15 RPM).
GEMINI_MODEL = os.environ.get("COMPOSER_GEMINI_MODEL", "gemini-3-flash-preview")

# Модель и лимиты (можно переопределить переменными окружения)
MODEL = os.environ.get("COMPOSER_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = int(os.environ.get("COMPOSER_MAX_TOKENS", "4096"))
MAX_STEPS = int(os.environ.get("COMPOSER_MAX_STEPS", "10"))
# Ретраи при 429/перегрузке (rate limit) с экспоненциальной паузой.
MAX_RETRIES = int(os.environ.get("COMPOSER_MAX_RETRIES", "6"))

# Параллелизм: сколько инструментов/суб-агентов выполнять одновременно.
MAX_PARALLEL = int(os.environ.get("COMPOSER_MAX_PARALLEL", "3"))
# Глубина вложенности делегирования (оркестратор -> суб-агент -> суб-суб-агент).
MAX_DELEGATION_DEPTH = int(os.environ.get("COMPOSER_MAX_DEPTH", "2"))
# Имя агента-оркестратора по умолчанию (динамический режим).
ORCHESTRATOR_AGENT = os.environ.get("COMPOSER_ORCHESTRATOR", "orchestrator")

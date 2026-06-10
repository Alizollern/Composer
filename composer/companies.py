"""
Компании (мульти-тенант).

Каждая компания — это папка workspace/companies/<slug>/ со своим профилем
(profile.md) и всеми документами, которые двойник для неё подготовил
(стандарты, анализ конкурентов, планы и т.д.). Прогоны агентов скоупятся
на папку компании: туда они читают/пишут, оттуда берут контекст профиля.

Это убирает «одну зашитую компанию» и «всё в один standards.md»: теперь у
каждого клиента своя папка с накапливающимися документами.
"""

import re
import json
import time
from pathlib import Path

from composer.config import COMPANIES_DIR

_META = ".meta.json"
_PROFILE = "profile.md"
# системные имена, которые не показываем как «документы»
_HIDDEN = {_META}


def slugify(name):
    s = (name or "").strip().lower()
    s = re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "company"


def company_dir(slug):
    d = (COMPANIES_DIR / slug).resolve()
    if not str(d).startswith(str(COMPANIES_DIR.resolve())):
        raise ValueError("Недопустимое имя компании")
    return d


def _meta(slug):
    p = company_dir(slug) / _META
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"slug": slug, "name": slug, "created": None}


def list_companies():
    out = []
    if not COMPANIES_DIR.is_dir():
        return out
    for d in sorted(COMPANIES_DIR.iterdir()):
        if not d.is_dir():
            continue
        m = _meta(d.name)
        files = [f for f in d.rglob("*")
                 if f.is_file() and f.name not in _HIDDEN and not f.name.startswith(".")]
        out.append({
            "slug": d.name,
            "name": m.get("name", d.name),
            "created": m.get("created"),
            "docs": len([f for f in files if f.name != _PROFILE]),
            "has_profile": (d / _PROFILE).exists(),
        })
    out.sort(key=lambda c: c.get("created") or 0, reverse=True)
    return out


def create_company(name, profile=""):
    slug = slugify(name)
    d = company_dir(slug)
    # если slug занят — добавляем суффикс
    if d.exists():
        n = 2
        while company_dir(f"{slug}-{n}").exists():
            n += 1
        slug = f"{slug}-{n}"
        d = company_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    meta = {"slug": slug, "name": name.strip() or slug, "created": time.time()}
    (d / _META).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    body = profile.strip() or f"# {meta['name']}\n\n_Профиль компании пока не заполнен._\n"
    (d / _PROFILE).write_text(body, encoding="utf-8")
    return get_company(slug)


def get_company(slug):
    d = company_dir(slug)
    if not d.is_dir():
        return None
    m = _meta(slug)
    profile_path = d / _PROFILE
    profile = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
    files = []
    for f in sorted(d.rglob("*")):
        if f.is_file() and f.name not in _HIDDEN and not f.name.startswith("."):
            files.append({
                "name": str(f.relative_to(d)),
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
    return {
        "slug": slug,
        "name": m.get("name", slug),
        "created": m.get("created"),
        "profile": profile,
        "files": files,
    }


def read_profile(slug):
    p = company_dir(slug) / _PROFILE
    return p.read_text(encoding="utf-8") if p.exists() else ""


def update_profile(slug, content):
    d = company_dir(slug)
    if not d.is_dir():
        return None
    (d / _PROFILE).write_text(content or "", encoding="utf-8")
    return get_company(slug)


def read_file(slug, name):
    p = (company_dir(slug) / name).resolve()
    base = company_dir(slug)
    if not str(p).startswith(str(base)) or not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="ignore")


def profile_context(slug):
    """Готовый блок контекста компании для подмешивания в задачу агента."""
    if not slug:
        return ""
    m = _meta(slug)
    prof = read_profile(slug).strip()
    if not prof:
        return ""
    return (f"[Контекст компании «{m.get('name', slug)}»]\n{prof}\n\n"
            f"Адаптируй результат именно под эту компанию.\n\n")

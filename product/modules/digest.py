"""M7 — «Сводка и тревоги собственнику»: продукт сам докладывает, где болит.

Идея: владельцу не нужно ходить по экранам и сравнивать филиалы вручную —
система раз в период собирает короткий брифинг «как дела в сети» и поднимает
тревоги по проседающим точкам.

Два слоя, намеренно разделены:
  1) ФАКТЫ считаются ДЕТЕРМИНИРОВАННО из данных (compute_alerts, ранжирование
     точек, пульс). Никакой модели — значит, в цифрах не может быть галлюцинаций.
  2) ТЕКСТ брифинга пишет модель (brain.complete) ПОВЕРХ уже посчитанных фактов,
     только «озвучивает» их по-человечески. Если модели нет/упала — детерминированный
     запасной текст из тех же фактов. Поэтому фича работает и офлайн.

Тревоги (alerts) — правила над сводкой командного центра:
  * низкий средний рейтинг точки;
  * высокая доля жалоб;
  * негатив преобладает над позитивом;
  * повторяющаяся боль по сети (одна и та же проблема в нескольких отзывах).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from product import brain
from product.agent_log import log_event
from product.modules import reviews as reviews_mod

# Пороги тревог. Держим на виду, чтобы владелец мог их при желании поменять.
MIN_REVIEWS_FOR_ALERT = 3      # на 1-2 отзывах выводы не делаем — мало данных
LOW_RATING = 3.5               # средний рейтинг ниже — тревога
HIGH_COMPLAINT_SHARE = 0.4     # доля жалоб от всех отзывов точки
MIN_COMPLAINTS = 2             # и не меньше стольких жалоб в абсолюте
MIN_NEGATIVE_DOMINATES = 3     # негатива столько и он не меньше позитива
REPEAT_PROBLEM_MIN = 3         # одна боль повторилась в стольких отзывах → по сети

SEV_HIGH = "high"
SEV_MEDIUM = "medium"


def _point_score(p: dict) -> float:
    """Чем выше — тем хуже точка. Для ранжирования «кто проседает»."""
    n = max(p.get("reviews_count", 0), 1)
    complaint_share = p.get("complaints_count", 0) / n
    negative_share = p.get("negative_count", 0) / n
    rating_gap = max(0.0, 5.0 - (p.get("avg_rating", 0.0) or 0.0))
    return complaint_share * 2 + negative_share + rating_gap * 0.5


def compute_alerts(cc: dict) -> List[dict]:
    """Детерминированные тревоги из данных командного центра.

    Возвращает список {severity, point_id, point_name, kind, message, metric}.
    Никакой модели — только арифметика над уже посчитанными цифрами.
    """
    alerts: List[dict] = []
    for p in cc.get("points", []):
        n = p.get("reviews_count", 0)
        if n < MIN_REVIEWS_FOR_ALERT:
            continue
        name = p.get("name", "Точка")
        avg = p.get("avg_rating", 0.0) or 0.0
        complaints = p.get("complaints_count", 0)
        negative = p.get("negative_count", 0)
        positive = p.get("positive_count", 0)
        share = complaints / n if n else 0.0

        if avg and avg < LOW_RATING:
            alerts.append({
                "severity": SEV_HIGH, "point_id": p["id"], "point_name": name,
                "kind": "low_rating",
                "message": f"«{name}»: низкий средний рейтинг {avg} из 5 ({n} отзывов).",
                "metric": avg,
            })
        if complaints >= MIN_COMPLAINTS and share >= HIGH_COMPLAINT_SHARE:
            alerts.append({
                "severity": SEV_HIGH, "point_id": p["id"], "point_name": name,
                "kind": "many_complaints",
                "message": (f"«{name}»: жалуется каждый {round(1/share) if share else 0}-й — "
                            f"{complaints} жалоб из {n} отзывов."),
                "metric": round(share, 2),
            })
        if negative >= MIN_NEGATIVE_DOMINATES and negative >= positive:
            alerts.append({
                "severity": SEV_MEDIUM, "point_id": p["id"], "point_name": name,
                "kind": "negative_dominates",
                "message": (f"«{name}»: негатива больше, чем позитива "
                            f"({negative} против {positive})."),
                "metric": negative,
            })

    # Повторяющаяся боль по всей сети (problems уже отсортированы по count).
    for prob in cc.get("problems", [])[:3]:
        if prob.get("count", 0) >= REPEAT_PROBLEM_MIN:
            alerts.append({
                "severity": SEV_MEDIUM, "point_id": None, "point_name": "Вся сеть",
                "kind": "repeat_problem",
                "message": (f"Повторяется по сети: «{prob.get('title', 'проблема')}» — "
                            f"{prob['count']} жалоб."),
                "metric": prob["count"],
            })

    order = {SEV_HIGH: 0, SEV_MEDIUM: 1}
    alerts.sort(key=lambda a: (order.get(a["severity"], 9), -float(a.get("metric") or 0)))
    return alerts


_SUMMARY_SYSTEM = (
    "Ты — операционный директор сети. Тебе дают УЖЕ ПОСЧИТАННЫЕ факты по сети "
    "(пульс, тревоги, проблемные точки). Напиши собственнику короткий деловой "
    "брифинг на русском: 3-5 предложений. Сначала общая картина, затем где болит "
    "и что сделать в первую очередь. НЕ придумывай цифр, которых нет в фактах. "
    "Без приветствий, маркдауна и воды — только суть."
)


def _facts_text(pulse: dict, alerts: List[dict], ranked: List[dict]) -> str:
    lines = [
        f"Всего отзывов: {pulse.get('total', 0)}, средний рейтинг: {pulse.get('avg_rating', 0)}, "
        f"негативных: {pulse.get('negative', 0)}, жалоб: {pulse.get('complaints', 0)}.",
    ]
    if ranked:
        worst = ranked[0]
        lines.append(f"Самая проблемная точка: «{worst['name']}» "
                     f"(рейтинг {worst.get('avg_rating', 0)}, жалоб {worst.get('complaints_count', 0)}).")
        if len(ranked) > 1:
            best = ranked[-1]
            lines.append(f"Лучшая точка: «{best['name']}» (рейтинг {best.get('avg_rating', 0)}).")
    if alerts:
        lines.append("Тревоги:")
        for a in alerts[:6]:
            lines.append(f"- {a['message']}")
    else:
        lines.append("Острых тревог нет.")
    return "\n".join(lines)


def _fallback_summary(pulse: dict, alerts: List[dict], ranked: List[dict]) -> str:
    """Детерминированный брифинг без модели — из тех же фактов."""
    if pulse.get("total", 0) == 0:
        return ("Пока нет данных по отзывам. Подключите точки в «Командном центре» "
                "и нажмите «Обновить отзывы», чтобы собрать первую сводку.")
    parts = [
        f"За период собрано {pulse['total']} отзывов, средний рейтинг по сети — "
        f"{pulse.get('avg_rating', 0)} из 5."
    ]
    high = [a for a in alerts if a["severity"] == SEV_HIGH]
    if high:
        parts.append(f"Срочно внимание: {high[0]['message']}")
    elif alerts:
        parts.append(alerts[0]["message"])
    else:
        parts.append("Острых проблем не видно — сеть работает ровно.")
    if ranked and len(ranked) > 1:
        parts.append(f"Слабее всех — «{ranked[0]['name']}», лучше всех — «{ranked[-1]['name']}».")
    return " ".join(parts)


def build_digest(db: Session, company_id: str, *, llm=None) -> dict:
    """Собрать сводку собственнику: пульс сети, тревоги, ранжирование точек,
    короткий человеческий брифинг (модель поверх детерминированных фактов)."""
    cc = reviews_mod.command_center(db, company_id)  # все точки
    pulse = cc.get("pulse", {})
    points = cc.get("points", [])
    alerts = compute_alerts(cc)
    ranked = sorted(points, key=_point_score, reverse=True)  # worst → best

    facts = _facts_text(pulse, alerts, ranked)
    summary = ""
    if pulse.get("total", 0) > 0:
        try:
            summary = brain.complete(_SUMMARY_SYSTEM, facts, llm=llm,
                                     operation="digest_summary", company=company_id).strip()
        except Exception:
            summary = ""
    if not summary:
        summary = _fallback_summary(pulse, alerts, ranked)

    log_event("digest.build", company=company_id,
              alerts=len(alerts), points=len(points), total=pulse.get("total", 0))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pulse": pulse,
        "alerts": alerts,
        "points": ranked,
        "top_problems": cc.get("problems", [])[:5],
        "summary": summary,
        "has_data": pulse.get("total", 0) > 0,
    }

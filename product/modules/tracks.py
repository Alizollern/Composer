"""
M3 — Учебные треки и прогресс онбординга.

Поверх генерации тестов (onboarding.py) этот модуль даёт собственнику/управляющему
инструмент адаптации сотрудников:

  * Трек — упорядоченный набор шагов, каждый шаг = стандарт (+ опц. проверочный
    тест с порогом сдачи). Собирается из уже загруженных документов компании.
  * Зачисление (Enrollment) — сотрудник назначен на трек; по каждому шагу ведётся
    прогресс (StepProgress): попытки, балл, статус. Шаг с тестом считается
    пройденным только при score ≥ pass_score.
  * Когда все шаги пройдены — трек считается завершённым (видно управляющему).

Принципы прежние: всё скоупится по company_id; сотрудник действует только над
своим зачислением; оценка теста — серверная (onboarding.grade), клиенту нельзя
доверять подсчёт балла.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from product.db import models as m
from product.modules import onboarding
from product.modules.knowledge import get_document


# --------------------------- Треки и шаги (управляющий) ---------------------------

def create_track(db: Session, company_id: str, *,
                 title: str, description: str = "",
                 created_by: Optional[str] = None) -> m.Track:
    track = m.Track(company_id=company_id, title=title,
                    description=description, created_by=created_by)
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


def get_track(db: Session, company_id: str, track_id: str) -> m.Track:
    track = db.get(m.Track, track_id)
    if track is None or track.company_id != company_id:
        raise KeyError("Трек не найден")
    return track


def list_tracks(db: Session, company_id: str, *,
                status: Optional[str] = None) -> List[m.Track]:
    stmt = select(m.Track).where(m.Track.company_id == company_id)
    if status:
        stmt = stmt.where(m.Track.status == status)
    stmt = stmt.order_by(m.Track.updated_at.desc())
    return list(db.execute(stmt).scalars().all())


def set_track_status(db: Session, company_id: str, track_id: str, status: str) -> m.Track:
    if status not in (m.TRACK_DRAFT, m.TRACK_PUBLISHED, m.TRACK_ARCHIVED):
        raise ValueError(f"Неизвестный статус трека: {status!r}")
    track = get_track(db, company_id, track_id)
    track.status = status
    db.commit()
    db.refresh(track)
    return track


def add_step(db: Session, company_id: str, track_id: str, *,
             document_id: str, title: str = "", require_quiz: bool = True,
             pass_score: float = 0.8, num_questions: int = 5) -> m.TrackStep:
    """Добавить шаг (документ) в конец трека. Документ должен принадлежать компании."""
    track = get_track(db, company_id, track_id)
    get_document(db, company_id, document_id)  # KeyError, если чужой/нет

    last = db.execute(
        select(func.max(m.TrackStep.ordinal))
        .where(m.TrackStep.track_id == track_id)
    ).scalar()
    ordinal = (last + 1) if last is not None else 0

    step = m.TrackStep(
        company_id=company_id, track_id=track.id, document_id=document_id,
        ordinal=ordinal, title=title, require_quiz=require_quiz,
        pass_score=pass_score, num_questions=num_questions)
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def list_steps(db: Session, company_id: str, track_id: str) -> List[m.TrackStep]:
    get_track(db, company_id, track_id)  # проверка владения
    stmt = (select(m.TrackStep)
            .where(m.TrackStep.track_id == track_id)
            .order_by(m.TrackStep.ordinal))
    return list(db.execute(stmt).scalars().all())


def delete_step(db: Session, company_id: str, track_id: str, step_id: str) -> None:
    """Убрать шаг из трека (правка курса до публикации). Остальные шаги
    переупорядочиваются, чтобы ordinal шёл без дыр."""
    get_track(db, company_id, track_id)  # проверка владения
    step = db.get(m.TrackStep, step_id)
    if step is None or step.track_id != track_id or step.company_id != company_id:
        raise KeyError("Шаг не найден")
    db.delete(step)
    db.flush()
    # Перенумеровать оставшиеся шаги (0,1,2,…), чтобы порядок был плотным.
    rest = list(db.execute(
        select(m.TrackStep).where(m.TrackStep.track_id == track_id)
        .order_by(m.TrackStep.ordinal)).scalars().all())
    for i, st in enumerate(rest):
        st.ordinal = i
    db.commit()


def autobuild_track(db: Session, company_id: str, *,
                    title: str = "Онбординг новичка",
                    description: str = "Курс из ваших опубликованных стандартов.",
                    require_quiz: bool = True, pass_score: float = 0.8,
                    num_questions: int = 5,
                    created_by: Optional[str] = None) -> m.Track:
    """Собрать черновик трека из ВСЕХ опубликованных стандартов компании.

    Каждый опубликованный документ становится шагом (в порядке загрузки). Трек
    создаётся как черновик (TRACK_DRAFT): руководитель может убрать лишние шаги
    и затем опубликовать. Если опубликованных документов нет — ValueError."""
    docs = list(db.execute(
        select(m.Document)
        .where(m.Document.company_id == company_id)
        .where(m.Document.status == m.DOC_PUBLISHED)
        .order_by(m.Document.created_at)).scalars().all())
    if not docs:
        raise ValueError("Нет опубликованных стандартов для сборки курса")

    track = create_track(db, company_id, title=title,
                         description=description, created_by=created_by)
    for doc in docs:
        add_step(db, company_id, track.id, document_id=doc.id,
                 title=doc.title, require_quiz=require_quiz,
                 pass_score=pass_score, num_questions=num_questions)
    db.refresh(track)
    return track


# --------------------------- Зачисление и прогресс ---------------------------

def _ensure_progress(db: Session, enrollment: m.Enrollment,
                     steps: List[m.TrackStep]) -> None:
    """Создать недостающие записи прогресса (на случай шагов, добавленных позже)."""
    existing = set(db.execute(
        select(m.StepProgress.step_id)
        .where(m.StepProgress.enrollment_id == enrollment.id)
    ).scalars().all())
    for step in steps:
        if step.id not in existing:
            db.add(m.StepProgress(
                company_id=enrollment.company_id,
                enrollment_id=enrollment.id, step_id=step.id))


def enroll(db: Session, company_id: str, track_id: str, user_id: str) -> m.Enrollment:
    """Зачислить пользователя на трек (идемпотентно). Создаёт записи прогресса."""
    get_track(db, company_id, track_id)
    user = db.get(m.User, user_id)
    if user is None or user.company_id != company_id:
        raise KeyError("Пользователь не найден")

    enrollment = db.execute(
        select(m.Enrollment)
        .where(m.Enrollment.track_id == track_id,
               m.Enrollment.user_id == user_id)
    ).scalars().first()
    if enrollment is None:
        enrollment = m.Enrollment(
            company_id=company_id, track_id=track_id, user_id=user_id)
        db.add(enrollment)
        db.flush()

    steps = list_steps(db, company_id, track_id)
    _ensure_progress(db, enrollment, steps)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def get_enrollment(db: Session, company_id: str, enrollment_id: str) -> m.Enrollment:
    e = db.get(m.Enrollment, enrollment_id)
    if e is None or e.company_id != company_id:
        raise KeyError("Зачисление не найдено")
    return e


def list_user_enrollments(db: Session, company_id: str,
                          user_id: str) -> List[m.Enrollment]:
    stmt = (select(m.Enrollment)
            .where(m.Enrollment.company_id == company_id,
                   m.Enrollment.user_id == user_id)
            .order_by(m.Enrollment.created_at.desc()))
    return list(db.execute(stmt).scalars().all())


def progress_map(db: Session, enrollment_id: str) -> dict:
    """step_id → StepProgress для зачисления (для сборки ответа фронту)."""
    rows = db.execute(
        select(m.StepProgress)
        .where(m.StepProgress.enrollment_id == enrollment_id)
    ).scalars().all()
    return {p.step_id: p for p in rows}


def _recompute_enrollment(db: Session, enrollment: m.Enrollment,
                          steps: List[m.TrackStep]) -> None:
    """Если все шаги трека пройдены — пометить зачисление завершённым."""
    pmap = progress_map(db, enrollment.id)
    all_passed = bool(steps) and all(
        pmap.get(s.id) is not None and pmap[s.id].status == m.STEP_PASSED
        for s in steps)
    if all_passed and enrollment.status != m.ENROLL_COMPLETED:
        enrollment.status = m.ENROLL_COMPLETED
        enrollment.completed_at = m._now()
    elif not all_passed and enrollment.status == m.ENROLL_COMPLETED:
        # Откат (например, добавили новый шаг) — снова активно.
        enrollment.status = m.ENROLL_ACTIVE
        enrollment.completed_at = None


def submit_step(db: Session, company_id: str, user_id: str, *,
                enrollment_id: str, step_id: str,
                quiz_token: Optional[str] = None,
                answers: Optional[List[int]] = None) -> dict:
    """Зафиксировать прохождение шага текущим сотрудником.

    Для шага с тестом (require_quiz) обязательны quiz_token+answers — сервер
    достаёт сохранённый тест по токену и грейдит ответы против СВОЕЙ копии
    (правильные ответы клиенту не отдаются), шаг пройден при score ≥ pass_score.
    Для шага без теста (ознакомление) — засчитывается сразу.

    Возвращает {step_status, score, enrollment_status, grade?}.
    """
    enrollment = get_enrollment(db, company_id, enrollment_id)
    if enrollment.user_id != user_id:
        raise PermissionError("Это чужое зачисление")

    step = db.get(m.TrackStep, step_id)
    if step is None or step.track_id != enrollment.track_id:
        raise KeyError("Шаг не найден в этом треке")

    progress = db.execute(
        select(m.StepProgress)
        .where(m.StepProgress.enrollment_id == enrollment_id,
               m.StepProgress.step_id == step_id)
    ).scalars().first()
    if progress is None:
        progress = m.StepProgress(
            company_id=company_id, enrollment_id=enrollment_id, step_id=step_id)
        db.add(progress)
        db.flush()

    grade_result = None
    if step.require_quiz:
        if not quiz_token:
            raise ValueError("Для шага с тестом нужны quiz_token и answers")
        try:
            quiz_inst = onboarding.load_quiz(db, company_id, quiz_token)
        except KeyError:
            raise ValueError("Тест не найден")
        # Тест должен быть сгенерирован по стандарту именно этого шага.
        if quiz_inst.document_id != step.document_id:
            raise ValueError("Тест не относится к этому шагу")
        grade_result = onboarding.grade(quiz_inst.questions, answers or [])
        score = grade_result["score"]
        passed = score >= step.pass_score
    else:
        score = 1.0
        passed = True

    progress.attempts += 1
    # Лучший результат не понижаем (повторная попытка хуже не сбрасывает зачёт).
    progress.score = max(progress.score, score)
    if passed and progress.status != m.STEP_PASSED:
        progress.status = m.STEP_PASSED
        progress.completed_at = m._now()

    steps = list_steps(db, company_id, enrollment.track_id)
    _recompute_enrollment(db, enrollment, steps)
    db.commit()
    db.refresh(progress)
    db.refresh(enrollment)

    return {
        "step_status": progress.status,
        "score": progress.score,
        "attempts": progress.attempts,
        "enrollment_status": enrollment.status,
        "grade": grade_result,
    }


def track_progress(db: Session, company_id: str, track_id: str) -> List[dict]:
    """Сводка по треку для управляющего: по каждому зачислению — доля пройденных шагов."""
    track = get_track(db, company_id, track_id)
    steps = list_steps(db, company_id, track_id)
    total = len(steps)
    step_ids = {s.id for s in steps}

    enrollments = db.execute(
        select(m.Enrollment).where(m.Enrollment.track_id == track_id)
    ).scalars().all()

    out: List[dict] = []
    for e in enrollments:
        pmap = progress_map(db, e.id)
        passed = sum(1 for sid in step_ids
                     if pmap.get(sid) is not None and pmap[sid].status == m.STEP_PASSED)
        out.append({
            "enrollment_id": e.id,
            "user_id": e.user_id,
            "status": e.status,
            "passed_steps": passed,
            "total_steps": total,
        })
    return out

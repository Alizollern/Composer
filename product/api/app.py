"""
HTTP-API продукта Evergreen (FastAPI).

Отдельное приложение продукта — не путать с composer/api (демо движка). Здесь
живут эндпоинты SaaS: регистрация/вход, база знаний (M1), чат-бот (M2), пробелы.

Сквозные правила:
  * Авторизация — через RBAC-зависимости (require_owner/manager/employee).
  * Изоляция тенанта — company_id всегда берётся из токена (principal), НИКОГДА
    из тела запроса. Поэтому обратиться к чужой компании технически невозможно.
  * Фабрика create_app() позволяет тестам поднять приложение и подменить БД
    (dependency override get_db) — без сети и без Postgres.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from product.api import schemas as s
from product.auth.deps import (
    Principal, get_db, get_current_principal,
    require_owner, require_manager, require_employee,
)
from product.auth.security import create_access_token
from product.modules import accounts, knowledge as kb, chat, onboarding, tracks, reviews, advisor
from product.modules.accounts import AccountError
from product.modules.onboarding import QuizError
from product.auth import ROLE_EMPLOYEE


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # На старте приводим схему БД в актуальное состояние.
    #   * Postgres (прод/докер) — через Alembic (alembic upgrade head): история
    #     изменений и воспроизводимые апгрейды.
    #   * SQLite (офлайн-разработка) — через create_all: быстро и без миграций.
    # Тесты поднимают собственный SQLite-движок и сюда не заходят (lifespan не
    # запускается без `with TestClient(...)`).
    from product.db.session import get_engine, init_db
    engine = get_engine()
    if engine.dialect.name == "sqlite":
        init_db(engine)
    else:
        from product.db.migrate import upgrade_to_head
        upgrade_to_head()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Evergreen API", version="0.1.0", lifespan=_lifespan)

    # ---------------------------- Auth ----------------------------
    @app.post("/api/auth/register-company", response_model=s.TokenOut)
    def register_company(body: s.RegisterCompanyIn, db: Session = Depends(get_db)):
        try:
            company, owner = accounts.register_company(
                db, company_name=body.company_name, slug=body.slug,
                owner_email=body.owner_email, owner_password=body.owner_password,
                owner_name=body.owner_name,
            )
        except AccountError as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e))
        token = create_access_token(
            user_id=owner.id, company_id=company.id, role=owner.role)
        return s.TokenOut(access_token=token, role=owner.role, company_id=company.id)

    @app.post("/api/auth/login", response_model=s.TokenOut)
    def login(body: s.LoginIn, db: Session = Depends(get_db)):
        try:
            user = accounts.authenticate(
                db, slug=body.slug, email=body.email, password=body.password)
        except AccountError as e:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
        token = create_access_token(
            user_id=user.id, company_id=user.company_id,
            role=user.role, point_id=user.point_id)
        return s.TokenOut(access_token=token, role=user.role, company_id=user.company_id)

    @app.get("/api/auth/me", response_model=s.MeOut)
    def me(principal: Principal = Depends(get_current_principal)):
        return s.MeOut(user_id=principal.user_id, company_id=principal.company_id,
                       role=principal.role, point_id=principal.point_id)

    @app.post("/api/users", response_model=s.UserOut, status_code=201)
    def create_user(body: s.CreateUserIn,
                    principal: Principal = Depends(require_owner),
                    db: Session = Depends(get_db)):
        try:
            user = accounts.create_user(
                db, principal.company_id, email=body.email, password=body.password,
                role=body.role, full_name=body.full_name, point_id=body.point_id)
        except AccountError as e:
            raise HTTPException(status.HTTP_409_CONFLICT, str(e))
        return s.UserOut(id=user.id, email=user.email, role=user.role,
                         full_name=user.full_name, point_id=user.point_id)

    @app.get("/api/users", response_model=list[s.UserOut])
    def list_users(principal: Principal = Depends(require_manager),
                   db: Session = Depends(get_db)):
        # Команда компании — для назначения обучения и обзора (управляющий/owner).
        users = accounts.list_users(db, principal.company_id)
        return [s.UserOut(id=u.id, email=u.email, role=u.role,
                          full_name=u.full_name, point_id=u.point_id)
                for u in users]

    # ------------------------ Documents (M1) ------------------------
    @app.post("/api/documents", response_model=s.DocumentOut, status_code=201)
    def ingest_document(body: s.IngestTextIn,
                        principal: Principal = Depends(require_manager),
                        db: Session = Depends(get_db)):
        doc = kb.ingest_text(
            db, principal.company_id, title=body.title, content=body.content,
            category=body.category, audience_roles=body.audience_roles,
            point_id=body.point_id, created_by=principal.user_id,
            publish=body.publish)
        return _doc_out(doc)

    @app.post("/api/documents/upload", response_model=s.DocumentOut, status_code=201)
    async def upload_document(file: UploadFile = File(...),
                              category: str = "",
                              principal: Principal = Depends(require_manager),
                              db: Session = Depends(get_db)):
        data = await file.read()
        try:
            doc = kb.ingest_file(
                db, principal.company_id, filename=file.filename, data=data,
                category=category, created_by=principal.user_id)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
        return _doc_out(doc)

    @app.get("/api/documents", response_model=list[s.DocumentOut])
    def list_documents(status_filter: Optional[str] = None,
                       principal: Principal = Depends(require_employee),
                       db: Session = Depends(get_db)):
        # Сотрудник видит только стандарты своей аудитории (M1.5); управляющий — все.
        enforce = principal.role == ROLE_EMPLOYEE
        docs = kb.list_documents(
            db, principal.company_id, status=status_filter,
            audience_role=principal.role, audience_point_id=principal.point_id,
            enforce_audience=enforce)
        return [_doc_out(d) for d in docs]

    @app.get("/api/documents/{document_id}", response_model=s.DocumentOut)
    def get_document(document_id: str,
                     principal: Principal = Depends(require_employee),
                     db: Session = Depends(get_db)):
        try:
            doc = kb.get_document(db, principal.company_id, document_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        # Сотрудник не должен видеть стандарт вне своей аудитории (M1.5).
        if principal.role == ROLE_EMPLOYEE and not kb.audience_ok(
                doc.audience_roles, doc.point_id,
                role=principal.role, point_id=principal.point_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        return _doc_out(doc)

    @app.get("/api/documents/{document_id}/content", response_model=s.DocumentContentOut)
    def get_document_content(document_id: str,
                             principal: Principal = Depends(require_employee),
                             db: Session = Depends(get_db)):
        # Текст стандарта для уроков/карточек обучения. Та же проверка аудитории,
        # что и для метаданных: сотрудник не читает чужие стандарты.
        try:
            doc = kb.get_document(db, principal.company_id, document_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        if principal.role == ROLE_EMPLOYEE and not kb.audience_ok(
                doc.audience_roles, doc.point_id,
                role=principal.role, point_id=principal.point_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        try:
            content = kb.get_content(db, principal.company_id, document_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "У документа нет содержимого")
        return s.DocumentContentOut(
            id=doc.id, title=doc.title, category=doc.category, content=content)

    @app.post("/api/documents/{document_id}/audience", response_model=s.DocumentOut)
    def set_audience(document_id: str, body: s.AudienceIn,
                     principal: Principal = Depends(require_manager),
                     db: Session = Depends(get_db)):
        try:
            doc = kb.set_audience(
                db, principal.company_id, document_id,
                audience_roles=body.audience_roles, point_id=body.point_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        return _doc_out(doc)

    @app.get("/api/documents/{document_id}/original")
    def download_original(document_id: str,
                          principal: Principal = Depends(require_employee),
                          db: Session = Depends(get_db)):
        try:
            filename, data = kb.get_original(db, principal.company_id, document_id)
        except KeyError as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return Response(content=data, media_type="application/octet-stream",
                        headers=headers)

    @app.post("/api/documents/{document_id}/versions", response_model=s.DocumentOut)
    def add_version(document_id: str, body: s.NewVersionIn,
                    principal: Principal = Depends(require_manager),
                    db: Session = Depends(get_db)):
        try:
            kb.add_version(db, principal.company_id, document_id,
                           content=body.content, created_by=principal.user_id)
            doc = kb.get_document(db, principal.company_id, document_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        return _doc_out(doc)

    @app.post("/api/documents/{document_id}/status", response_model=s.DocumentOut)
    def set_status(document_id: str, body: s.StatusIn,
                   principal: Principal = Depends(require_manager),
                   db: Session = Depends(get_db)):
        try:
            doc = kb.set_status(db, principal.company_id, document_id, body.status)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
        return _doc_out(doc)

    # -------------------------- Chat (M2) ---------------------------
    @app.post("/api/chat", response_model=s.ChatOut)
    def ask(body: s.ChatIn,
            principal: Principal = Depends(require_employee),
            db: Session = Depends(get_db)):
        # Сотруднику бот отвечает только по стандартам его аудитории (M1.5).
        enforce = principal.role == ROLE_EMPLOYEE
        result = chat.answer_question(
            db, principal.company_id, body.question, user_id=principal.user_id,
            enforce_audience=enforce, user_role=principal.role,
            user_point_id=principal.point_id)
        return s.ChatOut(
            answer=result["answer"], refused=result["refused"],
            sources=[s.SourceOut(**src) for src in result["sources"]],
            best_score=result["best_score"])

    # --------------------------- Gaps -------------------------------
    @app.get("/api/gaps", response_model=list[s.GapOut])
    def gaps(principal: Principal = Depends(require_manager),
             db: Session = Depends(get_db)):
        items = chat.list_gaps(db, principal.company_id)
        return [s.GapOut(id=g.id, question=g.question,
                         best_score=g.best_score, resolved=g.resolved) for g in items]

    # ----------------------- Onboarding (M3) ------------------------
    @app.post("/api/documents/{document_id}/quiz", response_model=s.QuizOut)
    def make_quiz(document_id: str, body: s.QuizGenIn,
                  principal: Principal = Depends(require_employee),
                  db: Session = Depends(get_db)):
        # Тест нужен и сотруднику (прохождение шага обучения), и управляющему
        # (предпросмотр). Сотрудник получает тест только по стандарту своей
        # аудитории — та же проверка, что и при чтении документа.
        if principal.role == ROLE_EMPLOYEE:
            try:
                doc = kb.get_document(db, principal.company_id, document_id)
            except KeyError:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
            if not kb.audience_ok(doc.audience_roles, doc.point_id,
                                  role=principal.role, point_id=principal.point_id):
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        try:
            questions = onboarding.generate_quiz_for_document(
                db, principal.company_id, document_id,
                num_questions=body.num_questions)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        except QuizError as e:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))
        # Полный тест (с ответами) сохраняем на сервере; клиенту — токен и вопросы
        # без правильных ответов. Сдача и оценка идут по токену против этой копии.
        inst = onboarding.store_quiz(
            db, principal.company_id, document_id, questions,
            user_id=principal.user_id)
        return s.QuizOut(
            document_id=document_id, quiz_token=inst.id,
            questions=[s.QuizQuestionOut(**q)
                       for q in onboarding.public_questions(questions)])

    @app.post("/api/quiz/grade", response_model=s.GradeOut)
    def grade_quiz(body: s.GradeIn,
                   principal: Principal = Depends(require_employee),
                   db: Session = Depends(get_db)):
        try:
            inst = onboarding.load_quiz(db, principal.company_id, body.quiz_token)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Тест не найден")
        return s.GradeOut(**onboarding.grade(inst.questions, body.answers))

    # ------------------- Tracks / Onboarding progress (M3) -------------------
    @app.post("/api/tracks", response_model=s.TrackOut, status_code=201)
    def create_track(body: s.TrackIn,
                     principal: Principal = Depends(require_manager),
                     db: Session = Depends(get_db)):
        track = tracks.create_track(
            db, principal.company_id, title=body.title,
            description=body.description, created_by=principal.user_id)
        return _track_out(track)

    @app.post("/api/tracks/auto", response_model=s.TrackDetailOut, status_code=201)
    def autobuild_track(body: s.TrackAutoBuildIn,
                        principal: Principal = Depends(require_manager),
                        db: Session = Depends(get_db)):
        # Собрать черновик курса из всех опубликованных стандартов в один клик.
        try:
            track = tracks.autobuild_track(
                db, principal.company_id, title=body.title,
                description=body.description, require_quiz=body.require_quiz,
                pass_score=body.pass_score, num_questions=body.num_questions,
                created_by=principal.user_id)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
        steps = tracks.list_steps(db, principal.company_id, track.id)
        return _track_detail_out(track, steps)

    @app.get("/api/tracks", response_model=list[s.TrackOut])
    def list_tracks(principal: Principal = Depends(require_employee),
                    db: Session = Depends(get_db)):
        # Сотрудник видит только опубликованные треки; управляющий — все.
        status_filter = m_track_published if principal.role == ROLE_EMPLOYEE else None
        items = tracks.list_tracks(db, principal.company_id, status=status_filter)
        return [_track_out(t) for t in items]

    @app.get("/api/tracks/{track_id}", response_model=s.TrackDetailOut)
    def get_track(track_id: str,
                  principal: Principal = Depends(require_employee),
                  db: Session = Depends(get_db)):
        try:
            track = tracks.get_track(db, principal.company_id, track_id)
            steps = tracks.list_steps(db, principal.company_id, track_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Трек не найден")
        return _track_detail_out(track, steps)

    @app.post("/api/tracks/{track_id}/steps", response_model=s.TrackStepOut, status_code=201)
    def add_track_step(track_id: str, body: s.TrackStepIn,
                       principal: Principal = Depends(require_manager),
                       db: Session = Depends(get_db)):
        try:
            step = tracks.add_step(
                db, principal.company_id, track_id, document_id=body.document_id,
                title=body.title, require_quiz=body.require_quiz,
                pass_score=body.pass_score, num_questions=body.num_questions)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Трек или документ не найден")
        return _step_out(step)

    @app.delete("/api/tracks/{track_id}/steps/{step_id}", status_code=204)
    def delete_track_step(track_id: str, step_id: str,
                          principal: Principal = Depends(require_manager),
                          db: Session = Depends(get_db)):
        # Убрать шаг из курса (правка черновика до публикации).
        try:
            tracks.delete_step(db, principal.company_id, track_id, step_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Трек или шаг не найден")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/tracks/{track_id}/status", response_model=s.TrackOut)
    def set_track_status(track_id: str, body: s.TrackStatusIn,
                         principal: Principal = Depends(require_manager),
                         db: Session = Depends(get_db)):
        try:
            track = tracks.set_track_status(
                db, principal.company_id, track_id, body.status)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Трек не найден")
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
        return _track_out(track)

    @app.post("/api/tracks/{track_id}/enroll", response_model=s.EnrollmentOut, status_code=201)
    def enroll_user(track_id: str, body: s.EnrollIn,
                    principal: Principal = Depends(require_manager),
                    db: Session = Depends(get_db)):
        try:
            e = tracks.enroll(db, principal.company_id, track_id, body.user_id)
        except KeyError as ex:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(ex))
        return s.EnrollmentOut(id=e.id, track_id=e.track_id,
                               user_id=e.user_id, status=e.status)

    @app.post("/api/tracks/{track_id}/enroll-me", response_model=s.EnrollmentOut, status_code=201)
    def enroll_self(track_id: str,
                    principal: Principal = Depends(require_employee),
                    db: Session = Depends(get_db)):
        try:
            e = tracks.enroll(db, principal.company_id, track_id, principal.user_id)
        except KeyError as ex:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(ex))
        return s.EnrollmentOut(id=e.id, track_id=e.track_id,
                               user_id=e.user_id, status=e.status)

    @app.get("/api/my/enrollments", response_model=list[s.MyEnrollmentOut])
    def my_enrollments(principal: Principal = Depends(require_employee),
                       db: Session = Depends(get_db)):
        out = []
        for e in tracks.list_user_enrollments(db, principal.company_id, principal.user_id):
            track = tracks.get_track(db, principal.company_id, e.track_id)
            steps = tracks.list_steps(db, principal.company_id, e.track_id)
            pmap = tracks.progress_map(db, e.id)
            step_outs = []
            for st in steps:
                prog = pmap.get(st.id)
                step_outs.append(s.EnrollmentStepOut(
                    **_step_out(st).model_dump(),
                    progress=s.StepProgressOut(
                        step_id=st.id,
                        status=prog.status if prog else "pending",
                        score=prog.score if prog else 0.0,
                        attempts=prog.attempts if prog else 0)))
            out.append(s.MyEnrollmentOut(
                enrollment_id=e.id, status=e.status,
                track=_track_out(track), steps=step_outs))
        return out

    @app.post("/api/enrollments/{enrollment_id}/steps/{step_id}/submit",
              response_model=s.SubmitStepOut)
    def submit_step(enrollment_id: str, step_id: str, body: s.SubmitStepIn,
                    principal: Principal = Depends(require_employee),
                    db: Session = Depends(get_db)):
        try:
            result = tracks.submit_step(
                db, principal.company_id, principal.user_id,
                enrollment_id=enrollment_id, step_id=step_id,
                quiz_token=body.quiz_token, answers=body.answers)
        except PermissionError:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Это чужое зачисление")
        except KeyError as ex:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(ex))
        except ValueError as ex:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(ex))
        grade = s.GradeOut(**result["grade"]) if result.get("grade") else None
        return s.SubmitStepOut(
            step_status=result["step_status"], score=result["score"],
            attempts=result["attempts"],
            enrollment_status=result["enrollment_status"], grade=grade)

    @app.get("/api/tracks/{track_id}/progress", response_model=list[s.TrackProgressRowOut])
    def track_progress(track_id: str,
                       principal: Principal = Depends(require_manager),
                       db: Session = Depends(get_db)):
        try:
            rows = tracks.track_progress(db, principal.company_id, track_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Трек не найден")
        return [s.TrackProgressRowOut(**r) for r in rows]

    # ------------------- Журнал «мыслей» ассистента -------------------
    @app.get("/api/agent-log")
    def agent_log(limit: int = 200,
                  principal: Principal = Depends(require_owner)):
        # Только владелец видит журнал ИИ (контроль). Записи скоупим по компании:
        # показываем общие события и события своей компании, чужие — отсекаем.
        from product.agent_log import read_recent
        rows = read_recent(limit=limit)
        cid = principal.company_id
        return [r for r in rows if r.get("company") in (None, cid)]

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # ------------- M4: Командный центр (отзывы → инсайты) -------------
    # «Цифровой опер-дир»: владелец подключает точку (ссылка 2GIS), система тянет
    # отзывы, AI сопоставляет жалобы со стандартами и выдаёт сводку собственнику.
    @app.post("/api/points", response_model=s.PointOut, status_code=201)
    def connect_point(body: s.ConnectPointIn,
                      principal: Principal = Depends(require_manager),
                      db: Session = Depends(get_db)):
        try:
            point = reviews.connect_point(
                db, principal.company_id, name=body.name, url=body.url,
                source=body.source)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
        return s.PointOut(id=point.id, name=point.name, source=point.source,
                          external_url=point.external_url)

    @app.post("/api/points/{point_id}/sync", response_model=s.SyncReviewsOut)
    def sync_point_reviews(point_id: str,
                           principal: Principal = Depends(require_manager),
                           db: Session = Depends(get_db)):
        try:
            res = reviews.sync_and_analyze(db, principal.company_id, point_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Точка не найдена")
        return s.SyncReviewsOut(**res)

    @app.get("/api/command-center", response_model=s.CommandCenterOut)
    def command_center(point_id: Optional[str] = None,
                       principal: Principal = Depends(require_manager),
                       db: Session = Depends(get_db)):
        return reviews.command_center(db, principal.company_id, point_id=point_id)

    @app.post("/api/advisor", response_model=s.AdvisorOut)
    def advisor_ask(body: s.AdvisorIn,
                    principal: Principal = Depends(require_manager),
                    db: Session = Depends(get_db)):
        """Цифровой опер-дир: многошаговый агент отвечает по данным компании."""
        try:
            res = advisor.ask(db, principal.company_id, body.question)
        except Exception as e:  # агент не должен ронять API внутренней ошибкой
            raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                                f"Опер-дир временно недоступен: {e}")
        return s.AdvisorOut(**res)

    @app.post("/api/advisor/stream")
    def advisor_stream(body: s.AdvisorIn,
                       principal: Principal = Depends(require_manager),
                       db: Session = Depends(get_db)):
        """Тот же опер-дир, но СО СТРИМОМ «мыслей»: фронт видит вживую, как агент
        зовёт инструменты (отзывы, стандарты, точки) и приходит к ответу.

        Server-Sent Events. Агент крутится в фоновом потоке и шлёт события в
        очередь; генератор отдаёт их клиенту. db-сессию трогает только worker —
        запросный поток лишь читает очередь (без гонок за сессию)."""
        import json as _json
        import queue as _queue
        import threading as _threading
        from fastapi.responses import StreamingResponse

        q: "_queue.Queue" = _queue.Queue()

        def on_event(ev):
            q.put(ev)

        def worker():
            try:
                res = advisor.ask(db, principal.company_id, body.question,
                                  on_event=on_event)
                q.put({"type": "final", "answer": res["answer"]})
            except Exception as e:
                q.put({"type": "error", "message": str(e)})
            finally:
                q.put(None)  # сигнал конца

        _threading.Thread(target=worker, daemon=True).start()

        def gen():
            while True:
                ev = q.get()
                if ev is None:
                    break
                yield f"data: {_json.dumps(ev, ensure_ascii=False)}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    # ---------------------- Фронтенд (SPA) ----------------------
    # Docker-образ кладёт собранный фронт в frontend/dist. Отдаём его прямо из
    # бэкенда, чтобы всё приложение жило на одном порту (http://localhost:8000).
    # /api/* регистрируются ВЫШE и имеют приоритет; ниже — статика и SPA-фолбэк
    # (любой клиентский маршрут вроде /app/chat при перезагрузке отдаёт index.html).
    from pathlib import Path
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if _dist.is_dir():
        assets = _dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @app.get("/")
        def _spa_index():
            return FileResponse(str(_dist / "index.html"))

        @app.get("/{full_path:path}")
        def _spa_fallback(full_path: str):
            # На несуществующий /api/* отвечаем честным 404 (а не HTML-страницей),
            # чтобы клиент видел ошибку API, а не «пустую» 200.
            if full_path.startswith("api/"):
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
            candidate = _dist / full_path
            if candidate.is_file():
                return FileResponse(str(candidate))
            return FileResponse(str(_dist / "index.html"))

    return app


def _doc_out(doc):
    return s.DocumentOut(
        id=doc.id, title=doc.title, category=doc.category,
        status=doc.status, current_version_id=doc.current_version_id,
        audience_roles=doc.audience_roles or [], point_id=doc.point_id)


# Статус «опубликован» для треков — берём из моделей (один источник правды).
from product.db.models import TRACK_PUBLISHED as m_track_published  # noqa: E402


def _track_out(track):
    return s.TrackOut(id=track.id, title=track.title,
                      description=track.description, status=track.status)


def _step_out(step):
    return s.TrackStepOut(
        id=step.id, document_id=step.document_id, ordinal=step.ordinal,
        title=step.title, require_quiz=step.require_quiz,
        pass_score=step.pass_score, num_questions=step.num_questions)


def _track_detail_out(track, steps):
    return s.TrackDetailOut(
        id=track.id, title=track.title, description=track.description,
        status=track.status, steps=[_step_out(st) for st in steps])


# ASGI-приложение по умолчанию (прод/докер): uvicorn product.api.app:app
app = create_app()

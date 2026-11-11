import math
from datetime import timedelta
from uuid import uuid4

from flask import current_app, g
from sqlalchemy import Integer, case, cast, func, literal, select

from backend import validation as v
from backend.academic_models import LoteCobranca, NotificacaoAcademica, Reuniao
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import Etapa, Matricula
from backend.errors import APIError
from backend.models import Aluno, Usuario
from backend.services import academic_mail, classes, monitoring_sources

M01 = "Alertas enviados com sucesso aos estudantes selecionados!"
M02 = "Nenhum estudante cadastrado ou localizado na turma selecionada."
M03 = "Nenhum estudante com inatividade superior a 30 dias localizado nesta turma."
M04 = "Selecione ao menos um estudante para efetuar o disparo do e-mail de alerta."
M05 = "Não foi possível enviar uma ou mais notificações por e-mail. Tente novamente mais tarde."
M06 = "Você não possui permissão para acessar o monitoramento ou enviar alertas desta turma."
TEMPLATE = (
    "Identificamos mais de 30 dias sem registro de reunião de orientação ou entrega "
    "no SIGG-TCC. Entre em contato com seu orientador e regularize o acompanhamento "
    "do trabalho junto ao professor da disciplina. Caso já tenha realizado atividades, "
    "confira se os registros foram atualizados no sistema."
)


def get_class(identifier, lock=False):
    try:
        item = classes.get_class(identifier, lock)
    except APIError as error:
        if error.status in {403, 404}:
            raise APIError(403, "UC_13_M06", M06) from None
        raise
    if not item.ativa_turma:
        raise APIError(409, "TURMA_INATIVA", "Selecione uma turma ativa para monitorar.")
    return item


def local_day(timestamp):
    if db.engine.dialect.name == "postgresql":
        return func.date(func.timezone("America/Manaus", func.timezone("UTC", timestamp)))
    return func.date(timestamp, "-4 hours")


def matrix(class_id):
    stage_ids = (
        select(Etapa.id_etapa_trabalho)
        .join(Matricula, Etapa.id_matricula_turma == Matricula.id_matricula_turma)
        .where(Matricula.id_turma == class_id, Matricula.situacao_matricula_turma == "ativa")
    )
    meetings = (
        select(
            Reuniao.id_etapa_trabalho.label("stage"),
            func.count(Reuniao.id_reuniao_orientacao).label("meeting_count"),
            func.max(Reuniao.data_encontro_reuniao_orientacao).label("last_meeting"),
        )
        .where(Reuniao.id_etapa_trabalho.in_(stage_ids))
        .group_by(Reuniao.id_etapa_trabalho)
        .subquery()
    )
    deliveries = monitoring_sources.deliveries(stage_ids)
    last_meeting = meetings.c.last_meeting
    last_delivery = local_day(deliveries.c.last_delivery)
    latest = case(
        (last_meeting.is_(None), last_delivery),
        (last_delivery.is_(None), last_meeting),
        (last_delivery > last_meeting, last_delivery),
        else_=last_meeting,
    )
    baseline = func.coalesce(latest, local_day(Matricula.data_matricula_matricula_turma))
    today = utcnow().astimezone(current_app.config["ACADEMIC_TIMEZONE"]).date()
    if db.engine.dialect.name == "postgresql":
        days = literal(today) - baseline
    else:
        days = cast(func.julianday(today.isoformat()) - func.julianday(baseline), Integer)
    return (
        select(
            Matricula.id_matricula_turma.label("id_matricula"),
            Aluno.id_aluno,
            Usuario.nome_usuario.label("nome"),
            Usuario.email_usuario.label("email"),
            Aluno.matricula_aluno.label("matricula"),
            Etapa.id_etapa_trabalho.label("id_etapa"),
            func.coalesce(meetings.c.meeting_count, 0).label("total_atas"),
            last_meeting.label("ultima_reuniao"),
            last_delivery.label("ultima_entrega"),
            baseline.label("ultima_atividade"),
            days.label("dias_inatividade"),
        )
        .select_from(Matricula)
        .join(Aluno, Matricula.id_aluno == Aluno.id_aluno)
        .join(Usuario, Aluno.id_aluno == Usuario.id_usuario)
        .outerjoin(Etapa, Etapa.id_matricula_turma == Matricula.id_matricula_turma)
        .outerjoin(meetings, meetings.c.stage == Etapa.id_etapa_trabalho)
        .outerjoin(deliveries, deliveries.c.stage == Etapa.id_etapa_trabalho)
        .where(
            Matricula.id_turma == class_id,
            Matricula.situacao_matricula_turma == "ativa",
            Usuario.ativo_usuario.is_(True),
        )
        .subquery()
    )


def row_json(row):
    def day(value):
        return value.isoformat() if hasattr(value, "isoformat") else value

    return {
        "id_matricula": row["id_matricula"],
        "nome": row["nome"],
        "matricula": row["matricula"],
        "id_etapa": row["id_etapa"],
        "total_atas": row["total_atas"],
        "ultima_reuniao": day(row["ultima_reuniao"]),
        "ultima_entrega": day(row["ultima_entrega"]),
        "ultima_atividade": day(row["ultima_atividade"]),
        "dias_inatividade": max(0, row["dias_inatividade"]),
        "inativo": row["dias_inatividade"] > 30,
    }


def overview(class_id, only_inactive=False):
    source = matrix(class_id)
    count, inactive = db.session.execute(
        select(
            func.count(),
            func.coalesce(func.sum(case((source.c.dias_inatividade > 30, 1), else_=0)), 0),
        ).select_from(source)
    ).one()
    query = select(source)
    if only_inactive:
        query = query.where(source.c.dias_inatividade > 30)
    page, size = v.pagination()
    rows = db.session.execute(
        query.order_by(source.c.nome, source.c.id_matricula).offset((page - 1) * size).limit(size)
    ).mappings()
    total = inactive if only_inactive else count
    result = {
        "data": [row_json(row) for row in rows],
        "meta": {
            "page": page,
            "per_page": size,
            "total": total,
            "pages": math.ceil(total / size),
            "total_turma": count,
            "total_inativos": inactive,
        },
        "mensagem_padrao": TEMPLATE,
    }
    if not count or not inactive:
        result.update(
            code="UC_13_M02" if not count else "UC_13_M03", message=M02 if not count else M03
        )
    return result


def ids(value, field):
    if not isinstance(value, list) or len(value) > 1000:
        raise APIError(422, "VALIDACAO", "Informe uma lista de até 1000 matrículas.")
    values = [v.integer(item, field) for item in value]
    if len(set(values)) != len(values):
        raise APIError(422, "VALIDACAO", "Não repita matrículas na seleção.")
    return values


def prepare(turma, data):
    all_late = data.get("todos_inativos", False)
    if type(all_late) is not bool:
        raise APIError(422, "VALIDACAO", "todos_inativos deve ser true ou false.")
    selected = ids(data.get("ids_matriculas", []), "ids_matriculas")
    excluded = ids(data.get("ids_excluidas", []), "ids_excluidas")
    if (all_late and selected) or (not all_late and excluded):
        raise APIError(422, "VALIDACAO", "Seleção de matrículas inconsistente.")
    source = matrix(turma.id_turma)
    query = select(source.c.id_matricula).where(source.c.dias_inatividade > 30)
    if all_late:
        query = query.where(source.c.id_matricula.not_in(excluded))
    else:
        if not selected:
            raise APIError(422, "UC_13_M04", M04)
        query = query.where(source.c.id_matricula.in_(selected))
    values = list(db.session.scalars(query.order_by(source.c.id_matricula)))
    if not all_late and set(values) != set(selected):
        raise APIError(
            409,
            "SELECAO_DESATUALIZADA",
            "A seleção contém estudante indisponível ou sem atraso. Recarregue a turma.",
        )
    if not values:
        raise APIError(422, "UC_13_M04", M04)
    item = LoteCobranca(
        id_lote=str(uuid4()),
        id_turma=turma.id_turma,
        id_usuario=g.user.id_usuario,
        matriculas=values,
        mensagem=TEMPLATE,
        expira_em=utcnow() + timedelta(minutes=10),
    )
    db.session.add(item)
    db.session.commit()
    return {
        "id_lote": item.id_lote,
        "quantidade": len(values),
        "mensagem": item.mensagem,
        "expira_em": item.expira_em.isoformat(),
    }


def pending_is_valid(notification):
    membership = db.session.get(Matricula, notification.id_matricula_turma)
    if not membership or not membership.turma.ativa_turma:
        return False
    source = matrix(membership.id_turma)
    return (
        db.session.scalar(
            select(source.c.id_matricula).where(
                source.c.id_matricula == membership.id_matricula_turma,
                source.c.dias_inatividade > 30,
            )
        )
        is not None
    )


def confirm(turma, identifier):
    item = db.session.scalar(
        select(LoteCobranca)
        .where(
            LoteCobranca.id_lote == identifier,
            LoteCobranca.id_turma == turma.id_turma,
            LoteCobranca.id_usuario == g.user.id_usuario,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not item:
        raise APIError(404, "LOTE_AUSENTE", "Confirmação não encontrada para seu usuário e turma.")
    if not item.confirmado_em:
        if item.expira_em <= utcnow():
            raise APIError(
                409,
                "CONFIRMACAO_EXPIRADA",
                "A confirmação expirou. Selecione e confira os destinatários novamente.",
            )
        # Class lock also serializes enrollment/work/meeting changes in the same class.
        list(
            db.session.scalars(
                select(Matricula)
                .where(Matricula.id_matricula_turma.in_(item.matriculas))
                .order_by(Matricula.id_matricula_turma)
                .with_for_update()
            )
        )
        source = matrix(turma.id_turma)
        rows = list(
            db.session.execute(
                select(source).where(
                    source.c.id_matricula.in_(item.matriculas), source.c.dias_inatividade > 30
                )
            ).mappings()
        )
        if {r["id_matricula"] for r in rows} != set(item.matriculas):
            raise APIError(
                409,
                "SELECAO_DESATUALIZADA",
                "A turma mudou desde a confirmação. Recarregue e confira a seleção novamente.",
            )
        for row in rows:
            user = db.session.get(Usuario, row["id_aluno"])
            notification = academic_mail.enqueue(
                user,
                "cobranca_inatividade",
                "Acompanhamento de TCC - SIGG-TCC",
                f"Olá, {row['nome']}.\nTurma {turma.codigo_turma}.\n\n{item.mensagem}\n\n"
                f"Acesse {current_app.config['FRONTEND_URL'].rstrip('/')}/#/reunioes",
                f"cobranca:{item.id_lote}:{row['id_matricula']}",
                id_matricula_turma=row["id_matricula"],
            )
            db.session.flush()
            audit(
                g.user.id_usuario,
                "cobranca_inatividade",
                "notificacao",
                notification.id_notificacao,
                {
                    "email_destinatario": (None, row["email"]),
                    "id_matricula": (None, row["id_matricula"]),
                },
                reason=f"UC13; lote {item.id_lote}; turma {turma.codigo_turma}",
            )
        item.confirmado_em = utcnow()
        db.session.commit()
    keys = [f"cobranca:{item.id_lote}:{identifier}" for identifier in item.matriculas]
    notifications = list(
        db.session.scalars(
            select(NotificacaoAcademica).where(
                NotificacaoAcademica.chave_idempotencia_notificacao.in_(keys)
            )
        )
    )
    academic_mail.deliver([n.id_notificacao for n in notifications])
    for notification in notifications:
        db.session.refresh(notification)
    sent = sum(n.situacao_notificacao == "enviada" for n in notifications)
    cancelled = sum(n.situacao_notificacao == "cancelada" for n in notifications)
    remaining = len(notifications) - sent - cancelled
    code = "UC_13_M05" if remaining else "UC_13_ATUALIZADO" if cancelled else "UC_13_M01"
    message = (
        M05
        if remaining
        else (
            "Alertas de estudantes regularizados foram cancelados. Confira o resultado do lote."
            if cancelled
            else M01
        )
    )
    return (
        {
            "id_lote": item.id_lote,
            "total": len(notifications),
            "enviados": sent,
            "pendentes": remaining,
            "cancelados": cancelled,
        },
        code,
        message,
    )

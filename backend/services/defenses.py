from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from flask import current_app, g
from sqlalchemy import select

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import Avaliacao, Banca, Nota, Rubrica
from backend.errors import APIError
from backend.models import Curso, Turma
from backend.serialization import check_version, iso


def number(value, field, places=2, maximum="999.99"):
    try:
        if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
            raise ValueError
        result = Decimal(str(value))
        if (
            not result.is_finite()
            or result.as_tuple().exponent < -places
            or abs(result) > Decimal(maximum)
        ):
            raise ValueError
        return result
    except InvalidOperation, ValueError:
        raise APIError(
            422, "VALIDACAO", "Informe um número decimal válido.", {field: "Valor inválido."}
        ) from None


def member(banca, user_id=None):
    user_id = user_id or g.user.id_usuario
    now = utcnow()
    return next(
        (
            m
            for m in banca.membros
            if (
                m.id_docente == user_id
                and m.papel_membro_banca != "suplente"
                and m.situacao_convite_membro_banca == "aceito"
                and m.data_inicio_acesso_membro_banca <= now <= m.data_fim_acesso_membro_banca
                and m.avaliador.usuario.ativo_usuario
            )
        ),
        None,
    )


def get_defense(defense_id, lock=False):
    query = select(Banca).where(Banca.id_banca == defense_id)
    if lock:
        query = query.with_for_update()
    banca = db.session.scalar(query.execution_options(populate_existing=True))
    if not banca or not member(banca):
        raise APIError(403, "UC_09_M05", "Você não possui permissão para avaliar esta defesa.")
    return banca


def criteria(banca):
    if banca.snapshot_avaliacao_banca is not None:
        result = banca.snapshot_avaliacao_banca
    else:
        result = [
            {
                "id_criterio": c.id_criterio_rubrica,
                "nome": c.nome_criterio_rubrica,
                "descricao": c.descricao_criterio_rubrica or "",
                "peso": str(c.peso_criterio_rubrica),
                "pontuacao_maxima": str(c.pontuacao_maxima_criterio_rubrica),
            }
            for c in banca.rubrica.criterios
        ]
    if (
        banca.rubrica.situacao_rubrica != "ativa"
        or not result
        or any(Decimal(c["peso"]) <= 0 or Decimal(c["pontuacao_maxima"]) <= 0 for c in result)
        or sum(Decimal(c["peso"]) for c in result) not in {Decimal(10), Decimal(100)}
    ):
        raise APIError(409, "UC_09_M07", "Os critérios de avaliação ainda não foram configurados.")
    return result


def weighted(grades, rubric):
    values = {n.id_criterio_rubrica: n.valor_nota_criterio for n in grades}
    return weighted_values(values, rubric)


def weighted_values(values, rubric):
    maxima = {c["id_criterio"]: Decimal(c["pontuacao_maxima"]) for c in rubric}
    if values.keys() != maxima.keys() or any(
        not 0 <= grade <= maxima[key] for key, grade in values.items()
    ):
        raise APIError(409, "AVALIACAO_INCOMPLETA", "Existem avaliações incompletas nesta banca.")
    total = sum(Decimal(c["peso"]) for c in rubric)
    return (
        sum(
            values[c["id_criterio"]] / Decimal(c["pontuacao_maxima"]) * Decimal(c["peso"])
            for c in rubric
        )
        * Decimal(10)
        / total
    )


def decimal_text(value):
    return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")


def evaluation_json(evaluation, rubric, calculated=None):
    if not evaluation or evaluation.situacao_avaliacao != "enviada":
        return None
    return {
        "id_avaliacao": evaluation.id_avaliacao,
        "data_envio": iso(evaluation.data_envio_avaliacao),
        "nota_individual": decimal_text(
            weighted(evaluation.notas, rubric) if calculated is None else calculated
        ),
        "parecer": evaluation.parecer_avaliacao,
        "notas": [
            {"id_criterio": n.id_criterio_rubrica, "nota": str(n.valor_nota_criterio)}
            for n in evaluation.notas
        ],
    }


def accepted_members(banca):
    # Expiry of temporary access must not remove a submitted examiner from the final average.
    return [m for m in banca.membros if m.papel_membro_banca != "suplente"]


def consolidation(banca, rubric):
    members = accepted_members(banca)
    completed = [m for m in members if m.avaliacao and m.avaliacao.situacao_avaliacao == "enviada"]
    average = None
    if members and len(completed) == len(members):
        average = decimal_text(
            sum(weighted(m.avaliacao.notas, rubric) for m in members) / len(members)
        )
    return {
        "avaliacoes_enviadas": len(completed),
        "total_avaliadores": len(members),
        "media_final": average,
        "avaliadores": [
            {
                "nome": m.avaliador.usuario.nome_usuario,
                "enviada": m in completed,
                "nota_individual": decimal_text(weighted(m.avaliacao.notas, rubric))
                if m in completed
                else None,
            }
            for m in members
        ],
    }


def defense_json(banca, full=True, calculated=None):
    work = banca.etapa.trabalho
    turma = db.session.get(Turma, banca.etapa.matricula.id_turma)
    course = db.session.get(Curso, turma.id_curso)
    today = utcnow().astimezone(current_app.config["ACADEMIC_TIMEZONE"]).date()
    local_date = banca.data_inicio_banca.astimezone(current_app.config["ACADEMIC_TIMEZONE"]).date()
    result = {
        "id_banca": banca.id_banca,
        "aluno": work.estudante.usuario.nome_usuario,
        "titulo": work.titulo_trabalho_tcc,
        "curso": course.nome_curso,
        "data_inicio": iso(banca.data_inicio_banca),
        "data_fim": iso(banca.data_fim_banca),
        "local": banca.local_defesa_banca,
        "situacao": banca.situacao_banca,
        "resultado": banca.resultado_banca,
        "pode_avaliar": today == local_date
        and banca.situacao_banca in {"agendada", "em_andamento"},
        "avaliador": g.user.nome_usuario,
    }
    if full:
        rubric = criteria(banca)
        evaluation = member(banca).avaliacao
        result.update(
            criterios=rubric,
            avaliacao=evaluation_json(evaluation, rubric, calculated),
            avaliacao_iniciada=evaluation is not None,
            **consolidation(banca, rubric),
        )
    return result


def evaluation_context(banca):
    check_version(banca)
    current = member(banca)
    if not defense_json(banca, False)["pode_avaliar"]:
        raise APIError(
            403, "UC_09_M06", "O formulário de avaliação não está disponível neste momento."
        )
    db.session.scalar(
        select(Rubrica)
        .where(Rubrica.id_rubrica == banca.id_rubrica)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    rubric = criteria(banca)
    if current.avaliacao and current.avaliacao.situacao_avaliacao == "enviada":
        raise APIError(
            409, "AVALIACAO_ENVIADA", "Sua avaliação já foi enviada e não pode ser sobrescrita."
        )
    return current, rubric


def open_evaluation(banca, current, rubric):
    evaluation = current.avaliacao
    if not evaluation:
        evaluation = Avaliacao(
            id_membro_banca=current.id_membro_banca, situacao_avaliacao="rascunho"
        )
        db.session.add(evaluation)
        audit(g.user.id_usuario, "avaliacao_iniciada", "banca", banca.id_banca)
    banca.rubrica.data_bloqueio_rubrica_avaliacao = (
        banca.rubrica.data_bloqueio_rubrica_avaliacao or utcnow()
    )
    banca.snapshot_avaliacao_banca = rubric
    banca.situacao_banca = "em_andamento"
    return evaluation


def start(banca):
    current, rubric = evaluation_context(banca)
    if not current.avaliacao or banca.snapshot_avaliacao_banca is None:
        open_evaluation(banca, current, rubric)
        banca.versao_banca += 1
        db.session.commit()
        db.session.expire_all()


def submit(banca, data):
    current, rubric = evaluation_context(banca)
    notes = data.get("notas")
    if not isinstance(notes, list) or len(notes) != len(rubric):
        raise APIError(422, "UC_09_M02", "Preencha as notas de todos os critérios obrigatórios.")
    mapped = {}
    expected = {c["id_criterio"]: c for c in rubric}
    for item in notes:
        if not isinstance(item, dict) or set(item) != {"id_criterio", "nota"}:
            raise APIError(
                422, "UC_09_M02", "Preencha as notas de todos os critérios obrigatórios."
            )
        key = item["id_criterio"]
        if type(key) is not int or key not in expected or key in mapped:
            raise APIError(
                422, "UC_09_M02", "Preencha as notas de todos os critérios obrigatórios."
            )
        grade = number(item["nota"], f"notas.{key}")
        field = f"notas.{key}"
        if grade < 0:
            raise APIError(
                422,
                "UC_09_M04",
                "A nota informada não pode ser negativa.",
                {field: "Informe uma nota igual ou maior que zero."},
            )
        if grade > Decimal(expected[key]["pontuacao_maxima"]):
            raise APIError(
                422,
                "UC_09_M03",
                "A nota informada excede a pontuação máxima permitida.",
                {field: f"Pontuação máxima: {expected[key]['pontuacao_maxima']}."},
            )
        mapped[key] = grade
    opinion = data.get("parecer")
    if opinion is not None:
        opinion = v.text(opinion, "parecer", 4000, minimum=0) or None
    individual = weighted_values(mapped, rubric)
    evaluation = open_evaluation(banca, current, rubric)
    db.session.flush()
    # Replace a pre-existing draft atomically; a submitted evaluation is immutable.
    for note in list(evaluation.notas):
        db.session.delete(note)
    db.session.flush()
    for key, grade in mapped.items():
        db.session.add(
            Nota(
                id_avaliacao=evaluation.id_avaliacao,
                id_criterio_rubrica=key,
                valor_nota_criterio=grade,
            )
        )
    evaluation.situacao_avaliacao = "enviada"
    evaluation.data_envio_avaliacao = utcnow()
    evaluation.parecer_avaliacao = opinion
    banca.versao_banca += 1
    audit(g.user.id_usuario, "avaliacao_enviada", "banca", banca.id_banca)
    db.session.commit()
    db.session.expire_all()
    return individual

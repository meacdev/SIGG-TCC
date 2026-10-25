import hashlib
import hmac

from flask import g
from sqlalchemy import select

from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import Matricula
from backend.errors import APIError
from backend.models import Aluno, Turma
from backend.services import academic_mail


def student(identifier):
    item = db.session.scalar(select(Aluno).where(Aluno.id_aluno == identifier).with_for_update())
    if not item or not item.usuario.ativo_usuario:
        raise APIError(404, "UC_04_M02", "Cadastro de estudante não encontrado!")
    return item


def enroll(turma, identifier, origin="professor"):
    if not turma.ativa_turma:
        raise APIError(409, "TURMA_INATIVA", "A turma está inativa.")
    aluno = student(identifier)
    if aluno.id_curso != turma.id_curso:
        raise APIError(422, "CURSO_DIVERGENTE", "O estudante deve pertencer ao curso da turma.")
    item = db.session.scalar(
        select(Matricula).where(
            Matricula.id_turma == turma.id_turma, Matricula.id_aluno == identifier
        )
    )
    if item and item.situacao_matricula_turma == "ativa":
        raise APIError(409, "MATRICULA_DUPLICADA", "O estudante já está matriculado nesta turma.")
    if not item:
        item = Matricula(
            id_turma=turma.id_turma, id_aluno=identifier, id_usuario_inclusao=g.user.id_usuario
        )
        db.session.add(item)
    else:
        item.versao_matricula += 1
    item.situacao_matricula_turma = "ativa"
    item.origem_matricula_turma = origin
    item.id_usuario_inclusao = g.user.id_usuario
    item.data_matricula_matricula_turma = utcnow()
    item.data_remocao_matricula_turma = None
    item.motivo_remocao_matricula_turma = None
    db.session.flush()
    audit(g.user.id_usuario, "inclusao_matricula", "matricula_turma", item.id_matricula_turma)
    db.session.commit()
    return item


def self_enroll(code):
    if not g.user.aluno:
        raise APIError(403, "ACESSO_NEGADO", "A autoinscrição exige uma conta de estudante.")
    if (
        not isinstance(code, str)
        or len(code.strip()) != 24
        or not code.strip().isascii()
        or not code.strip().isalnum()
    ):
        raise APIError(422, "CODIGO_INVALIDO", "Informe um código de acesso válido.")
    digest = hashlib.sha256(code.strip().encode()).hexdigest()
    turma = db.session.scalar(
        select(Turma).where(Turma.hash_codigo_acesso_turma == digest).with_for_update(of=Turma)
    )
    if (
        not turma
        or not hmac.compare_digest(turma.hash_codigo_acesso_turma, digest)
        or not turma.ativa_turma
        or not turma.autoinscricao_ativa_turma
        or not turma.data_expiracao_acesso_turma
        or turma.data_expiracao_acesso_turma <= utcnow()
    ):
        raise APIError(
            422, "CODIGO_INVALIDO", "Código inválido, expirado ou autoinscrição desabilitada."
        )
    return enroll(turma, g.user.id_usuario, "codigo")


def serialize(item):
    return {
        "id_matricula": item.id_matricula_turma,
        "id_turma": item.id_turma,
        "id_aluno": item.id_aluno,
        "nome": item.aluno.usuario.nome_usuario,
        "matricula": item.aluno.matricula_aluno,
        "situacao": item.situacao_matricula_turma,
        "codigo_turma": item.turma.codigo_turma,
        "periodo_letivo": (
            f"{item.turma.periodo.ano_periodo_letivo}/{item.turma.periodo.semestre_periodo_letivo}"
        ),
        "nivel_turma": item.turma.nivel_turma,
        "id_curso": item.turma.id_curso,
        "turma_ativa": item.turma.ativa_turma,
        "data_matricula": item.data_matricula_matricula_turma.isoformat(),
        "versao": item.versao_matricula,
    }


def remove(item, confirmation, reason):
    expected = f"{item.aluno.usuario.nome_usuario}/{item.turma.codigo_turma}"
    if confirmation != expected:
        raise APIError(
            422,
            "CONFIRMACAO_INVALIDA",
            "Digite exatamente nome do estudante/nome da turma para confirmar.",
        )
    if item.situacao_matricula_turma != "ativa":
        raise APIError(409, "MATRICULA_REMOVIDA", "O estudante já foi removido desta turma.")
    item.situacao_matricula_turma = "removida"
    item.data_remocao_matricula_turma = utcnow()
    item.motivo_remocao_matricula_turma = reason
    item.versao_matricula += 1
    notification = academic_mail.enqueue(
        item.aluno.usuario,
        "remocao_matricula",
        "Desligamento de turma - SIGG-TCC",
        f"Sua matrícula na turma {item.turma.codigo_turma} foi removida pelo responsável. "
        f"Motivo: {reason}",
        f"remocao:{item.id_matricula_turma}:{item.versao_matricula}",
        id_matricula_turma=item.id_matricula_turma,
    )
    db.session.flush()
    identifier = notification.id_notificacao
    audit(
        g.user.id_usuario,
        "remocao_matricula",
        "matricula_turma",
        item.id_matricula_turma,
        reason=reason,
    )
    db.session.commit()
    academic_mail.deliver([identifier])
    return {**serialize(item), "notificacao": notification.situacao_notificacao}

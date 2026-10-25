import re

from flask import current_app, g
from sqlalchemy import select

from backend import validation as v
from backend.audit import audit
from backend.db import db, utcnow
from backend.defense_models import Etapa, Matricula, Orientacao, Trabalho
from backend.errors import APIError
from backend.models import Aluno, Curso, Docente, Turma
from backend.serialization import check_version, iso
from backend.services import academic_mail

FIELDS = {
    "titulo",
    "subtitulo",
    "tema",
    "modalidade",
    "tipo_artigo",
    "url",
    "doi",
    "id_curso",
    "id_matricula",
    "id_orientador",
    "id_coorientador",
    "palavras_chave",
}
REQUIRED = {"titulo", "tema", "modalidade", "id_curso", "id_matricula", "id_orientador"}


def own_work(lock=False):
    if not g.user.aluno:
        raise APIError(
            403,
            "UC_06_M05",
            "Você somente pode cadastrar ou atualizar as informações do próprio trabalho.",
        )
    query = select(Trabalho).where(Trabalho.id_aluno == g.user.id_usuario)
    if lock:
        query = query.with_for_update()
    return db.session.scalar(query.execution_options(populate_existing=True))


def orientations(work):
    return list(
        db.session.scalars(
            select(Orientacao)
            .where(
                Orientacao.id_trabalho == work.id_trabalho,
                Orientacao.data_encerramento_orientacao.is_(None),
            )
            .order_by(Orientacao.id_orientacao)
        )
    )


def serialize(work):
    records = orientations(work)
    enrollment = (
        db.session.get(Matricula, work.id_matricula_atual) if work.id_matricula_atual else None
    )
    stage = (
        db.session.scalar(
            select(Etapa).where(
                Etapa.id_trabalho == work.id_trabalho,
                Etapa.id_matricula_turma == work.id_matricula_atual,
            )
        )
        if enrollment
        else None
    )
    return {
        "id_trabalho": work.id_trabalho,
        "titulo": work.titulo_trabalho,
        "subtitulo": work.subtitulo_trabalho,
        "tema": work.tema_trabalho,
        "modalidade": "monografia" if work.modalidade_trabalho == "monografia" else "artigo",
        "tipo_artigo": "publicado"
        if work.modalidade_trabalho == "artigo_publicado"
        else "a_submeter"
        if work.modalidade_trabalho == "artigo_a_submeter"
        else None,
        "url": work.url_artigo_trabalho,
        "doi": work.doi_artigo_trabalho,
        "id_curso": work.aluno.id_curso,
        "id_matricula": work.id_matricula_atual,
        "id_etapa": stage.id_etapa_trabalho if stage else None,
        "nivel_turma": enrollment.turma.nivel_turma if enrollment else None,
        "codigo_turma": enrollment.turma.codigo_turma if enrollment else None,
        "palavras_chave": work.palavras_chave_trabalho,
        "situacao": work.situacao_trabalho,
        "aluno": work.aluno.usuario.nome_usuario,
        "id_aluno": work.id_aluno,
        "data_criacao": iso(work.data_criacao_trabalho),
        "versao": work.versao_trabalho,
        "orientacoes": [
            {
                "id_orientacao": o.id_orientacao,
                "id_docente": o.id_docente,
                "nome": o.docente.usuario.nome_usuario,
                "papel": o.papel_orientacao,
                "situacao": o.situacao_aceite_orientacao,
                "data_resposta": iso(o.data_resposta_orientacao),
            }
            for o in records
        ],
    }


def validate(data):
    result = {
        "titulo_trabalho": v.text(data.get("titulo"), "titulo", 500),
        "subtitulo_trabalho": v.text(data["subtitulo"], "subtitulo", 500)
        if data.get("subtitulo")
        else None,
        "tema_trabalho": v.text(data.get("tema"), "tema", 5000),
    }
    modality = v.choice(data.get("modalidade"), "modalidade", ("monografia", "artigo"))
    subtype = data.get("tipo_artigo")
    if modality == "artigo":
        if not isinstance(subtype, str) or subtype not in {"publicado", "a_submeter"}:
            raise APIError(
                422,
                "UC_06_M03",
                "Informe se o artigo é Publicado ou A Submeter.",
                {"tipo_artigo": "Obrigatório."},
            )
        if subtype == "publicado" and (not data.get("url") or not data.get("doi")):
            raise APIError(
                422,
                "UC_06_M04",
                "Para artigos publicados, informe o Link/URL e o DOI.",
                {"url": "Obrigatório.", "doi": "Obrigatório."},
            )
        if subtype == "publicado":
            url = v.lattes(data["url"])
            doi = v.text(data["doi"], "doi", 255)
            if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
                raise APIError(
                    422,
                    "DOI_INVALIDO",
                    "Informe um DOI válido, no formato 10.xxxx/identificador.",
                    {"doi": "DOI inválido."},
                )
            result.update(url_artigo_trabalho=url, doi_artigo_trabalho=doi)
    result["modalidade_trabalho"] = (
        "monografia" if modality == "monografia" else f"artigo_{subtype}"
    )
    if result["modalidade_trabalho"] != "artigo_publicado":
        result.update(url_artigo_trabalho=None, doi_artigo_trabalho=None)
    keywords = data.get("palavras_chave", [])
    if not isinstance(keywords, list) or len(keywords) > 10:
        raise APIError(
            422,
            "VALIDACAO",
            "Informe até 10 palavras-chave.",
            {"palavras_chave": "Lista de até 10 termos."},
        )
    result["palavras_chave_trabalho"] = list(
        dict.fromkeys(v.text(k, "palavras_chave", 100) for k in keywords)
    )
    return result


def save(data):
    own_work()
    values = validate(data)
    identifier = v.integer(data.get("id_matricula"), "id_matricula")
    membership = db.session.get(Matricula, identifier)
    if not membership or membership.id_aluno != g.user.id_usuario:
        raise APIError(
            422,
            "UC_06_M06",
            "Não foi possível identificar o nível da disciplina. "
            "Verifique seu vínculo com a turma.",
        )
    # Match enrollment mutation lock order: class, student, enrollment, work.
    turma = db.session.scalar(
        select(Turma).where(Turma.id_turma == membership.id_turma).with_for_update(of=Turma)
    )
    db.session.scalar(select(Aluno).where(Aluno.id_aluno == g.user.id_usuario).with_for_update())
    membership = db.session.scalar(
        select(Matricula)
        .where(Matricula.id_matricula_turma == identifier)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        membership.situacao_matricula_turma != "ativa"
        or not turma.ativa_turma
        or turma.nivel_turma not in {1, 2}
    ):
        raise APIError(
            422,
            "UC_06_M06",
            "Não foi possível identificar o nível da disciplina. "
            "Verifique seu vínculo com a turma.",
        )
    if (
        v.integer(data.get("id_curso"), "id_curso") != g.user.aluno.id_curso
        or turma.id_curso != g.user.aluno.id_curso
    ):
        raise APIError(
            422,
            "CURSO_DIVERGENTE",
            "O curso deve corresponder ao cadastro e à matrícula do estudante.",
        )
    course = db.session.get(Curso, turma.id_curso)
    if not course or not course.ativo_curso:
        raise APIError(422, "CURSO_INVALIDO", "O curso da matrícula deve estar ativo.")
    advisors = {"orientador": v.integer(data.get("id_orientador"), "id_orientador")}
    if data.get("id_coorientador") is not None:
        advisors["coorientador"] = v.integer(data["id_coorientador"], "id_coorientador")
    if len(set(advisors.values())) != len(advisors):
        raise APIError(
            422, "ORIENTADOR_REPETIDO", "Orientador e coorientador devem ser pessoas distintas."
        )
    for role, teacher_id in advisors.items():
        teacher = db.session.scalar(
            select(Docente).where(Docente.id_docente == teacher_id).with_for_update()
        )
        if not teacher or not teacher.ativo_docente or not teacher.usuario.ativo_usuario:
            raise APIError(422, "DOCENTE_INVALIDO", f"Selecione um {role} ativo.")
    work = own_work(lock=True)
    created = work is None
    if work:
        check_version(work)
        if work.situacao_trabalho != "em_andamento":
            raise APIError(409, "TRABALHO_ENCERRADO", "Este trabalho não admite alterações.")
    else:
        work = Trabalho(id_aluno=g.user.id_usuario)
        db.session.add(work)
    records = orientations(work) if not created else []
    current = {o.papel_orientacao: o for o in records}
    for role, record in current.items():
        if advisors.get(role) != record.id_docente:
            raise APIError(
                409,
                "TROCA_ORIENTACAO_RF05",
                "A troca ou remoção de orientação exige o fluxo autorizado do RF05, "
                "com justificativa.",
            )
    for key, value in values.items():
        setattr(work, key, value)
    work.id_matricula_atual = identifier
    if not created:
        work.versao_trabalho += 1
    db.session.flush()
    stage = db.session.scalar(select(Etapa).where(Etapa.id_matricula_turma == identifier))
    if stage and stage.id_trabalho != work.id_trabalho:
        raise APIError(409, "ETAPA_DIVERGENTE", "A matrícula já está vinculada a outro trabalho.")
    if not stage:
        db.session.add(Etapa(id_trabalho=work.id_trabalho, id_matricula_turma=identifier))
    notifications = []
    for role, teacher_id in advisors.items():
        if role in current:
            continue
        record = Orientacao(
            id_trabalho=work.id_trabalho,
            id_docente=teacher_id,
            papel_orientacao=role,
            id_usuario_registro=g.user.id_usuario,
        )
        db.session.add(record)
        db.session.flush()
        teacher = db.session.get(Docente, teacher_id)
        notification = academic_mail.enqueue(
            teacher.usuario,
            "convite_orientacao",
            "Vínculo de orientação - SIGG-TCC",
            f"{g.user.nome_usuario} indicou você como {role} de {work.titulo_trabalho}. "
            "Entre no SIGG-TCC e acesse Trabalhos para consultar e responder ao vínculo: "
            f"{current_app.config['FRONTEND_URL'].rstrip('/')}/#/trabalhos",
            f"orientacao:{record.id_orientacao}",
            id_orientacao=record.id_orientacao,
        )
        db.session.flush()
        notifications.append(notification.id_notificacao)
    audit(
        g.user.id_usuario,
        "registro_trabalho" if created else "atualizacao_trabalho",
        "trabalho",
        work.id_trabalho,
    )
    db.session.commit()
    academic_mail.deliver(notifications)
    return work, created


def respond(work, record, decision):
    check_version(work)
    if (
        not g.user.docente
        or not g.user.docente.ativo_docente
        or record.id_docente != g.user.id_usuario
        or record.data_encerramento_orientacao
    ):
        raise APIError(
            403, "ACESSO_NEGADO", "Somente o docente indicado pode responder ao vínculo."
        )
    if record.situacao_aceite_orientacao != "pendente":
        raise APIError(409, "RESPOSTA_REGISTRADA", "Este vínculo já possui uma resposta.")
    decision = v.choice(decision, "decisao", ("aceito", "recusado"))
    record.situacao_aceite_orientacao = decision
    record.data_resposta_orientacao = utcnow()
    work.versao_trabalho += 1
    audit(
        g.user.id_usuario,
        "resposta_orientacao",
        "orientacao",
        record.id_orientacao,
        {"situacao_aceite_orientacao": ("pendente", decision)},
    )
    db.session.commit()

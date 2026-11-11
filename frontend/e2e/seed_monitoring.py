"""UC13 scenarios exclusively for the in-memory browser test database."""

from datetime import timedelta

from flask import g
from sqlalchemy import select

from backend.academic_models import Reuniao
from backend.db import db, utcnow
from backend.defense_models import Matricula, Orientacao
from backend.models import Usuario
from backend.serialization import etag
from backend.services import classes, works
from backend.services.users import signup


def seed(app):
    if not app.testing or app.config["SQLALCHEMY_DATABASE_URI"] != "sqlite://":
        raise RuntimeError("Only disposable test data is supported")
    teacher = db.session.scalar(
        select(Usuario).where(Usuario.email_usuario == "professora@example.com")
    )

    def turma(code):
        g.user = teacher
        return classes.create_class(
            {
                "periodo_letivo": "2026/2",
                "codigo_turma": code,
                "nivel_turma": 1,
                "id_curso": 1,
                "id_docente_responsavel": teacher.id_usuario,
            }
        )[0]

    with app.test_request_context():
        target = turma("ESTSI13")
        turma("ESTVAZIA13")
        fresh = turma("ESTATIVA13")
        primary = None
        for index in range(1, 23):
            student = signup(
                {
                    "nome_usuario": f"Aluno Monitoramento {index:02}",
                    "email_usuario": f"monitoramento{index:02}@example.com",
                    "senha": "Senha de teste UC03 123",
                    "tipo_cadastro": "aluno",
                    "id_curso": 1,
                    "matricula_aluno": f"000UC13{index:04}",
                }
            )
            membership = Matricula(
                id_turma=target.id_turma,
                id_aluno=student.id_usuario,
                id_usuario_inclusao=teacher.id_usuario,
                data_matricula_matricula_turma=utcnow() - timedelta(days=40 if index <= 21 else 2),
            )
            db.session.add(membership)
            db.session.flush()
            if index == 1:
                primary = (student, membership)
        db.session.add(
            Matricula(
                id_turma=fresh.id_turma,
                id_aluno=primary[0].id_usuario,
                id_usuario_inclusao=teacher.id_usuario,
                data_matricula_matricula_turma=utcnow(),
            )
        )
        db.session.commit()
        student, membership = primary
        g.user = student
        work, _ = works.save(
            {
                "titulo": "Pesquisa acompanhada no UC13",
                "tema": "Monitoramento acadêmico",
                "modalidade": "monografia",
                "id_curso": 1,
                "id_matricula": membership.id_matricula_turma,
                "id_orientador": teacher.id_usuario,
            }
        )
        orientation = db.session.scalar(
            select(Orientacao).where(Orientacao.id_trabalho == work.id_trabalho)
        )
        identifier = orientation.id_orientacao
        version = etag(work)
    with app.test_request_context(headers={"If-Match": f'"{version}"'}):
        g.user = teacher
        works.respond(work, orientation, "aceito")
    from backend.defense_models import Etapa

    stage = db.session.scalar(select(Etapa).where(Etapa.id_trabalho == work.id_trabalho))
    db.session.add(
        Reuniao(
            id_etapa_trabalho=stage.id_etapa_trabalho,
            id_orientacao=identifier,
            data_encontro_reuniao_orientacao=utcnow().date() - timedelta(days=40),
            resumo_encaminhamentos_reuniao_orientacao="Revisar os objetivos do trabalho.",
            id_usuario_registro=student.id_usuario,
        )
    )
    db.session.commit()

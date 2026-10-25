"""Synthetic accounts exclusively for the disposable browser test server."""

from datetime import timedelta

from backend.db import db, utcnow
from backend.models import DocenteCurso, Perfil, UsuarioPerfil
from backend.services.users import signup


def seed(app):
    if not app.testing or app.config["SQLALCHEMY_DATABASE_URI"] != "sqlite://":
        raise RuntimeError("Only the disposable browser database is supported")
    teacher = signup(
        {
            "nome_usuario": "Professora de Teste",
            "email_usuario": "professora@example.com",
            "senha": "Senha de teste UC03 123",
            "titulacao_docente": "doutor",
        }
    )
    role = db.session.scalar(
        db.select(Perfil).where(Perfil.codigo_perfil == "professor_disciplina")
    )
    db.session.add(UsuarioPerfil(id_usuario=teacher.id_usuario, id_perfil=role.id_perfil))
    db.session.add(
        DocenteCurso(
            id_docente=teacher.id_usuario,
            id_curso=1,
            data_inicio_docente_curso=utcnow().date() - timedelta(days=1),
        )
    )
    db.session.commit()

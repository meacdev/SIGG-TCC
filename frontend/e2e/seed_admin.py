"""Synthetic Administrator (UC14) exclusively for the disposable browser test server."""

from sqlalchemy import select

from backend.db import db
from backend.models import Perfil, Usuario, UsuarioPerfil
from backend.security import hash_password


def seed(app):
    if not app.testing or app.config["SQLALCHEMY_DATABASE_URI"] != "sqlite://":
        raise RuntimeError("Only the disposable browser database is supported")
    # Administrative account: no student or teacher record, only the administrator role.
    user = Usuario(
        nome_usuario="Secretaria de Teste",
        email_usuario="secretaria@uea.edu.br",
        hash_senha_usuario=hash_password("Senha de teste UC14 123"),
    )
    db.session.add(user)
    db.session.flush()
    role = db.session.scalar(select(Perfil).where(Perfil.codigo_perfil == "administrador"))
    db.session.add(UsuarioPerfil(id_usuario=user.id_usuario, id_perfil=role.id_perfil))
    db.session.commit()

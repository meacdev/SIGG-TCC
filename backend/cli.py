import hashlib
from datetime import UTC, datetime
from pathlib import Path

import click
from flask.cli import with_appcontext
from sqlalchemy import inspect, select, text

from backend.audit import audit
from backend.db import db, utcnow
from backend.models import Curso, DocenteCurso, Perfil, Usuario, UsuarioPerfil
from backend.services.classes import get_period

PROFILES = {
    "aluno": "Estudante",
    "professor_disciplina": "Professor da disciplina de TCC",
    "orientador": "Orientador ou coorientador",
    "coordenador": "Coordenador de curso",
    "avaliador": "Membro da banca",
}


def seed_profiles():
    for code, description in PROFILES.items():
        if not db.session.scalar(select(Perfil).where(Perfil.codigo_perfil == code)):
            db.session.add(Perfil(codigo_perfil=code, descricao_perfil=description))
    db.session.flush()


def register_cli(app):
    @app.cli.command("db-upgrade")
    @with_appcontext
    def upgrade():
        """Apply reviewed complementary migrations to the existing PostgreSQL schema."""
        if db.engine.dialect.name != "postgresql":
            raise click.ClickException("As migrações exigem PostgreSQL.")
        folder = Path(__file__).parent / "sql" / "migrations"
        with db.engine.begin() as connection:
            connection.execute(text("SELECT pg_advisory_xact_lock(1936287591)"))
            connection.exec_driver_sql(
                "CREATE TABLE IF NOT EXISTS sigg_migracao "
                "(versao VARCHAR(100) PRIMARY KEY, sha256 CHAR(64) NOT NULL, "
                "aplicada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            if "usuario" not in inspect(connection).get_table_names():
                raise click.ClickException("Importe primeiro o SQL base fornecido do projeto.")
            for path in sorted(folder.glob("*.sql")):
                source = path.read_text(encoding="utf-8")
                digest = hashlib.sha256(source.encode()).hexdigest()
                previous = connection.execute(
                    text("SELECT sha256 FROM sigg_migracao WHERE versao=:version"),
                    {"version": path.name},
                ).scalar()
                if previous:
                    if previous != digest:
                        raise click.ClickException(f"Migração aplicada foi modificada: {path.name}")
                    continue
                connection.exec_driver_sql(source)
                connection.execute(
                    text("INSERT INTO sigg_migracao (versao,sha256) VALUES (:version,:digest)"),
                    {"version": path.name, "digest": digest},
                )
                click.echo(f"Aplicada: {path.name}")
        click.echo("Banco atualizado.")

    @app.cli.command("seed-perfis")
    @with_appcontext
    def seed():
        """Create the five catalog roles without granting administrative access."""
        seed_profiles()
        db.session.commit()
        click.echo("Perfis inicializados.")

    @app.cli.command("criar-curso")
    @click.option("--codigo", required=True)
    @click.option("--nome", required=True)
    @with_appcontext
    def create_course(codigo, nome):
        from backend.validation import text as validate_text

        code = validate_text(codigo, "codigo_curso", 30).upper()
        if db.session.scalar(select(Curso).where(Curso.codigo_curso == code)):
            raise click.ClickException("Curso já cadastrado.")
        course = Curso(codigo_curso=code, nome_curso=validate_text(nome, "nome_curso"))
        db.session.add(course)
        db.session.flush()
        audit(None, "criacao_curso_cli", "curso", course.id_curso)
        db.session.commit()
        click.echo(f"Curso criado: {course.id_curso}")

    @app.cli.command("criar-periodo")
    @click.argument("periodo")
    @with_appcontext
    def create_period(periodo):
        item = get_period(periodo)
        db.session.commit()
        click.echo(f"Período: {item.id_periodo_letivo}")

    @app.cli.command("conceder-perfil")
    @click.option("--email", required=True)
    @click.option("--perfil", type=click.Choice(list(PROFILES)), required=True)
    @click.option("--id-curso", type=int)
    @click.option("--expira-em", help="ISO 8601 com fuso, por exemplo 2027-01-01T00:00:00Z.")
    @click.option("--revogar", is_flag=True)
    @click.option("--justificativa", required=True)
    @with_appcontext
    def grant(email, perfil, id_curso, expira_em, revogar, justificativa):
        """Grant/revoke privileges through a trusted administrator's terminal."""
        user = db.session.scalar(
            select(Usuario).where(Usuario.email_usuario == email.strip().lower()).with_for_update()
        )
        if not user or not user.ativo_usuario:
            raise click.ClickException("Usuário ativo não encontrado.")
        if not justificativa.strip():
            raise click.ClickException("Informe uma justificativa.")
        expiration = None
        if expira_em:
            try:
                expiration = datetime.fromisoformat(expira_em)
                if not expiration.tzinfo or expiration <= utcnow():
                    raise ValueError
                expiration = expiration.astimezone(UTC)
            except ValueError:
                raise click.ClickException(
                    "Informe uma expiração futura com fuso horário."
                ) from None
        if perfil == "aluno" and not user.aluno:
            raise click.ClickException("O usuário não possui cadastro de estudante.")
        if perfil != "aluno" and (not user.docente or not user.docente.ativo_docente):
            raise click.ClickException("O usuário não possui cadastro docente ativo.")
        if perfil in {"professor_disciplina", "coordenador"}:
            if user.docente.tipo_docente != "interno":
                raise click.ClickException("Esse perfil exige docente interno.")
            course = db.session.get(Curso, id_curso) if id_curso else None
            if not course or not course.ativo_curso:
                raise click.ClickException("Informe --id-curso de um curso ativo.")
            link = db.session.scalar(
                select(DocenteCurso).where(
                    DocenteCurso.id_docente == user.id_usuario,
                    DocenteCurso.id_curso == id_curso,
                    DocenteCurso.data_fim_docente_curso.is_(None),
                )
            )
            if not link and not revogar:
                link = DocenteCurso(
                    id_docente=user.id_usuario,
                    id_curso=id_curso,
                    data_inicio_docente_curso=(
                        utcnow().astimezone(app.config["ACADEMIC_TIMEZONE"]).date()
                    ),
                )
                db.session.add(link)
            if link and perfil == "coordenador":
                link.coordenador_docente_curso = not revogar
        seed_profiles()
        profile = db.session.scalar(select(Perfil).where(Perfil.codigo_perfil == perfil))
        association = db.session.get(UsuarioPerfil, (user.id_usuario, profile.id_perfil))
        old = bool(
            association
            and (
                not association.data_expiracao_usuario_perfil
                or association.data_expiracao_usuario_perfil > utcnow()
            )
        )
        if not association:
            if revogar:
                raise click.ClickException("Perfil não concedido a este usuário.")
            association = UsuarioPerfil(id_usuario=user.id_usuario, id_perfil=profile.id_perfil)
            db.session.add(association)
        if revogar:
            association.data_expiracao_usuario_perfil = utcnow()
        else:
            association.data_concessao_usuario_perfil = utcnow()
            association.data_expiracao_usuario_perfil = expiration
        audit(
            None,
            "revogacao_perfil_cli" if revogar else "concessao_perfil_cli",
            "usuario",
            user.id_usuario,
            {f"perfil_{perfil}": (old, not revogar)},
            reason=f"{justificativa.strip()} (curso={id_curso})",
        )
        db.session.commit()
        click.echo("Permissões atualizadas. Revogação do papel é global para o usuário.")

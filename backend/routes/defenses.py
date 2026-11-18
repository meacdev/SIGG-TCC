from flask import Blueprint, current_app, g
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend import validation as v
from backend.db import utcnow
from backend.defense_models import Banca, Membro
from backend.errors import APIError
from backend.routes.catalogs import page_response
from backend.security import authenticated
from backend.serialization import resource_response
from backend.services import defenses

bp = Blueprint("defenses", __name__, url_prefix="/api/v1/bancas")


@bp.get("")
@authenticated()
def list_defenses():
    now = utcnow()
    query = (
        select(Banca)
        .join(Membro)
        .where(
            Membro.id_docente == g.user.id_usuario,
            Membro.papel_membro_banca != "suplente",
            Membro.situacao_convite_membro_banca == "aceito",
            Membro.data_inicio_acesso_membro_banca <= now,
            Membro.data_fim_acesso_membro_banca >= now,
        )
        .order_by(Banca.data_inicio_banca.desc())
    )
    return page_response(query, lambda banca: defenses.defense_json(banca, False))


@bp.get("/<int:defense_id>")
@authenticated()
def detail(defense_id):
    banca = defenses.get_defense(defense_id)
    return resource_response(banca, defenses.defense_json(banca))


@bp.post("/<int:defense_id>/avaliacao")
@authenticated()
def evaluate(defense_id):
    data = v.body({"notas", "parecer"}, ("notas",), "UC_09_M02")
    try:
        banca = defenses.get_defense(defense_id, lock=True)
        individual = defenses.submit(banca, data)
        detail = defenses.defense_json(banca, calculated=individual)
    except SQLAlchemyError as error:
        current_app.logger.error("Falha ao confirmar avaliação: %s", type(error).__name__)
        raise APIError(
            503,
            "UC_09_M08",
            "Não foi possível confirmar a gravação. Atualize a ficha antes de tentar novamente.",
        ) from error
    return resource_response(banca, detail, 201, "UC_09_M01", "Avaliação registrada com sucesso!")


@bp.post("/<int:defense_id>/avaliacao/inicio")
@authenticated()
def start(defense_id):
    banca = defenses.get_defense(defense_id, lock=True)
    defenses.start(banca)
    return resource_response(banca, defenses.defense_json(banca))

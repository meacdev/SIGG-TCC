from flask import has_request_context, request

from backend.db import db
from backend.models import Auditoria, AuditoriaAlteracao


def audit(user_id, action, entity, record_id, changes=None, reason=None):
    event = Auditoria(
        id_usuario=user_id,
        acao_auditoria=action,
        entidade_auditoria=entity,
        id_registro_auditoria=record_id,
        justificativa_auditoria=reason,
        ip_origem_auditoria=request.remote_addr if has_request_context() else None,
    )
    db.session.add(event)
    db.session.flush()
    for field, (old, new) in (changes or {}).items():
        if old != new:
            db.session.add(
                AuditoriaAlteracao(
                    id_auditoria=event.id_auditoria,
                    nome_campo_auditoria_alteracao=field,
                    valor_anterior_auditoria_alteracao=None if old is None else str(old),
                    valor_novo_auditoria_alteracao=None if new is None else str(new),
                )
            )

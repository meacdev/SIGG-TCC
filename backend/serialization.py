import hashlib

from flask import jsonify, request

from backend.errors import APIError
from backend.security import roles


def iso(value):
    return value.isoformat().replace("+00:00", "Z") if value else None


def user_json(user):
    result = {
        "id_usuario": user.id_usuario,
        "nome_usuario": user.nome_usuario,
        "email_usuario": user.email_usuario,
        "ativo_usuario": user.ativo_usuario,
        "data_criacao_usuario": iso(user.data_criacao_usuario),
        "data_atualizacao_usuario": iso(user.data_atualizacao_usuario),
        "perfis": roles(user.id_usuario),
    }
    if user.docente:
        result["docente"] = {
            "tipo_docente": user.docente.tipo_docente,
            "titulacao_docente": user.docente.titulacao_docente,
            "url_lattes_docente": user.docente.url_lattes_docente,
            "instituicao_origem_docente": user.docente.instituicao_origem_docente,
            "areas_interesse": [area.nome_area_conhecimento for area in user.docente.areas],
        }
    if user.aluno:
        result["aluno"] = {
            "matricula_aluno": user.aluno.matricula_aluno,
            "id_curso": user.aluno.id_curso,
        }
    return result


def class_json(item):
    return {
        "id_turma": item.id_turma,
        "codigo_turma": item.codigo_turma,
        "nivel_turma": item.nivel_turma,
        "id_curso": item.id_curso,
        "id_docente_responsavel": item.id_docente_responsavel,
        "periodo_letivo": (
            f"{item.periodo.ano_periodo_letivo}/{item.periodo.semestre_periodo_letivo}"
        ),
        "id_periodo_letivo": item.id_periodo_letivo,
        "ativa_turma": item.ativa_turma,
        "autoinscricao_ativa_turma": item.autoinscricao_ativa_turma,
        "data_expiracao_acesso_turma": iso(item.data_expiracao_acesso_turma),
        "data_criacao_turma": iso(item.data_criacao_turma),
        "data_atualizacao_turma": iso(item.data_atualizacao_turma),
    }


def etag(item):
    if hasattr(item, "id_matricula_turma"):
        value = f"matricula:{item.id_matricula_turma}:{item.versao_matricula}"
    elif hasattr(item, "id_turma"):
        value = f"turma:{item.id_turma}:{iso(item.data_atualizacao_turma)}"
    else:
        value = f"usuario:{item.id_usuario}:{iso(item.data_atualizacao_usuario)}"
    return hashlib.sha256(value.encode()).hexdigest()


def check_version(item):
    if "If-Match" not in request.headers:
        raise APIError(428, "VERSAO_OBRIGATORIA", "Envie o ETag atual no cabeçalho If-Match.")
    if request.if_match.star_tag or not request.if_match.contains(etag(item)):
        raise APIError(412, "VERSAO_DESATUALIZADA", "O registro foi alterado. Recarregue os dados.")


def resource_response(item, data, status=200, code=None, message=None):
    result = {"data": data}
    if code:
        result.update(code=code, message=message)
    response = jsonify(result)
    response.status_code = status
    response.set_etag(etag(item))
    return response

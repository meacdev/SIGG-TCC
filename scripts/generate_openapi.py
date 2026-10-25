"""Regenerate the committed OpenAPI contract with Python's standard library."""

import json
from pathlib import Path

from openapi_academic import extend
from openapi_meetings import extend as extend_meetings
from openapi_works import extend as extend_works


def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def obj(properties, required=(), **extra):
    result = {"type": "object", "properties": properties, **extra}
    if required:
        result["required"] = list(required)
    return result


def string(**extra):
    return {"type": "string", **extra}


identifier = {"type": "integer", "format": "int64", "minimum": 1}
timestamp = string(format="date-time")
title = string(enum=["especialista", "mestre", "doutor"])
password = string(minLength=12, maxLength=128, writeOnly=True)
class_fields = {
    "periodo_letivo": string(pattern=r"^[0-9]{4}/[12]$", examples=["2026/2"]),
    "codigo_turma": string(pattern=r"^EST[A-Za-z]+[0-9]+$", maxLength=40),
    "nivel_turma": {"type": "integer", "enum": [1, 2]},
    "id_curso": identifier,
    "id_docente_responsavel": identifier,
}
profile_fields = {
    "nome_usuario": string(minLength=1, maxLength=200),
    "email_usuario": string(format="email", maxLength=254),
    "titulacao_docente": title,
    "url_lattes_docente": {"type": ["string", "null"], "format": "uri", "maxLength": 2048},
    "instituicao_origem_docente": {"type": ["string", "null"], "maxLength": 200},
    "areas_interesse": {"type": "array", "maxItems": 20, "items": string(maxLength=150)},
}
signup_fields = profile_fields | {
    "senha": password,
    "tipo_cadastro": string(enum=["docente", "aluno"], default="docente"),
    "tipo_docente": string(enum=["interno", "externo"], default="interno"),
    "matricula_aluno": string(minLength=1, maxLength=30),
    "id_curso": identifier,
}
schemas = {
    "Erro": obj(
        {
            "error": obj(
                {
                    "code": string(),
                    "message": string(),
                    "fields": {"type": "object", "additionalProperties": string()},
                },
                ("code", "message"),
            )
        },
        ("error",),
    ),
    "Cadastro": obj(
        signup_fields,
        ("nome_usuario", "email_usuario", "senha"),
        additionalProperties=False,
        description="Docente (padrão) exige titulacao_docente. Aluno exige tipo_cadastro=aluno, "
        "matricula_aluno e id_curso e rejeita campos docentes. Perfis administrativos "
        "são concedidos exclusivamente pela administração via CLI.",
        allOf=[
            {
                "if": {
                    "properties": {"tipo_cadastro": {"const": "aluno"}},
                    "required": ["tipo_cadastro"],
                },
                "then": {"required": ["matricula_aluno", "id_curso"]},
                "else": {"required": ["titulacao_docente"]},
            }
        ],
    ),
    "AtualizarCadastro": obj(
        profile_fields | {"senha_atual": string(writeOnly=True)},
        additionalProperties=False,
        description="Alterar e-mail exige senha_atual e revoga as sessões.",
    ),
    "Usuario": obj(
        {
            "id_usuario": identifier,
            "nome_usuario": string(),
            "email_usuario": string(format="email"),
            "ativo_usuario": {"type": "boolean"},
            "data_criacao_usuario": timestamp,
            "data_atualizacao_usuario": timestamp,
            "perfis": {
                "type": "array",
                "items": string(
                    enum=["aluno", "professor_disciplina", "orientador", "coordenador", "avaliador"]
                ),
            },
            "docente": obj(
                {
                    "tipo_docente": string(),
                    "titulacao_docente": title,
                    "url_lattes_docente": {"type": ["string", "null"]},
                    "instituicao_origem_docente": {"type": ["string", "null"]},
                    "areas_interesse": {"type": "array", "items": string()},
                }
            ),
            "aluno": obj({"matricula_aluno": string(), "id_curso": identifier}),
        },
        ("id_usuario", "nome_usuario", "email_usuario", "perfis"),
    ),
    "Login": obj(
        {"email_usuario": string(format="email"), "senha": string(writeOnly=True)},
        ("email_usuario", "senha"),
        additionalProperties=False,
    ),
    "Tokens": obj(
        {
            "access_token": string(),
            "refresh_token": string(),
            "token_type": string(const="Bearer"),
            "expires_in": {"type": "integer"},
            "usuario": ref("Usuario"),
        },
        ("access_token", "refresh_token", "token_type", "expires_in"),
    ),
    "CriarTurma": obj(class_fields, class_fields.keys(), additionalProperties=False),
    "AtualizarTurma": obj(
        class_fields
        | {"ativa_turma": {"type": "boolean"}, "autoinscricao_ativa_turma": {"type": "boolean"}},
        additionalProperties=False,
    ),
    "Turma": obj(
        class_fields
        | {
            "id_turma": identifier,
            "id_periodo_letivo": identifier,
            "ativa_turma": {"type": "boolean"},
            "autoinscricao_ativa_turma": {"type": "boolean"},
            "data_criacao_turma": timestamp,
            "data_atualizacao_turma": timestamp,
            "data_expiracao_acesso_turma": {"type": ["string", "null"], "format": "date-time"},
            "codigo_acesso": string(
                description="Somente na criação ou rotação. Copie neste momento."
            ),
        },
        (
            "id_turma",
            "codigo_turma",
            "nivel_turma",
            "id_curso",
            "id_docente_responsavel",
            "periodo_letivo",
            "ativa_turma",
        ),
    ),
    "Curso": obj({"id_curso": identifier, "codigo_curso": string(), "nome_curso": string()}),
    "Periodo": obj({"id_periodo_letivo": identifier, "periodo_letivo": string()}),
    "Docente": obj(
        {"id_docente": identifier, "nome_usuario": string(), "titulacao_docente": title}
    ),
    "Paginacao": obj(
        {
            "page": {"type": "integer"},
            "per_page": {"type": "integer"},
            "total": {"type": "integer"},
            "pages": {"type": "integer"},
        }
    ),
}
etag = {
    "name": "If-Match",
    "in": "header",
    "required": True,
    "schema": string(),
    "description": "ETag completo (com aspas) retornado pelo GET ou pela última alteração.",
}
class_id = {"name": "class_id", "in": "path", "required": True, "schema": identifier}
pagination = [
    {
        "name": "page",
        "in": "query",
        "schema": {"type": "integer", "minimum": 1, "maximum": 100000, "default": 1},
    },
    {
        "name": "per_page",
        "in": "query",
        "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
    },
]
paths = {}


def operation(
    path,
    method,
    summary,
    tag,
    output=None,
    input_schema=None,
    status=200,
    public=False,
    params=None,
    paginated=False,
    description="",
):
    response = {"description": "Operação concluída."}
    if output:
        output_schema = ref(output) if isinstance(output, str) else output
        result = obj({"data": output_schema, "code": string(), "message": string()}, ("data",))
        if paginated:
            result = obj(
                {"data": {"type": "array", "items": output_schema}, "meta": ref("Paginacao")},
                ("data", "meta"),
            )
        response["content"] = {"application/json": {"schema": result}}
    if tag in {"Cadastro", "Turmas"} and not paginated and status != 204:
        response["headers"] = {"ETag": {"schema": string(), "description": "Versão do recurso."}}
    responses = {str(status): response}
    for code in (400, 401, 403, 404, 409, 412, 413, 415, 422, 428, 429, 503):
        responses[str(code)] = {
            "description": "Erro de validação, acesso ou disponibilidade.",
            "content": {"application/json": {"schema": ref("Erro")}},
        }
    result = {
        "summary": summary,
        "operationId": summary.replace(" ", "_"),
        "tags": [tag],
        "security": [] if public else [{"bearerAuth": []}],
        "responses": responses,
    }
    if input_schema:
        result["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": ref(input_schema) if isinstance(input_schema, str) else input_schema
                }
            },
        }
    if params:
        result["parameters"] = params
    if description:
        result["description"] = description
    paths.setdefault(path, {})[method] = result


base = "/api/v1"
operation(
    base + "/usuarios", "post", "Cadastrar usuário", "Cadastro", "Usuario", "Cadastro", 201, True
)
operation(base + "/usuarios/me", "get", "Consultar meu cadastro", "Cadastro", "Usuario")
operation(
    base + "/usuarios/me",
    "patch",
    "Atualizar meu cadastro",
    "Cadastro",
    "Usuario",
    "AtualizarCadastro",
    params=[etag],
)
operation(
    base + "/usuarios/me",
    "delete",
    "Inativar meu cadastro",
    "Cadastro",
    status=204,
    input_schema=obj(
        {"senha_atual": string(writeOnly=True)}, ("senha_atual",), additionalProperties=False
    ),
    params=[etag],
)
operation(
    base + "/auth/login",
    "post",
    "Autenticar usuário",
    "Autenticação",
    "Tokens",
    "Login",
    public=True,
    description="Usuário inexistente: UC_13_CONTA_NAO_CADASTRADA. "
    "Permissões e rota do painel são interpretadas pelo frontend a partir de usuario.perfis.",
)
operation(
    base + "/auth/refresh",
    "post",
    "Renovar tokens",
    "Autenticação",
    "Tokens",
    description="Bearer deve conter o refresh_token. Rotaciona-o; descarte o anterior. "
    "Não renove em segundo plano sem atividade do usuário.",
)
operation(
    base + "/auth/logout",
    "delete",
    "Encerrar sessão",
    "Autenticação",
    status=204,
    description="Aceita access ou refresh token. Revoga ambos para a sessão atual.",
)
operation(
    base + "/auth/recuperacao-senha",
    "post",
    "Solicitar recuperação",
    "Autenticação",
    obj({"id_recuperacao": string(format="uuid")}),
    obj({"email_usuario": string(format="email")}, ("email_usuario",), additionalProperties=False),
    202,
    True,
)
operation(
    base + "/auth/recuperacao-senha/verificar",
    "post",
    "Verificar código",
    "Autenticação",
    obj({"token_redefinicao": string()}),
    obj(
        {"id_recuperacao": string(format="uuid"), "codigo": string(pattern="^[0-9]{10}$")},
        ("id_recuperacao", "codigo"),
        additionalProperties=False,
    ),
    public=True,
)
operation(
    base + "/auth/recuperacao-senha/redefinir",
    "post",
    "Redefinir senha",
    "Autenticação",
    input_schema=obj(
        {
            "id_recuperacao": string(format="uuid"),
            "token_redefinicao": string(),
            "nova_senha": password,
            "confirmacao_senha": password,
        },
        ("id_recuperacao", "token_redefinicao", "nova_senha", "confirmacao_senha"),
        additionalProperties=False,
    ),
    public=True,
)
operation(base + "/turmas", "post", "Cadastrar turma", "Turmas", "Turma", "CriarTurma", 201)
operation(
    base + "/turmas",
    "get",
    "Listar turmas",
    "Turmas",
    "Turma",
    paginated=True,
    params=pagination
    + [
        {"name": name, "in": "query", "schema": schema}
        for name, schema in {
            "id_curso": identifier,
            "periodo_letivo": class_fields["periodo_letivo"],
            "nivel_turma": class_fields["nivel_turma"],
            "ativa_turma": string(enum=["true", "false"]),
        }.items()
    ],
)
operation(
    base + "/turmas/{class_id}", "get", "Consultar turma", "Turmas", "Turma", params=[class_id]
)
operation(
    base + "/turmas/{class_id}",
    "patch",
    "Atualizar turma",
    "Turmas",
    "Turma",
    "AtualizarTurma",
    params=[class_id, etag],
)
operation(
    base + "/turmas/{class_id}",
    "delete",
    "Inativar turma",
    "Turmas",
    status=204,
    params=[class_id, etag],
)
operation(
    base + "/turmas/{class_id}/codigo-acesso",
    "post",
    "Rotacionar código da turma",
    "Turmas",
    "Turma",
    params=[class_id, etag],
)
for suffix, title_, schema in [
    ("cursos", "cursos", "Curso"),
    ("periodos-letivos", "períodos", "Periodo"),
    ("docentes", "docentes", "Docente"),
]:
    params = pagination.copy()
    if suffix == "docentes":
        params.append({"name": "id_curso", "in": "query", "required": True, "schema": identifier})
    operation(
        base + "/" + suffix,
        "get",
        "Consultar " + title_,
        "Catálogos",
        schema,
        public=suffix == "cursos",
        params=params,
        paginated=True,
    )
for suffix in ("live", "ready"):
    operation(base + "/health/" + suffix, "get", "Saúde " + suffix, "Operação", public=True)
    paths[base + "/health/" + suffix]["get"]["responses"]["200"]["content"] = {
        "application/json": {"schema": obj({"status": string(const="ok")}, ("status",))}
    }
operation(base + "/openapi.json", "get", "Consultar contrato OpenAPI", "Operação", public=True)

extend(paths, schemas, operation, obj, string, identifier)
extend_works(paths, schemas, operation, obj, string, identifier)
extend_meetings(paths, schemas, operation, obj, string, identifier)

document = {
    "openapi": "3.1.0",
    "info": {
        "title": "SIGG-TCC API",
        "version": "1.0.0",
        "description": "Primeira entrega: UC01, UC13 e UC02. "
        "Datas em UTC/ISO 8601; datas acadêmicas em Manaus. "
        "IDs correspondem às PKs do banco. Senhas, hashes e códigos não são expostos em consultas.",
    },
    "servers": [{"url": "/"}],
    "paths": paths,
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        },
        "schemas": schemas,
    },
}
destination = Path(__file__).resolve().parents[1] / "backend/static/openapi.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(destination)

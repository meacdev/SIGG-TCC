"""UC06 contract and the formal orientation prerequisite."""


def extend(paths, schemas, operation, obj, string, identifier):
    orientation = obj(
        {
            "id_orientacao": identifier,
            "id_docente": identifier,
            "nome": string(),
            "papel": string(enum=["orientador", "coorientador"]),
            "situacao": string(enum=["pendente", "aceito", "recusado"]),
            "data_resposta": {"type": ["string", "null"]},
        }
    )
    fields = {
        "titulo": string(maxLength=500),
        "subtitulo": string(maxLength=500),
        "tema": string(maxLength=5000),
        "modalidade": string(enum=["monografia", "artigo"]),
        "tipo_artigo": {"type": ["string", "null"], "enum": ["publicado", "a_submeter", None]},
        "url": {"type": ["string", "null"]},
        "doi": {"type": ["string", "null"]},
        "id_curso": identifier,
        "id_matricula": identifier,
        "id_orientador": identifier,
        "id_coorientador": {"type": ["integer", "null"]},
        "palavras_chave": {"type": "array", "items": string(maxLength=100), "maxItems": 10},
    }
    schemas["SalvarTrabalho"] = obj(
        fields,
        ("titulo", "tema", "modalidade", "id_curso", "id_matricula", "id_orientador"),
        additionalProperties=False,
    )
    schemas["Trabalho"] = obj(
        {
            **fields,
            "id_trabalho": identifier,
            "id_etapa": {"type": ["integer", "null"]},
            "nivel_turma": {"type": ["integer", "null"]},
            "codigo_turma": {"type": ["string", "null"]},
            "aluno": string(),
            "id_aluno": identifier,
            "versao": identifier,
            "data_criacao": string(format="date-time"),
            "situacao": string(),
            "orientacoes": {"type": "array", "items": orientation},
        }
    )
    prefix = "/api/v1"
    version = {
        "name": "If-Match",
        "in": "header",
        "schema": string(),
        "description": "Obrigatório ao atualizar trabalho existente ou responder ao vínculo.",
    }

    def param(name):
        return {"name": name, "in": "path", "required": True, "schema": identifier}

    pages = [
        {"name": "page", "in": "query", "schema": identifier},
        {
            "name": "per_page",
            "in": "query",
            "schema": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    ]
    operation(
        prefix + "/meu-trabalho",
        "get",
        "Consultar meu trabalho",
        "Trabalhos",
        {"anyOf": [{"$ref": "#/components/schemas/Trabalho"}, {"type": "null"}]},
    )
    operation(
        prefix + "/meu-trabalho",
        "put",
        "Registrar ou atualizar meu trabalho",
        "Trabalhos",
        "Trabalho",
        "SalvarTrabalho",
        params=[version],
        description="201 na criação; 200 na atualização. Curso e nível vêm da matrícula ativa. "
        "Orientações são pendentes até resposta do docente; troca exige RF05.",
    )
    paths[prefix + "/meu-trabalho"]["put"]["responses"]["201"] = paths[prefix + "/meu-trabalho"][
        "put"
    ]["responses"]["200"]
    operation(
        prefix + "/docentes-orientacao",
        "get",
        "Consultar docentes ativos para orientação",
        "Trabalhos",
        obj({"id_docente": identifier, "nome": string(), "titulacao": string()}),
        params=pages,
        paginated=True,
    )
    operation(
        prefix + "/orientacoes",
        "get",
        "Listar trabalhos indicados ao docente",
        "Trabalhos",
        "Trabalho",
        params=pages,
        paginated=True,
    )
    operation(
        prefix + "/orientacoes/{work_id}",
        "get",
        "Consultar trabalho de orientação",
        "Trabalhos",
        "Trabalho",
        params=[param("work_id")],
    )
    operation(
        prefix + "/orientacoes/{orientation_id}/resposta",
        "post",
        "Responder vínculo de orientação",
        "Trabalhos",
        "Trabalho",
        obj(
            {"decisao": string(enum=["aceito", "recusado"])},
            ("decisao",),
            additionalProperties=False,
        ),
        params=[param("orientation_id"), {**version, "required": True}],
    )
    for path, method in [
        ("/meu-trabalho", "get"),
        ("/meu-trabalho", "put"),
        ("/orientacoes/{work_id}", "get"),
        ("/orientacoes/{orientation_id}/resposta", "post"),
    ]:
        paths[prefix + path][method]["responses"]["200"]["headers"] = {"ETag": {"schema": string()}}

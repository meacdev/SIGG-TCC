"""Defense API additions to the versioned OpenAPI generator."""


def extend(paths, schemas, operation, obj, string, identifier):
    schemas["CriterioDefesa"] = obj(
        {
            "id_criterio": identifier,
            "nome": string(),
            "descricao": string(),
            "peso": string(),
            "pontuacao_maxima": string(),
        },
        ("id_criterio", "nome", "descricao", "peso", "pontuacao_maxima"),
    )
    schemas["NotaDefesa"] = obj(
        {"id_criterio": identifier, "nota": string()},
        ("id_criterio", "nota"),
        additionalProperties=False,
    )
    schemas["AvaliacaoDefesa"] = obj(
        {
            "id_avaliacao": identifier,
            "data_envio": string(format="date-time"),
            "nota_individual": string(),
            "notas": {"type": "array", "items": {"$ref": "#/components/schemas/NotaDefesa"}},
        }
    )
    schemas["Defesa"] = obj(
        {
            "id_banca": identifier,
            "aluno": string(),
            "titulo": string(),
            "curso": string(),
            "data_inicio": string(format="date-time"),
            "data_fim": string(format="date-time"),
            "local": string(),
            "situacao": string(),
            "resultado": {"type": ["string", "null"]},
            "pode_avaliar": {"type": "boolean"},
            "avaliador": string(),
            "criterios": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/CriterioDefesa"},
            },
            "avaliacao": {
                "anyOf": [{"$ref": "#/components/schemas/AvaliacaoDefesa"}, {"type": "null"}]
            },
            "avaliacoes_enviadas": {"type": "integer"},
            "total_avaliadores": {"type": "integer"},
            "media_final": {"type": ["string", "null"]},
            "avaliadores": {
                "type": "array",
                "items": obj(
                    {
                        "nome": string(),
                        "enviada": {"type": "boolean"},
                        "nota_individual": {"type": ["string", "null"]},
                    }
                ),
            },
        }
    )
    schemas["EnviarAvaliacao"] = obj(
        {
            "notas": {
                "type": "array",
                "minItems": 1,
                "items": {"$ref": "#/components/schemas/NotaDefesa"},
            }
        },
        ("notas",),
        additionalProperties=False,
    )
    identifier_param = {"name": "defense_id", "in": "path", "required": True, "schema": identifier}
    version_param = {"name": "If-Match", "in": "header", "required": True, "schema": string()}
    operation(
        "/api/v1/bancas",
        "get",
        "Listar minhas bancas",
        "Bancas",
        "Defesa",
        paginated=True,
        params=[
            {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1}},
            {
                "name": "per_page",
                "in": "query",
                "schema": {"type": "integer", "minimum": 1, "maximum": 100},
            },
        ],
    )
    operation(
        "/api/v1/bancas/{defense_id}",
        "get",
        "Consultar ficha de defesa",
        "Bancas",
        "Defesa",
        params=[identifier_param],
    )
    operation(
        "/api/v1/bancas/{defense_id}/avaliacao",
        "post",
        "Enviar avaliação definitiva",
        "Bancas",
        "Defesa",
        "EnviarAvaliacao",
        201,
        params=[identifier_param, version_param],
        description=(
            "Restrito ao examinador com participação aceita e acesso vigente, no dia da defesa "
            "em America/Manaus. Nota individual: 10 × soma(nota / máximo × peso) / soma(pesos). "
            "Média final sem arredondamento intermediário; exibição com duas casas e ROUND_HALF_UP."
        ),
    )
    for path in ("/api/v1/bancas/{defense_id}", "/api/v1/bancas/{defense_id}/avaliacao"):
        for operation_ in paths[path].values():
            for status in ("200", "201"):
                if status in operation_["responses"]:
                    operation_["responses"][status]["headers"] = {"ETag": {"schema": string()}}

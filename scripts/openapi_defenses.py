"""Defense API additions to the versioned OpenAPI generator."""


def extend(paths, schemas, operation, obj, string, identifier):
    schemas["CriterioDefesa"] = obj(
        {
            "id_criterio": identifier,
            "nome": string(),
            "componente": {
                "type": ["string", "null"],
                "enum": ["parte_escrita", "parte_oral", None],
            },
            "descricao": string(),
            "descritores": {
                "anyOf": [
                    obj(
                        {
                            "exemplar": string(),
                            "competente": string(),
                            "necessita_trabalho": string(),
                        }
                    ),
                    {"type": "null"},
                ]
            },
            "peso": string(),
            "pontuacao_maxima": string(),
        },
        ("id_criterio", "nome", "descricao", "peso", "pontuacao_maxima"),
    )
    concept = string(enum=["exemplar", "competente", "necessita_trabalho"])
    schemas["NotaDefesa"] = obj(
        {"id_criterio": identifier, "conceito": concept, "nota": string()},
        ("id_criterio", "conceito", "nota"),
        additionalProperties=False,
    )
    schemas["NotaRegistrada"] = obj(
        {
            "id_criterio": identifier,
            "conceito": {"type": ["string", "null"]},
            "nota": string(),
            "nota_ponderada": string(),
        }
    )
    schemas["AvaliacaoDefesa"] = obj(
        {
            "id_avaliacao": identifier,
            "data_envio": string(format="date-time"),
            "nota_individual": string(),
            "subtotais": {"type": "object", "additionalProperties": string()},
            "parecer": {"type": ["string", "null"], "maxLength": 4000},
            "notas": {"type": "array", "items": {"$ref": "#/components/schemas/NotaRegistrada"}},
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
            "avaliacao_iniciada": {"type": "boolean"},
            "avaliador": string(),
            "nivel": {"type": "integer"},
            "tempo_apresentacao": {"type": ["integer", "null"]},
            "aprovacao_minima": string(),
            "conceitos": {
                "type": "array",
                "items": obj(
                    {"chave": string(), "nome": string(), "minimo": string(), "maximo": string()}
                ),
            },
            "componentes": {
                "type": "array",
                "items": obj({"chave": string(), "nome": string(), "pontos": string()}),
            },
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
                        "papel": string(enum=["presidente", "examinador"]),
                        "enviada": {"type": "boolean"},
                        "nota_individual": {"type": ["string", "null"]},
                    }
                ),
            },
        }
    )
    schemas["EnviarAvaliacao"] = obj(
        {
            "parecer": string(maxLength=4000),
            "notas": {
                "type": "array",
                "minItems": 1,
                "items": {"$ref": "#/components/schemas/NotaDefesa"},
            },
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
            "em America/Manaus. Cada critério exige o conceito marcado e uma nota dentro da "
            "faixa (Exemplar 8,0-10,0; Competente 6,0-7,9; Necessita de Trabalho 0,0-5,9), "
            "senão UC_09_M09. Nota ponderada = nota × peso / 10; nota individual = soma. "
            "Média final sem arredondamento intermediário; exibição com duas casas e ROUND_HALF_UP."
        ),
    )
    submit_path = "/api/v1/bancas/{defense_id}/avaliacao"
    operation(
        submit_path + "/inicio",
        "post",
        "Iniciar ficha de avaliação",
        "Bancas",
        "Defesa",
        params=[identifier_param, version_param],
        description="Cria o rascunho e bloqueia a edição dos critérios da rubrica.",
    )
    for path in ("/api/v1/bancas/{defense_id}", submit_path, submit_path + "/inicio"):
        for operation_ in paths[path].values():
            for status in ("200", "201"):
                if status in operation_["responses"]:
                    operation_["responses"][status]["headers"] = {"ETag": {"schema": string()}}

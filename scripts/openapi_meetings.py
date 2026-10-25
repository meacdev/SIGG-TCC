"""UC05 immutable meeting records and scoped attendance."""


def extend(paths, schemas, operation, obj, string, identifier):
    schemas["EtapaReuniao"] = obj(
        {
            "id_etapa": identifier,
            "id_trabalho": identifier,
            "titulo": string(),
            "aluno": string(),
            "codigo_turma": string(),
            "nivel_turma": {"type": "integer"},
            "pode_registrar": {"type": "boolean"},
        }
    )
    schemas["AtaReuniao"] = obj(
        {
            "id_reuniao": identifier,
            "id_etapa": identifier,
            "data_encontro": string(),
            "resumo": string(),
            "orientador": string(),
            "autor": string(),
            "data_registro": string(format="date-time"),
        }
    )
    schemas["Assiduidade"] = obj(
        {
            "id_matricula": identifier,
            "id_etapa": {"type": ["integer", "null"]},
            "aluno": string(),
            "matricula": string(),
            "codigo_turma": string(),
            "titulo": {"type": ["string", "null"]},
            "quantidade_reunioes": {"type": "integer"},
            "ultimo_encontro": {"type": ["string", "null"]},
            "dias_sem_reuniao": {"type": "integer"},
            "alerta_inatividade": {"type": "boolean"},
        }
    )
    pages = [
        {"name": "page", "in": "query", "schema": identifier},
        {
            "name": "per_page",
            "in": "query",
            "schema": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    ]
    stage = {"name": "stage_id", "in": "path", "required": True, "schema": identifier}
    operation(
        "/api/v1/trabalhos-reunioes",
        "get",
        "Listar etapas autorizadas para reuniões",
        "Reuniões",
        "EtapaReuniao",
        params=pages,
        paginated=True,
    )
    operation(
        "/api/v1/etapas/{stage_id}/reunioes",
        "get",
        "Consultar histórico de reuniões",
        "Reuniões",
        "AtaReuniao",
        params=[stage, *pages],
        paginated=True,
    )
    operation(
        "/api/v1/etapas/{stage_id}/reunioes",
        "post",
        "Registrar ata de reunião",
        "Reuniões",
        "AtaReuniao",
        obj(
            {
                "data_encontro": string(pattern=r"^\d{2}/\d{2}/\d{4}$"),
                "resumo": string(minLength=1, maxLength=10000),
            },
            ("data_encontro", "resumo"),
            additionalProperties=False,
        ),
        201,
        params=[stage],
        description="Data DD/MM/AAAA até hoje. Exige matrícula ativa e orientação aceita. "
        "Sem edição ou exclusão. Notificações persistidas para estudante e orientador.",
    )
    operation(
        "/api/v1/acompanhamento-reunioes",
        "get",
        "Consultar assiduidade das minhas turmas",
        "Reuniões",
        "Assiduidade",
        params=pages,
        paginated=True,
    )

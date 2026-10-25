"""UC13 monitoring matrix, history and confirmed notification batches."""


def extend(paths, schemas, operation, obj, string, identifier):
    day = {"type": ["string", "null"], "format": "date"}
    schemas["AlunoMonitoramento"] = obj(
        {
            "id_matricula": identifier,
            "nome": string(),
            "matricula": string(),
            "id_etapa": {"type": ["integer", "null"]},
            "total_atas": {"type": "integer"},
            "ultima_reuniao": day,
            "ultima_entrega": day,
            "ultima_atividade": string(format="date"),
            "dias_inatividade": {"type": "integer", "minimum": 0},
            "inativo": {"type": "boolean"},
        }
    )
    schemas["SelecaoCobranca"] = obj(
        {
            "ids_matriculas": {
                "type": "array",
                "items": identifier,
                "maxItems": 1000,
                "uniqueItems": True,
            },
            "todos_inativos": {"type": "boolean", "default": False},
            "ids_excluidas": {
                "type": "array",
                "items": identifier,
                "maxItems": 1000,
                "uniqueItems": True,
            },
        },
        additionalProperties=False,
        description="Seleção explícita ou todos os inativos, "
        "incluindo páginas não exibidas, com exclusões opcionais.",
    )
    schemas["PreviaCobranca"] = obj(
        {
            "id_lote": string(format="uuid"),
            "quantidade": {"type": "integer"},
            "mensagem": string(),
            "expira_em": string(format="date-time"),
        }
    )
    schemas["ResultadoCobranca"] = obj(
        {
            "id_lote": string(format="uuid"),
            **{
                name: {"type": "integer"}
                for name in ("total", "enviados", "pendentes", "cancelados")
            },
        }
    )
    prefix = "/api/v1/turmas/{class_id}/monitoramento"

    def param(name, schema=identifier):
        return {"name": name, "in": "path", "required": True, "schema": schema}

    pages = [
        {"name": "page", "in": "query", "schema": identifier},
        {
            "name": "per_page",
            "in": "query",
            "schema": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    ]
    operation(
        prefix,
        "get",
        "Monitorar atividade da turma",
        "Monitoramento",
        params=[
            param("class_id"),
            *pages,
            {"name": "status", "in": "query", "schema": string(enum=["todos", "inativos"])},
        ],
    )
    paths[prefix]["get"]["responses"]["200"]["content"] = {
        "application/json": {
            "schema": obj(
                {
                    "data": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/AlunoMonitoramento"},
                    },
                    "meta": obj(
                        {
                            key: {"type": "integer"}
                            for key in [
                                "page",
                                "pages",
                                "per_page",
                                "total",
                                "total_turma",
                                "total_inativos",
                            ]
                        }
                    ),
                    "mensagem_padrao": string(),
                    "code": string(),
                    "message": string(),
                }
            )
        }
    }
    operation(
        prefix + "/{enrollment_id}/atas",
        "get",
        "Consultar atas do estudante na turma",
        "Monitoramento",
        "AtaReuniao",
        params=[param("class_id"), param("enrollment_id"), *pages],
        paginated=True,
    )
    operation(
        prefix + "/previa",
        "post",
        "Preparar confirmação da cobrança",
        "Monitoramento",
        "PreviaCobranca",
        "SelecaoCobranca",
        201,
        params=[param("class_id")],
        description="Não envia e-mail. Cria confirmação restrita ao ator e turma, "
        "válida por dez minutos.",
    )
    operation(
        prefix + "/lotes/{batch_id}/confirmar",
        "post",
        "Confirmar ou repetir pendentes da cobrança",
        "Monitoramento",
        "ResultadoCobranca",
        obj({}, additionalProperties=False),
        params=[param("class_id"), param("batch_id", string(format="uuid"))],
        description="Revalida turma e inatividade; persiste notificações e auditoria "
        "antes do SMTP. "
        "Repetir o mesmo lote não duplica notificações nem reenvia as já entregues. "
        "HTTP 200 com UC_13_M05 indica pendências persistidas, nunca sucesso de entrega total.",
    )

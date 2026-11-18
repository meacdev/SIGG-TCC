"""OpenAPI operations for UC07 and UC08."""


def extend(paths, schemas, operation, obj, string, identifier):
    def ref(name):
        return {"$ref": f"#/components/schemas/{name}"}

    def array(item):
        return {"type": "array", "items": item}

    def param(name):
        return {"name": name, "in": "path", "required": True, "schema": identifier}

    criterion = obj(
        {
            "nome": string(maxLength=150),
            "descricao": string(maxLength=4000),
            "peso": {"type": ["string", "number"]},
        },
        ("nome", "descricao", "peso"),
    )
    rubric = {
        "nome": string(maxLength=150),
        "situacao": string(enum=["rascunho", "ativa", "inativa"]),
        "criterios": array(criterion),
    }
    schemas["RubricaEntrada"] = obj(rubric, tuple(rubric))
    schemas["RubricaGestao"] = obj(rubric | {"id": identifier, "bloqueada": {"type": "boolean"}})
    booking = {
        "etapa": identifier,
        "rubrica": identifier,
        "inicio": string(format="date-time"),
        "fim": string(format="date-time"),
        "local": string(),
        "url": string(),
        "modalidade": string(enum=["presencial", "remota", "hibrida"]),
        "titulares": array(identifier),
        "suplentes": array(identifier),
    }
    schemas["BancaEntrada"] = obj(
        booking, tuple(key for key in booking if key not in {"local", "url"})
    )
    schemas["Agendamento"] = obj(
        {
            **{k: v for k, v in booking.items() if k not in {"titulares", "suplentes", "url"}},
            "id": identifier,
            "url": {"type": ["string", "null"]},
            "situacao": string(),
            "membros": array(obj({"id": identifier, "papel": string(), "nome": string()})),
        }
    )
    prefix = "/api/v1/turmas/{class_id}"
    scoped = [param("class_id")]
    item = [*scoped, param("identifier")]
    tag = "Organização de defesas"
    operation(
        prefix + "/rubricas",
        "get",
        "Consultar rubricas da turma",
        tag,
        array(ref("RubricaGestao")),
        params=scoped,
    )
    operation(
        prefix + "/rubricas",
        "post",
        "Criar rubrica",
        tag,
        "RubricaGestao",
        "RubricaEntrada",
        201,
        params=scoped,
    )
    operation(
        prefix + "/rubricas/{identifier}",
        "patch",
        "Atualizar rubrica",
        tag,
        "RubricaGestao",
        "RubricaEntrada",
        params=item,
    )
    operation(
        prefix + "/bancas",
        "get",
        "Consultar agenda da turma",
        tag,
        obj(
            {
                "trabalhos": array(
                    obj(
                        {
                            "id": identifier,
                            "titulo": string(),
                            "orientador": {"type": ["integer", "null"]},
                            "manuscrito": {"type": "boolean"},
                        }
                    )
                ),
                "bancas": array(ref("Agendamento")),
            }
        ),
        params=scoped,
    )
    operation(
        prefix + "/bancas",
        "post",
        "Agendar banca",
        tag,
        "Agendamento",
        "BancaEntrada",
        201,
        params=scoped,
    )
    operation(
        prefix + "/bancas/{identifier}",
        "patch",
        "Reagendar banca",
        tag,
        "Agendamento",
        "BancaEntrada",
        params=item,
    )
    operation(
        prefix + "/avaliadores",
        "get",
        "Buscar avaliadores",
        tag,
        array(
            obj(
                {
                    "id": identifier,
                    "nome": string(),
                    "tipo": string(),
                    "titulacao": string(),
                    "instituicao": {"type": ["string", "null"]},
                }
            )
        ),
        params=[*scoped, {"name": "q", "in": "query", "schema": string()}],
    )
    upload = "/api/v1/etapas/{stage_id}/manuscritos"
    operation(
        upload,
        "post",
        "Enviar manuscrito de TCC",
        tag,
        obj({"versao": identifier}),
        status=201,
        params=[param("stage_id")],
    )
    paths[upload]["post"]["requestBody"] = {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": obj({"arquivo": string(format="binary")}, ("arquivo",))
            }
        },
    }
    download = "/api/v1/bancas/{identifier}/manuscrito"
    operation(download, "get", "Baixar manuscrito de TCC", tag, params=[param("identifier")])
    paths[download]["get"]["responses"]["200"]["content"] = {
        "application/pdf": {"schema": string(format="binary")}
    }

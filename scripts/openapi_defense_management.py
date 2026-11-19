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
    boolean = {"type": "boolean"}
    schemas["RubricaEntrada"] = obj(rubric | {"substituir": identifier}, tuple(rubric))
    schemas["RubricaGestao"] = obj(
        rubric | {"id": identifier, "versao": identifier, "bloqueada": boolean}
    )
    schemas["RubricaAnterior"] = obj(
        {"id": identifier, "nome": string(), "versao": identifier, "periodo": string()}
    )
    schemas["ImportacaoRubrica"] = obj({"origem": identifier}, ("origem",))
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
            "titulo": string(),
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
        prefix + "/rubricas/anteriores",
        "get",
        "Consultar rubricas anteriores do curso",
        tag,
        array(ref("RubricaAnterior")),
        params=scoped,
    )
    operation(
        prefix + "/rubricas/importacoes",
        "post",
        "Importar rubrica como rascunho",
        tag,
        "RubricaGestao",
        "ImportacaoRubrica",
        201,
        params=scoped,
    )
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
                            "orientador": identifier,
                            "nome_orientador": string(),
                            "estudante": string(),
                            "nivel": identifier,
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
        "get",
        "Consultar banca para reagendamento",
        tag,
        "Agendamento",
        params=item,
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
    schemas["AvaliadorGestao"] = obj(
        {
            "id": identifier,
            "nome": string(),
            "tipo": string(),
            "titulacao": string(),
            "instituicao": {"type": ["string", "null"]},
        }
    )
    external = {
        "nome": string(maxLength=100),
        "email": string(format="email", maxLength=254),
        "titulacao": string(enum=["Especialista", "Mestre", "Doutor"]),
        "instituicao": string(maxLength=200),
    }
    schemas["AvaliadorExternoEntrada"] = obj(external, tuple(external))
    operation(
        prefix + "/avaliadores/externos",
        "post",
        "Cadastrar avaliador externo para a banca",
        tag,
        "AvaliadorGestao",
        "AvaliadorExternoEntrada",
        201,
        params=scoped,
    )
    operation(
        prefix + "/avaliadores",
        "get",
        "Buscar avaliadores",
        tag,
        array(ref("AvaliadorGestao")),
        params=[*scoped, {"name": "q", "in": "query", "schema": string()}],
    )
    operation(
        prefix + "/bancas/disponibilidade",
        "post",
        "Consultar disponibilidade da banca",
        tag,
        obj({"disponivel": boolean, "conflitos": array(identifier)}),
        obj(
            {
                "etapa": identifier,
                "banca": identifier,
                "inicio": string(format="date-time"),
                "fim": string(format="date-time"),
                "membros": array(identifier),
            },
            ("etapa", "inicio", "fim", "membros"),
        ),
        params=scoped,
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
    preview = prefix + "/etapas/{stage_id}/manuscrito"
    operation(
        preview,
        "get",
        "Consultar manuscrito antes de agendar",
        tag,
        params=[*scoped, param("stage_id")],
    )
    paths[preview]["get"]["responses"]["200"]["content"] = paths[download]["get"]["responses"][
        "200"
    ]["content"]

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

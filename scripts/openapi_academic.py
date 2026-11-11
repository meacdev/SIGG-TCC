"""Academic workflow OpenAPI additions, composed without importing Flask."""


def extend(paths, schemas, operation, obj, string, identifier):
    enrollment = obj(
        {
            "id_matricula": identifier,
            "id_turma": identifier,
            "id_aluno": identifier,
            "nome": string(),
            "matricula": string(),
            "situacao": string(),
            "codigo_turma": string(),
            "periodo_letivo": string(),
            "nivel_turma": {"type": "integer", "enum": [1, 2]},
            "id_curso": identifier,
            "turma_ativa": {"type": "boolean"},
            "data_matricula": string(format="date-time"),
            "versao": identifier,
            "notificacao": string(),
        }
    )
    schemas["Matricula"] = enrollment

    def path(name):
        return {"name": name, "in": "path", "required": True, "schema": identifier}

    pages = [
        {"name": "page", "in": "query", "schema": identifier},
        {
            "name": "per_page",
            "in": "query",
            "schema": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    ]
    version = {"name": "If-Match", "in": "header", "required": True, "schema": string()}
    prefix = "/api/v1"
    operation(
        prefix + "/turmas/{class_id}/estudantes",
        "get",
        "Buscar estudantes do curso",
        "Matrículas",
        obj({"id_aluno": identifier, "nome": string(), "matricula": string()}),
        params=[
            path("class_id"),
            *pages,
            {
                "name": "q",
                "in": "query",
                "required": True,
                "schema": string(minLength=2, maxLength=100),
            },
        ],
        paginated=True,
    )
    operation(
        prefix + "/turmas/{class_id}/matriculas",
        "get",
        "Listar matrículas da turma",
        "Matrículas",
        "Matricula",
        params=[path("class_id"), *pages],
        paginated=True,
    )
    operation(
        prefix + "/turmas/{class_id}/matriculas",
        "post",
        "Matricular estudante",
        "Matrículas",
        "Matricula",
        obj({"id_aluno": identifier}, ("id_aluno",), additionalProperties=False),
        201,
        params=[path("class_id")],
    )
    operation(
        prefix + "/turmas/{class_id}/matriculas/{enrollment_id}",
        "delete",
        "Remover matrícula",
        "Matrículas",
        "Matricula",
        obj(
            {"confirmacao": string(), "motivo": string(maxLength=2000)},
            ("confirmacao", "motivo"),
            additionalProperties=False,
        ),
        params=[path("class_id"), path("enrollment_id"), version],
        description="Preserva histórico; confirmação nome/turma, motivo e ETag obrigatórios. "
        "Notificação persistente por e-mail.",
    )
    operation(
        prefix + "/matriculas/{enrollment_id}",
        "get",
        "Consultar matrícula autorizada",
        "Matrículas",
        "Matricula",
        params=[path("enrollment_id")],
    )
    operation(
        prefix + "/minhas-matriculas",
        "get",
        "Listar minhas matrículas",
        "Matrículas",
        "Matricula",
        params=pages,
        paginated=True,
    )
    operation(
        prefix + "/matriculas/autoinscricao",
        "post",
        "Entrar por código de acesso",
        "Matrículas",
        "Matricula",
        obj(
            {"codigo_acesso": string(minLength=24, maxLength=24)},
            ("codigo_acesso",),
            additionalProperties=False,
        ),
        201,
    )
    for route, method, status in [
        ("/matriculas/{enrollment_id}", "get", "200"),
        ("/turmas/{class_id}/matriculas", "post", "201"),
        ("/turmas/{class_id}/matriculas/{enrollment_id}", "delete", "200"),
        ("/matriculas/autoinscricao", "post", "201"),
    ]:
        paths[prefix + route][method]["responses"][status]["headers"] = {
            "ETag": {"schema": string()}
        }

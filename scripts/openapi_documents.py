"""Official defense-document API additions."""


def extend(paths, schemas, operation, obj, string, identifier):
    nullable = {"type": ["string", "null"]}
    boolean = {"type": "boolean"}
    schemas["DocumentosDefesa"] = obj(
        {
            "ata": {
                "anyOf": [
                    obj(
                        {
                            "id_documento": identifier,
                            "versao": {"type": "integer"},
                            "codigo_verificacao": string(),
                            "data_emissao": string(format="date-time"),
                            "assinada": boolean,
                            "liberada_aluno": boolean,
                        }
                    ),
                    {"type": "null"},
                ]
            },
            "resultado": nullable,
            "prazo": nullable,
            "correcoes": nullable,
            "declaracoes": {
                "type": "array",
                "items": obj({"id_documento": identifier, "codigo_verificacao": string()}),
            },
            "emails": {
                "type": "array",
                "items": obj(
                    {
                        "id_notificacao": identifier,
                        "situacao": string(),
                        "tentativas": {"type": "integer"},
                    }
                ),
            },
        }
    )
    schemas["EmitirAta"] = obj(
        {
            "resultado": string(enum=["aprovado", "reprovado", "aprovado_com_correcoes"]),
            "prazo": nullable,
            "correcoes": string(maxLength=10000),
            "justificativa": string(maxLength=2000),
        },
        ("resultado",),
        additionalProperties=False,
        description=(
            "Correções exigem prazo e descrição. Reemissão exige justificativa "
            "e é bloqueada após arquivo assinado ou submissão de correções."
        ),
    )
    schemas["AtaAluno"] = obj(
        {
            "id_banca": identifier,
            "titulo": string(),
            "resultado": nullable,
            "assinada": boolean,
            "liberada": boolean,
        }
    )
    schemas["VerificacaoDocumento"] = obj(
        {
            "vigente": boolean,
            "tipo": string(),
            "data_emissao": string(format="date-time"),
            "sha256": string(),
            "sha256_assinado": nullable,
        }
    )
    bank = {"name": "defense_id", "in": "path", "required": True, "schema": identifier}
    doc = {"name": "document_id", "in": "path", "required": True, "schema": identifier}
    version = {"name": "If-Match", "in": "header", "required": True, "schema": string()}
    prefix = "/api/v1/bancas/{defense_id}"
    operation(
        prefix + "/documentos",
        "get",
        "Consultar documentos da banca",
        "Documentos",
        "DocumentosDefesa",
        params=[bank],
    )
    operation(
        prefix + "/ata",
        "post",
        "Emitir ou reemitir ata",
        "Documentos",
        "DocumentosDefesa",
        "EmitirAta",
        201,
        params=[bank, version],
    )
    operation(
        prefix + "/ata",
        "get",
        "Baixar ata",
        "Documentos",
        params=[
            bank,
            {"name": "assinada", "in": "query", "schema": string(enum=["true", "false"])},
        ],
    )
    operation(
        prefix + "/ata/assinada",
        "post",
        "Registrar arquivo assinado conferido",
        "Documentos",
        "DocumentosDefesa",
        params=[bank, version],
        description=(
            "Upload privado de PDF de até 50 MB. O responsável atesta a conferência "
            "das assinaturas; o sistema não realiza certificação ICP-Brasil."
        ),
    )
    paths[prefix + "/ata/assinada"]["post"]["requestBody"] = {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": obj(
                    {
                        "arquivo": string(format="binary"),
                        "assinaturas_conferidas": string(enum=["true"]),
                    },
                    ("arquivo", "assinaturas_conferidas"),
                    additionalProperties=False,
                )
            }
        },
    }
    operation(
        prefix + "/declaracoes/{document_id}",
        "get",
        "Baixar declaração de participação",
        "Documentos",
        params=[bank, doc],
    )
    operation(
        prefix + "/declaracoes/reenvio",
        "post",
        "Repetir envio das declarações pendentes",
        "Documentos",
        "DocumentosDefesa",
        params=[bank],
    )
    operation(
        "/api/v1/minhas-atas",
        "get",
        "Consultar minhas atas",
        "Documentos",
        {"type": "array", "items": {"$ref": "#/components/schemas/AtaAluno"}},
    )
    operation(
        "/api/v1/documentos/verificar",
        "get",
        "Verificar registro do documento",
        "Documentos",
        "VerificacaoDocumento",
        public=True,
        params=[
            {"name": "codigo", "in": "query", "required": True, "schema": string(maxLength=100)}
        ],
    )
    for path in (prefix + "/ata", prefix + "/declaracoes/{document_id}"):
        paths[path]["get"]["responses"]["200"]["content"] = {
            "application/pdf": {"schema": string(format="binary")}
        }
    for path in (
        prefix + "/ata",
        prefix + "/ata/assinada",
        prefix + "/documentos",
        prefix + "/declaracoes/reenvio",
    ):
        for entry in paths[path].values():
            if (
                "application/json" in entry["responses"].get("200", {}).get("content", {})
                or "201" in entry["responses"]
            ):
                status = "201" if "201" in entry["responses"] else "200"
                entry["responses"][status]["headers"] = {"ETag": {"schema": string()}}

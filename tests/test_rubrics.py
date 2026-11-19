def test_import_and_atomic_replacement(client, teacher, created_class, class_payload):
    headers = teacher["headers"]
    current = created_class.json["data"]["id_turma"]
    past = client.post(
        "/api/v1/turmas", headers=headers, json={**class_payload, "periodo_letivo": "2026/1"}
    )
    assert past.status_code == 201, past.json
    previous = past.json["data"]["id_turma"]
    prefix = f"/api/v1/turmas/{current}/rubricas"
    payload = {
        "nome": "Critérios da banca",
        "situacao": "ativa",
        "criterios": [{"nome": "Método", "descricao": "Justifica a escolha.", "peso": "100"}],
    }
    origin = client.post(f"/api/v1/turmas/{previous}/rubricas", headers=headers, json=payload)
    existing = client.post(prefix, headers=headers, json=payload)
    assert origin.status_code == existing.status_code == 201
    existing_id = existing.json["data"]["id"]
    origin_id = origin.json["data"]["id"]
    prior = client.get(f"{prefix}/anteriores", headers=headers)
    assert [item["id"] for item in prior.json["data"]] == [origin_id]
    assert (
        client.post(
            f"{prefix}/importacoes", headers=headers, json={"origem": existing_id}
        ).status_code
        == 404
    )
    imported = client.post(f"{prefix}/importacoes", headers=headers, json={"origem": origin_id})
    assert imported.status_code == 201, imported.json
    draft = imported.json["data"]
    assert draft["situacao"] == "rascunho"
    assert draft["versao"] == 2
    assert draft["criterios"] == origin.json["data"]["criterios"]
    deactivated = client.patch(
        f"{prefix}/{existing_id}", headers=headers, json={**payload, "situacao": "inativa"}
    )
    assert deactivated.status_code == 409
    replacement = client.patch(
        f"{prefix}/{draft['id']}", headers=headers, json={**payload, "substituir": existing_id}
    )
    assert replacement.status_code == 200, replacement.json
    statuses = {
        item["id"]: item["situacao"] for item in client.get(prefix, headers=headers).json["data"]
    }
    assert statuses == {existing_id: "inativa", draft["id"]: "ativa"}

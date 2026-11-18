from datetime import timedelta
from io import BytesIO

from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select

from backend.db import db, utcnow
from backend.defense_models import Banca
from tests.conftest import headers
from tests.test_works import registered_work as registered_work
from tests.test_works import student as student
from tests.test_works import work_payload as work_payload


def test_defense_from_rubric_to_issued_documents(
    app, client, teacher, student, created_class, registered_work, signup, login, tmp_path
):
    app.config["PRIVATE_STORAGE_DIR"] = str(tmp_path)
    mail = []
    app.config["DOCUMENT_MAIL_SENDER"] = lambda *message: mail.append(message)
    work = registered_work.json["data"]
    class_id = created_class.json["data"]["id_turma"]
    prefix = f"/api/v1/turmas/{class_id}"
    auth = teacher["headers"]
    current = client.get(f"/api/v1/orientacoes/{work['id_trabalho_tcc']}", headers=auth)
    accepted = client.post(
        f"/api/v1/orientacoes/{work['orientacoes'][0]['id_orientacao']}/resposta",
        headers={**auth, "If-Match": current.headers["ETag"]},
        json={"decisao": "aceito"},
    )
    assert accepted.status_code == 200, accepted.json
    pdf = BytesIO()
    canvas = Canvas(pdf)
    canvas.drawString(50, 100, "Manuscrito para teste")
    canvas.save()
    uploaded = client.post(
        f"/api/v1/etapas/{work['id_etapa']}/manuscritos",
        headers=student["headers"],
        data={"arquivo": (BytesIO(pdf.getvalue()), "manuscrito.pdf")},
    )
    assert uploaded.status_code == 201, uploaded.json
    criteria = [
        {"nome": "Método", "descricao": "Consistência do método", "peso": "60"},
        {"nome": "Texto", "descricao": "Clareza do texto", "peso": "40"},
    ]
    draft = {"nome": "Rubrica TCC", "situacao": "rascunho", "criterios": criteria[:1]}
    assert (
        client.post(f"{prefix}/rubricas", headers=student["headers"], json=draft).status_code == 403
    )
    saved = client.post(f"{prefix}/rubricas", headers=auth, json=draft)
    assert saved.status_code == 201, saved.json
    rubric_id = saved.json["data"]["id"]
    rubric_path = f"{prefix}/rubricas/{rubric_id}"
    assert (
        client.patch(rubric_path, headers=auth, json={**draft, "situacao": "ativa"}).status_code
        == 422
    )
    payload = {**draft, "situacao": "ativa", "criterios": criteria}
    assert client.patch(rubric_path, headers=auth, json=payload).status_code == 200
    examiners = [
        signup(nome_usuario=name)
        for name in ["Avaliadora Um", "Avaliador Dois", "Docente Suplente"]
    ]
    accounts = [headers(login(person)["access_token"]) for person in examiners]
    start = utcnow() + timedelta(minutes=2)
    booking = {
        "etapa": work["id_etapa"],
        "rubrica": rubric_id,
        "inicio": start.isoformat(),
        "fim": (start + timedelta(hours=1)).isoformat(),
        "modalidade": "presencial",
        "local": "Sala 8",
        "url": "",
        "titulares": [p["id_usuario"] for p in examiners[:2]],
        "suplentes": [examiners[2]["id_usuario"]],
    }
    assert (
        client.post(f"{prefix}/bancas", headers=auth, json={**booking, "suplentes": []}).status_code
        == 422
    )
    booked = client.post(f"{prefix}/bancas", headers=auth, json=booking)
    assert booked.status_code == 201, booked.json
    identifier = booked.json["data"]["id"]
    endpoint = f"/api/v1/bancas/{identifier}"
    assert client.get(f"{endpoint}/manuscrito", headers=accounts[2]).data.startswith(b"%PDF-")
    assert client.get(endpoint, headers=student["headers"]).status_code == 403
    assert client.get(endpoint, headers=accounts[2]).status_code == 403
    with app.app_context():
        # Explicitly align the fixture with the academic day, even around midnight.
        banca = db.session.scalar(select(Banca))
        banca.data_inicio_banca = utcnow() - timedelta(seconds=1)
        db.session.commit()
    first = client.get(endpoint, headers=auth)
    token = {**auth, "If-Match": first.headers["ETag"]}
    assert (
        client.post(f"{endpoint}/ata", headers=token, json={"resultado": "aprovado"}).status_code
        == 409
    )
    ids = [c["id_criterio"] for c in first.json["data"]["criterios"]]
    invalid = client.post(
        f"{endpoint}/avaliacao",
        headers=token,
        json={"notas": [{"id_criterio": i, "nota": "11"} for i in ids]},
    )
    assert invalid.status_code == 422
    for actor in [auth, *accounts[:2]]:
        detail = client.get(endpoint, headers=actor)
        scored = client.post(
            f"{endpoint}/avaliacao",
            headers={**actor, "If-Match": detail.headers["ETag"]},
            json={
                "notas": [
                    {"id_criterio": ids[0], "nota": "10"},
                    {"id_criterio": ids[1], "nota": "5"},
                ]
            },
        )
        assert scored.status_code == 201, scored.json
    assert scored.json["data"]["media_final"] == "8.00"
    assert client.patch(rubric_path, headers=auth, json=payload).status_code == 409
    detail = client.get(endpoint, headers=auth)
    issued = client.post(
        f"{endpoint}/ata",
        headers={**auth, "If-Match": detail.headers["ETag"]},
        json={"resultado": "aprovado"},
    )
    assert issued.status_code == 201, issued.json
    assert len(issued.json["data"]["declaracoes"]) == 3
    assert len(mail) == 3
    assert client.get(f"{endpoint}/ata", headers=auth).data.startswith(b"%PDF-")
    assert client.get(f"{endpoint}/ata", headers=student["headers"]).status_code == 403

from datetime import timedelta
from io import BytesIO

from pypdf import PdfReader
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select

from backend.academic_models import NotificacaoAcademica
from backend.db import db, utcnow
from backend.defense_models import Banca, Membro
from tests.conftest import headers
from tests.test_works import registered_work as registered_work
from tests.test_works import student as student
from tests.test_works import work_payload as work_payload


def test_defense_from_rubric_to_issued_documents(
    app, client, teacher, student, created_class, registered_work, signup, login, tmp_path
):
    app.config["PRIVATE_STORAGE_DIR"] = str(tmp_path)
    mail = []

    def unavailable(*args):
        raise RuntimeError("SMTP indisponível")

    app.config["DOCUMENT_MAIL_SENDER"] = unavailable
    work = registered_work.json["data"]
    class_id = created_class.json["data"]["id_turma"]
    prefix = f"/api/v1/turmas/{class_id}"
    auth = teacher["headers"]
    waiting = client.get(f"{prefix}/bancas", headers=auth)
    assert waiting.status_code == 200, waiting.json
    assert waiting.json["data"]["trabalhos"] == []
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
    eligible = client.get(f"{prefix}/bancas", headers=auth)
    assert eligible.status_code == 200, eligible.json
    assert eligible.json["data"]["trabalhos"] == [
        {
            "id": work["id_etapa"],
            "titulo": work["titulo"],
            "orientador": teacher["id_usuario"],
            "nome_orientador": teacher["nome_usuario"],
            "estudante": student["nome_usuario"],
            "nivel": 1,
            "manuscrito": True,
        }
    ]
    preview = f"{prefix}/etapas/{work['id_etapa']}/manuscrito"
    assert client.get(preview, headers=auth).data.startswith(b"%PDF-")
    assert client.get(preview, headers=student["headers"]).status_code == 403
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
    external_url = f"{prefix}/avaliadores/externos"
    external_data = {
        "nome": "Docente Externa",
        "email": "docente@example.com",
        "titulacao": "Doutor",
    }
    missing = client.post(external_url, headers=auth, json=external_data)
    assert missing.status_code == 422 and missing.json["error"]["code"] == "UC_07_M05"
    external_data["instituicao"] = "Instituição Convidada"
    assert (
        client.post(external_url, headers=student["headers"], json=external_data).status_code == 403
    )
    external = client.post(external_url, headers=auth, json=external_data)
    assert external.status_code == 201, external.json
    external_id = external.json["data"]["id"]
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
    availability = f"{prefix}/bancas/disponibilidade"
    slot = {key: booking[key] for key in ("etapa", "inicio", "fim")}
    slot["membros"] = booking["titulares"] + booking["suplentes"]
    assert client.post(availability, headers=auth, json=slot).json["data"]["disponivel"]
    booked = client.post(f"{prefix}/bancas", headers=auth, json=booking)
    assert booked.status_code == 201, booked.json
    assert booked.json["code"] == "UC_07_M01"
    identifier = booked.json["data"]["id"]
    assert not client.post(availability, headers=auth, json=slot).json["data"]["disponivel"]
    editing = client.post(availability, headers=auth, json={**slot, "banca": identifier})
    assert editing.json["data"]["disponivel"]
    endpoint = f"/api/v1/bancas/{identifier}"
    assert client.get(f"{endpoint}/manuscrito", headers=accounts[2]).data.startswith(b"%PDF-")
    assert client.get(endpoint, headers=student["headers"]).status_code == 403
    assert client.get(endpoint, headers=accounts[2]).status_code == 403
    with app.app_context():
        members = {m.id_docente: m.id_membro_banca for m in db.session.scalars(select(Membro))}
    new_start = start + timedelta(days=2)
    amended = client.patch(
        f"{prefix}/bancas/{identifier}",
        headers=auth,
        json={
            **booking,
            "suplentes": [external_id],
            "inicio": new_start.isoformat(),
            "fim": (new_start + timedelta(hours=1)).isoformat(),
        },
    )
    assert amended.status_code == 200, amended.json
    opened_booking = client.get(f"{prefix}/bancas/{identifier}", headers=auth)
    assert opened_booking.json == {"data": amended.json["data"]}
    assert client.get(f"{endpoint}/manuscrito", headers=accounts[2]).status_code == 403
    with app.app_context():
        updated = {m.id_docente: m.id_membro_banca for m in db.session.scalars(select(Membro))}
        for person in [teacher, *examiners[:2]]:
            key = person["id_usuario"]
            assert updated[key] == members[key]
        assert external_id in updated and examiners[2]["id_usuario"] not in updated
        notices = db.session.scalars(
            select(NotificacaoAcademica).where(
                NotificacaoAcademica.id_banca == identifier,
                NotificacaoAcademica.id_usuario_destinatario == external_id,
            )
        ).all()
        assert {n.tipo_notificacao: n.situacao_notificacao for n in notices} == {
            "reagendamento_banca": "enviada",
            "lembrete_banca": "pendente",
        }
        for notice in notices:
            assert "SEQUENCE:1\r\n" in notice.anexo_ics_notificacao
            assert f"DTSTART:{new_start:%Y%m%dT%H%M%SZ}" in notice.anexo_ics_notificacao
            assert f"#/manuscrito-banca?banca={identifier}" in notice.corpo_notificacao
            assert "Recuperar senha" in notice.corpo_notificacao
        # Explicitly align the fixture with the academic day, even around midnight.
        banca = db.session.scalar(select(Banca))
        banca.data_inicio_banca = utcnow()
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
    opened = client.post(f"{endpoint}/avaliacao/inicio", headers=token)
    assert opened.status_code == 200, opened.json
    assert opened.json["data"]["avaliacao_iniciada"]
    assert not opened.json["data"]["avaliacao"]
    assert opened.json["data"]["situacao"] == "em_andamento"
    assert client.get(f"{prefix}/bancas/{identifier}", headers=auth).status_code == 409
    locked = client.patch(rubric_path, headers=auth, json=payload)
    assert locked.status_code == 409 and locked.json["error"]["code"] == "UC_08_M04"
    pending = client.post(
        f"{endpoint}/ata",
        headers={**auth, "If-Match": opened.headers["ETag"]},
        json={"resultado": "aprovado"},
    )
    assert pending.status_code == 409 and pending.json["error"]["code"] == "UC_10_M02"
    for actor in [auth, *accounts[:2]]:
        detail = client.get(endpoint, headers=actor)
        scored = client.post(
            f"{endpoint}/avaliacao",
            headers={**actor, "If-Match": detail.headers["ETag"]},
            json={
                "parecer": "Método consistente.",
                "notas": [
                    {"id_criterio": ids[0], "nota": "10"},
                    {"id_criterio": ids[1], "nota": "5"},
                ],
            },
        )
        assert scored.status_code == 201, scored.json
        assert scored.json["data"]["avaliacao"]["parecer"] == "Método consistente."
    assert scored.json["data"]["media_final"] == "8.00"
    assert client.patch(rubric_path, headers=auth, json=payload).status_code == 409
    detail = client.get(endpoint, headers=auth)
    issuance_headers = {**auth, "If-Match": detail.headers["ETag"]}
    no_result = client.post(f"{endpoint}/ata", headers=issuance_headers, json={})
    assert no_result.status_code == 422 and no_result.json["error"]["code"] == "UC_10_M04"
    no_deadline = client.post(
        f"{endpoint}/ata", headers=issuance_headers, json={"resultado": "aprovado_com_correcoes"}
    )
    assert no_deadline.status_code == 422 and no_deadline.json["error"]["code"] == "UC_10_M05"
    issued = client.post(
        f"{endpoint}/ata",
        headers=issuance_headers,
        json={"resultado": "aprovado"},
    )
    assert issued.status_code == 201, issued.json
    assert issued.json["code"] == "UC_10_M07"
    assert len(issued.json["data"]["declaracoes"]) == 3
    assert all(n["situacao"] == "falha" for n in issued.json["data"]["emails"])
    app.config["DOCUMENT_MAIL_SENDER"] = lambda *message: mail.append(message)
    retried = client.post(f"{endpoint}/declaracoes/reenvio", headers=auth)
    assert retried.json["code"] == "UC_10_M06"
    assert len(mail) == 3
    official = client.get(f"{endpoint}/ata", headers=auth)
    reader = PdfReader(BytesIO(official.data))
    text = " ".join(page.extract_text() for page in reader.pages)
    assert "Notas por critério" in text
    assert "5,00" in text and "10,00" in text
    assert len(reader.get_fields()) == 3
    assert client.get(f"{endpoint}/ata", headers=student["headers"]).status_code == 403

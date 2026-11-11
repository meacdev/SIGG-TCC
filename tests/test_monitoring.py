from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.academic_models import LoteCobranca, NotificacaoAcademica
from backend.db import db, utcnow
from backend.defense_models import Matricula
from backend.models import Auditoria, AuditoriaAlteracao, DocenteCurso, Perfil, Turma, UsuarioPerfil
from backend.services import academic_mail
from tests.test_concurrency import postgres_only as postgres_only
from tests.test_enrollments import student as student
from tests.test_meetings import accepted_work as accepted_work
from tests.test_works import work_payload as work_payload


@pytest.fixture
def roster(app, client, teacher, student, accepted_work, password):
    class_id = None
    with app.app_context():
        member = db.session.get(Matricula, accepted_work["id_matricula"])
        class_id = member.id_turma
        member.data_matricula_matricula_turma = utcnow() - timedelta(days=60)
        db.session.commit()
    old_day = (
        utcnow().astimezone(app.config["ACADEMIC_TIMEZONE"]).date() - timedelta(days=31)
    ).strftime("%d/%m/%Y")
    result = client.post(
        f"/api/v1/etapas/{accepted_work['id_etapa']}/reunioes",
        headers=student["headers"],
        json={"data_encontro": old_day, "resumo": "Encaminhamentos da reunião antiga."},
    )
    assert result.status_code == 201, result.json

    def add(name, age):
        user = client.post(
            "/api/v1/usuarios",
            json={
                "nome_usuario": name,
                "email_usuario": uuid4().hex + "@example.com",
                "senha": password,
                "tipo_cadastro": "aluno",
                "id_curso": 1,
                "matricula_aluno": "000" + uuid4().hex[:9],
            },
        ).json["data"]
        response = client.post(
            f"/api/v1/turmas/{class_id}/matriculas",
            headers=teacher["headers"],
            json={"id_aluno": user["id_usuario"]},
        )
        assert response.status_code == 201
        identifier = response.json["data"]["id_matricula"]
        with app.app_context():
            db.session.get(Matricula, identifier).data_matricula_matricula_turma = (
                utcnow() - timedelta(days=age)
            )
            db.session.commit()
        return identifier

    late = add("Sem reunião há 40 dias", 40)
    boundary = add("Limite de 30 dias", 30)
    recent = add("Matrícula recente", 2)
    app.outbox.clear()
    return {
        "class": class_id,
        "old": accepted_work["id_matricula"],
        "late": late,
        "boundary": boundary,
        "recent": recent,
        "work": accepted_work,
        "base": f"/api/v1/turmas/{class_id}/monitoramento",
    }


def preview(client, teacher, roster, selection=None):
    response = client.post(
        roster["base"] + "/previa",
        headers=teacher["headers"],
        json=selection or {"ids_matriculas": [roster["old"], roster["late"]]},
    )
    assert response.status_code == 201, response.json
    return response.json["data"]


def confirm(client, teacher, roster, batch, headers=None):
    return client.post(
        roster["base"] + f"/lotes/{batch['id_lote']}/confirmar",
        headers=headers or teacher["headers"],
        json={},
    )


def test_matrix_filter_boundary_and_scoped_history(client, teacher, roster):
    response = client.get(roster["base"], headers=teacher["headers"])
    assert response.status_code == 200, response.json
    assert response.json["meta"]["total_turma"] == 4
    assert response.json["meta"]["total_inativos"] == 2
    rows = {r["id_matricula"]: r for r in response.json["data"]}
    assert rows[roster["old"]]["total_atas"] == 1
    assert rows[roster["old"]]["dias_inatividade"] == 31
    assert rows[roster["boundary"]]["dias_inatividade"] == 30
    assert not rows[roster["boundary"]]["inativo"]
    filtered = client.get(
        roster["base"] + "?status=inativos&per_page=1&page=2", headers=teacher["headers"]
    )
    assert filtered.json["meta"]["total"] == 2
    assert len(filtered.json["data"]) == 1
    history = client.get(roster["base"] + f"/{roster['old']}/atas", headers=teacher["headers"])
    assert history.json["meta"]["total"] == 1
    assert history.json["data"][0]["orientador"] == "Orientador de Teste"
    empty = client.get(roster["base"] + f"/{roster['late']}/atas", headers=teacher["headers"])
    assert empty.json["data"] == []


def test_empty_and_current_class_messages(app, client, teacher, created_class):
    base = f"/api/v1/turmas/{created_class.json['data']['id_turma']}/monitoramento"
    assert client.get(base, headers=teacher["headers"]).json["code"] == "UC_13_M02"


def test_roles_and_current_course_scope(app, client, teacher, student, roster, signup, login):
    assert client.get(roster["base"]).status_code == 401
    assert (
        client.get(roster["base"], headers=student["headers"]).json["error"]["code"] == "UC_13_M06"
    )
    other = signup()
    headers = {"Authorization": f"Bearer {login(other)['access_token']}"}
    assert client.get(roster["base"], headers=headers).status_code == 403
    assert (
        client.post(
            roster["base"] + "/previa", headers=headers, json={"todos_inativos": True}
        ).status_code
        == 403
    )
    with app.app_context():
        role = db.session.scalar(select(Perfil).where(Perfil.codigo_perfil == "coordenador"))
        db.session.add(UsuarioPerfil(id_usuario=other["id_usuario"], id_perfil=role.id_perfil))
        db.session.add(
            DocenteCurso(
                id_docente=other["id_usuario"],
                id_curso=1,
                coordenador_docente_curso=True,
                data_inicio_docente_curso=utcnow()
                .astimezone(app.config["ACADEMIC_TIMEZONE"])
                .date()
                - timedelta(days=1),
            )
        )
        db.session.commit()
    assert client.get(roster["base"], headers=headers).status_code == 200
    with app.app_context():
        db.session.scalar(
            select(DocenteCurso).where(DocenteCurso.id_docente == other["id_usuario"])
        ).data_fim_docente_curso = utcnow().astimezone(
            app.config["ACADEMIC_TIMEZONE"]
        ).date() - timedelta(days=1)
        db.session.commit()
    assert client.get(roster["base"], headers=headers).status_code == 403


def test_preview_has_no_sends_confirm_is_idempotent_and_audited(app, client, teacher, roster):
    batch = preview(client, teacher, roster)
    assert batch["quantidade"] == 2
    assert app.outbox == []
    result = confirm(client, teacher, roster, batch)
    assert result.status_code == 200, result.json
    assert result.json["code"] == "UC_13_M01"
    assert result.json["data"]["enviados"] == 2
    assert len(app.outbox) == 2
    assert confirm(client, teacher, roster, batch).json["data"]["enviados"] == 2
    assert len(app.outbox) == 2
    with app.app_context():
        notifications = list(
            db.session.scalars(
                select(NotificacaoAcademica).where(
                    NotificacaoAcademica.tipo_notificacao == "cobranca_inatividade"
                )
            )
        )
        assert len(notifications) == 2
        audits = list(
            db.session.scalars(
                select(Auditoria).where(Auditoria.acao_auditoria == "cobranca_inatividade")
            )
        )
        assert len(audits) == 2
        assert all(
            a.id_usuario == teacher["id_usuario"]
            and a.ip_origem_auditoria
            and a.data_ocorrencia_auditoria
            for a in audits
        )
        changes = list(
            db.session.scalars(
                select(AuditoriaAlteracao).where(
                    AuditoriaAlteracao.nome_campo_auditoria_alteracao == "email_destinatario"
                )
            )
        )
        assert {change.valor_novo_auditoria_alteracao for change in changes} == {
            n.email_destino_notificacao for n in notifications
        }


def test_select_all_covers_pages_and_exclusions(client, teacher, roster):
    batch = preview(
        client, teacher, roster, {"todos_inativos": True, "ids_excluidas": [roster["old"]]}
    )
    assert batch["quantidade"] == 1
    assert confirm(client, teacher, roster, batch).json["data"]["total"] == 1


def test_empty_invalid_and_outdated_selection(client, teacher, roster):
    response = client.post(roster["base"] + "/previa", headers=teacher["headers"], json={})
    assert response.json["error"]["code"] == "UC_13_M04"
    for payload in [
        {"ids_matriculas": [roster["recent"]]},
        {"ids_matriculas": [999999]},
        {"ids_matriculas": [True]},
        {"ids_matriculas": [roster["old"], roster["old"]]},
        {"todos_inativos": "true"},
        {"todos_inativos": True, "ids_matriculas": [roster["old"]]},
    ]:
        assert client.post(
            roster["base"] + "/previa", headers=teacher["headers"], json=payload
        ).status_code in {409, 422}


def test_pending_email_retry_and_cancellation_after_activity(app, client, teacher, roster):
    batch = preview(client, teacher, roster)

    def fail(*args):
        raise OSError("Synthetic mail failure")

    app.config["MAIL_SENDER"] = fail
    result = confirm(client, teacher, roster, batch)
    assert result.json["code"] == "UC_13_M05"
    assert result.json["data"]["pendentes"] == 2
    with app.app_context():
        db.session.get(Matricula, roster["late"]).situacao_matricula_turma = "removida"
        db.session.commit()
    app.config["MAIL_SENDER"] = lambda *args: app.outbox.append(args)
    retried = confirm(client, teacher, roster, batch)
    assert retried.json["data"]["enviados"] == 1
    assert retried.json["data"]["cancelados"] == 1
    assert retried.json["code"] != "UC_13_M01"
    assert len(app.outbox) == 1
    with app.app_context():
        academic_mail.deliver()
    assert len(app.outbox) == 1


def test_expired_preview_and_new_meeting_block_stale_confirmation(
    app, client, teacher, student, roster
):
    batch = preview(client, teacher, roster)
    with app.app_context():
        db.session.get(LoteCobranca, batch["id_lote"]).expira_em = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert confirm(client, teacher, roster, batch).json["error"]["code"] == "CONFIRMACAO_EXPIRADA"
    batch = preview(client, teacher, roster)
    now = utcnow().astimezone(app.config["ACADEMIC_TIMEZONE"]).date().strftime("%d/%m/%Y")
    sent = client.post(
        f"/api/v1/etapas/{roster['work']['id_etapa']}/reunioes",
        headers=student["headers"],
        json={"data_encontro": now, "resumo": "Reunião realizada hoje."},
    )
    assert sent.status_code == 201
    app.outbox.clear()
    assert confirm(client, teacher, roster, batch).json["error"]["code"] == "SELECAO_DESATUALIZADA"
    assert app.outbox == []


def test_delivery_is_activity_without_becoming_a_meeting(app, client, teacher, student, roster):
    with app.app_context():
        db.session.execute(
            text(
                "INSERT INTO arquivo_pdf (id_arquivo_pdf,nome_original_arquivo_pdf,"
                "chave_armazenamento_arquivo_pdf,tamanho_bytes_arquivo_pdf,sha256_arquivo_pdf,"
                "id_usuario_envio,data_envio_arquivo_pdf) "
                "VALUES (901,:name,:key,100,:sha,:user,:sent)"
            ),
            {
                "name": "teste.pdf",
                "key": "test-only-delivery.pdf",
                "sha": "a" * 64,
                "user": student["id_usuario"],
                "sent": utcnow().replace(tzinfo=None).isoformat(sep=" "),
            },
        )
        db.session.execute(
            text(
                "INSERT INTO entrega_final (id_entrega_final,id_etapa_trabalho,id_arquivo_pdf) "
                "VALUES (901,:stage,901)"
            ),
            {"stage": roster["work"]["id_etapa"]},
        )
        db.session.commit()
    result = client.get(roster["base"], headers=teacher["headers"])
    assert result.status_code == 200, result.json
    row = next(r for r in result.json["data"] if r["id_matricula"] == roster["old"])
    assert row["total_atas"] == 1
    assert row["ultima_entrega"]
    assert row["dias_inatividade"] == 0
    assert not row["inativo"]


def test_correction_submission_also_counts_as_activity(app, client, teacher, student, roster):
    now = utcnow().replace(tzinfo=None).isoformat(sep=" ")
    with app.app_context():
        records = [
            (
                "INSERT INTO arquivo_pdf (id_arquivo_pdf,nome_original_arquivo_pdf,"
                "chave_armazenamento_arquivo_pdf,tamanho_bytes_arquivo_pdf,sha256_arquivo_pdf,"
                "id_usuario_envio,data_envio_arquivo_pdf) VALUES (902,'correcao.pdf',"
                "'test-only-correction.pdf',100,:sha,:student,:now)"
            ),
            (
                "INSERT INTO rubrica (id_rubrica,id_turma,nome_rubrica,id_usuario_criacao) "
                "VALUES (902,:class,'Rubrica de teste',:teacher)"
            ),
            (
                "INSERT INTO banca (id_banca,id_etapa_trabalho,id_rubrica,data_inicio_banca,"
                "data_fim_banca,local_defesa_banca,id_usuario_agendamento) "
                "VALUES (902,:stage,902,:now,:now,'Sala de teste',:teacher)"
            ),
            (
                "INSERT INTO solicitacao_correcao (id_solicitacao_correcao,id_banca,"
                "descricao_solicitacao_correcao,data_limite_reenvio_solicitacao_correcao,"
                "id_usuario_registro) VALUES (902,902,'Revisão de teste',:deadline,:teacher)"
            ),
            (
                "INSERT INTO entrega_correcao (id_entrega_correcao,id_solicitacao_correcao,"
                "id_arquivo_pdf) VALUES (902,902,902)"
            ),
        ]
        params = {
            "sha": "b" * 64,
            "student": student["id_usuario"],
            "now": now,
            "class": roster["class"],
            "teacher": teacher["id_usuario"],
            "stage": roster["work"]["id_etapa"],
            "deadline": utcnow().astimezone(app.config["ACADEMIC_TIMEZONE"]).date().isoformat(),
        }
        for statement in records:
            db.session.execute(text(statement), params)
        db.session.commit()
    row = next(
        r
        for r in client.get(roster["base"], headers=teacher["headers"]).json["data"]
        if r["id_matricula"] == roster["old"]
    )
    assert row["ultima_entrega"]
    assert not row["inativo"]
    assert row["total_atas"] == 1


def test_no_inactive_message_and_inactive_class(app, client, teacher, roster):
    with app.app_context():
        for identifier in (roster["old"], roster["late"]):
            db.session.get(Matricula, identifier).situacao_matricula_turma = "removida"
        db.session.commit()
    result = client.get(roster["base"], headers=teacher["headers"])
    assert result.json["code"] == "UC_13_M03"
    with app.app_context():
        db.session.get(Turma, roster["class"]).ativa_turma = False
        db.session.commit()
    assert client.get(roster["base"], headers=teacher["headers"]).status_code == 409
    assert (
        client.post(
            roster["base"] + "/previa", headers=teacher["headers"], json={"todos_inativos": True}
        ).status_code
        == 409
    )


def test_batch_is_actor_bound_and_unknown_fields_are_rejected(
    app, client, teacher, roster, signup, login
):
    batch = preview(client, teacher, roster)
    coordinator = signup()
    with app.app_context():
        role = db.session.scalar(select(Perfil).where(Perfil.codigo_perfil == "coordenador"))
        db.session.add(
            UsuarioPerfil(id_usuario=coordinator["id_usuario"], id_perfil=role.id_perfil)
        )
        db.session.add(
            DocenteCurso(
                id_docente=coordinator["id_usuario"],
                id_curso=1,
                coordenador_docente_curso=True,
                data_inicio_docente_curso=utcnow()
                .astimezone(app.config["ACADEMIC_TIMEZONE"])
                .date()
                - timedelta(days=1),
            )
        )
        db.session.commit()
    headers = {"Authorization": f"Bearer {login(coordinator)['access_token']}"}
    assert client.get(roster["base"], headers=headers).status_code == 200
    assert confirm(client, teacher, roster, batch, headers).status_code == 404
    wrong = client.post(
        roster["base"] + "/previa",
        headers=teacher["headers"],
        json={"ids_matriculas": [roster["old"]], "email": "arbitrary@example.com"},
    )
    assert wrong.status_code == 422
    assert app.outbox == []


def test_academic_timezone_is_used(app):
    from sqlalchemy import literal

    from backend.services.monitoring import local_day

    with app.app_context():
        result = db.session.scalar(select(local_day(literal(datetime(2026, 10, 25, 3, 30)))))
        assert str(result) == "2026-10-24"


@pytest.mark.postgres
def test_concurrent_confirmations_do_not_duplicate_alerts(
    postgres_only, app, client, teacher, roster
):
    batch = preview(client, teacher, roster)

    def send(_):
        with app.test_client() as concurrent:
            return confirm(concurrent, teacher, roster, batch).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(send, range(2)))
    assert statuses == [200, 200]
    assert len(app.outbox) == 2
    with app.app_context():
        assert (
            db.session.scalar(
                select(db.func.count())
                .select_from(NotificacaoAcademica)
                .where(NotificacaoAcademica.tipo_notificacao == "cobranca_inatividade")
            )
            == 2
        )

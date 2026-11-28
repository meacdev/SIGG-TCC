import re
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.db import db, utcnow
from backend.models import (
    Auditoria,
    AuditoriaAlteracao,
    Perfil,
    ProfessorCurso,
    TokenUsuario,
    Usuario,
    UsuarioPerfil,
)
from tests.conftest import headers

BASE = "/api/v1/admin/usuarios"


@pytest.fixture
def admin(app, signup, login):
    user = signup(nome_usuario="Secretaria")
    result = app.test_cli_runner().invoke(
        args=[
            "conceder-perfil",
            "--email",
            user["email_usuario"],
            "--perfil",
            "administrador",
            "--justificativa",
            "Primeiro administrador",
        ]
    )
    assert result.exit_code == 0, result.output + str(result.exception)
    user["headers"] = headers(login(user)["access_token"])
    return user


def payload(**overrides):
    data = {
        "nome_usuario": "Pessoa Convidada",
        "email_usuario": f"{uuid4().hex}@uea.edu.br",
        "tipo_cadastro": "administrativo",
    }
    data.update(overrides)
    return data


def docente(**overrides):
    return payload(
        tipo_cadastro="docente", tipo_professor="interno", titulacao_professor="doutor", **overrides
    )


def link_token(app, index=-1):
    return re.search(r"#/\S+\?token=(\S+)", app.outbox[index][2]).group(1)


def create(client, admin, data=None):
    response = client.post(BASE, json=data or payload(), headers=admin["headers"])
    assert response.status_code == 201, response.json
    return response


def versioned(admin, response):
    return {**admin["headers"], "If-Match": response.headers["ETag"]}


def error_code(response):
    return response.json["error"]["code"]


def accept(client, token, secret):
    return client.post(
        "/api/v1/auth/convite/aceitar",
        json={"token": token, "nova_senha": secret, "confirmacao_senha": secret},
    )


def test_only_administrator_reaches_the_area(client, admin, teacher):
    assert client.get(BASE).status_code == 401
    for method, path in (("get", BASE), ("post", BASE), ("get", f"{BASE}/1")):
        kwargs = {"json": payload()} if method == "post" else {}
        response = getattr(client, method)(path, headers=teacher["headers"], **kwargs)
        assert response.status_code == 403
        assert error_code(response) == "UC_14_M06"
    assert client.get(BASE, headers=admin["headers"]).status_code == 200


def test_invite_lifecycle(app, client, admin, password):
    response = create(client, admin)
    assert response.json["code"] == "UC_14_M01"
    data = response.json["data"]
    assert data["situacao_conta"] == "pendente" and data["convite_enviado"] is True
    assert "hash_senha_usuario" not in data
    token = link_token(app)
    assert f"/#/aceitar-convite?token={token}" in app.outbox[-1][2]
    with app.app_context():
        stored = db.session.scalar(
            select(TokenUsuario).where(TokenUsuario.id_usuario == data["id_usuario"])
        )
        assert stored.hash_token_usuario != token
        days = stored.data_expiracao_token_usuario - stored.data_criacao_token_usuario
        assert days == timedelta(days=7)
    login_data = {"email_usuario": data["email_usuario"], "senha": password}
    assert client.post("/api/v1/auth/login", json=login_data).status_code == 401
    valid = client.post("/api/v1/auth/convite/validar", json={"token": token})
    assert valid.json["data"]["email_usuario"] == data["email_usuario"]
    weak = accept(client, token, "fraca")
    assert weak.status_code == 422 and error_code(weak) == "UC_14_M03"
    accepted = accept(client, token, password)
    assert accepted.status_code == 200 and accepted.json["code"] == "UC_14_M19"
    assert client.post("/api/v1/auth/login", json=login_data).status_code == 200
    reused = accept(client, token, password)
    assert reused.status_code == 410 and error_code(reused) == "UC_14_M13"
    detail = client.get(f"{BASE}/{data['id_usuario']}", headers=admin["headers"])
    assert detail.json["data"]["situacao_conta"] == "ativo"
    resend = client.post(f"{BASE}/{data['id_usuario']}/convite", headers=versioned(admin, detail))
    assert resend.status_code == 409


def test_resend_invalidates_previous_and_expired_invite_fails(app, client, admin, password):
    response = create(client, admin)
    user_id = response.json["data"]["id_usuario"]
    first = link_token(app)
    resent = client.post(f"{BASE}/{user_id}/convite", headers=versioned(admin, response))
    assert resent.status_code == 200 and resent.json["code"] == "UC_14_M18"
    second = link_token(app)
    assert error_code(accept(client, first, password)) == "UC_14_M13"
    with app.app_context():
        stored = db.session.scalar(
            select(TokenUsuario).where(
                TokenUsuario.id_usuario == user_id,
                TokenUsuario.data_consumo_token_usuario.is_(None),
            )
        )
        stored.data_criacao_token_usuario = utcnow() - timedelta(days=8)
        stored.data_expiracao_token_usuario = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert error_code(accept(client, second, password)) == "UC_14_M13"


def test_pending_account_cannot_use_password_recovery(app, client, admin):
    data = create(client, admin).json["data"]
    sent = len(app.outbox)
    response = client.post(
        "/api/v1/auth/recuperacao-senha", json={"email_usuario": data["email_usuario"]}
    )
    assert response.status_code == 202 and len(app.outbox) == sent


def test_mail_failure_keeps_pending_account(app, client, admin):
    def broken(*args):
        from backend.errors import APIError

        raise APIError(503, "EMAIL_INDISPONIVEL", "Falha")

    app.config["MAIL_SENDER"] = broken
    response = create(client, admin)
    assert response.json["code"] == "UC_14_CONVITE_PENDENTE"
    assert response.json["data"]["convite_enviado"] is False


def test_pre_registration_validation(client, admin):
    create(client, admin, payload(email_usuario="repetido@uea.edu.br", cpf_usuario="52998224725"))
    student = payload(tipo_cadastro="estudante", matricula_estudante="2026001", id_curso=1)
    assert create(client, admin, student).json["data"]["perfis"] == ["estudante"]
    cases = [
        ({"nome_usuario": "Sem Email", "tipo_cadastro": "docente"}, 422, "UC_14_M02"),
        (payload(tipo_cadastro="estudante"), 422, "UC_14_M02"),
        (payload(email_usuario="invalido"), 422, "UC_14_M03"),
        (payload(cpf_usuario="11111111111"), 422, "UC_14_M03"),
        (payload(matricula_estudante="1"), 422, "UC_14_M03"),
        (payload(email_usuario="repetido@uea.edu.br"), 409, "UC_14_M04"),
        (payload(cpf_usuario="52998224725"), 409, "UC_14_M05"),
        (
            payload(tipo_cadastro="estudante", matricula_estudante="2026001", id_curso=1),
            409,
            "UC_14_M05",
        ),
        (
            payload(
                tipo_cadastro="docente", tipo_professor="externo", titulacao_professor="mestre"
            ),
            422,
            "UC_14_M02",
        ),
    ]
    for data, status, code in cases:
        response = client.post(BASE, json=data, headers=admin["headers"])
        assert (response.status_code, error_code(response)) == (status, code), data


def test_list_filters(client, admin):
    marker = uuid4().hex[:10]
    create(client, admin, docente(email_usuario=f"{marker}@uea.edu.br"))
    create(
        client,
        admin,
        payload(tipo_cadastro="estudante", matricula_estudante=marker, id_curso=2),
    )
    query = lambda **args: client.get(BASE, query_string=args, headers=admin["headers"])  # noqa: E731
    assert query(busca=marker).json["meta"]["total"] == 2
    assert query(busca=marker, tipo_cadastro="docente").json["meta"]["total"] == 1
    assert query(busca=marker, situacao="pendente").json["meta"]["total"] == 2
    assert query(busca=marker, situacao="inativo").json["meta"]["total"] == 0
    assert query(busca=marker, id_curso="2").json["meta"]["total"] == 1
    assert query(perfil="administrador").json["data"][0]["id_usuario"] == admin["id_usuario"]
    assert query(situacao="x").status_code == 422
    assert query(id_curso="abc").status_code == 422


def test_update_uses_timestamp_and_email_token(app, client, admin, password):
    response = create(client, admin)
    data = response.json["data"]
    accept(client, link_token(app), password)
    target = f"{BASE}/{data['id_usuario']}"
    assert (
        client.patch(target, json={"nome_usuario": "Nome"}, headers=admin["headers"]).status_code
        == 428
    )
    stale = versioned(admin, response)
    conflict = client.patch(target, json={"nome_usuario": "Outro Nome"}, headers=stale)
    assert conflict.status_code == 409 and error_code(conflict) == "UC_14_M14"
    current = client.get(target, headers=admin["headers"])
    address = f"{uuid4().hex}@uea.edu.br"
    changed = client.patch(
        target,
        json={"nome_usuario": "Nome Novo", "email_usuario": address},
        headers=versioned(admin, current),
    )
    assert changed.status_code == 200 and changed.json["code"] == "UC_14_M15"
    assert changed.json["data"]["email_usuario"] == data["email_usuario"]
    assert changed.json["data"]["alteracao_email"] == {"novo_email": address, "enviado": True}
    assert app.outbox[-1][0] == address
    token = link_token(app)
    confirmed = client.post("/api/v1/auth/alteracao-email/confirmar", json={"token": token})
    assert confirmed.status_code == 200
    detail = client.get(target, headers=admin["headers"])
    assert detail.json["data"]["email_usuario"] == address
    reused = client.post("/api/v1/auth/alteracao-email/confirmar", json={"token": token})
    assert reused.status_code == 410


def test_email_change_of_pending_account_replaces_invite(app, client, admin, password):
    response = create(client, admin)
    old_invite = link_token(app)
    address = f"{uuid4().hex}@uea.edu.br"
    target = f"{BASE}/{response.json['data']['id_usuario']}"
    client.patch(target, json={"email_usuario": address}, headers=versioned(admin, response))
    client.post("/api/v1/auth/alteracao-email/confirmar", json={"token": link_token(app)})
    assert app.outbox[-1][0] == address
    assert error_code(accept(client, old_invite, password)) == "UC_14_M13"
    assert accept(client, link_token(app), password).status_code == 200


def test_status_rules(app, client, admin, teacher, created_class, signup, login, password):
    own = client.get(f"{BASE}/{admin['id_usuario']}", headers=admin["headers"])
    body = {"ativo_usuario": False, "justificativa": "Desligamento"}
    response = client.patch(
        f"{BASE}/{admin['id_usuario']}/situacao", json=body, headers=versioned(admin, own)
    )
    assert response.status_code == 409 and error_code(response) == "UC_14_M11"
    target = f"{BASE}/{teacher['id_usuario']}"
    current = client.get(target, headers=admin["headers"])
    missing = client.patch(
        f"{target}/situacao", json={"ativo_usuario": False}, headers=versioned(admin, current)
    )
    assert error_code(missing) == "UC_14_M09"
    blocked = client.patch(f"{target}/situacao", json=body, headers=versioned(admin, current))
    assert blocked.status_code == 409 and error_code(blocked) == "UC_14_M12"
    assert blocked.json["error"]["fields"]["vinculos"][0]["tipo"] == "turma"

    other = signup()
    session = login(other)
    other_url = f"{BASE}/{other['id_usuario']}"
    current = client.get(other_url, headers=admin["headers"])
    done = client.patch(f"{other_url}/situacao", json=body, headers=versioned(admin, current))
    assert done.status_code == 200 and done.json["code"] == "UC_14_M17"
    assert done.json["data"]["situacao_conta"] == "inativo"
    me = client.get("/api/v1/usuarios/me", headers=headers(session["access_token"]))
    assert me.status_code == 401
    denied = client.post(
        "/api/v1/auth/login", json={"email_usuario": other["email_usuario"], "senha": password}
    )
    assert denied.status_code == 403
    back = client.patch(
        f"{other_url}/situacao",
        json={"ativo_usuario": True, "justificativa": "Retorno"},
        headers=versioned(admin, done),
    )
    assert back.json["data"]["professor"]["ativo_professor"] is True


def test_grant_validation(client, admin, signup):
    student = create(
        client,
        admin,
        payload(tipo_cadastro="estudante", matricula_estudante=uuid4().hex[:12], id_curso=1),
    )
    teacher = create(client, admin, docente())
    future = (utcnow() + timedelta(days=30)).isoformat()
    past = (utcnow() - timedelta(days=1)).isoformat()
    base = {"codigo_perfil": "professor_disciplina", "id_curso": 1, "justificativa": "Portaria"}
    cases = [
        (teacher, {"codigo_perfil": "professor_disciplina", "justificativa": "x"}, "UC_14_M02"),
        (teacher, {**base, "justificativa": " "}, "UC_14_M09"),
        (teacher, {**base, "data_expiracao": past}, "UC_14_M10"),
        (teacher, {**base, "data_expiracao": "ontem"}, "UC_14_M03"),
        (student, base, "UC_14_M07"),
        (teacher, {**base, "id_curso": 999}, "UC_14_M07"),
        (teacher, {**base, "codigo_perfil": "coordenador"}, "UC_14_M08"),
        (teacher, {**base, "codigo_perfil": "orientador"}, "UC_14_M03"),
        (
            teacher,
            {
                "codigo_perfil": "administrador",
                "data_expiracao": future,
                "justificativa": "Portaria",
            },
            "UC_14_M03",
        ),
    ]
    for owner, data, code in cases:
        response = client.post(
            f"{BASE}/{owner.json['data']['id_usuario']}/perfis",
            json=data,
            headers=versioned(admin, owner),
        )
        assert error_code(response) == code, data


def test_course_roles_are_granted_and_revoked_per_course(
    app, client, admin, signup, login, class_payload
):
    user = signup()
    target = f"{BASE}/{user['id_usuario']}"
    current = client.get(target, headers=admin["headers"])
    for course in (1, 2):
        current = client.post(
            f"{target}/perfis",
            json={
                "codigo_perfil": "professor_disciplina",
                "id_curso": course,
                "justificativa": "Designação",
            },
            headers=versioned(admin, current),
        )
        assert current.status_code == 200 and current.json["code"] == "UC_14_M16"
    assert len(current.json["data"]["vinculos_curso"]) == 2
    auth = headers(login(user)["access_token"])
    body = {**class_payload, "id_professor_responsavel": user["id_usuario"]}
    assert client.post("/api/v1/turmas", json=body, headers=auth).status_code == 201

    revoke = {"codigo_perfil": "professor_disciplina", "id_curso": 1, "justificativa": "Fim"}
    current = client.post(
        f"{target}/perfis/revogar", json=revoke, headers=versioned(admin, current)
    )
    assert current.status_code == 200
    assert "professor_disciplina" in current.json["data"]["perfis"]
    denied = {**body, "codigo_turma": "ESTCOMP02"}
    assert client.post("/api/v1/turmas", json=denied, headers=auth).status_code == 403
    allowed = {**body, "codigo_turma": "ESTMAT01", "id_curso": 2}
    assert client.post("/api/v1/turmas", json=allowed, headers=auth).status_code == 201

    again = client.post(f"{target}/perfis/revogar", json=revoke, headers=versioned(admin, current))
    assert again.status_code == 404
    last = {**revoke, "id_curso": 2}
    current = client.post(f"{target}/perfis/revogar", json=last, headers=versioned(admin, current))
    assert "professor_disciplina" not in current.json["data"]["perfis"]
    with app.app_context():
        links = db.session.scalars(
            select(ProfessorCurso).where(ProfessorCurso.id_professor == user["id_usuario"])
        ).all()
        assert len(links) == 2
        assert not any(link.professor_disciplina_professor_curso for link in links)


def test_expired_grant_does_not_revive_old_course(app, client, admin, signup):
    user = signup()
    target = f"{BASE}/{user['id_usuario']}"
    current = client.get(target, headers=admin["headers"])
    grant = {"codigo_perfil": "professor_disciplina", "id_curso": 1, "justificativa": "Designação"}
    current = client.post(f"{target}/perfis", json=grant, headers=versioned(admin, current))
    with app.app_context():
        profile = db.session.scalar(
            select(Perfil).where(Perfil.codigo_perfil == "professor_disciplina")
        )
        association = db.session.get(UsuarioPerfil, (user["id_usuario"], profile.id_perfil))
        association.data_expiracao_usuario_perfil = utcnow() - timedelta(seconds=1)
        db.session.commit()
    result = client.post(
        f"{target}/perfis", json={**grant, "id_curso": 2}, headers=versioned(admin, current)
    )
    assert result.status_code == 200
    active = {
        item["id_curso"]
        for item in result.json["data"]["vinculos_curso"]
        if item["professor_disciplina"]
    }
    assert active == {2}


def test_coordinator_and_administrator_roles(app, client, admin, signup, login):
    user = signup()
    target = f"{BASE}/{user['id_usuario']}"
    current = client.get(target, headers=admin["headers"])
    current = client.post(
        f"{target}/perfis",
        json={
            "codigo_perfil": "coordenador",
            "id_curso": 1,
            "departamento_unidade": "EST",
            "justificativa": "Portaria",
        },
        headers=versioned(admin, current),
    )
    assert current.json["data"]["vinculos_curso"][0]["coordenador"] is True
    current = client.post(
        f"{target}/perfis",
        json={"codigo_perfil": "administrador", "justificativa": "Secretaria"},
        headers=versioned(admin, current),
    )
    assert "administrador" in current.json["data"]["perfis"]
    assert client.get(BASE, headers=headers(login(user)["access_token"])).status_code == 200
    current = client.post(
        f"{target}/perfis/revogar",
        json={"codigo_perfil": "administrador", "justificativa": "Fim"},
        headers=versioned(admin, current),
    )
    assert "administrador" not in current.json["data"]["perfis"]
    own = client.get(f"{BASE}/{admin['id_usuario']}", headers=admin["headers"])
    denied = client.post(
        f"{BASE}/{admin['id_usuario']}/perfis/revogar",
        json={"codigo_perfil": "administrador", "justificativa": "Fim"},
        headers=versioned(admin, own),
    )
    assert denied.status_code == 409 and error_code(denied) == "UC_14_M11"


def test_audit_records_author_and_never_secrets(app, client, admin, password):
    response = create(client, admin)
    user_id = response.json["data"]["id_usuario"]
    token = link_token(app)
    accept(client, token, password)
    with app.app_context():
        event = db.session.scalar(
            select(Auditoria).where(
                Auditoria.acao_auditoria == "pre_cadastro_usuario",
                Auditoria.id_registro_auditoria == user_id,
            )
        )
        assert event.id_usuario == admin["id_usuario"] and event.ip_origem_auditoria
        stored = db.session.get(Usuario, user_id).hash_senha_usuario
        values = db.session.execute(
            select(
                AuditoriaAlteracao.valor_anterior_auditoria_alteracao,
                AuditoriaAlteracao.valor_novo_auditoria_alteracao,
            )
        ).all()
        flat = " ".join(str(value) for row in values for value in row)
        assert token not in flat and password not in flat and stored not in flat


def test_update_student_and_teacher_data(app, client, admin, teacher):
    first = create(
        client,
        admin,
        payload(tipo_cadastro="estudante", matricula_estudante=uuid4().hex[:12], id_curso=1),
    )
    taken = first.json["data"]["estudante"]["matricula_estudante"]
    student = create(
        client,
        admin,
        payload(tipo_cadastro="estudante", matricula_estudante=uuid4().hex[:12], id_curso=1),
    )
    url = f"{BASE}/{student.json['data']['id_usuario']}"
    auth = versioned(admin, student)
    duplicate = client.patch(url, json={"matricula_estudante": taken}, headers=auth)
    assert error_code(duplicate) == "UC_14_M05"
    wrong = client.patch(url, json={"titulacao_professor": "Mestre"}, headers=auth)
    assert error_code(wrong) == "UC_14_M03"
    changed = client.patch(url, json={"matricula_estudante": "NOVA01", "id_curso": 2}, headers=auth)
    assert changed.status_code == 200
    assert changed.json["data"]["estudante"] == {"matricula_estudante": "NOVA01", "id_curso": 2}

    url = f"{BASE}/{teacher['id_usuario']}"
    current = client.get(url, headers=admin["headers"])
    auth = versioned(admin, current)
    external = {"tipo_professor": "externo", "instituicao_origem_professor": "UFAM"}
    blocked = client.patch(url, json=external, headers=auth)
    assert blocked.status_code == 409 and error_code(blocked) == "UC_14_M07"
    no_place = client.patch(url, json={"tipo_professor": "externo"}, headers=auth)
    assert error_code(no_place) == "UC_14_M02"
    done = client.patch(url, json={"titulacao_professor": "doutor"}, headers=auth)
    assert done.json["data"]["professor"]["titulacao_professor"] == "Doutor"


def test_active_advising_blocks_inactivation(app, client, admin, teacher):
    from backend.defense_models import Orientacao, TrabalhoTcc

    student = create(
        client,
        admin,
        payload(tipo_cadastro="estudante", matricula_estudante=uuid4().hex[:12], id_curso=1),
    ).json["data"]
    with app.app_context():
        work = TrabalhoTcc(
            id_estudante=student["id_usuario"],
            titulo_trabalho_tcc="Trabalho",
            modalidade_trabalho_tcc="monografia",
        )
        db.session.add(work)
        db.session.flush()
        db.session.add(
            Orientacao(
                id_trabalho_tcc=work.id_trabalho_tcc,
                id_professor=teacher["id_usuario"],
                papel_orientacao="orientador",
                situacao_aceite_orientacao="aceito",
                id_usuario_registro=student["id_usuario"],
            )
        )
        db.session.commit()
    url = f"{BASE}/{teacher['id_usuario']}"
    current = client.get(url, headers=admin["headers"])
    blocked = client.patch(
        f"{url}/situacao",
        json={"ativo_usuario": False, "justificativa": "Desligamento"},
        headers=versioned(admin, current),
    )
    assert error_code(blocked) == "UC_14_M12"
    assert blocked.json["error"]["fields"]["vinculos"][0]["tipo"] == "orientacao"


def test_institutional_email_rule(client, admin, teacher):
    student = payload(
        tipo_cadastro="estudante",
        matricula_estudante=uuid4().hex[:12],
        id_curso=1,
    )
    outsiders = (
        "pessoa@gmail.com",
        "pessoa@fakeuea.edu.br",
        "pessoa@uea.edu.br.exemplo.com",
    )
    for address in outsiders:
        for data in (payload(), docente(), student):
            response = client.post(
                BASE, json={**data, "email_usuario": address}, headers=admin["headers"]
            )
            assert response.status_code == 422 and error_code(response) == "UC_14_M03"
            assert "email_usuario" in response.json["error"]["fields"]
    assert create(client, admin, {**payload(), "email_usuario": "Pessoa@UEA.edu.br"})
    external = payload(
        email_usuario=f"{uuid4().hex}@ufam.edu.br",
        tipo_cadastro="docente",
        tipo_professor="externo",
        titulacao_professor="doutor",
        instituicao_origem_professor="UFAM",
    )
    created = create(client, admin, external)
    url = f"{BASE}/{created.json['data']['id_usuario']}"
    auth = versioned(admin, created)
    internal = client.patch(url, json={"tipo_professor": "interno"}, headers=auth)
    assert error_code(internal) == "UC_14_M03"
    other = client.patch(url, json={"email_usuario": "novo@ufam.edu.br"}, headers=auth)
    assert other.status_code == 200

    legacy = f"{BASE}/{teacher['id_usuario']}"
    current = client.get(legacy, headers=admin["headers"])
    auth = versioned(admin, current)
    denied = client.patch(legacy, json={"email_usuario": "novo@gmail.com"}, headers=auth)
    assert error_code(denied) == "UC_14_M03"
    kept = client.patch(legacy, json={"nome_usuario": "Nome Mantido"}, headers=auth)
    assert kept.status_code == 200

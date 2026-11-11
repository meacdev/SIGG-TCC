import pytest


@pytest.mark.parametrize("url", ["https://[invalid", "https://example.com:invalid"])
def test_malformed_lattes_is_validation_error(client, password, url):
    response = client.post(
        "/api/v1/usuarios",
        json={
            "nome_usuario": "Nome",
            "email_usuario": "edge@example.com",
            "senha": password,
            "titulacao_docente": "mestre",
            "url_lattes_docente": url,
        },
    )
    assert response.status_code == 422
    assert response.json["error"]["code"] == "URL_INVALIDA"


def test_reset_rejects_non_string_recovery_id(client, password):
    response = client.post(
        "/api/v1/auth/recuperacao-senha/redefinir",
        json={
            "id_recuperacao": [],
            "token_redefinicao": "invalid",
            "nova_senha": password,
            "confirmacao_senha": password,
        },
    )
    assert response.status_code == 422

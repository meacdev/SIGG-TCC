import re
from urllib.parse import urlparse

from email_validator import EmailNotValidError, validate_email
from flask import request

from backend.errors import APIError


def body(allowed, required=(), code="VALIDACAO"):
    data = request.get_json()
    if not isinstance(data, dict):
        raise APIError(422, code, "Envie um objeto JSON.")
    unknown = set(data) - set(allowed)
    missing = [k for k in required if data.get(k) is None or data.get(k) == ""]
    if unknown:
        raise APIError(422, code, "Campos não permitidos.", {k: "Não permitido." for k in unknown})
    if missing:
        raise APIError(
            422,
            code,
            "Preencha todos os campos obrigatórios.",
            {k: "Obrigatório." for k in missing},
        )
    return data


def text(value, field, maximum=200, minimum=1):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise APIError(
            422,
            "VALIDACAO",
            "Campo inválido.",
            {field: f"Informe entre {minimum} e {maximum} caracteres."},
        )
    return value.strip()


def email(value, code="EMAIL_INVALIDO"):
    try:
        if not isinstance(value, str):
            raise ValueError
        normalized = validate_email(value.strip(), check_deliverability=False).normalized.lower()
        if len(normalized) > 254:
            raise ValueError
        return normalized
    except EmailNotValidError, ValueError:
        raise APIError(422, code, "Informe um endereço de e-mail válido.") from None


def password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 128 or value.isspace():
        raise APIError(422, "SENHA_INVALIDA", "A senha deve conter de 12 a 128 caracteres.")
    return value


def integer(value, field, minimum=1, maximum=9223372036854775807):
    if type(value) is not int or not minimum <= value <= maximum:
        raise APIError(422, "VALIDACAO", "Número inválido.", {field: "Valor fora do intervalo."})
    return value


def choice(value, field, choices):
    if value not in choices or not isinstance(value, str):
        raise APIError(422, "VALIDACAO", "Opção inválida.", {field: ", ".join(choices)})
    return value


def lattes(value):
    if value in (None, ""):
        return None
    value = text(value, "url_lattes_docente", 2048)
    try:
        parsed = urlparse(value)
        valid = parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username
        # Accessing .port validates malformed textual ports as well.
        _ = parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise APIError(422, "URL_INVALIDA", "Informe uma URL HTTP ou HTTPS válida.")
    return value


def period(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}/[12]", value):
        raise APIError(422, "PERIODO_INVALIDO", "Informe o período no formato AAAA/1 ou AAAA/2.")
    year, semester = map(int, value.split("/"))
    integer(year, "periodo_letivo", 2000, 9999)
    return year, semester


def class_code(value):
    value = text(value, "codigo_turma", 40).upper()
    if not re.fullmatch(r"EST[A-Z]+[0-9]+", value):
        raise APIError(422, "CODIGO_TURMA_INVALIDO", "Use EST<SIGLA><NUM>, por exemplo ESTCOMP01.")
    return value


def pagination():
    try:
        page = int(request.args.get("page", "1"))
        size = int(request.args.get("per_page", "20"))
    except ValueError:
        raise APIError(422, "PAGINACAO_INVALIDA", "Informe uma paginação válida.") from None
    integer(page, "page", 1, 100000)
    integer(size, "per_page", 1, 100)
    return page, size

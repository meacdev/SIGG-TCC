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


PASSWORD_RULE = (
    "A senha deve ter de 8 a 128 caracteres, com ao menos 1 letra maiúscula, "
    "1 número e 1 caractere especial."
)


def password(value):
    """RF21.1.1: 8 to 128 characters, with an uppercase letter, a digit and a special one."""
    if (
        not isinstance(value, str)
        or not 8 <= len(value) <= 128
        or not any(c.isupper() for c in value)
        or not any(c.isdigit() for c in value)
        or all(c.isalnum() for c in value)
    ):
        raise APIError(422, "SENHA_INVALIDA", PASSWORD_RULE)
    return value


def cpf(value):
    """RF20.1 and ck_usuario_cpf: optional, stored as 11 digits with valid check digits."""
    if value in (None, ""):
        return None
    digits = re.sub(r"[.\-\s]", "", value) if isinstance(value, str) else ""
    valid = re.fullmatch(r"[0-9]{11}", digits) is not None and len(set(digits)) > 1
    for size in (9, 10):
        if not valid:
            break
        total = sum(int(d) * (size + 1 - i) for i, d in enumerate(digits[:size]))
        valid = int(digits[size]) == total * 10 % 11 % 10
    if not valid:
        raise APIError(
            422, "CPF_INVALIDO", "Informe um CPF válido.", {"cpf_usuario": "CPF inválido."}
        )
    return digits


def phone(value):
    """RF20.1: optional contact phone, stored as digits (DDD + number, optional country code)."""
    if value in (None, ""):
        return None
    valid = isinstance(value, str) and re.fullmatch(r"\+?[0-9\s().\-]{10,30}", value.strip())
    digits = re.sub(r"[^0-9]", "", value) if valid else ""
    if not 10 <= len(digits) <= 13:
        raise APIError(
            422,
            "TELEFONE_INVALIDO",
            "Informe um telefone válido com DDD.",
            {"telefone_usuario": "Use de 10 a 13 dígitos, por exemplo (92) 99999-9999."},
        )
    return digits


def integer(value, field, minimum=1, maximum=9223372036854775807):
    if type(value) is not int or not minimum <= value <= maximum:
        raise APIError(422, "VALIDACAO", "Número inválido.", {field: "Valor fora do intervalo."})
    return value


def choice(value, field, choices):
    if value not in choices or not isinstance(value, str):
        raise APIError(422, "VALIDACAO", "Opção inválida.", {field: ", ".join(choices)})
    return value


def _parsed_url(value, field):
    value = text(value, field, 2048)
    try:
        parsed = urlparse(value)
        valid = parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username
        # Accessing .port validates malformed textual ports as well.
        _ = parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise APIError(422, "URL_INVALIDA", "Informe uma URL HTTP ou HTTPS válida.")
    return value, parsed


def url(value, field):
    return _parsed_url(value, field)[0]


def lattes(value):
    """RF20.2.2 and ck_professor_lattes: http(s)://lattes.cnpq.br/..."""
    if value in (None, ""):
        return None
    value, parsed = _parsed_url(value, "url_lattes_professor")
    if parsed.hostname != "lattes.cnpq.br" or not value.lower().startswith(
        ("http://lattes.cnpq.br/", "https://lattes.cnpq.br/")
    ):
        raise APIError(
            422,
            "URL_INVALIDA",
            "Informe o link do Currículo Lattes (https://lattes.cnpq.br/...).",
            {"url_lattes_professor": "Use um endereço de lattes.cnpq.br."},
        )
    return value


def name(value, field="nome_usuario"):
    """RF20.1.1 and ck_usuario_nome: 3 to 100 characters."""
    return text(value, field, 100, 3)


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

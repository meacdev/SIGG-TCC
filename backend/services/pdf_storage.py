import hashlib
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import current_app
from pypdf import PdfReader
from werkzeug.utils import secure_filename

from backend.db import db
from backend.document_models import ArquivoPDF
from backend.errors import APIError

MAX_PDF_BYTES = 50 * 1024 * 1024


def validate_pdf(content):
    if not content or len(content) > MAX_PDF_BYTES:
        raise APIError(422, "PDF_TAMANHO_INVALIDO", "Envie um PDF de até 50 MB.")
    try:
        if not content.startswith(b"%PDF-"):
            raise ValueError
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 2000:
            raise ValueError
        root = reader.trailer["/Root"]
        if "/OpenAction" in root or "/AA" in root:
            raise ValueError
        names = root.get("/Names", {})
        if hasattr(names, "get_object"):
            names = names.get_object()
        if any(key in names for key in ("/JavaScript", "/EmbeddedFiles")):
            raise ValueError
        for page in reader.pages:
            if "/AA" in page:
                raise ValueError
    except Exception:
        raise APIError(
            422, "PDF_INVALIDO", "Envie um PDF válido, sem criptografia ou conteúdo ativo."
        ) from None
    return reader


def root_directory():
    return Path(current_app.config["PRIVATE_STORAGE_DIR"]).resolve()


def file_path(file):
    root = root_directory()
    path = (root / file.chave_armazenamento_arquivo_pdf).resolve()
    if path.parent != root:
        raise APIError(503, "ARQUIVO_INDISPONIVEL", "Não foi possível acessar o arquivo.")
    return path


def save(content, name, user_id):
    validate_pdf(content)
    root = root_directory()
    key = uuid4().hex + ".pdf"
    try:
        root.mkdir(parents=True, exist_ok=True)
        with (root / key).open("xb") as stream:
            stream.write(content)
    except OSError:
        raise APIError(
            503, "ARMAZENAMENTO_INDISPONIVEL", "Não foi possível armazenar o PDF."
        ) from None
    result = ArquivoPDF(
        nome_original_arquivo_pdf=(secure_filename(name) or "documento.pdf")[:255],
        chave_armazenamento_arquivo_pdf=key,
        tamanho_bytes_arquivo_pdf=len(content),
        sha256_arquivo_pdf=hashlib.sha256(content).hexdigest(),
        id_usuario_envio=user_id,
    )
    db.session.add(result)
    try:
        db.session.flush()
    except Exception:
        (root / key).unlink(missing_ok=True)
        raise
    return result


def read(file):
    try:
        content = file_path(file).read_bytes()
    except OSError:
        raise APIError(503, "ARQUIVO_INDISPONIVEL", "Não foi possível acessar o arquivo.") from None
    if (
        len(content) != file.tamanho_bytes_arquivo_pdf
        or hashlib.sha256(content).hexdigest() != file.sha256_arquivo_pdf
    ):
        raise APIError(
            503, "ARQUIVO_INDISPONIVEL", "A integridade do arquivo não pôde ser confirmada."
        )
    return content


def discard(files):
    for file in files:
        try:
            file_path(file).unlink(missing_ok=True)
        except OSError:
            current_app.logger.error("Falha ao remover arquivo temporário de documento.")

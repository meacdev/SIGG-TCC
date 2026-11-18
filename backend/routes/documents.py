from io import BytesIO

from flask import Blueprint, g, jsonify, request, send_file
from sqlalchemy import select

from backend import validation as v
from backend.db import db
from backend.defense_models import Banca, Etapa, TrabalhoTcc
from backend.document_models import Ata, Declaracao, Documento
from backend.errors import APIError
from backend.security import authenticated, limiter
from backend.serialization import check_version, iso, resource_response
from backend.services import defenses, document_mail, documents, pdf_storage

bp = Blueprint("documents", __name__, url_prefix="/api/v1")


def pdf_response(file):
    return send_file(
        BytesIO(pdf_storage.read(file)),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=file.nome_original_arquivo_pdf,
    )


@bp.get("/bancas/<int:defense_id>/documentos")
@authenticated()
def detail(defense_id):
    banca = defenses.get_defense(defense_id)
    return resource_response(banca, documents.info(banca))


@bp.post("/bancas/<int:defense_id>/ata")
@authenticated()
def emit(defense_id):
    banca = defenses.get_defense(defense_id, lock=True)
    data = v.body({"resultado", "prazo", "correcoes", "justificativa"})
    result = documents.emit(banca, data)
    return resource_response(banca, result, 201, "UC_10_M01", "Ata de Defesa gerada com sucesso!")


@bp.get("/bancas/<int:defense_id>/ata")
@authenticated()
def minutes_pdf(defense_id):
    banca = db.session.get(Banca, defense_id)
    minutes = documents.current_minutes(defense_id)
    if not banca or not minutes:
        raise APIError(404, "ATA_AUSENTE", "Ata não encontrada.")
    own = banca.etapa.trabalho.id_estudante == g.user.id_usuario
    examiner = defenses.member(banca)
    if not examiner and not own:
        raise APIError(403, "ACESSO_NEGADO", "Você não possui acesso a esta ata.")
    signed = request.args.get("assinada") == "true"
    if own:
        signed = True
        if (
            not minutes.documento.data_liberacao_estudante_documento_oficial
            or not documents.corrections_approved(banca)
        ):
            raise APIError(
                403,
                "UC_10_M09",
                "A Ata Assinada ficará disponível após a aprovação das correções "
                "pelo orientador e o registro do arquivo assinado.",
            )
    file = minutes.documento.arquivo_assinado if signed else minutes.documento.arquivo
    if not file:
        raise APIError(
            409, "ATA_NAO_ASSINADA", "O arquivo da ata assinada ainda não foi registrado."
        )
    return pdf_response(file)


@bp.post("/bancas/<int:defense_id>/ata/assinada")
@authenticated()
def signed(defense_id):
    banca = defenses.get_defense(defense_id, lock=True)
    check_version(banca)
    request.max_content_length = pdf_storage.MAX_PDF_BYTES + 65536
    if set(request.files) != {"arquivo"} or set(request.form) != {"assinaturas_conferidas"}:
        raise APIError(
            422, "PDF_OBRIGATORIO", "Envie o arquivo PDF e a confirmação das assinaturas."
        )
    content = request.files["arquivo"].read(pdf_storage.MAX_PDF_BYTES + 1)
    result = documents.record_signed(
        banca, content, request.form.get("assinaturas_conferidas") == "true"
    )
    return resource_response(
        banca, result, code="ATA_ASSINADA_REGISTRADA", message="Arquivo da ata assinada registrado."
    )


@bp.get("/bancas/<int:defense_id>/declaracoes/<int:document_id>")
@authenticated()
def declaration_pdf(defense_id, document_id):
    banca = defenses.get_defense(defense_id)
    item = db.session.get(Declaracao, document_id)
    members = {m.id_membro_banca for m in banca.membros}
    if (
        not item
        or item.id_membro_banca not in members
        or item.documento.data_revogacao_documento_oficial
    ):
        raise APIError(404, "DECLARACAO_AUSENTE", "Declaração não encontrada.")
    return pdf_response(item.documento.arquivo)


@bp.post("/bancas/<int:defense_id>/declaracoes/reenvio")
@authenticated()
def retry_mail(defense_id):
    banca = defenses.get_defense(defense_id)
    document_mail.deliver(banca.id_banca)
    result = documents.info(banca)
    all_sent = bool(result["emails"]) and all(n["situacao"] == "enviada" for n in result["emails"])
    return resource_response(
        banca,
        result,
        code="UC_10_M06" if all_sent else "UC_10_M07",
        message="Declarações de participação enviadas com sucesso!"
        if all_sent
        else "Não foi possível enviar todas as declarações. As falhas foram registradas.",
    )


@bp.get("/minhas-atas")
@authenticated()
def my_minutes():
    items = db.session.execute(
        select(Ata, Banca, TrabalhoTcc)
        .join(Documento, Ata.id_ata_defesa == Documento.id_documento_oficial)
        .join(Banca, Banca.id_banca == Ata.id_banca)
        .join(Etapa, Etapa.id_etapa_trabalho == Banca.id_etapa_trabalho)
        .join(TrabalhoTcc, TrabalhoTcc.id_trabalho_tcc == Etapa.id_trabalho_tcc)
        .where(
            TrabalhoTcc.id_estudante == g.user.id_usuario,
            Documento.data_revogacao_documento_oficial.is_(None),
        )
        .order_by(Banca.data_inicio_banca.desc())
        .limit(100)
    ).all()
    return jsonify(
        data=[
            {
                "id_banca": banca.id_banca,
                "titulo": work.titulo_trabalho_tcc,
                "resultado": banca.resultado_banca,
                "assinada": ata.documento.id_arquivo_assinado is not None,
                "liberada": ata.documento.data_liberacao_estudante_documento_oficial is not None
                and documents.corrections_approved(banca),
            }
            for ata, banca, work in items
        ]
    )


@bp.get("/documentos/verificar")
@limiter.limit("30 per minute")
def verify():
    code = v.text(request.args.get("codigo"), "codigo", 100)
    document = db.session.scalar(
        select(Documento).where(Documento.codigo_verificacao_documento_oficial == code)
    )
    if not document:
        raise APIError(404, "DOCUMENTO_AUSENTE", "Documento não encontrado.")
    return jsonify(
        data={
            "vigente": document.data_revogacao_documento_oficial is None,
            "tipo": document.modelo.tipo_modelo_documento,
            "data_emissao": iso(document.data_emissao_documento_oficial),
            "sha256": document.arquivo.sha256_arquivo_pdf,
            "sha256_assinado": document.arquivo_assinado.sha256_arquivo_pdf
            if document.arquivo_assinado
            else None,
        }
    )

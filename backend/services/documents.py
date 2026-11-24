import secrets
from datetime import date

from flask import current_app, g
from sqlalchemy import select

from backend import official_rubric as official
from backend import validation as v
from backend.academic_models import NotificacaoAcademica as NotificacaoDocumento
from backend.audit import audit
from backend.db import db, utcnow
from backend.document_models import (
    Ata,
    Declaracao,
    Documento,
    EntregaCorrecao,
    ModeloDocumento,
    Solicitacao,
)
from backend.errors import APIError
from backend.models import Curso, ProfessorCurso, Turma, Usuario
from backend.serialization import check_version, iso
from backend.services import classes, defense_pdf, defenses, document_mail, pdf_storage

RESULTS = {
    "aprovado": "Aprovado",
    "reprovado": "Reprovado",
    "aprovado_com_correcoes": "Aprovado com Correções",
}
EXAMINER_LABELS = ["Primeiro Avaliador", "Segundo Avaliador"]


def member_label(member, index):
    if member.papel_membro_banca == "presidente":
        return "Orientador"
    return EXAMINER_LABELS[index] if index < len(EXAMINER_LABELS) else f"Avaliador {index + 1}"


def coordinator_name(course_id):
    return db.session.scalar(
        select(Usuario.nome_usuario)
        .join(ProfessorCurso, ProfessorCurso.id_professor == Usuario.id_usuario)
        .where(
            ProfessorCurso.id_curso == course_id,
            ProfessorCurso.coordenador_professor_curso.is_(True),
            classes.current_link(),
        )
        .order_by(ProfessorCurso.data_inicio_professor_curso.desc())
        .limit(1)
    )


def needs_approval_sheet(banca, result):
    """A Folha de Aprovação é exclusiva de TCC 2 e de artigo, e só para trabalho aprovado."""
    work = banca.etapa.trabalho
    level = banca.etapa.matricula.turma.nivel_turma
    return result != "reprovado" and (level == 2 or work.modalidade_trabalho_tcc == "artigo")


MONTHS = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]


def current_minutes(defense_id):
    return db.session.scalar(
        select(Ata)
        .join(Documento)
        .where(
            Ata.id_banca == defense_id,
            Documento.data_revogacao_documento_oficial.is_(None),
        )
        .order_by(Ata.versao_ata_defesa.desc())
    )


def request_for(banca):
    return db.session.scalar(select(Solicitacao).where(Solicitacao.id_banca == banca.id_banca))


def corrections_approved(banca):
    correction = request_for(banca)
    if not correction:
        return banca.resultado_banca != "aprovado_com_correcoes"
    return (
        db.session.scalar(
            select(EntregaCorrecao.id_entrega_correcao).where(
                EntregaCorrecao.id_solicitacao_correcao == correction.id_solicitacao_correcao,
                EntregaCorrecao.situacao_entrega_correcao == "aprovado",
            )
        )
        is not None
    )


def release_if_ready(banca, minutes):
    document = minutes.documento
    if document.id_arquivo_assinado and corrections_approved(banca):
        document.data_liberacao_estudante_documento_oficial = utcnow()


def info(banca):
    minutes = current_minutes(banca.id_banca)
    correction = request_for(banca)
    pending = list(
        db.session.scalars(
            select(NotificacaoDocumento).where(
                NotificacaoDocumento.id_banca == banca.id_banca,
                NotificacaoDocumento.tipo_notificacao == "declaracao_banca",
                NotificacaoDocumento.situacao_notificacao != "cancelada",
            )
        )
    )
    declarations = list(
        db.session.scalars(
            select(Declaracao)
            .join(Documento)
            .join(
                NotificacaoDocumento,
                NotificacaoDocumento.id_documento_oficial == Documento.id_documento_oficial,
            )
            .where(
                NotificacaoDocumento.id_banca == banca.id_banca,
                Documento.data_revogacao_documento_oficial.is_(None),
            )
        )
    )
    return {
        "ata": None
        if not minutes
        else {
            "id_documento": minutes.id_ata_defesa,
            "versao": minutes.versao_ata_defesa,
            "codigo_verificacao": minutes.documento.codigo_verificacao_documento_oficial,
            "data_emissao": iso(minutes.documento.data_emissao_documento_oficial),
            "assinada": minutes.documento.id_arquivo_assinado is not None,
            "liberada_aluno": minutes.documento.data_liberacao_estudante_documento_oficial
            is not None,
        },
        "resultado": banca.resultado_banca,
        "prazo": correction.data_limite_reenvio_solicitacao_correcao.isoformat()
        if correction
        else None,
        "correcoes": correction.descricao_solicitacao_correcao if correction else None,
        "declaracoes": [
            {
                "id_documento": d.id_declaracao_banca,
                "codigo_verificacao": d.documento.codigo_verificacao_documento_oficial,
            }
            for d in declarations
        ],
        "emails": [
            {
                "id_notificacao": n.id_notificacao,
                "situacao": n.situacao_notificacao,
                "tentativas": n.tentativas_notificacao,
            }
            for n in pending
        ],
    }


def template(kind):
    result = db.session.scalar(
        select(ModeloDocumento)
        .where(
            ModeloDocumento.tipo_modelo_documento == kind,
            ModeloDocumento.ativo_modelo_documento.is_(True),
        )
        .order_by(ModeloDocumento.versao_modelo_documento.desc())
    )
    if not result:
        result = ModeloDocumento(
            tipo_modelo_documento=kind,
            versao_modelo_documento=1,
            nome_modelo_documento="Ata de Defesa"
            if kind == "ata_defesa"
            else "Declaração de Participação",
            conteudo_template_modelo_documento=(
                "Modelo operacional SIGG-TCC - NUCOMP/UEA; homologar com a instituição."
            ),
        )
        db.session.add(result)
        db.session.flush()
    return result


def emit(banca, data):
    check_version(banca)
    try:
        rubric = defenses.criteria(banca)
        consolidated = defenses.consolidation(banca, rubric)
    except APIError:
        raise APIError(
            409,
            "UC_10_M03",
            "Não foi possível calcular a média final. Verifique os critérios de avaliação.",
        ) from None
    if consolidated["media_final"] is None:
        missing = ", ".join(
            examiner["nome"] for examiner in consolidated["avaliadores"] if not examiner["enviada"]
        )
        hint = f" Avaliações pendentes: {missing}." if missing else ""
        raise APIError(409, "UC_10_M02", f"A ata exige todas as avaliações definitivas.{hint}")
    if banca.situacao_banca == "cancelada":
        raise APIError(
            409, "BANCA_CANCELADA", "Não é possível gerar documentos de uma banca cancelada."
        )
    # RN05: o resultado não é escolhido; decorre da média final e da observação de alterações.
    reason = data.get("correcoes")
    if reason is None or (isinstance(reason, str) and not reason.strip()):
        reason = ""
    else:
        reason = v.text(reason, "correcoes", 10000)
    result = official.result_for(consolidated["media_final"], reason)
    deadline = None
    if result == "aprovado_com_correcoes":
        try:
            deadline = date.fromisoformat(data.get("prazo", ""))
            today = utcnow().astimezone(current_app.config["ACADEMIC_TIMEZONE"]).date()
            if deadline < today:
                raise ValueError
        except (ValueError, TypeError):
            raise APIError(
                422, "UC_10_M05", "Informe o prazo para envio das correções solicitadas."
            ) from None
    previous = current_minutes(banca.id_banca)
    correction = request_for(banca)
    if previous:
        if previous.documento.id_arquivo_assinado:
            raise APIError(
                409, "ATA_ASSINADA", "A ata assinada não pode ser reemitida por este fluxo."
            )
        if correction and db.session.scalar(
            select(EntregaCorrecao.id_entrega_correcao)
            .where(EntregaCorrecao.id_solicitacao_correcao == correction.id_solicitacao_correcao)
            .limit(1)
        ):
            raise APIError(
                409,
                "CORRECOES_INICIADAS",
                "Não é possível reemitir a ata após o início das correções.",
            )
        justification = v.text(data.get("justificativa"), "justificativa", 2000)
    else:
        justification = "Primeira emissão da ata"
    version = previous.versao_ata_defesa + 1 if previous else 1
    turma = db.session.get(Turma, banca.etapa.matricula.id_turma)
    course = db.session.get(Curso, turma.id_curso)
    members = defenses.accepted_members(banca)
    examiners_seen = 0
    labels = {}
    for m in members:
        labels[m.id_membro_banca] = member_label(m, examiners_seen)
        if m.papel_membro_banca != "presidente":
            examiners_seen += 1
    advisor_member = next((m for m in members if m.papel_membro_banca == "presidente"), None)
    defense_date = banca.data_inicio_banca.astimezone(current_app.config["ACADEMIC_TIMEZONE"])
    snapshot = {
        **defenses.defense_json(banca, False),
        "versao": version,
        "criterios": rubric,
        "resultado_label": RESULTS[result],
        "resultado": result,
        "media_final": consolidated["media_final"],
        "prazo": deadline.strftime("%d/%m/%Y") if deadline else None,
        "correcoes": reason,
        "nivel": turma.nivel_turma,
        "orientador": advisor_member.avaliador.usuario.nome_usuario if advisor_member else "",
        "responsavel_disciplina": turma.responsavel.nome_usuario if turma.responsavel else "",
        "coordenador_curso": coordinator_name(course.id_curso) or "",
        "data_defesa": defense_date.strftime("%d/%m/%Y"),
        "data_extenso": f"{defense_date.day} de {MONTHS[defense_date.month - 1]} "
        f"de {defense_date.year}",
        "folha_aprovacao": needs_approval_sheet(banca, result),
        "componentes": [{"chave": key, **value} for key, value in official.COMPONENTS.items()],
        "conceitos": {key: value["nome"] for key, value in official.CONCEPTS.items()},
        "data_local": banca.data_inicio_banca.astimezone(
            current_app.config["ACADEMIC_TIMEZONE"]
        ).strftime("%d/%m/%Y às %H:%M (Manaus)"),
        "membros": [
            {
                "id_docente": m.id_docente,
                "id_membro": m.id_membro_banca,
                "nome": m.avaliador.usuario.nome_usuario,
                "papel": m.papel_membro_banca,
                "rotulo": labels[m.id_membro_banca],
                "titulacao": m.avaliador.titulacao_avaliador,
                "email": m.avaliador.usuario.email_usuario,
                "nota": defenses.decimal_text(defenses.weighted(m.avaliacao.notas, rubric)),
                "subtotais": defenses.subtotals(
                    {n.id_criterio_rubrica: n.valor_nota_criterio for n in m.avaliacao.notas},
                    rubric,
                ),
                "notas_por_criterio": {
                    str(n.id_criterio_rubrica): defenses.decimal_text(n.valor_nota_criterio)
                    for n in m.avaliacao.notas
                },
                "conceitos_por_criterio": {
                    str(n.id_criterio_rubrica): n.conceito_nota_criterio for n in m.avaliacao.notas
                },
            }
            for m in members
        ],
    }
    files = []
    try:
        code = secrets.token_urlsafe(24)
        content = defense_pdf.render(snapshot, code)
        file = pdf_storage.save(
            content, f"ata-defesa-{banca.id_banca}-v{version}.pdf", g.user.id_usuario
        )
        files.append(file)
        document = Documento(
            id_modelo_documento=template("ata_defesa").id_modelo_documento,
            id_arquivo_pdf=file.id_arquivo_pdf,
            codigo_verificacao_documento_oficial=code,
        )
        db.session.add(document)
        db.session.flush()
        minutes = Ata(
            id_ata_defesa=document.id_documento_oficial,
            id_banca=banca.id_banca,
            versao_ata_defesa=version,
            snapshot_ata_defesa=snapshot,
        )
        db.session.add(minutes)
        if previous:
            previous.documento.data_revogacao_documento_oficial = utcnow()
            old = list(
                db.session.scalars(
                    select(NotificacaoDocumento).where(
                        NotificacaoDocumento.id_banca == banca.id_banca,
                        NotificacaoDocumento.tipo_notificacao == "declaracao_banca",
                        NotificacaoDocumento.id_documento_oficial.is_not(None),
                    )
                )
            )
            for notification in old:
                notification.documento.data_revogacao_documento_oficial = utcnow()
                notification.situacao_notificacao = "cancelada"
        for examiner in snapshot["membros"]:
            code = secrets.token_urlsafe(24)
            file = pdf_storage.save(
                defense_pdf.render(snapshot, code, examiner),
                "declaracao-participacao.pdf",
                g.user.id_usuario,
            )
            files.append(file)
            declaration_doc = Documento(
                id_modelo_documento=template("declaracao").id_modelo_documento,
                id_arquivo_pdf=file.id_arquivo_pdf,
                codigo_verificacao_documento_oficial=code,
            )
            db.session.add(declaration_doc)
            db.session.flush()
            db.session.add(
                Declaracao(
                    id_declaracao_banca=declaration_doc.id_documento_oficial,
                    id_membro_banca=examiner["id_membro"],
                )
            )
            db.session.add(
                NotificacaoDocumento(
                    id_usuario_destinatario=examiner["id_docente"],
                    email_destino_notificacao=examiner["email"],
                    tipo_notificacao="declaracao_banca",
                    assunto_notificacao="Declaração de participação em banca - SIGG-TCC",
                    corpo_notificacao=(
                        "Sua declaração de participação segue em anexo. "
                        f"Código de verificação: {code}"
                    ),
                    id_banca=banca.id_banca,
                    id_documento_oficial=declaration_doc.id_documento_oficial,
                    chave_idempotencia_notificacao=f"declaracao:{declaration_doc.id_documento_oficial}",
                )
            )
        if result == "aprovado_com_correcoes":
            if not correction:
                correction = Solicitacao(
                    id_banca=banca.id_banca, id_usuario_registro=g.user.id_usuario
                )
                db.session.add(correction)
            correction.descricao_solicitacao_correcao = reason
            correction.data_limite_reenvio_solicitacao_correcao = deadline
        elif correction:
            db.session.delete(correction)
        banca.resultado_banca = result
        banca.situacao_banca = "concluida"
        banca.data_conclusao_banca = utcnow()
        banca.versao_banca += 1
        audit(g.user.id_usuario, "ata_emitida", "banca", banca.id_banca, reason=justification)
        db.session.commit()
    except Exception:
        pdf_storage.discard(files)
        db.session.rollback()
        raise APIError(
            503, "UC_10_M08", "Não foi possível gerar o arquivo PDF. Tente novamente."
        ) from None
    # PDF persistence is committed first; mail failure cannot invalidate an emitted minutes file.
    document_mail.deliver(banca.id_banca)
    db.session.refresh(banca)
    return info(banca)


def record_signed(banca, content, confirmed):
    check_version(banca)
    if not confirmed:
        raise APIError(
            422,
            "ASSINATURAS_NAO_CONFERIDAS",
            "Confirme que as assinaturas dos membros foram conferidas.",
        )
    minutes = current_minutes(banca.id_banca)
    if not minutes:
        raise APIError(409, "ATA_AUSENTE", "Gere a ata antes de registrar o arquivo assinado.")
    if minutes.documento.id_arquivo_assinado:
        raise APIError(409, "ATA_ASSINADA", "O arquivo assinado já foi registrado.")
    file = pdf_storage.save(content, "ata-assinada.pdf", g.user.id_usuario)
    try:
        minutes.documento.id_arquivo_assinado = file.id_arquivo_pdf
        minutes.documento.data_assinatura_documento_oficial = utcnow()
        release_if_ready(banca, minutes)
        banca.versao_banca += 1
        audit(
            g.user.id_usuario,
            "ata_assinada_registrada",
            "banca",
            banca.id_banca,
            reason="Responsável confirmou a conferência das assinaturas",
        )
        db.session.commit()
    except Exception:
        pdf_storage.discard([file])
        db.session.rollback()
        raise
    return info(banca)

"""Official documents and private PDF metadata, using the supplied table names."""

from backend.db import ID, UTCDateTime, db, utcnow


class ArquivoPDF(db.Model):
    __tablename__ = "arquivo_pdf"
    id_arquivo_pdf = db.Column(ID, primary_key=True)
    nome_original_arquivo_pdf = db.Column(db.String(255), nullable=False)
    chave_armazenamento_arquivo_pdf = db.Column(db.Text, nullable=False, unique=True)
    mime_type_arquivo_pdf = db.Column(
        db.String(50), nullable=False, default="application/pdf", server_default="application/pdf"
    )
    tamanho_bytes_arquivo_pdf = db.Column(ID, nullable=False)
    sha256_arquivo_pdf = db.Column(db.String(64), nullable=False)
    id_usuario_envio = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False)
    data_envio_arquivo_pdf = db.Column(UTCDateTime, nullable=False, default=utcnow)


class ModeloDocumento(db.Model):
    __tablename__ = "modelo_documento"
    __table_args__ = (db.UniqueConstraint("tipo_modelo_documento", "versao_modelo_documento"),)
    id_modelo_documento = db.Column(ID, primary_key=True)
    tipo_modelo_documento = db.Column(db.String(20), nullable=False)
    versao_modelo_documento = db.Column(db.SmallInteger, nullable=False)
    nome_modelo_documento = db.Column(db.String(150), nullable=False)
    conteudo_template_modelo_documento = db.Column(db.Text, nullable=False)
    ativo_modelo_documento = db.Column(db.Boolean, nullable=False, default=True)


class Documento(db.Model):
    __tablename__ = "documento_oficial"
    id_documento_oficial = db.Column(ID, primary_key=True)
    id_modelo_documento = db.Column(
        ID, db.ForeignKey("modelo_documento.id_modelo_documento"), nullable=False
    )
    id_arquivo_pdf = db.Column(
        ID, db.ForeignKey("arquivo_pdf.id_arquivo_pdf"), nullable=False, unique=True
    )
    codigo_verificacao_documento_oficial = db.Column(db.String(100), nullable=False, unique=True)
    data_emissao_documento_oficial = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_assinatura_documento_oficial = db.Column(UTCDateTime)
    data_liberacao_estudante_documento_oficial = db.Column(UTCDateTime)
    data_revogacao_documento_oficial = db.Column(UTCDateTime)
    arquivo = db.relationship(ArquivoPDF, foreign_keys=[id_arquivo_pdf])
    modelo = db.relationship(ModeloDocumento)
    id_arquivo_assinado = db.Column(ID, db.ForeignKey("arquivo_pdf.id_arquivo_pdf"))
    arquivo_assinado = db.relationship(ArquivoPDF, foreign_keys=[id_arquivo_assinado])


class Ata(db.Model):
    __tablename__ = "ata_defesa"
    __table_args__ = (db.UniqueConstraint("id_banca_defesa", "versao_ata_defesa"),)
    id_ata_defesa = db.Column(
        ID, db.ForeignKey("documento_oficial.id_documento_oficial"), primary_key=True
    )
    id_banca = db.Column(
        "id_banca_defesa", ID, db.ForeignKey("banca_defesa.id_banca_defesa"), nullable=False
    )
    versao_ata_defesa = db.Column(db.Integer, nullable=False, default=1)
    snapshot_ata_defesa = db.Column(db.JSON, nullable=False)
    documento = db.relationship(Documento)


class Declaracao(db.Model):
    __tablename__ = "declaracao_banca"
    id_declaracao_banca = db.Column(
        ID, db.ForeignKey("documento_oficial.id_documento_oficial"), primary_key=True
    )
    id_membro_banca = db.Column(ID, db.ForeignKey("membro_banca.id_membro_banca"), nullable=False)
    documento = db.relationship(Documento)


class Solicitacao(db.Model):
    __tablename__ = "solicitacao_correcao"
    id_solicitacao_correcao = db.Column(ID, primary_key=True)
    id_banca = db.Column(
        "id_banca_defesa",
        ID,
        db.ForeignKey("banca_defesa.id_banca_defesa"),
        nullable=False,
        unique=True,
    )
    descricao_solicitacao_correcao = db.Column(db.Text, nullable=False)
    data_limite_reenvio_solicitacao_correcao = db.Column(db.Date, nullable=False)
    id_usuario_registro = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False)
    data_registro_solicitacao_correcao = db.Column(
        UTCDateTime, nullable=False, default=utcnow, server_default=db.func.now()
    )


class EntregaCorrecao(db.Model):
    __tablename__ = "entrega_correcao"
    id_entrega_correcao = db.Column(ID, primary_key=True)
    id_solicitacao_correcao = db.Column(
        ID, db.ForeignKey("solicitacao_correcao.id_solicitacao_correcao"), nullable=False
    )
    id_arquivo_pdf = db.Column(
        ID, db.ForeignKey("arquivo_pdf.id_arquivo_pdf"), nullable=False, unique=True
    )
    situacao_entrega_correcao = db.Column(
        db.String(15), nullable=False, default="pendente", server_default="pendente"
    )
    id_docente_validacao = db.Column(
        "id_professor_validacao", ID, db.ForeignKey("professor.id_professor")
    )
    data_validacao_entrega_correcao = db.Column(UTCDateTime)
    parecer_entrega_correcao = db.Column(db.Text)
    arquivo = db.relationship(ArquivoPDF)

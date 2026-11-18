"""Academic prerequisite mappings, shared with the defense workflows."""

from backend.db import ID, UTCDateTime, db, utcnow


class Matricula(db.Model):
    __tablename__ = "matricula_turma"
    __table_args__ = (db.UniqueConstraint("id_turma", "id_estudante"),)
    id_matricula_turma = db.Column(ID, primary_key=True)
    id_turma = db.Column(ID, db.ForeignKey("turma.id_turma"), nullable=False)
    id_estudante = db.Column(ID, db.ForeignKey("estudante.id_estudante"), nullable=False)
    origem_matricula_turma = db.Column(db.String(15), nullable=False, default="professor")
    situacao_matricula_turma = db.Column(db.String(15), nullable=False, default="ativa")
    id_usuario_inclusao = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False)
    data_matricula_matricula_turma = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_remocao_matricula_turma = db.Column(UTCDateTime)
    motivo_remocao_matricula_turma = db.Column(db.Text)
    versao_matricula = db.Column(db.Integer, nullable=False, default=1)
    estudante = db.relationship("Estudante")
    turma = db.relationship("Turma")


class TrabalhoTcc(db.Model):
    __tablename__ = "trabalho_tcc"
    __table_args__ = (
        # One work in progress per student; concluded works stay as history.
        db.Index(
            "uq_trabalho_ativo_estudante",
            "id_estudante",
            unique=True,
            sqlite_where=db.text("situacao_trabalho_tcc = 'em_andamento'"),
            postgresql_where=db.text("situacao_trabalho_tcc = 'em_andamento'"),
        ),
    )
    id_trabalho_tcc = db.Column(ID, primary_key=True)
    id_estudante = db.Column(ID, db.ForeignKey("estudante.id_estudante"), nullable=False)
    titulo_trabalho_tcc = db.Column(db.String(500), nullable=False)
    subtitulo_trabalho_tcc = db.Column(db.String(500))
    tema_trabalho_tcc = db.Column(db.Text)
    modalidade_trabalho_tcc = db.Column(db.String(25), nullable=False)  # monografia | artigo
    tipo_artigo_trabalho_tcc = db.Column(db.String(15))  # publicado | a_submeter (only for artigo)
    url_artigo_trabalho_tcc = db.Column(db.Text)
    doi_artigo_trabalho_tcc = db.Column(db.String(255))
    situacao_trabalho_tcc = db.Column(db.String(20), nullable=False, default="em_andamento")
    data_criacao_trabalho_tcc = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_conclusao_trabalho_tcc = db.Column(UTCDateTime)
    versao_trabalho_tcc = db.Column(db.Integer, nullable=False, default=1)
    palavras_chave_trabalho_tcc = db.Column(db.JSON, nullable=False, default=list)
    id_matricula_atual = db.Column(ID, db.ForeignKey("matricula_turma.id_matricula_turma"))
    estudante = db.relationship("Estudante")


class Etapa(db.Model):
    __tablename__ = "etapa_trabalho"
    id_etapa_trabalho = db.Column(ID, primary_key=True)
    id_trabalho_tcc = db.Column(ID, db.ForeignKey("trabalho_tcc.id_trabalho_tcc"), nullable=False)
    id_matricula_turma = db.Column(
        ID, db.ForeignKey("matricula_turma.id_matricula_turma"), nullable=False, unique=True
    )
    situacao_etapa_trabalho = db.Column(db.String(25), nullable=False, default="em_andamento")
    data_inicio_etapa_trabalho = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_conclusao_etapa_trabalho = db.Column(UTCDateTime)
    data_limite_etapa_trabalho = db.Column(UTCDateTime)
    trabalho = db.relationship(TrabalhoTcc)
    matricula = db.relationship(Matricula)


class Orientacao(db.Model):
    __tablename__ = "orientacao"
    __table_args__ = (
        db.Index(
            "uq_orientacao_papel_vigente",
            "id_trabalho_tcc",
            "papel_orientacao",
            unique=True,
            sqlite_where=db.text("data_encerramento_orientacao IS NULL"),
            postgresql_where=db.text("data_encerramento_orientacao IS NULL"),
        ),
        db.Index(
            "uq_orientacao_professor_vigente",
            "id_trabalho_tcc",
            "id_professor",
            unique=True,
            sqlite_where=db.text("data_encerramento_orientacao IS NULL"),
            postgresql_where=db.text("data_encerramento_orientacao IS NULL"),
        ),
    )
    id_orientacao = db.Column(ID, primary_key=True)
    id_trabalho_tcc = db.Column(ID, db.ForeignKey("trabalho_tcc.id_trabalho_tcc"), nullable=False)
    id_professor = db.Column(ID, db.ForeignKey("professor.id_professor"), nullable=False)
    papel_orientacao = db.Column(db.String(15), nullable=False)
    situacao_aceite_orientacao = db.Column(db.String(15), nullable=False, default="pendente")
    data_solicitacao_orientacao = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_resposta_orientacao = db.Column(UTCDateTime)
    data_encerramento_orientacao = db.Column(UTCDateTime)
    id_usuario_registro = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False)
    id_usuario_encerramento = db.Column(ID, db.ForeignKey("usuario.id_usuario"))
    justificativa_encerramento_orientacao = db.Column(db.Text)
    professor = db.relationship("Professor")


class Rubrica(db.Model):
    __tablename__ = "rubrica_avaliacao"
    __table_args__ = (
        db.UniqueConstraint("id_turma", "nome_rubrica_avaliacao", "versao_rubrica_avaliacao"),
    )
    id_rubrica = db.Column("id_rubrica_avaliacao", ID, primary_key=True)
    id_turma = db.Column(ID, db.ForeignKey("turma.id_turma"), nullable=False)
    nome_rubrica = db.Column("nome_rubrica_avaliacao", db.String(150), nullable=False)
    versao_rubrica = db.Column(
        "versao_rubrica_avaliacao", db.SmallInteger, nullable=False, default=1, server_default="1"
    )
    situacao_rubrica = db.Column(
        "situacao_rubrica_avaliacao",
        db.String(15),
        nullable=False,
        default="rascunho",
        server_default="rascunho",
    )
    id_usuario_criacao = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False)
    data_criacao_rubrica = db.Column(
        "data_criacao_rubrica_avaliacao",
        UTCDateTime,
        nullable=False,
        default=utcnow,
        server_default=db.func.now(),
    )
    data_bloqueio_rubrica_avaliacao = db.Column(UTCDateTime)
    data_modificacao_rubrica_avaliacao = db.Column(
        UTCDateTime, nullable=False, default=utcnow, server_default=db.func.now()
    )
    criterios = db.relationship(
        "Criterio", cascade="all, delete-orphan", order_by="Criterio.ordem_criterio_rubrica"
    )


class Criterio(db.Model):
    __tablename__ = "criterio_rubrica"
    __table_args__ = (
        db.UniqueConstraint("id_rubrica_avaliacao", "nome_criterio_rubrica"),
        db.UniqueConstraint("id_rubrica_avaliacao", "ordem_criterio_rubrica"),
    )
    id_criterio_rubrica = db.Column(ID, primary_key=True)
    id_rubrica = db.Column(
        "id_rubrica_avaliacao",
        ID,
        db.ForeignKey("rubrica_avaliacao.id_rubrica_avaliacao"),
        nullable=False,
    )
    nome_criterio_rubrica = db.Column(db.String(150), nullable=False)
    descricao_criterio_rubrica = db.Column(db.Text)
    peso_criterio_rubrica = db.Column(db.Numeric(6, 3), nullable=False)
    pontuacao_maxima_criterio_rubrica = db.Column(db.Numeric(5, 2), nullable=False)
    ordem_criterio_rubrica = db.Column(db.SmallInteger, nullable=False)


class Banca(db.Model):
    __tablename__ = "banca_defesa"
    id_banca = db.Column("id_banca_defesa", ID, primary_key=True)
    id_etapa_trabalho = db.Column(
        ID, db.ForeignKey("etapa_trabalho.id_etapa_trabalho"), nullable=False
    )
    id_rubrica = db.Column(
        "id_rubrica_avaliacao",
        ID,
        db.ForeignKey("rubrica_avaliacao.id_rubrica_avaliacao"),
        nullable=False,
    )
    data_inicio_banca = db.Column("data_inicio_banca_defesa", UTCDateTime, nullable=False)
    data_fim_banca = db.Column("data_fim_banca_defesa", UTCDateTime, nullable=False)
    local_defesa_banca = db.Column("local_defesa_banca_defesa", db.Text, nullable=False)
    situacao_banca = db.Column(
        "situacao_banca_defesa",
        db.String(15),
        nullable=False,
        default="agendada",
        server_default="agendada",
    )
    resultado_banca = db.Column("resultado_banca_defesa", db.String(25))
    id_usuario_agendamento = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False)
    data_agendamento_banca = db.Column(
        "data_agendamento_banca_defesa",
        UTCDateTime,
        nullable=False,
        default=utcnow,
        server_default=db.func.now(),
    )
    data_conclusao_banca = db.Column("data_conclusao_banca_defesa", UTCDateTime)
    uid_calendario_banca = db.Column("uid_calendario_banca_defesa", db.String(200), unique=True)
    id_evento_google_banca = db.Column("id_evento_google_banca_defesa", db.String(255))
    modalidade_banca_defesa = db.Column(db.String(15), nullable=False)
    url_defesa_banca_defesa = db.Column(db.Text)
    id_arquivo_pdf_manuscrito = db.Column(
        ID, db.ForeignKey("arquivo_pdf.id_arquivo_pdf"), nullable=False
    )
    versao_banca = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    snapshot_avaliacao_banca = db.Column(db.JSON)
    etapa = db.relationship(Etapa)
    rubrica = db.relationship(Rubrica)
    membros = db.relationship("Membro", order_by="Membro.id_membro_banca")


class Membro(db.Model):
    __tablename__ = "membro_banca"
    __table_args__ = (db.UniqueConstraint("id_banca_defesa", "id_avaliador"),)
    id_membro_banca = db.Column(ID, primary_key=True)
    id_banca = db.Column(
        "id_banca_defesa", ID, db.ForeignKey("banca_defesa.id_banca_defesa"), nullable=False
    )
    id_docente = db.Column(
        "id_avaliador", ID, db.ForeignKey("avaliador.id_avaliador"), nullable=False
    )
    papel_membro_banca = db.Column(db.String(15), nullable=False, default="examinador")
    situacao_convite_membro_banca = db.Column(db.String(15), nullable=False, default="pendente")
    data_convite_membro_banca = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_resposta_membro_banca = db.Column(UTCDateTime)
    data_inicio_acesso_membro_banca = db.Column(UTCDateTime, nullable=False)
    data_fim_acesso_membro_banca = db.Column(UTCDateTime, nullable=False)
    avaliador = db.relationship("Avaliador")
    avaliacao = db.relationship("Avaliacao", uselist=False)


class Avaliacao(db.Model):
    __tablename__ = "avaliacao_banca"
    id_avaliacao = db.Column("id_avaliacao_banca", ID, primary_key=True)
    id_membro_banca = db.Column(
        ID, db.ForeignKey("membro_banca.id_membro_banca"), nullable=False, unique=True
    )
    parecer_avaliacao = db.Column("parecer_avaliacao_banca", db.Text)
    situacao_avaliacao = db.Column(
        "situacao_avaliacao_banca", db.String(15), nullable=False, default="enviada"
    )
    data_envio_avaliacao = db.Column("data_envio_avaliacao_banca", UTCDateTime)
    notas = db.relationship("Nota")


class Nota(db.Model):
    __tablename__ = "nota_criterio"
    id_avaliacao = db.Column(
        "id_avaliacao_banca",
        ID,
        db.ForeignKey("avaliacao_banca.id_avaliacao_banca"),
        primary_key=True,
    )
    id_criterio_rubrica = db.Column(
        ID, db.ForeignKey("criterio_rubrica.id_criterio_rubrica"), primary_key=True
    )
    valor_nota_criterio = db.Column(db.Numeric(5, 2), nullable=False)
    observacao_nota_criterio = db.Column(db.Text)
    data_registro_nota_criterio = db.Column(UTCDateTime, nullable=False, default=utcnow)


class Avaliador(db.Model):
    __tablename__ = "avaliador"
    id_avaliador = db.Column(ID, db.ForeignKey("usuario.id_usuario"), primary_key=True)
    tipo_avaliador = db.Column(db.String(10), nullable=False)
    instituicao_avaliador = db.Column(db.String(200), nullable=False)
    titulacao_avaliador = db.Column(db.String(20), nullable=False)
    usuario = db.relationship("Usuario")


class Manuscrito(db.Model):
    __tablename__ = "manuscrito_trabalho"
    id_manuscrito_trabalho = db.Column(ID, primary_key=True)
    id_etapa_trabalho = db.Column(
        ID, db.ForeignKey("etapa_trabalho.id_etapa_trabalho"), nullable=False
    )
    id_arquivo_pdf = db.Column(ID, db.ForeignKey("arquivo_pdf.id_arquivo_pdf"), nullable=False)
    versao_manuscrito_trabalho = db.Column(db.Integer, nullable=False)
    arquivo = db.relationship("ArquivoPDF")

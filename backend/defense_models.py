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

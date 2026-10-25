"""Academic prerequisite mappings, shared with the defense workflows."""

from backend.db import ID, UTCDateTime, db, utcnow


class Matricula(db.Model):
    __tablename__ = "matricula_turma"
    __table_args__ = (db.UniqueConstraint("id_turma", "id_aluno"),)
    id_matricula_turma = db.Column(ID, primary_key=True)
    id_turma = db.Column(ID, db.ForeignKey("turma.id_turma"), nullable=False)
    id_aluno = db.Column(ID, db.ForeignKey("aluno.id_aluno"), nullable=False)
    origem_matricula_turma = db.Column(db.String(15), nullable=False, default="professor")
    situacao_matricula_turma = db.Column(db.String(15), nullable=False, default="ativa")
    id_usuario_inclusao = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False)
    data_matricula_matricula_turma = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_remocao_matricula_turma = db.Column(UTCDateTime)
    motivo_remocao_matricula_turma = db.Column(db.Text)
    versao_matricula = db.Column(db.Integer, nullable=False, default=1)
    aluno = db.relationship("Aluno")
    turma = db.relationship("Turma")


class Trabalho(db.Model):
    __tablename__ = "trabalho"
    id_trabalho = db.Column(ID, primary_key=True)
    id_aluno = db.Column(ID, db.ForeignKey("aluno.id_aluno"), nullable=False, unique=True)
    titulo_trabalho = db.Column(db.String(500), nullable=False)
    subtitulo_trabalho = db.Column(db.String(500))
    tema_trabalho = db.Column(db.Text)
    modalidade_trabalho = db.Column(db.String(25), nullable=False)
    url_artigo_trabalho = db.Column(db.Text)
    doi_artigo_trabalho = db.Column(db.String(255))
    situacao_trabalho = db.Column(db.String(20), nullable=False, default="em_andamento")
    data_criacao_trabalho = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_conclusao_trabalho = db.Column(UTCDateTime)
    versao_trabalho = db.Column(db.Integer, nullable=False, default=1)
    palavras_chave_trabalho = db.Column(db.JSON, nullable=False, default=list)
    id_matricula_atual = db.Column(ID, db.ForeignKey("matricula_turma.id_matricula_turma"))
    aluno = db.relationship("Aluno")


class Etapa(db.Model):
    __tablename__ = "etapa_trabalho"
    id_etapa_trabalho = db.Column(ID, primary_key=True)
    id_trabalho = db.Column(ID, db.ForeignKey("trabalho.id_trabalho"), nullable=False)
    id_matricula_turma = db.Column(
        ID, db.ForeignKey("matricula_turma.id_matricula_turma"), nullable=False, unique=True
    )
    situacao_etapa_trabalho = db.Column(db.String(25), nullable=False, default="em_andamento")
    data_inicio_etapa_trabalho = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_conclusao_etapa_trabalho = db.Column(UTCDateTime)
    trabalho = db.relationship(Trabalho)
    matricula = db.relationship(Matricula)


class Orientacao(db.Model):
    __tablename__ = "orientacao"
    __table_args__ = (
        db.Index(
            "uq_orientacao_papel_vigente",
            "id_trabalho",
            "papel_orientacao",
            unique=True,
            sqlite_where=db.text("data_encerramento_orientacao IS NULL"),
            postgresql_where=db.text("data_encerramento_orientacao IS NULL"),
        ),
        db.Index(
            "uq_orientacao_docente_vigente",
            "id_trabalho",
            "id_docente",
            unique=True,
            sqlite_where=db.text("data_encerramento_orientacao IS NULL"),
            postgresql_where=db.text("data_encerramento_orientacao IS NULL"),
        ),
    )
    id_orientacao = db.Column(ID, primary_key=True)
    id_trabalho = db.Column(ID, db.ForeignKey("trabalho.id_trabalho"), nullable=False)
    id_docente = db.Column(ID, db.ForeignKey("docente.id_docente"), nullable=False)
    papel_orientacao = db.Column(db.String(15), nullable=False)
    situacao_aceite_orientacao = db.Column(db.String(15), nullable=False, default="pendente")
    data_solicitacao_orientacao = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_resposta_orientacao = db.Column(UTCDateTime)
    data_encerramento_orientacao = db.Column(UTCDateTime)
    id_usuario_registro = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False)
    id_usuario_encerramento = db.Column(ID, db.ForeignKey("usuario.id_usuario"))
    justificativa_encerramento_orientacao = db.Column(db.Text)
    docente = db.relationship("Docente")

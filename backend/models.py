"""Mappings preserve the names and keys of the supplied PostgreSQL export."""

from sqlalchemy.dialects.postgresql import INET

from backend.db import ID, UTCDateTime, db, utcnow


class Usuario(db.Model):
    __tablename__ = "usuario"
    id_usuario = db.Column(ID, primary_key=True)
    nome_usuario = db.Column(db.String(200), nullable=False)
    email_usuario = db.Column(db.String(254), unique=True, nullable=False)
    hash_senha_usuario = db.Column(db.Text)
    url_foto_usuario = db.Column(db.Text)
    ativo_usuario = db.Column(db.Boolean, nullable=False, default=True)
    data_criacao_usuario = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_atualizacao_usuario = db.Column(UTCDateTime, nullable=False, default=utcnow)
    docente = db.relationship("Docente", uselist=False, back_populates="usuario")
    aluno = db.relationship("Aluno", uselist=False, back_populates="usuario")


class Perfil(db.Model):
    __tablename__ = "perfil"
    id_perfil = db.Column(ID, primary_key=True)
    codigo_perfil = db.Column(db.String(40), unique=True, nullable=False)
    descricao_perfil = db.Column(db.String(150), nullable=False)


class UsuarioPerfil(db.Model):
    __tablename__ = "usuario_perfil"
    id_usuario = db.Column(ID, db.ForeignKey("usuario.id_usuario"), primary_key=True)
    id_perfil = db.Column(ID, db.ForeignKey("perfil.id_perfil"), primary_key=True)
    data_concessao_usuario_perfil = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_expiracao_usuario_perfil = db.Column(UTCDateTime)


class Curso(db.Model):
    __tablename__ = "curso"
    id_curso = db.Column(ID, primary_key=True)
    codigo_curso = db.Column(db.String(30), nullable=False, unique=True)
    nome_curso = db.Column(db.String(200), nullable=False)
    ativo_curso = db.Column(db.Boolean, nullable=False, default=True)


class PeriodoLetivo(db.Model):
    __tablename__ = "periodo_letivo"
    __table_args__ = (db.UniqueConstraint("ano_periodo_letivo", "semestre_periodo_letivo"),)
    id_periodo_letivo = db.Column(ID, primary_key=True)
    ano_periodo_letivo = db.Column(db.SmallInteger, nullable=False)
    semestre_periodo_letivo = db.Column(db.SmallInteger, nullable=False)
    data_inicio_periodo_letivo = db.Column(db.Date)
    data_fim_periodo_letivo = db.Column(db.Date)


class Docente(db.Model):
    __tablename__ = "docente"
    id_docente = db.Column(ID, db.ForeignKey("usuario.id_usuario"), primary_key=True)
    tipo_docente = db.Column(db.String(10), nullable=False)
    titulacao_docente = db.Column(db.String(20), nullable=False)
    instituicao_origem_docente = db.Column(db.String(200))
    url_lattes_docente = db.Column(db.Text)
    ativo_docente = db.Column(db.Boolean, nullable=False, default=True)
    usuario = db.relationship(Usuario, back_populates="docente")
    areas = db.relationship("AreaConhecimento", secondary="docente_area", lazy="selectin")


class Aluno(db.Model):
    __tablename__ = "aluno"
    id_aluno = db.Column(ID, db.ForeignKey("usuario.id_usuario"), primary_key=True)
    matricula_aluno = db.Column(db.String(30), unique=True, nullable=False)
    id_curso = db.Column(ID, db.ForeignKey("curso.id_curso"), nullable=False)
    usuario = db.relationship(Usuario, back_populates="aluno")


class AreaConhecimento(db.Model):
    __tablename__ = "area_conhecimento"
    id_area_conhecimento = db.Column(ID, primary_key=True)
    nome_area_conhecimento = db.Column(db.String(150), unique=True, nullable=False)


docente_area = db.Table(
    "docente_area",
    db.Column("id_docente", ID, db.ForeignKey("docente.id_docente"), primary_key=True),
    db.Column(
        "id_area_conhecimento",
        ID,
        db.ForeignKey("area_conhecimento.id_area_conhecimento"),
        primary_key=True,
    ),
)


class DocenteCurso(db.Model):
    __tablename__ = "docente_curso"
    __table_args__ = (db.UniqueConstraint("id_docente", "id_curso", "data_inicio_docente_curso"),)
    id_docente_curso = db.Column(ID, primary_key=True)
    id_docente = db.Column(ID, db.ForeignKey("docente.id_docente"), nullable=False)
    id_curso = db.Column(ID, db.ForeignKey("curso.id_curso"), nullable=False)
    data_inicio_docente_curso = db.Column(db.Date, nullable=False)
    data_fim_docente_curso = db.Column(db.Date)
    coordenador_docente_curso = db.Column(db.Boolean, nullable=False, default=False)
    capacidade_orientandos_docente_curso = db.Column(db.SmallInteger)


class Turma(db.Model):
    __tablename__ = "turma"
    __table_args__ = (db.UniqueConstraint("id_periodo_letivo", "codigo_turma"),)
    id_turma = db.Column(ID, primary_key=True)
    id_periodo_letivo = db.Column(
        ID, db.ForeignKey("periodo_letivo.id_periodo_letivo"), nullable=False
    )
    id_curso = db.Column(ID, db.ForeignKey("curso.id_curso"), nullable=False)
    id_docente_responsavel = db.Column(ID, db.ForeignKey("docente.id_docente"), nullable=False)
    codigo_turma = db.Column(db.String(40), nullable=False)
    nivel_turma = db.Column(db.SmallInteger, nullable=False)
    hash_codigo_acesso_turma = db.Column(db.String(128), unique=True)
    data_expiracao_acesso_turma = db.Column(UTCDateTime)
    autoinscricao_ativa_turma = db.Column(db.Boolean, nullable=False, default=False)
    data_criacao_turma = db.Column(UTCDateTime, nullable=False, default=utcnow)
    ativa_turma = db.Column(db.Boolean, nullable=False, default=True)
    data_atualizacao_turma = db.Column(UTCDateTime, nullable=False, default=utcnow)
    periodo = db.relationship(PeriodoLetivo, lazy="joined")


class Auditoria(db.Model):
    __tablename__ = "auditoria"
    id_auditoria = db.Column(ID, primary_key=True)
    id_usuario = db.Column(ID, db.ForeignKey("usuario.id_usuario"))
    acao_auditoria = db.Column(db.String(60), nullable=False)
    entidade_auditoria = db.Column(db.String(80), nullable=False)
    id_registro_auditoria = db.Column(ID, nullable=False)
    justificativa_auditoria = db.Column(db.Text)
    ip_origem_auditoria = db.Column(INET().with_variant(db.String(45), "sqlite"))
    data_ocorrencia_auditoria = db.Column(UTCDateTime, nullable=False, default=utcnow)


class AuditoriaAlteracao(db.Model):
    __tablename__ = "auditoria_alteracao"
    id_auditoria = db.Column(ID, db.ForeignKey("auditoria.id_auditoria"), primary_key=True)
    nome_campo_auditoria_alteracao = db.Column(db.String(100), primary_key=True)
    valor_anterior_auditoria_alteracao = db.Column(db.Text)
    valor_novo_auditoria_alteracao = db.Column(db.Text)


class Sessao(db.Model):
    __tablename__ = "sessao_autenticacao"
    id_sessao = db.Column(db.String(36), primary_key=True)
    id_usuario = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    refresh_jti = db.Column(db.String(36), unique=True, nullable=False)
    criada_em = db.Column(UTCDateTime, nullable=False, default=utcnow)
    ultima_atividade_em = db.Column(UTCDateTime, nullable=False, default=utcnow)
    expira_em = db.Column(UTCDateTime, nullable=False)
    revogada_em = db.Column(UTCDateTime)


class RecuperacaoSenha(db.Model):
    __tablename__ = "recuperacao_senha"
    id_recuperacao = db.Column(db.String(36), primary_key=True)
    id_usuario = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    hash_codigo = db.Column(db.String(64), nullable=False)
    expira_em = db.Column(UTCDateTime, nullable=False)
    tentativas = db.Column(db.SmallInteger, nullable=False, default=0)
    usada_em = db.Column(UTCDateTime)
    hash_token_redefinicao = db.Column(db.String(64))

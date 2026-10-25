"""Notification outbox over the table supplied by the project."""

from backend.db import ID, UTCDateTime, db, utcnow


class NotificacaoAcademica(db.Model):
    __tablename__ = "notificacao"
    id_notificacao = db.Column(ID, primary_key=True)
    id_usuario_destinatario = db.Column(ID, db.ForeignKey("usuario.id_usuario"), nullable=False)
    email_destino_notificacao = db.Column(db.String(254), nullable=False)
    tipo_notificacao = db.Column(db.String(50), nullable=False)
    assunto_notificacao = db.Column(db.String(255), nullable=False)
    corpo_notificacao = db.Column(db.Text, nullable=False)
    id_matricula_turma = db.Column(ID, db.ForeignKey("matricula_turma.id_matricula_turma"))
    # These nullable references have their foreign keys in the supplied PostgreSQL schema.
    id_orientacao = db.Column(ID)
    id_reuniao_orientacao = db.Column(ID)
    chave_idempotencia_notificacao = db.Column(db.String(200), nullable=False, unique=True)
    data_agendamento_notificacao = db.Column(UTCDateTime, nullable=False, default=utcnow)
    data_envio_notificacao = db.Column(UTCDateTime)
    situacao_notificacao = db.Column(db.String(15), nullable=False, default="pendente")
    tentativas_notificacao = db.Column(db.SmallInteger, nullable=False, default=0)
    ultimo_erro_notificacao = db.Column(db.Text)
    data_tentativa_notificacao = db.Column(UTCDateTime)

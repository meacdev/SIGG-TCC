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

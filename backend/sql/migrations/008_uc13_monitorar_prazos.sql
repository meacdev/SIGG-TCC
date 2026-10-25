CREATE TABLE IF NOT EXISTS lote_cobranca (
    id_lote VARCHAR(36) PRIMARY KEY,
    id_turma BIGINT NOT NULL REFERENCES turma(id_turma),
    id_usuario BIGINT NOT NULL REFERENCES usuario(id_usuario),
    matriculas JSONB NOT NULL,
    mensagem TEXT NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em TIMESTAMP NOT NULL,
    confirmado_em TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_lote_cobranca_turma ON lote_cobranca(id_turma, criado_em);

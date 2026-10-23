-- Complementary migration for the supplied 37-table export. Applied transactionally by CLI.
-- Do not edit after application; add a new numbered migration instead.

CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_email_normalizado ON usuario (lower(email_usuario));
UPDATE usuario SET email_usuario = lower(email_usuario) WHERE email_usuario <> lower(email_usuario);
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS data_atualizacao_usuario
    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE turma ADD COLUMN IF NOT EXISTS ativa_turma BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE turma ADD COLUMN IF NOT EXISTS data_atualizacao_turma
    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
CREATE UNIQUE INDEX IF NOT EXISTS uq_turma_codigo_normalizado
    ON turma (id_periodo_letivo, upper(codigo_turma));

CREATE TABLE sessao_autenticacao (
    id_sessao VARCHAR(36) PRIMARY KEY,
    id_usuario BIGINT NOT NULL REFERENCES usuario(id_usuario),
    refresh_jti VARCHAR(36) NOT NULL UNIQUE,
    criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultima_atividade_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em TIMESTAMPTZ NOT NULL,
    revogada_em TIMESTAMPTZ,
    CHECK (expira_em > criada_em)
);
CREATE INDEX ix_sessao_usuario ON sessao_autenticacao (id_usuario);

CREATE TABLE recuperacao_senha (
    id_recuperacao VARCHAR(36) PRIMARY KEY,
    id_usuario BIGINT NOT NULL REFERENCES usuario(id_usuario),
    hash_codigo VARCHAR(64) NOT NULL,
    expira_em TIMESTAMPTZ NOT NULL,
    tentativas SMALLINT NOT NULL DEFAULT 0 CHECK (tentativas BETWEEN 0 AND 5),
    usada_em TIMESTAMPTZ,
    hash_token_redefinicao VARCHAR(64)
);
CREATE INDEX ix_recuperacao_usuario ON recuperacao_senha (id_usuario);

-- Reject UPDATE, DELETE and TRUNCATE even for accidental application SQL.
-- A superuser/schema owner can disable triggers: use a separate restricted app role.
CREATE FUNCTION sigg_bloquear_alteracao_auditoria() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Registros de auditoria são imutáveis' USING ERRCODE = '42501';
END;
$$;
CREATE TRIGGER trg_auditoria_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON auditoria
    FOR EACH STATEMENT EXECUTE FUNCTION sigg_bloquear_alteracao_auditoria();
CREATE TRIGGER trg_auditoria_alteracao_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON auditoria_alteracao
    FOR EACH STATEMENT EXECUTE FUNCTION sigg_bloquear_alteracao_auditoria();

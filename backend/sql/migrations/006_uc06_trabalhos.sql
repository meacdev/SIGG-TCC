ALTER TABLE trabalho ADD COLUMN IF NOT EXISTS versao_trabalho INTEGER NOT NULL DEFAULT 1;
ALTER TABLE trabalho ADD COLUMN IF NOT EXISTS palavras_chave_trabalho JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE trabalho ADD COLUMN IF NOT EXISTS id_matricula_atual BIGINT REFERENCES matricula_turma(id_matricula_turma);
DROP INDEX IF EXISTS uq_orientacao_papel_vigente;
CREATE UNIQUE INDEX uq_orientacao_papel_vigente ON orientacao(id_trabalho, papel_orientacao)
    WHERE data_encerramento_orientacao IS NULL;
DROP INDEX IF EXISTS uq_orientacao_docente_vigente;
CREATE UNIQUE INDEX uq_orientacao_docente_vigente ON orientacao(id_trabalho, id_docente)
    WHERE data_encerramento_orientacao IS NULL;

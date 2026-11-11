-- Aligns the database with the updated data model (TCC_atualizado.sql + data dictionary, 09/11/2026).
-- Renames keep existing rows, sequences, foreign keys and triggers (they follow the table OID).
-- Deviations from the supplied script, on purpose:
--   * types are unquoted ("VARCHAR(100)" is not a valid PostgreSQL type);
--   * "vigente"/"ativa"/"aceita"/"presidente" indexes get the WHERE filter their names imply;
--   * project tables and columns from migrations 001-008 are kept (sessions, recovery, batches...).
-- New CHECKs are added NOT VALID and validated at the end; legacy rows that violate one
-- only raise a WARNING, while every new or updated row is always checked.

-- 1. Tables ------------------------------------------------------------------------------------
ALTER TABLE docente RENAME TO professor;
ALTER TABLE aluno RENAME TO estudante;
ALTER TABLE docente_area RENAME TO professor_area;
ALTER TABLE docente_curso RENAME TO professor_curso;
ALTER TABLE trabalho RENAME TO trabalho_tcc;
ALTER TABLE reuniao_orientacao RENAME TO ata_orientacao;
ALTER TABLE rubrica RENAME TO rubrica_avaliacao;
ALTER TABLE banca RENAME TO banca_defesa;
ALTER TABLE avaliacao RENAME TO avaliacao_banca;

-- 2. Columns -----------------------------------------------------------------------------------
ALTER TABLE professor RENAME COLUMN id_docente TO id_professor;
ALTER TABLE professor RENAME COLUMN tipo_docente TO tipo_professor;
ALTER TABLE professor RENAME COLUMN titulacao_docente TO titulacao_professor;
ALTER TABLE professor RENAME COLUMN instituicao_origem_docente TO instituicao_origem_professor;
ALTER TABLE professor RENAME COLUMN url_lattes_docente TO url_lattes_professor;
ALTER TABLE professor RENAME COLUMN ativo_docente TO ativo_professor;

ALTER TABLE estudante RENAME COLUMN id_aluno TO id_estudante;
ALTER TABLE estudante RENAME COLUMN matricula_aluno TO matricula_estudante;

ALTER TABLE professor_area RENAME COLUMN id_docente TO id_professor;

ALTER TABLE professor_curso RENAME COLUMN id_docente_curso TO id_professor_curso;
ALTER TABLE professor_curso RENAME COLUMN id_docente TO id_professor;
ALTER TABLE professor_curso RENAME COLUMN data_inicio_docente_curso TO data_inicio_professor_curso;
ALTER TABLE professor_curso RENAME COLUMN data_fim_docente_curso TO data_fim_professor_curso;
ALTER TABLE professor_curso RENAME COLUMN coordenador_docente_curso TO coordenador_professor_curso;
ALTER TABLE professor_curso
    RENAME COLUMN capacidade_orientandos_docente_curso TO capacidade_orientandos_professor_curso;

ALTER TABLE turma RENAME COLUMN id_docente_responsavel TO id_professor_responsavel;
ALTER TABLE matricula_turma RENAME COLUMN id_aluno TO id_estudante;

ALTER TABLE trabalho_tcc RENAME COLUMN id_trabalho TO id_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN id_aluno TO id_estudante;
ALTER TABLE trabalho_tcc RENAME COLUMN titulo_trabalho TO titulo_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN subtitulo_trabalho TO subtitulo_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN tema_trabalho TO tema_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN modalidade_trabalho TO modalidade_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN url_artigo_trabalho TO url_artigo_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN doi_artigo_trabalho TO doi_artigo_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN situacao_trabalho TO situacao_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN data_criacao_trabalho TO data_criacao_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN data_conclusao_trabalho TO data_conclusao_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN versao_trabalho TO versao_trabalho_tcc;
ALTER TABLE trabalho_tcc RENAME COLUMN palavras_chave_trabalho TO palavras_chave_trabalho_tcc;

ALTER TABLE trabalho_area RENAME COLUMN id_trabalho TO id_trabalho_tcc;
ALTER TABLE etapa_trabalho RENAME COLUMN id_trabalho TO id_trabalho_tcc;
ALTER TABLE orientacao RENAME COLUMN id_trabalho TO id_trabalho_tcc;
ALTER TABLE orientacao RENAME COLUMN id_docente TO id_professor;

ALTER TABLE ata_orientacao RENAME COLUMN id_reuniao_orientacao TO id_ata_orientacao;
ALTER TABLE ata_orientacao RENAME COLUMN data_encontro_reuniao_orientacao TO data_encontro_ata_orientacao;
ALTER TABLE ata_orientacao
    RENAME COLUMN resumo_encaminhamentos_reuniao_orientacao TO resumo_encaminhamentos_ata_orientacao;
ALTER TABLE ata_orientacao RENAME COLUMN data_registro_reuniao_orientacao TO data_registro_ata_orientacao;

ALTER TABLE rubrica_avaliacao RENAME COLUMN id_rubrica TO id_rubrica_avaliacao;
ALTER TABLE rubrica_avaliacao RENAME COLUMN nome_rubrica TO nome_rubrica_avaliacao;
ALTER TABLE rubrica_avaliacao RENAME COLUMN versao_rubrica TO versao_rubrica_avaliacao;
ALTER TABLE rubrica_avaliacao RENAME COLUMN situacao_rubrica TO situacao_rubrica_avaliacao;
ALTER TABLE rubrica_avaliacao RENAME COLUMN data_criacao_rubrica TO data_criacao_rubrica_avaliacao;
ALTER TABLE criterio_rubrica RENAME COLUMN id_rubrica TO id_rubrica_avaliacao;

ALTER TABLE banca_defesa RENAME COLUMN id_banca TO id_banca_defesa;
ALTER TABLE banca_defesa RENAME COLUMN id_rubrica TO id_rubrica_avaliacao;
ALTER TABLE banca_defesa RENAME COLUMN data_inicio_banca TO data_inicio_banca_defesa;
ALTER TABLE banca_defesa RENAME COLUMN data_fim_banca TO data_fim_banca_defesa;
ALTER TABLE banca_defesa RENAME COLUMN local_defesa_banca TO local_defesa_banca_defesa;
ALTER TABLE banca_defesa RENAME COLUMN situacao_banca TO situacao_banca_defesa;
ALTER TABLE banca_defesa RENAME COLUMN resultado_banca TO resultado_banca_defesa;
ALTER TABLE banca_defesa RENAME COLUMN data_agendamento_banca TO data_agendamento_banca_defesa;
ALTER TABLE banca_defesa RENAME COLUMN data_conclusao_banca TO data_conclusao_banca_defesa;
ALTER TABLE banca_defesa RENAME COLUMN uid_calendario_banca TO uid_calendario_banca_defesa;
ALTER TABLE banca_defesa RENAME COLUMN id_evento_google_banca TO id_evento_google_banca_defesa;

ALTER TABLE membro_banca RENAME COLUMN id_banca TO id_banca_defesa;
ALTER TABLE membro_banca RENAME COLUMN id_docente TO id_avaliador;

ALTER TABLE avaliacao_banca RENAME COLUMN id_avaliacao TO id_avaliacao_banca;
ALTER TABLE avaliacao_banca RENAME COLUMN parecer_avaliacao TO parecer_avaliacao_banca;
ALTER TABLE avaliacao_banca RENAME COLUMN situacao_avaliacao TO situacao_avaliacao_banca;
ALTER TABLE avaliacao_banca RENAME COLUMN data_envio_avaliacao TO data_envio_avaliacao_banca;
ALTER TABLE nota_criterio RENAME COLUMN id_avaliacao TO id_avaliacao_banca;

ALTER TABLE ata_defesa RENAME COLUMN id_banca TO id_banca_defesa;
ALTER TABLE solicitacao_correcao RENAME COLUMN id_banca TO id_banca_defesa;
ALTER TABLE documento_oficial
    RENAME COLUMN data_liberacao_aluno_documento_oficial TO data_liberacao_estudante_documento_oficial;
ALTER TABLE entrega_correcao RENAME COLUMN id_docente_validacao TO id_professor_validacao;
ALTER TABLE entrega_final RENAME COLUMN id_docente_validacao TO id_professor_validacao;
ALTER TABLE publicacao_trabalho RENAME COLUMN id_docente_validacao TO id_professor_validacao;
ALTER TABLE notificacao RENAME COLUMN id_reuniao_orientacao TO id_ata_orientacao;
ALTER TABLE notificacao RENAME COLUMN id_banca TO id_banca_defesa;

-- Sequences and primary keys follow the new names (defaults use the OID, so they keep working).
ALTER SEQUENCE IF EXISTS docente_curso_id_docente_curso_seq
    RENAME TO professor_curso_id_professor_curso_seq;
ALTER SEQUENCE IF EXISTS trabalho_id_trabalho_seq RENAME TO trabalho_tcc_id_trabalho_tcc_seq;
ALTER SEQUENCE IF EXISTS reuniao_orientacao_id_reuniao_orientacao_seq
    RENAME TO ata_orientacao_id_ata_orientacao_seq;
ALTER SEQUENCE IF EXISTS rubrica_id_rubrica_seq RENAME TO rubrica_avaliacao_id_rubrica_avaliacao_seq;
ALTER SEQUENCE IF EXISTS banca_id_banca_seq RENAME TO banca_defesa_id_banca_defesa_seq;
ALTER SEQUENCE IF EXISTS avaliacao_id_avaliacao_seq RENAME TO avaliacao_banca_id_avaliacao_banca_seq;
ALTER INDEX IF EXISTS docente_pkey RENAME TO professor_pkey;
ALTER INDEX IF EXISTS aluno_pkey RENAME TO estudante_pkey;
ALTER INDEX IF EXISTS docente_area_pkey RENAME TO professor_area_pkey;
ALTER INDEX IF EXISTS docente_curso_pkey RENAME TO professor_curso_pkey;
ALTER INDEX IF EXISTS trabalho_pkey RENAME TO trabalho_tcc_pkey;
ALTER INDEX IF EXISTS reuniao_orientacao_pkey RENAME TO ata_orientacao_pkey;
ALTER INDEX IF EXISTS rubrica_pkey RENAME TO rubrica_avaliacao_pkey;
ALTER INDEX IF EXISTS banca_pkey RENAME TO banca_defesa_pkey;
ALTER INDEX IF EXISTS avaliacao_pkey RENAME TO avaliacao_banca_pkey;
ALTER TABLE professor_curso RENAME CONSTRAINT docente_curso_unique_0 TO professor_curso_unique_0;

-- 3. Data conversions for the new value domains -----------------------------------------------
UPDATE professor SET titulacao_professor = initcap(lower(titulacao_professor))
    WHERE titulacao_professor <> initcap(lower(titulacao_professor));

ALTER TABLE trabalho_tcc ADD COLUMN tipo_artigo_trabalho_tcc VARCHAR(15);
UPDATE trabalho_tcc
    SET tipo_artigo_trabalho_tcc = substring(modalidade_trabalho_tcc FROM 8),
        modalidade_trabalho_tcc = 'artigo'
    WHERE modalidade_trabalho_tcc IN ('artigo_publicado', 'artigo_a_submeter');

UPDATE perfil SET codigo_perfil = 'estudante' WHERE codigo_perfil = 'aluno'
    AND NOT EXISTS (SELECT 1 FROM perfil WHERE codigo_perfil = 'estudante');

-- 4. New and changed columns -------------------------------------------------------------------
ALTER TABLE usuario ALTER COLUMN nome_usuario TYPE VARCHAR(100);
ALTER TABLE usuario
    ADD COLUMN cpf_usuario VARCHAR(11) UNIQUE,
    ADD COLUMN telefone_usuario VARCHAR(30),
    ADD COLUMN email_validado_usuario BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN tentativas_login_usuario SMALLINT NOT NULL DEFAULT 0,
    ADD COLUMN bloqueado_ate_usuario TIMESTAMP;

ALTER TABLE professor_curso ADD COLUMN departamento_unidade_professor_curso VARCHAR(200);
ALTER TABLE etapa_trabalho ADD COLUMN data_limite_etapa_trabalho TIMESTAMP;
ALTER TABLE rubrica_avaliacao
    ADD COLUMN data_bloqueio_rubrica_avaliacao TIMESTAMP,
    ADD COLUMN data_modificacao_rubrica_avaliacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
-- The defense workflow (UC07) is not implemented yet, so banca_defesa has no rows to backfill.
ALTER TABLE banca_defesa
    ADD COLUMN modalidade_banca_defesa VARCHAR(15) NOT NULL,
    ADD COLUMN url_defesa_banca_defesa TEXT,
    ADD COLUMN id_arquivo_pdf_manuscrito BIGINT NOT NULL;

-- 5. New tables --------------------------------------------------------------------------------
CREATE TABLE avaliador (
    id_avaliador BIGINT PRIMARY KEY REFERENCES usuario (id_usuario) DEFERRABLE INITIALLY IMMEDIATE,
    tipo_avaliador VARCHAR(10) NOT NULL CHECK (tipo_avaliador IN ('interno', 'externo')),
    instituicao_avaliador VARCHAR(200) NOT NULL CHECK (length(btrim(instituicao_avaliador)) > 0),
    titulacao_avaliador VARCHAR(20) NOT NULL
        CHECK (titulacao_avaliador IN ('Especialista', 'Mestre', 'Doutor'))
);

-- membro_banca is empty for the same reason as banca_defesa: re-point its member key.
DO $$
DECLARE constraint_name TEXT;
BEGIN
    SELECT c.conname INTO constraint_name
    FROM pg_constraint c
    WHERE c.conrelid = 'membro_banca'::regclass AND c.contype = 'f'
      AND c.confrelid = 'professor'::regclass;
    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE membro_banca DROP CONSTRAINT ' || quote_ident(constraint_name);
    END IF;
END $$;
ALTER TABLE membro_banca ADD FOREIGN KEY (id_avaliador) REFERENCES avaliador (id_avaliador)
    DEFERRABLE INITIALLY IMMEDIATE;

CREATE TABLE manuscrito_trabalho (
    id_manuscrito_trabalho BIGSERIAL PRIMARY KEY,
    id_etapa_trabalho BIGINT NOT NULL REFERENCES etapa_trabalho (id_etapa_trabalho)
        DEFERRABLE INITIALLY IMMEDIATE,
    id_arquivo_pdf BIGINT UNIQUE NOT NULL REFERENCES arquivo_pdf (id_arquivo_pdf)
        DEFERRABLE INITIALLY IMMEDIATE,
    versao_manuscrito_trabalho INTEGER NOT NULL CHECK (versao_manuscrito_trabalho > 0)
);
CREATE UNIQUE INDEX uq_manuscrito_trabalho_versao
    ON manuscrito_trabalho (id_etapa_trabalho, versao_manuscrito_trabalho);
CREATE UNIQUE INDEX uq_manuscrito_trabalho_arquivo
    ON manuscrito_trabalho (id_etapa_trabalho, id_arquivo_pdf);
ALTER TABLE banca_defesa ADD FOREIGN KEY (id_etapa_trabalho, id_arquivo_pdf_manuscrito)
    REFERENCES manuscrito_trabalho (id_etapa_trabalho, id_arquivo_pdf) DEFERRABLE INITIALLY IMMEDIATE;

-- Declared by the model for RF21. The API still uses sessao_autenticacao/recuperacao_senha
-- (migration 001), which carry fields these tables lack (absolute expiry, refresh JTI).
CREATE TABLE sessao_usuario (
    id_sessao_usuario BIGSERIAL PRIMARY KEY,
    id_usuario BIGINT NOT NULL REFERENCES usuario (id_usuario) DEFERRABLE INITIALLY IMMEDIATE,
    hash_token_sessao_usuario TEXT UNIQUE NOT NULL,
    data_ultima_atividade_sessao_usuario TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_revogacao_sessao_usuario TIMESTAMP
);

CREATE TABLE token_usuario (
    id_token_usuario BIGSERIAL PRIMARY KEY,
    id_usuario BIGINT NOT NULL REFERENCES usuario (id_usuario) DEFERRABLE INITIALLY IMMEDIATE,
    hash_token_usuario TEXT UNIQUE NOT NULL,
    finalidade_token_usuario VARCHAR(25) NOT NULL CHECK (
        finalidade_token_usuario IN
            ('redefinir_senha', 'validar_email', 'alterar_email', 'convite_externo')
    ),
    novo_email_token_usuario VARCHAR(254),
    data_criacao_token_usuario TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_expiracao_token_usuario TIMESTAMP NOT NULL,
    data_consumo_token_usuario TIMESTAMP,
    CHECK (data_expiracao_token_usuario > data_criacao_token_usuario),
    CHECK (finalidade_token_usuario <> 'redefinir_senha'
        OR data_expiracao_token_usuario <= data_criacao_token_usuario + INTERVAL '30 minutes'),
    CHECK ((finalidade_token_usuario = 'alterar_email') = (novo_email_token_usuario IS NOT NULL))
);

-- 6. Indexes -----------------------------------------------------------------------------------
ALTER INDEX IF EXISTS ix_aluno_curso RENAME TO ix_estudante_curso;
ALTER INDEX IF EXISTS ix_matricula_aluno RENAME TO ix_matricula_estudante;
ALTER INDEX IF EXISTS ix_orientacao_docente RENAME TO ix_orientacao_professor;
ALTER INDEX IF EXISTS ix_membro_docente RENAME TO ix_membro_avaliador;
ALTER INDEX IF EXISTS uq_orientacao_docente_vigente RENAME TO uq_orientacao_professor_vigente;

DROP INDEX IF EXISTS uq_docente_curso_vigente;
CREATE UNIQUE INDEX uq_professor_curso_vigente ON professor_curso (id_professor, id_curso)
    WHERE data_fim_professor_curso IS NULL;

DROP INDEX IF EXISTS uq_trabalho_ativo_aluno;
CREATE UNIQUE INDEX uq_trabalho_ativo_estudante ON trabalho_tcc (id_estudante)
    WHERE situacao_trabalho_tcc = 'em_andamento';

CREATE UNIQUE INDEX uq_rubrica_ativa_turma ON rubrica_avaliacao (id_turma)
    WHERE situacao_rubrica_avaliacao = 'ativa';

DROP INDEX IF EXISTS uq_banca_vigente_etapa;
CREATE UNIQUE INDEX uq_banca_vigente_etapa ON banca_defesa (id_etapa_trabalho)
    WHERE situacao_banca_defesa <> 'cancelada';

CREATE UNIQUE INDEX uq_presidente_banca_defesa ON membro_banca (id_banca_defesa)
    WHERE papel_membro_banca = 'presidente';

DROP INDEX IF EXISTS uq_correcao_aprovada;
CREATE UNIQUE INDEX uq_correcao_aprovada ON entrega_correcao (id_solicitacao_correcao)
    WHERE situacao_entrega_correcao = 'aprovado';

DROP INDEX IF EXISTS uq_entrega_final_aceita;
CREATE UNIQUE INDEX uq_entrega_final_aceita ON entrega_final (id_etapa_trabalho)
    WHERE situacao_entrega_final = 'aceita';

-- 7. Integrity rules from the dictionary -------------------------------------------------------
ALTER TABLE usuario
    ADD CONSTRAINT ck_usuario_nome CHECK (length(btrim(nome_usuario)) BETWEEN 3 AND 100) NOT VALID,
    ADD CONSTRAINT ck_usuario_email
        CHECK (email_usuario ~* '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$') NOT VALID,
    ADD CONSTRAINT ck_usuario_cpf CHECK (cpf_usuario IS NULL OR cpf_usuario ~ '^[0-9]{11}$') NOT VALID,
    ADD CONSTRAINT ck_usuario_tentativas_login
        CHECK (tentativas_login_usuario BETWEEN 0 AND 5) NOT VALID,
    ADD CONSTRAINT ck_usuario_hash_senha CHECK (
        hash_senha_usuario IS NULL OR hash_senha_usuario ~ '^[$](2[aby][$]|argon2(id|i|d)[$])'
    ) NOT VALID;

ALTER TABLE periodo_letivo
    ADD CONSTRAINT ck_periodo_letivo_semestre CHECK (semestre_periodo_letivo IN (1, 2)) NOT VALID,
    ADD CONSTRAINT ck_periodo_letivo_ano CHECK (ano_periodo_letivo BETWEEN 1000 AND 9999) NOT VALID,
    ADD CONSTRAINT ck_periodo_letivo_datas
        CHECK (data_fim_periodo_letivo >= data_inicio_periodo_letivo) NOT VALID;

ALTER TABLE professor
    ADD CONSTRAINT ck_professor_tipo CHECK (tipo_professor IN ('interno', 'externo')) NOT VALID,
    ADD CONSTRAINT ck_professor_titulacao
        CHECK (titulacao_professor IN ('Especialista', 'Mestre', 'Doutor')) NOT VALID,
    ADD CONSTRAINT ck_professor_instituicao_externo CHECK (
        tipo_professor <> 'externo'
        OR (instituicao_origem_professor IS NOT NULL
            AND length(btrim(instituicao_origem_professor)) > 0)
    ) NOT VALID,
    ADD CONSTRAINT ck_professor_lattes CHECK (
        url_lattes_professor IS NULL OR url_lattes_professor ~ '^https?://lattes[.]cnpq[.]br/'
    ) NOT VALID;

ALTER TABLE professor_curso
    ADD CONSTRAINT ck_professor_curso_datas
        CHECK (data_fim_professor_curso >= data_inicio_professor_curso) NOT VALID,
    ADD CONSTRAINT ck_professor_curso_capacidade
        CHECK (capacidade_orientandos_professor_curso > 0) NOT VALID,
    ADD CONSTRAINT ck_professor_curso_coordenador_departamento CHECK (
        NOT coordenador_professor_curso OR departamento_unidade_professor_curso IS NOT NULL
    ) NOT VALID;

ALTER TABLE turma
    ADD CONSTRAINT ck_turma_nivel CHECK (nivel_turma IN (1, 2)) NOT VALID,
    ADD CONSTRAINT ck_turma_codigo CHECK (codigo_turma ~ '^[A-Za-z0-9]+$') NOT VALID,
    ADD CONSTRAINT ck_turma_autoinscricao
        CHECK (NOT autoinscricao_ativa_turma OR hash_codigo_acesso_turma IS NOT NULL) NOT VALID;

ALTER TABLE trabalho_tcc
    ADD CONSTRAINT ck_trabalho_tcc_titulo CHECK (length(btrim(titulo_trabalho_tcc)) > 0) NOT VALID,
    ADD CONSTRAINT ck_trabalho_tcc_modalidade
        CHECK (modalidade_trabalho_tcc IN ('monografia', 'artigo')) NOT VALID,
    ADD CONSTRAINT ck_trabalho_tcc_tipo_artigo
        CHECK (tipo_artigo_trabalho_tcc IN ('publicado', 'a_submeter')) NOT VALID,
    ADD CONSTRAINT ck_trabalho_tcc_tipo_artigo_modalidade CHECK (
        (modalidade_trabalho_tcc = 'artigo') = (tipo_artigo_trabalho_tcc IS NOT NULL)
    ) NOT VALID,
    ADD CONSTRAINT ck_trabalho_tcc_artigo_publicado CHECK (
        tipo_artigo_trabalho_tcc IS DISTINCT FROM 'publicado'
        OR (url_artigo_trabalho_tcc IS NOT NULL AND url_artigo_trabalho_tcc ~ '^https?://'
            AND doi_artigo_trabalho_tcc IS NOT NULL AND length(btrim(doi_artigo_trabalho_tcc)) > 0)
    ) NOT VALID;

ALTER TABLE orientacao
    ADD CONSTRAINT ck_orientacao_papel
        CHECK (papel_orientacao IN ('orientador', 'coorientador')) NOT VALID,
    ADD CONSTRAINT ck_orientacao_situacao_aceite
        CHECK (situacao_aceite_orientacao IN ('pendente', 'aceito', 'recusado')) NOT VALID,
    ADD CONSTRAINT ck_orientacao_encerramento CHECK (
        data_encerramento_orientacao IS NULL
        OR (id_usuario_encerramento IS NOT NULL AND justificativa_encerramento_orientacao IS NOT NULL
            AND length(btrim(justificativa_encerramento_orientacao)) > 0)
    ) NOT VALID;

ALTER TABLE rubrica_avaliacao
    ADD CONSTRAINT ck_rubrica_avaliacao_situacao
        CHECK (situacao_rubrica_avaliacao IN ('rascunho', 'ativa', 'inativa')) NOT VALID;

ALTER TABLE criterio_rubrica
    ADD CONSTRAINT ck_criterio_rubrica_peso
        CHECK (peso_criterio_rubrica > 0 AND peso_criterio_rubrica <= 100) NOT VALID,
    ADD CONSTRAINT ck_criterio_rubrica_pontuacao
        CHECK (pontuacao_maxima_criterio_rubrica > 0) NOT VALID;

ALTER TABLE banca_defesa
    ADD CONSTRAINT ck_banca_defesa_datas
        CHECK (data_fim_banca_defesa > data_inicio_banca_defesa) NOT VALID,
    ADD CONSTRAINT ck_banca_defesa_modalidade
        CHECK (modalidade_banca_defesa IN ('presencial', 'remota', 'hibrida')) NOT VALID,
    ADD CONSTRAINT ck_banca_defesa_resultado CHECK (
        resultado_banca_defesa IN ('aprovado', 'reprovado', 'aprovado_com_correcoes')
    ) NOT VALID;

ALTER TABLE membro_banca
    ADD CONSTRAINT ck_membro_banca_papel
        CHECK (papel_membro_banca IN ('presidente', 'examinador', 'suplente')) NOT VALID,
    ADD CONSTRAINT ck_membro_banca_acesso
        CHECK (data_fim_acesso_membro_banca > data_inicio_acesso_membro_banca) NOT VALID;

ALTER TABLE nota_criterio
    ADD CONSTRAINT ck_nota_criterio_valor CHECK (valor_nota_criterio >= 0) NOT VALID;

ALTER TABLE arquivo_pdf
    ADD CONSTRAINT ck_arquivo_pdf_mime CHECK (mime_type_arquivo_pdf = 'application/pdf') NOT VALID,
    ADD CONSTRAINT ck_arquivo_pdf_tamanho CHECK (tamanho_bytes_arquivo_pdf > 0) NOT VALID,
    ADD CONSTRAINT ck_arquivo_pdf_sha256 CHECK (sha256_arquivo_pdf ~ '^[0-9a-fA-F]{64}$') NOT VALID;

ALTER TABLE entrega_correcao
    ADD CONSTRAINT ck_entrega_correcao_situacao
        CHECK (situacao_entrega_correcao IN ('pendente', 'aprovado', 'rejeitado')) NOT VALID;

ALTER TABLE entrega_final
    ADD CONSTRAINT ck_entrega_final_situacao
        CHECK (situacao_entrega_final IN ('pendente', 'aceita', 'rejeitada')) NOT VALID;

ALTER TABLE publicacao_trabalho
    ADD CONSTRAINT ck_publicacao_trabalho_palavras CHECK (
        minimo_palavras_publicacao_trabalho >= 100
        AND maximo_palavras_publicacao_trabalho <= 250
        AND minimo_palavras_publicacao_trabalho <= maximo_palavras_publicacao_trabalho
    ) NOT VALID;

-- Validate legacy rows; a violation is reported instead of blocking the upgrade.
-- (No percent signs here: the migration runner sends this file through psycopg.)
DO $$
DECLARE item RECORD;
BEGIN
    FOR item IN
        SELECT c.conrelid::regclass::text AS table_name, c.conname::text AS conname
        FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE n.nspname = current_schema() AND c.contype = 'c' AND NOT c.convalidated
          AND left(c.conname, 3) = 'ck_'
    LOOP
        BEGIN
            EXECUTE 'ALTER TABLE ' || item.table_name
                || ' VALIDATE CONSTRAINT ' || quote_ident(item.conname);
        EXCEPTION WHEN check_violation THEN
            RAISE WARNING USING MESSAGE = 'Dados legados violam ' || item.table_name || '.'
                || item.conname || '; corrija-os e execute VALIDATE CONSTRAINT.';
        END;
    END LOOP;
END $$;

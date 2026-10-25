CREATE TABLE IF NOT EXISTS "usuario" (
	"id_usuario" BIGSERIAL,
	"nome_usuario" VARCHAR(200) NOT NULL,
	"email_usuario" VARCHAR(254) NOT NULL UNIQUE,
	"hash_senha_usuario" TEXT,
	"url_foto_usuario" TEXT,
	"ativo_usuario" BOOLEAN NOT NULL DEFAULT true,
	"data_criacao_usuario" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id_usuario")
);

CREATE TABLE IF NOT EXISTS "perfil" (
	"id_perfil" BIGSERIAL,
	"codigo_perfil" VARCHAR(40) NOT NULL UNIQUE,
	"descricao_perfil" VARCHAR(150) NOT NULL,
	PRIMARY KEY("id_perfil")
);

CREATE TABLE IF NOT EXISTS "usuario_perfil" (
	"id_usuario" BIGINT NOT NULL,
	"id_perfil" BIGINT NOT NULL,
	"data_concessao_usuario_perfil" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"data_expiracao_usuario_perfil" TIMESTAMP,
	PRIMARY KEY("id_usuario", "id_perfil")
);

CREATE TABLE IF NOT EXISTS "curso" (
	"id_curso" BIGSERIAL,
	"codigo_curso" VARCHAR(30) NOT NULL UNIQUE,
	"nome_curso" VARCHAR(200) NOT NULL,
	"ativo_curso" BOOLEAN NOT NULL DEFAULT true,
	PRIMARY KEY("id_curso")
);

CREATE TABLE IF NOT EXISTS "periodo_letivo" (
	"id_periodo_letivo" BIGSERIAL,
	"ano_periodo_letivo" SMALLINT NOT NULL,
	"semestre_periodo_letivo" SMALLINT NOT NULL,
	"data_inicio_periodo_letivo" DATE,
	"data_fim_periodo_letivo" DATE,
	PRIMARY KEY("id_periodo_letivo"),
	CONSTRAINT "periodo_letivo_unique_0" UNIQUE ("ano_periodo_letivo", "semestre_periodo_letivo")
);

CREATE TABLE IF NOT EXISTS "docente" (
	"id_docente" BIGINT,
	"tipo_docente" VARCHAR(10) NOT NULL,
	"titulacao_docente" VARCHAR(20) NOT NULL,
	"instituicao_origem_docente" VARCHAR(200),
	"url_lattes_docente" TEXT,
	"ativo_docente" BOOLEAN NOT NULL DEFAULT true,
	PRIMARY KEY("id_docente")
);

CREATE TABLE IF NOT EXISTS "aluno" (
	"id_aluno" BIGINT,
	"matricula_aluno" VARCHAR(30) NOT NULL UNIQUE,
	"id_curso" BIGINT NOT NULL,
	PRIMARY KEY("id_aluno")
);

CREATE INDEX "ix_aluno_curso"
ON "aluno" ("id_curso");

CREATE TABLE IF NOT EXISTS "area_conhecimento" (
	"id_area_conhecimento" BIGSERIAL,
	"nome_area_conhecimento" VARCHAR(150) NOT NULL UNIQUE,
	PRIMARY KEY("id_area_conhecimento")
);

CREATE TABLE IF NOT EXISTS "docente_area" (
	"id_docente" BIGINT NOT NULL,
	"id_area_conhecimento" BIGINT NOT NULL,
	PRIMARY KEY("id_docente", "id_area_conhecimento")
);

CREATE TABLE IF NOT EXISTS "docente_curso" (
	"id_docente_curso" BIGSERIAL,
	"id_docente" BIGINT NOT NULL,
	"id_curso" BIGINT NOT NULL,
	"data_inicio_docente_curso" DATE NOT NULL,
	"data_fim_docente_curso" DATE,
	"coordenador_docente_curso" BOOLEAN NOT NULL DEFAULT false,
	"capacidade_orientandos_docente_curso" SMALLINT,
	PRIMARY KEY("id_docente_curso"),
	CONSTRAINT "docente_curso_unique_0" UNIQUE ("id_docente", "id_curso", "data_inicio_docente_curso")
);

CREATE UNIQUE INDEX "uq_docente_curso_vigente"
ON "docente_curso" ("id_docente", "id_curso");

CREATE TABLE IF NOT EXISTS "turma" (
	"id_turma" BIGSERIAL,
	"id_periodo_letivo" BIGINT NOT NULL,
	"id_curso" BIGINT NOT NULL,
	"id_docente_responsavel" BIGINT NOT NULL,
	"codigo_turma" VARCHAR(40) NOT NULL,
	"nivel_turma" SMALLINT NOT NULL,
	"hash_codigo_acesso_turma" VARCHAR(128) UNIQUE,
	"data_expiracao_acesso_turma" TIMESTAMP,
	"autoinscricao_ativa_turma" BOOLEAN NOT NULL DEFAULT false,
	"data_criacao_turma" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id_turma"),
	CONSTRAINT "turma_unique_0" UNIQUE ("id_periodo_letivo", "codigo_turma")
);

CREATE INDEX "ix_turma_curso_periodo"
ON "turma" ("id_curso", "id_periodo_letivo");
CREATE INDEX "ix_turma_professor"
ON "turma" ("id_docente_responsavel");

CREATE TABLE IF NOT EXISTS "matricula_turma" (
	"id_matricula_turma" BIGSERIAL,
	"id_turma" BIGINT NOT NULL,
	"id_aluno" BIGINT NOT NULL,
	"origem_matricula_turma" VARCHAR(15) NOT NULL,
	"situacao_matricula_turma" VARCHAR(15) NOT NULL DEFAULT 'ativa',
	"id_usuario_inclusao" BIGINT NOT NULL,
	"data_matricula_matricula_turma" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"data_remocao_matricula_turma" TIMESTAMP,
	"motivo_remocao_matricula_turma" TEXT,
	PRIMARY KEY("id_matricula_turma"),
	CONSTRAINT "matricula_turma_unique_0" UNIQUE ("id_turma", "id_aluno")
);

CREATE INDEX "ix_matricula_aluno"
ON "matricula_turma" ("id_aluno", "situacao_matricula_turma");

CREATE TABLE IF NOT EXISTS "trabalho" (
	"id_trabalho" BIGSERIAL,
	"id_aluno" BIGINT NOT NULL,
	"titulo_trabalho" VARCHAR(500) NOT NULL,
	"subtitulo_trabalho" VARCHAR(500),
	"tema_trabalho" TEXT,
	"modalidade_trabalho" VARCHAR(25) NOT NULL,
	"url_artigo_trabalho" TEXT,
	"doi_artigo_trabalho" VARCHAR(255),
	"situacao_trabalho" VARCHAR(20) NOT NULL DEFAULT 'em_andamento',
	"data_criacao_trabalho" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"data_conclusao_trabalho" TIMESTAMP,
	PRIMARY KEY("id_trabalho")
);

CREATE UNIQUE INDEX "uq_trabalho_ativo_aluno"
ON "trabalho" ("id_aluno");

CREATE TABLE IF NOT EXISTS "trabalho_area" (
	"id_trabalho" BIGINT NOT NULL,
	"id_area_conhecimento" BIGINT NOT NULL,
	PRIMARY KEY("id_trabalho", "id_area_conhecimento")
);

CREATE TABLE IF NOT EXISTS "etapa_trabalho" (
	"id_etapa_trabalho" BIGSERIAL,
	"id_trabalho" BIGINT NOT NULL,
	"id_matricula_turma" BIGINT NOT NULL UNIQUE,
	"situacao_etapa_trabalho" VARCHAR(25) NOT NULL DEFAULT 'em_andamento',
	"data_inicio_etapa_trabalho" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"data_conclusao_etapa_trabalho" TIMESTAMP,
	PRIMARY KEY("id_etapa_trabalho")
);

CREATE INDEX "ix_etapa_trabalho"
ON "etapa_trabalho" ("id_trabalho");

CREATE TABLE IF NOT EXISTS "orientacao" (
	"id_orientacao" BIGSERIAL,
	"id_trabalho" BIGINT NOT NULL,
	"id_docente" BIGINT NOT NULL,
	"papel_orientacao" VARCHAR(15) NOT NULL,
	"situacao_aceite_orientacao" VARCHAR(15) NOT NULL DEFAULT 'pendente',
	"data_solicitacao_orientacao" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"data_resposta_orientacao" TIMESTAMP,
	"data_encerramento_orientacao" TIMESTAMP,
	"id_usuario_registro" BIGINT NOT NULL,
	"id_usuario_encerramento" BIGINT,
	"justificativa_encerramento_orientacao" TEXT,
	PRIMARY KEY("id_orientacao")
);

CREATE UNIQUE INDEX "uq_orientacao_papel_vigente"
ON "orientacao" ("id_trabalho", "papel_orientacao");
CREATE UNIQUE INDEX "uq_orientacao_docente_vigente"
ON "orientacao" ("id_trabalho", "id_docente");
CREATE INDEX "ix_orientacao_docente"
ON "orientacao" ("id_docente", "data_encerramento_orientacao");

CREATE TABLE IF NOT EXISTS "reuniao_orientacao" (
	"id_reuniao_orientacao" BIGSERIAL,
	"id_etapa_trabalho" BIGINT NOT NULL,
	"id_orientacao" BIGINT NOT NULL,
	"data_encontro_reuniao_orientacao" DATE NOT NULL,
	"resumo_encaminhamentos_reuniao_orientacao" TEXT NOT NULL,
	"id_usuario_registro" BIGINT NOT NULL,
	"data_registro_reuniao_orientacao" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id_reuniao_orientacao")
);

CREATE INDEX "ix_reuniao_etapa_data"
ON "reuniao_orientacao" ("id_etapa_trabalho", "data_encontro_reuniao_orientacao");

CREATE TABLE IF NOT EXISTS "rubrica" (
	"id_rubrica" BIGSERIAL,
	"id_turma" BIGINT NOT NULL,
	"nome_rubrica" VARCHAR(150) NOT NULL,
	"versao_rubrica" SMALLINT NOT NULL DEFAULT 1,
	"situacao_rubrica" VARCHAR(15) NOT NULL DEFAULT 'rascunho',
	"id_usuario_criacao" BIGINT NOT NULL,
	"data_criacao_rubrica" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id_rubrica"),
	CONSTRAINT "rubrica_unique_0" UNIQUE ("id_turma", "nome_rubrica", "versao_rubrica")
);

CREATE TABLE IF NOT EXISTS "criterio_rubrica" (
	"id_criterio_rubrica" BIGSERIAL,
	"id_rubrica" BIGINT NOT NULL,
	"nome_criterio_rubrica" VARCHAR(150) NOT NULL,
	"descricao_criterio_rubrica" TEXT,
	"peso_criterio_rubrica" NUMERIC(6,3) NOT NULL,
	"pontuacao_maxima_criterio_rubrica" NUMERIC(5,2) NOT NULL DEFAULT 10,
	"ordem_criterio_rubrica" SMALLINT NOT NULL,
	PRIMARY KEY("id_criterio_rubrica"),
	CONSTRAINT "criterio_rubrica_unique_0" UNIQUE ("id_rubrica", "nome_criterio_rubrica"),
	CONSTRAINT "criterio_rubrica_unique_1" UNIQUE ("id_rubrica", "ordem_criterio_rubrica")
);

CREATE TABLE IF NOT EXISTS "banca" (
	"id_banca" BIGSERIAL,
	"id_etapa_trabalho" BIGINT NOT NULL,
	"id_rubrica" BIGINT NOT NULL,
	"data_inicio_banca" TIMESTAMP NOT NULL,
	"data_fim_banca" TIMESTAMP NOT NULL,
	"local_defesa_banca" TEXT NOT NULL,
	"situacao_banca" VARCHAR(15) NOT NULL DEFAULT 'agendada',
	"resultado_banca" VARCHAR(25),
	"id_usuario_agendamento" BIGINT NOT NULL,
	"data_agendamento_banca" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"data_conclusao_banca" TIMESTAMP,
	"uid_calendario_banca" VARCHAR(200) UNIQUE,
	"id_evento_google_banca" VARCHAR(255),
	PRIMARY KEY("id_banca")
);

CREATE UNIQUE INDEX "uq_banca_vigente_etapa"
ON "banca" ("id_etapa_trabalho");
CREATE INDEX "ix_banca_inicio"
ON "banca" ("data_inicio_banca", "situacao_banca");

CREATE TABLE IF NOT EXISTS "membro_banca" (
	"id_membro_banca" BIGSERIAL,
	"id_banca" BIGINT NOT NULL,
	"id_docente" BIGINT NOT NULL,
	"papel_membro_banca" VARCHAR(15) NOT NULL DEFAULT 'examinador',
	"situacao_convite_membro_banca" VARCHAR(15) NOT NULL DEFAULT 'pendente',
	"data_convite_membro_banca" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"data_resposta_membro_banca" TIMESTAMP,
	"data_inicio_acesso_membro_banca" TIMESTAMP NOT NULL,
	"data_fim_acesso_membro_banca" TIMESTAMP NOT NULL,
	PRIMARY KEY("id_membro_banca"),
	CONSTRAINT "membro_banca_unique_0" UNIQUE ("id_banca", "id_docente")
);

CREATE INDEX "ix_membro_docente"
ON "membro_banca" ("id_docente", "id_banca");

CREATE TABLE IF NOT EXISTS "avaliacao" (
	"id_avaliacao" BIGSERIAL,
	"id_membro_banca" BIGINT NOT NULL UNIQUE,
	"parecer_avaliacao" TEXT,
	"situacao_avaliacao" VARCHAR(15) NOT NULL DEFAULT 'rascunho',
	"data_envio_avaliacao" TIMESTAMP,
	PRIMARY KEY("id_avaliacao")
);

CREATE TABLE IF NOT EXISTS "nota_criterio" (
	"id_avaliacao" BIGINT NOT NULL,
	"id_criterio_rubrica" BIGINT NOT NULL,
	"valor_nota_criterio" NUMERIC(5,2) NOT NULL,
	"observacao_nota_criterio" TEXT,
	"data_registro_nota_criterio" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id_avaliacao", "id_criterio_rubrica")
);

CREATE TABLE IF NOT EXISTS "arquivo_pdf" (
	"id_arquivo_pdf" BIGSERIAL,
	"nome_original_arquivo_pdf" VARCHAR(255) NOT NULL,
	"chave_armazenamento_arquivo_pdf" TEXT NOT NULL UNIQUE,
	"mime_type_arquivo_pdf" VARCHAR(50) NOT NULL DEFAULT 'application/pdf',
	"tamanho_bytes_arquivo_pdf" BIGINT NOT NULL,
	"sha256_arquivo_pdf" CHAR(64) NOT NULL,
	"id_usuario_envio" BIGINT NOT NULL,
	"data_envio_arquivo_pdf" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id_arquivo_pdf")
);

CREATE TABLE IF NOT EXISTS "modelo_documento" (
	"id_modelo_documento" BIGSERIAL,
	"tipo_modelo_documento" VARCHAR(20) NOT NULL,
	"versao_modelo_documento" SMALLINT NOT NULL,
	"nome_modelo_documento" VARCHAR(150) NOT NULL,
	"conteudo_template_modelo_documento" TEXT NOT NULL,
	"ativo_modelo_documento" BOOLEAN NOT NULL DEFAULT true,
	PRIMARY KEY("id_modelo_documento"),
	CONSTRAINT "modelo_documento_unique_0" UNIQUE ("tipo_modelo_documento", "versao_modelo_documento")
);

CREATE TABLE IF NOT EXISTS "documento_oficial" (
	"id_documento_oficial" BIGSERIAL,
	"id_modelo_documento" BIGINT NOT NULL,
	"id_arquivo_pdf" BIGINT NOT NULL UNIQUE,
	"codigo_verificacao_documento_oficial" VARCHAR(100) NOT NULL UNIQUE,
	"data_emissao_documento_oficial" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"data_assinatura_documento_oficial" TIMESTAMP,
	"data_liberacao_aluno_documento_oficial" TIMESTAMP,
	"data_revogacao_documento_oficial" TIMESTAMP,
	PRIMARY KEY("id_documento_oficial")
);

CREATE TABLE IF NOT EXISTS "ata_defesa" (
	"id_ata_defesa" BIGINT,
	"id_banca" BIGINT NOT NULL,
	PRIMARY KEY("id_ata_defesa")
);

CREATE TABLE IF NOT EXISTS "declaracao_banca" (
	"id_declaracao_banca" BIGINT,
	"id_membro_banca" BIGINT NOT NULL,
	PRIMARY KEY("id_declaracao_banca")
);

CREATE TABLE IF NOT EXISTS "solicitacao_correcao" (
	"id_solicitacao_correcao" BIGSERIAL,
	"id_banca" BIGINT NOT NULL UNIQUE,
	"descricao_solicitacao_correcao" TEXT NOT NULL,
	"data_limite_reenvio_solicitacao_correcao" DATE NOT NULL,
	"id_usuario_registro" BIGINT NOT NULL,
	"data_registro_solicitacao_correcao" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id_solicitacao_correcao")
);

CREATE INDEX "ix_correcao_prazo"
ON "solicitacao_correcao" ("data_limite_reenvio_solicitacao_correcao");

CREATE TABLE IF NOT EXISTS "entrega_correcao" (
	"id_entrega_correcao" BIGSERIAL,
	"id_solicitacao_correcao" BIGINT NOT NULL,
	"id_arquivo_pdf" BIGINT NOT NULL UNIQUE,
	"situacao_entrega_correcao" VARCHAR(15) NOT NULL DEFAULT 'pendente',
	"id_docente_validacao" BIGINT,
	"data_validacao_entrega_correcao" TIMESTAMP,
	"parecer_entrega_correcao" TEXT,
	PRIMARY KEY("id_entrega_correcao")
);

CREATE UNIQUE INDEX "uq_correcao_aprovada"
ON "entrega_correcao" ("id_solicitacao_correcao");

CREATE TABLE IF NOT EXISTS "entrega_final" (
	"id_entrega_final" BIGSERIAL,
	"id_etapa_trabalho" BIGINT NOT NULL,
	"id_arquivo_pdf" BIGINT NOT NULL UNIQUE,
	"situacao_entrega_final" VARCHAR(15) NOT NULL DEFAULT 'pendente',
	"id_docente_validacao" BIGINT,
	"data_validacao_entrega_final" TIMESTAMP,
	"parecer_entrega_final" TEXT,
	PRIMARY KEY("id_entrega_final")
);

CREATE UNIQUE INDEX "uq_entrega_final_aceita"
ON "entrega_final" ("id_etapa_trabalho");
CREATE INDEX "ix_entrega_final_etapa"
ON "entrega_final" ("id_etapa_trabalho");

CREATE TABLE IF NOT EXISTS "publicacao_trabalho" (
	"id_publicacao_trabalho" BIGSERIAL,
	"id_etapa_trabalho" BIGINT NOT NULL UNIQUE,
	"resumo_publicacao_trabalho" TEXT NOT NULL,
	"minimo_palavras_publicacao_trabalho" SMALLINT NOT NULL DEFAULT 100,
	"maximo_palavras_publicacao_trabalho" SMALLINT NOT NULL DEFAULT 250,
	"situacao_publicacao_trabalho" VARCHAR(15) NOT NULL DEFAULT 'rascunho',
	"data_submissao_publicacao_trabalho" TIMESTAMP,
	"id_docente_validacao" BIGINT,
	"data_validacao_publicacao_trabalho" TIMESTAMP,
	"data_publicacao_publicacao_trabalho" TIMESTAMP,
	"parecer_publicacao_trabalho" TEXT,
	PRIMARY KEY("id_publicacao_trabalho")
);

CREATE TABLE IF NOT EXISTS "palavra_chave" (
	"id_palavra_chave" BIGSERIAL,
	"termo_palavra_chave" VARCHAR(100) NOT NULL UNIQUE,
	PRIMARY KEY("id_palavra_chave")
);

CREATE TABLE IF NOT EXISTS "publicacao_palavra_chave" (
	"id_publicacao_trabalho" BIGINT NOT NULL,
	"id_palavra_chave" BIGINT NOT NULL,
	PRIMARY KEY("id_publicacao_trabalho", "id_palavra_chave")
);

CREATE TABLE IF NOT EXISTS "notificacao" (
	"id_notificacao" BIGSERIAL,
	"id_usuario_destinatario" BIGINT NOT NULL,
	"email_destino_notificacao" VARCHAR(254) NOT NULL,
	"tipo_notificacao" VARCHAR(50) NOT NULL,
	"assunto_notificacao" VARCHAR(255) NOT NULL,
	"corpo_notificacao" TEXT NOT NULL,
	"id_matricula_turma" BIGINT,
	"id_orientacao" BIGINT,
	"id_reuniao_orientacao" BIGINT,
	"id_banca" BIGINT,
	"id_documento_oficial" BIGINT,
	"anexo_ics_notificacao" TEXT,
	"chave_idempotencia_notificacao" VARCHAR(200) NOT NULL UNIQUE,
	"data_agendamento_notificacao" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"data_envio_notificacao" TIMESTAMP,
	"situacao_notificacao" VARCHAR(15) NOT NULL DEFAULT 'pendente',
	"tentativas_notificacao" SMALLINT NOT NULL DEFAULT 0,
	"ultimo_erro_notificacao" TEXT,
	PRIMARY KEY("id_notificacao")
);

CREATE INDEX "ix_notificacao_fila"
ON "notificacao" ("situacao_notificacao", "data_agendamento_notificacao");

CREATE TABLE IF NOT EXISTS "auditoria" (
	"id_auditoria" BIGSERIAL,
	"id_usuario" BIGINT,
	"acao_auditoria" VARCHAR(60) NOT NULL,
	"entidade_auditoria" VARCHAR(80) NOT NULL,
	"id_registro_auditoria" BIGINT NOT NULL,
	"justificativa_auditoria" TEXT,
	"ip_origem_auditoria" INET,
	"data_ocorrencia_auditoria" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id_auditoria")
);

CREATE INDEX "ix_auditoria_registro"
ON "auditoria" ("entidade_auditoria", "id_registro_auditoria", "data_ocorrencia_auditoria");

CREATE TABLE IF NOT EXISTS "auditoria_alteracao" (
	"id_auditoria" BIGINT NOT NULL,
	"nome_campo_auditoria_alteracao" VARCHAR(100) NOT NULL,
	"valor_anterior_auditoria_alteracao" TEXT,
	"valor_novo_auditoria_alteracao" TEXT,
	PRIMARY KEY("id_auditoria", "nome_campo_auditoria_alteracao")
);

ALTER TABLE "usuario_perfil"
ADD FOREIGN KEY("id_usuario") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "usuario_perfil"
ADD FOREIGN KEY("id_perfil") REFERENCES "perfil"("id_perfil")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "docente"
ADD FOREIGN KEY("id_docente") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "aluno"
ADD FOREIGN KEY("id_aluno") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "aluno"
ADD FOREIGN KEY("id_curso") REFERENCES "curso"("id_curso")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "docente_area"
ADD FOREIGN KEY("id_docente") REFERENCES "docente"("id_docente")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "docente_area"
ADD FOREIGN KEY("id_area_conhecimento") REFERENCES "area_conhecimento"("id_area_conhecimento")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "docente_curso"
ADD FOREIGN KEY("id_docente") REFERENCES "docente"("id_docente")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "docente_curso"
ADD FOREIGN KEY("id_curso") REFERENCES "curso"("id_curso")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "turma"
ADD FOREIGN KEY("id_periodo_letivo") REFERENCES "periodo_letivo"("id_periodo_letivo")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "turma"
ADD FOREIGN KEY("id_curso") REFERENCES "curso"("id_curso")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "turma"
ADD FOREIGN KEY("id_docente_responsavel") REFERENCES "docente"("id_docente")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "matricula_turma"
ADD FOREIGN KEY("id_turma") REFERENCES "turma"("id_turma")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "matricula_turma"
ADD FOREIGN KEY("id_aluno") REFERENCES "aluno"("id_aluno")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "matricula_turma"
ADD FOREIGN KEY("id_usuario_inclusao") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "trabalho"
ADD FOREIGN KEY("id_aluno") REFERENCES "aluno"("id_aluno")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "trabalho_area"
ADD FOREIGN KEY("id_trabalho") REFERENCES "trabalho"("id_trabalho")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "trabalho_area"
ADD FOREIGN KEY("id_area_conhecimento") REFERENCES "area_conhecimento"("id_area_conhecimento")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "etapa_trabalho"
ADD FOREIGN KEY("id_trabalho") REFERENCES "trabalho"("id_trabalho")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "etapa_trabalho"
ADD FOREIGN KEY("id_matricula_turma") REFERENCES "matricula_turma"("id_matricula_turma")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "orientacao"
ADD FOREIGN KEY("id_trabalho") REFERENCES "trabalho"("id_trabalho")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "orientacao"
ADD FOREIGN KEY("id_docente") REFERENCES "docente"("id_docente")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "orientacao"
ADD FOREIGN KEY("id_usuario_registro") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "orientacao"
ADD FOREIGN KEY("id_usuario_encerramento") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "reuniao_orientacao"
ADD FOREIGN KEY("id_etapa_trabalho") REFERENCES "etapa_trabalho"("id_etapa_trabalho")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "reuniao_orientacao"
ADD FOREIGN KEY("id_orientacao") REFERENCES "orientacao"("id_orientacao")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "reuniao_orientacao"
ADD FOREIGN KEY("id_usuario_registro") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "rubrica"
ADD FOREIGN KEY("id_turma") REFERENCES "turma"("id_turma")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "rubrica"
ADD FOREIGN KEY("id_usuario_criacao") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "criterio_rubrica"
ADD FOREIGN KEY("id_rubrica") REFERENCES "rubrica"("id_rubrica")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "banca"
ADD FOREIGN KEY("id_etapa_trabalho") REFERENCES "etapa_trabalho"("id_etapa_trabalho")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "banca"
ADD FOREIGN KEY("id_rubrica") REFERENCES "rubrica"("id_rubrica")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "banca"
ADD FOREIGN KEY("id_usuario_agendamento") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "membro_banca"
ADD FOREIGN KEY("id_banca") REFERENCES "banca"("id_banca")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "membro_banca"
ADD FOREIGN KEY("id_docente") REFERENCES "docente"("id_docente")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "avaliacao"
ADD FOREIGN KEY("id_membro_banca") REFERENCES "membro_banca"("id_membro_banca")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "nota_criterio"
ADD FOREIGN KEY("id_avaliacao") REFERENCES "avaliacao"("id_avaliacao")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "nota_criterio"
ADD FOREIGN KEY("id_criterio_rubrica") REFERENCES "criterio_rubrica"("id_criterio_rubrica")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "arquivo_pdf"
ADD FOREIGN KEY("id_usuario_envio") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "documento_oficial"
ADD FOREIGN KEY("id_modelo_documento") REFERENCES "modelo_documento"("id_modelo_documento")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "documento_oficial"
ADD FOREIGN KEY("id_arquivo_pdf") REFERENCES "arquivo_pdf"("id_arquivo_pdf")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "ata_defesa"
ADD FOREIGN KEY("id_ata_defesa") REFERENCES "documento_oficial"("id_documento_oficial")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "ata_defesa"
ADD FOREIGN KEY("id_banca") REFERENCES "banca"("id_banca")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "declaracao_banca"
ADD FOREIGN KEY("id_declaracao_banca") REFERENCES "documento_oficial"("id_documento_oficial")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "declaracao_banca"
ADD FOREIGN KEY("id_membro_banca") REFERENCES "membro_banca"("id_membro_banca")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "solicitacao_correcao"
ADD FOREIGN KEY("id_banca") REFERENCES "banca"("id_banca")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "solicitacao_correcao"
ADD FOREIGN KEY("id_usuario_registro") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "entrega_correcao"
ADD FOREIGN KEY("id_solicitacao_correcao") REFERENCES "solicitacao_correcao"("id_solicitacao_correcao")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "entrega_correcao"
ADD FOREIGN KEY("id_arquivo_pdf") REFERENCES "arquivo_pdf"("id_arquivo_pdf")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "entrega_correcao"
ADD FOREIGN KEY("id_docente_validacao") REFERENCES "docente"("id_docente")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "entrega_final"
ADD FOREIGN KEY("id_etapa_trabalho") REFERENCES "etapa_trabalho"("id_etapa_trabalho")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "entrega_final"
ADD FOREIGN KEY("id_arquivo_pdf") REFERENCES "arquivo_pdf"("id_arquivo_pdf")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "entrega_final"
ADD FOREIGN KEY("id_docente_validacao") REFERENCES "docente"("id_docente")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "publicacao_trabalho"
ADD FOREIGN KEY("id_etapa_trabalho") REFERENCES "etapa_trabalho"("id_etapa_trabalho")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "publicacao_trabalho"
ADD FOREIGN KEY("id_docente_validacao") REFERENCES "docente"("id_docente")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "publicacao_palavra_chave"
ADD FOREIGN KEY("id_publicacao_trabalho") REFERENCES "publicacao_trabalho"("id_publicacao_trabalho")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "publicacao_palavra_chave"
ADD FOREIGN KEY("id_palavra_chave") REFERENCES "palavra_chave"("id_palavra_chave")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "notificacao"
ADD FOREIGN KEY("id_usuario_destinatario") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "notificacao"
ADD FOREIGN KEY("id_matricula_turma") REFERENCES "matricula_turma"("id_matricula_turma")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "notificacao"
ADD FOREIGN KEY("id_orientacao") REFERENCES "orientacao"("id_orientacao")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "notificacao"
ADD FOREIGN KEY("id_reuniao_orientacao") REFERENCES "reuniao_orientacao"("id_reuniao_orientacao")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "notificacao"
ADD FOREIGN KEY("id_banca") REFERENCES "banca"("id_banca")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "notificacao"
ADD FOREIGN KEY("id_documento_oficial") REFERENCES "documento_oficial"("id_documento_oficial")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "auditoria"
ADD FOREIGN KEY("id_usuario") REFERENCES "usuario"("id_usuario")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "auditoria_alteracao"
ADD FOREIGN KEY("id_auditoria") REFERENCES "auditoria"("id_auditoria")
ON UPDATE NO ACTION ON DELETE NO ACTION;
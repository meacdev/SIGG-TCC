-- Freeze the rubric used by this defense and track optimistic concurrency.
ALTER TABLE banca_defesa ADD COLUMN IF NOT EXISTS versao_banca INTEGER NOT NULL DEFAULT 1;
ALTER TABLE banca_defesa ADD COLUMN IF NOT EXISTS snapshot_avaliacao_banca JSONB;
ALTER TABLE documento_oficial ADD COLUMN IF NOT EXISTS id_arquivo_assinado BIGINT
    REFERENCES arquivo_pdf(id_arquivo_pdf);
ALTER TABLE ata_defesa ADD COLUMN IF NOT EXISTS versao_ata_defesa INTEGER NOT NULL DEFAULT 1;
ALTER TABLE ata_defesa ADD COLUMN IF NOT EXISTS snapshot_ata_defesa JSONB NOT NULL DEFAULT '{}';
CREATE UNIQUE INDEX IF NOT EXISTS uq_ata_banca_versao ON ata_defesa(id_banca_defesa, versao_ata_defesa);
ALTER TABLE notificacao ADD COLUMN IF NOT EXISTS data_tentativa_notificacao TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS ix_notificacao_pendente ON notificacao(situacao_notificacao, data_tentativa_notificacao);

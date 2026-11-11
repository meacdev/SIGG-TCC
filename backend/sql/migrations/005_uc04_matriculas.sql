ALTER TABLE matricula_turma ADD COLUMN IF NOT EXISTS versao_matricula INTEGER NOT NULL DEFAULT 1;
ALTER TABLE notificacao ADD COLUMN IF NOT EXISTS data_tentativa_notificacao TIMESTAMP;

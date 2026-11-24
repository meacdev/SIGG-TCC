-- UC14 Manter Usuários (CR-2026-0001): perfil Administrador, convite de pré-cadastro
-- e papel de Professor da Disciplina por curso (RN 03 e RN 07).

INSERT INTO perfil (codigo_perfil, descricao_perfil)
VALUES ('administrador', 'Administrador do sistema (secretaria)')
ON CONFLICT (codigo_perfil) DO NOTHING;

ALTER TABLE token_usuario DROP CONSTRAINT token_usuario_finalidade_token_usuario_check;
ALTER TABLE token_usuario ADD CONSTRAINT ck_token_usuario_finalidade CHECK (
    finalidade_token_usuario IN ('redefinir_senha', 'validar_email', 'alterar_email',
                                 'convite_externo', 'convite_cadastro'));

-- RN 03: um novo envio invalida o anterior, portanto há no máximo um convite pendente.
CREATE UNIQUE INDEX uq_token_convite_pendente ON token_usuario (id_usuario)
    WHERE finalidade_token_usuario = 'convite_cadastro' AND data_consumo_token_usuario IS NULL;

ALTER TABLE professor_curso
    ADD COLUMN professor_disciplina_professor_curso BOOLEAN NOT NULL DEFAULT false;

-- Preserva o acesso atual: o papel era global e valia em todos os vínculos vigentes.
UPDATE professor_curso pc SET professor_disciplina_professor_curso = true
WHERE (pc.data_fim_professor_curso IS NULL OR pc.data_fim_professor_curso >= CURRENT_DATE)
  AND EXISTS (SELECT 1 FROM usuario_perfil up JOIN perfil p ON p.id_perfil = up.id_perfil
              WHERE up.id_usuario = pc.id_professor AND p.codigo_perfil = 'professor_disciplina'
                AND (up.data_expiracao_usuario_perfil IS NULL
                     OR up.data_expiracao_usuario_perfil > CURRENT_TIMESTAMP));

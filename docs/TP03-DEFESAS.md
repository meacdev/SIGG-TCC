# TP03 • Defesas do SIGG-TCC

## Fluxo de demonstração

1. Use banco de desenvolvimento ou homologação com o esquema base e aplique as migrações com `yarn db:upgrade`. As migrações 009 e 010 alinham, respectivamente, o modelo acadêmico e o versionamento de bancas e documentos.
2. Como estudante, registre o trabalho vinculado a uma matrícula ativa. O orientador precisa aceitar o vínculo. Em **Trabalhos**, envie o PDF do manuscrito.
3. Como professor da disciplina ou coordenador autorizado, abra **Organizar defesas**. Ative uma rubrica com pesos que somem 100 ou 10. Agende a defesa com dois titulares adicionais e pelo menos um suplente. O orientador aceito preside a banca.
4. No dia da defesa, os três titulares registram notas em **Minhas bancas**. A primeira avaliação congela a rubrica. A ata exige todas as avaliações.
5. Na seção de documentos da banca, registre o resultado, emita a ata e baixe as declarações. O código de verificação confere a emissão e a vigência. A validação institucional das assinaturas é realizada antes de registrar o PDF assinado. O estudante consulta a liberação em **Minhas atas**.

## Operação e limites

- A composição é registrada pelo gestor. Avaliadores externos são incluídos pelo perfil docente externo existente, com instituição e titulação. A tela de agendamento usa a busca por nome para selecionar a conta já cadastrada.
- Configure `FRONTEND_URL` para os links do portal e `PRIVATE_STORAGE_DIR` para o armazenamento com acesso restrito. O padrão é `instance/private`.
- Execute periodicamente `flask --app backend.app:create_app enviar-notificacoes-academicas` no ambiente da aplicação. A fila registra convites e reagendamentos com anexo ICS, e programa o lembrete quando há pelo menos 24 horas de antecedência. Configuração e entrega real por SMTP precisam de validação no ambiente institucional.
- Os PDFs usam modelos operacionais do SIGG-TCC. O NUCOMP precisa homologar o conteúdo institucional. A solicitação de correção já pode ser registrada com o resultado da banca, enquanto a submissão e validação das correções segue o planejamento do TP04.
- O contrato OpenAPI concentra os caminhos das APIs. O cenário automatizado `tests/test_defense_workflow.py` cobre as etapas de rubrica, manuscrito, banca, notas e emissão de PDFs.

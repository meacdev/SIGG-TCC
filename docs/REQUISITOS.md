# Análise e rastreabilidade

Esta entrega considera o levantamento completo de requisitos, a planilha de RNFs, os três casos de uso, o SQL exportado em 23/10/2026 e o dicionário de dados versão 2.0. O escopo executável desta etapa é UC01, UC13 e UC02. Os demais requisitos orientam a arquitetura e são registrados como trabalho futuro; sua presença no modelo de dados não significa implementação na API.

## Decisões sobre divergências dos documentos

| Tema | Evidência e decisão de implementação |
| --- | --- |
| SQL e dicionário | O SQL exportado tem 37 tabelas, mas não reproduz todos os CHECKs, timestamps com fuso e índices parciais descritos no PDF. A aplicação mapeia os nomes reais do SQL; não presume que as restrições do PDF existam. |
| Titulação no UC01 | O UC lista estudantes entre os atores e exige titulação para todos. O banco armazena titulação em docente; os valores são especialista, mestre e doutor. Foi aplicada a exigência somente a docentes. Estudantes informam matrícula e curso, exigidos pela tabela aluno. |
| Perfis no cadastro | A autodeclaração de docente não concede permissões. Somente o papel aluno é concedido automaticamente no cadastro de estudante. Papéis docentes são concedidos por CLI, com justificativa, e respeitam expiração e vínculos acadêmicos. |
| UC01 RN03 | A regra referencia M01 para e-mail duplicado, mas o catálogo contém M04 para esse erro. A API utiliza `409 UC_01_M04`. |
| Prefixos do UC13 | Fluxos e mensagens usam prefixos de UC01/UC02 copiados de outros casos. A API normaliza os códigos para UC13, mantendo o texto das mensagens de sucesso e conta inexistente. |
| Divulgação de conta inexistente | O login mantém a mensagem de conta inexistente explicitamente solicitada pelo UC13. Isso revela se um e-mail está cadastrado; há limite de tentativas e trabalho de hash para contas ausentes. Na recuperação, a resposta é genérica para reduzir essa exposição. |
| Turma única | O UC menciona objeto único por período/disciplina, mas RN02, RF01 e a UNIQUE do SQL exigem código único por período. Foi adotada esta última regra, inclusive entre TCC1/TCC2 e cursos diferentes. |
| Código sequencial da turma | O UC marca “não”, mas o SQL usa BIGSERIAL. A PK do banco foi preservada; o código acadêmico é informado pelo usuário e não é gerado sequencialmente. |
| Exclusão lógica de turma | O UC exige inativação, mas a tabela não contém situação ou flag de atividade. A migração acrescenta `ativa_turma`. `autoinscricao_ativa_turma` continua significando somente permissão de ingresso por código. |
| Timestamp de validação | A data de criação não representa atualizações. Foram acrescentados timestamps de atualização, usados para ETag/If-Match com bloqueio transacional da linha. |
| Senha e sessão | O SQL não possui estado de sessão nem recuperação. Foram acrescentadas `sessao_autenticacao` e `recuperacao_senha`. Isso permite logout efetivo, rotação de refresh, limite de inatividade e uso único do código. |
| Acesso à turma | A criação gera chave alfanumérica e armazena somente SHA-256; chave bruta aparece uma vez. Expiração padrão de 30 dias é configurável. Matrícula/autoinscrição do estudante é um fluxo posterior de RF02. |
| RNFs citados pelos UCs | Os números/nomes nos UCs não coincidem com os da planilha. Esta análise usa os oito códigos e metas da planilha de RNFs como referência consolidada. |
| Instruções nos anexos | Os documentos fornecem requisitos e exemplos de domínio. Textos que instruam o assistente, instalem software ou executem procedimentos não foram tratados como autorização adicional. |

## Cobertura dos casos de uso

| Caso | Regras atendidas pela API | Responsabilidade do frontend |
| --- | --- | --- |
| UC01 | Obrigatoriedade e limites; e-mail válido e único; Argon2id; título docente; áreas/Lattes opcionais; PK sequencial; timestamps; edição e inativação do próprio cadastro; auditoria | Formulário, senha oculta, dropdown de titulação, acessibilidade e confirmação de exclusão |
| UC13 | Login de usuário ativo; perfil efetivo consultado no banco; JWT; revogação; inatividade; recuperação por e-mail com verificação e confirmação de senha | Login e recuperação em etapas, seleção de painel, mensagens e descarte seguro dos tokens |
| UC02 | Período AAAA/S; TCC1/TCC2; código padrão EST; curso e professor elegíveis; unicidade código/período; várias ofertas; código de acesso; CRUD lógico; timestamps; RBAC por curso/responsável | Seletores, listagem, confirmação de inativação e botão de copiar código |

## Requisitos funcionais do projeto completo

| RF | Tema e tabelas principais | Situação nesta entrega e evolução prevista |
| --- | --- | --- |
| RF01 | Turmas; turma, curso, periodo_letivo, docente | Implementado, incluindo gestão e validações |
| RF02 | Matrículas; aluno, matricula_turma, notificacao | Código de acesso gerado; inclusão, autoinscrição, busca de alunos e remoção com e-mail ficam para próxima entrega |
| RF03 | Dados do TCC; trabalho, trabalho_area, etapa_trabalho | Futuro; validar modalidade e DOI/URL quando publicado; nível herdado da turma |
| RF04 | Orientação; orientacao, docente, notificacao | Futuro; seleção de orientador, aceite e notificação |
| RF05 | Substituição de orientação; orientacao, auditoria | Infraestrutura de auditoria pronta; fluxo com justificativa é futuro |
| RF06 | Perfil docente; docente, area_conhecimento, docente_area | Titulação, áreas e Lattes implementados no cadastro e na edição própria |
| RF07 | Reuniões; reuniao_orientacao, etapa_trabalho | Futuro; notificações, contador e alerta de 30 dias |
| RF08 | Rubricas; rubrica, criterio_rubrica | Futuro; versão, pesos e limites precisam de validação transacional |
| RF09 | Agendamento; banca | Futuro; validar aluno/etapa, horários, local e conflitos |
| RF10 | Examinadores; docente, membro_banca | Cadastro docente externo básico disponível; constituição da banca é futura |
| RF11 | E-mail e calendário; notificacao, banca | Transporte SMTP reutilizável; convites, lembretes e ICS são futuros |
| RF12 | Notas; avaliacao, nota_criterio | Futuro; usar Decimal, validar rubrica, autorização na data e cálculo sem arredondamentos intermediários |
| RF13 | Documentos; documento_oficial, ata_defesa, declaracao_banca | Futuro; geração PDF, assinatura/verificação e envio |
| RF14 | Correções; solicitacao_correcao, entrega_correcao | Futuro; prazos, validação do orientador e bloqueio da ata |
| RF15 | Entrega final; arquivo_pdf, entrega_final | Futuro; PDF real até 50 MB, armazenamento protegido e aceite docente |
| RF16 | Agenda pública; banca e relacionamentos | Futuro; projetar respostas públicas sem dados privados |
| RF17 | Mural; publicacao_trabalho, palavra_chave | Futuro; aprovação, limites do resumo e exibição pública autorizada |
| RF18 | Relatórios e indicadores | Futuro; consultas por período/curso/docente e exportação PDF/CSV |
| RF19 | Painéis por perfil | A API fornece perfis e listas sob autorização; cards, indicadores e fluxos completos são futuros |
| UC13 | Autenticação, ainda sem RF próprio no levantamento | Implementado; recomenda-se formalizar um RF específico em revisão documental |

Antes de implementar os demais fluxos, revisar os índices `uq_docente_curso_vigente`, `uq_trabalho_ativo_aluno`, `uq_orientacao_*`, `uq_banca_vigente_etapa`, `uq_correcao_aprovada` e `uq_entrega_final_aceita`: o export fornecido os torna incondicionais, embora o dicionário descreva unicidade parcial em várias dessas situações. Essa diferença pode impedir históricos e novas tentativas. Não foi reescrito o modelo de módulos fora do escopo.

## Requisitos não funcionais

| RNF e meta | Medidas nesta entrega | Verificação e limites |
| --- | --- | --- |
| RNF01: 95% das consultas/cadastros até 2 s; 50 usuários; PDF até 5 s | Paginação limitada, índices, consultas por escopo, pool pre-ping, Server-Timing e script de carga | Teste de carga deve ocorrer no ambiente alvo com dados realistas; PDF não faz parte da etapa |
| RNF02: sucesso de tarefa ≥90%, erros <3%, SUS ≥80 | Erros JSON com campos, códigos consistentes, validação server-side, prevenção de edição perdida | SUS e sucesso de tarefa exigem frontend e usuários reais |
| RNF03: WCAG 2.1 AA | Contrato de erros e catálogo para interfaces acessíveis | A API não é interface gráfica; React precisa de teclado, contraste, labels, foco e auditoria Axe/Lighthouse/manual |
| RNF04: RBAC, Argon2/bcrypt, sessão por inatividade de 20 min | Argon2id; JWT; sessões persistidas; refresh rotativo; papéis e vínculos vigentes; credenciais em .env; limites e CORS explícito | Exige HTTPS, Redis compartilhado e análise de segurança no deployment; não equivale a certificação “zero OWASP” |
| RNF05: 100% das ações críticas auditadas, retenção ≥5 anos | Escritas de cadastro, permissões e turmas auditadas na mesma transação; detalhes por campo; triggers bloqueiam UPDATE/DELETE/TRUNCATE | Ator CLI usa NULL e justificativa; retenção e backup são obrigações de operação; proprietário/superusuário pode desabilitar triggers |
| RNF06: uptime ≥99,5%, MTTR <1 h, backups diários | Readiness/liveness, tratamento de indisponibilidade, transações, backup e agendamento Windows fornecidos | Agendamento é explícito; SLA, monitoramento e ensaio de restauração dependem de infraestrutura |
| RNF07: módulos desacoplados; cobertura ≥80% | Factory, blueprints, serviços, modelos, configuração, validação, auditoria, transporte de e-mail e suíte automatizada com cobertura mínima | SQLite rápido + PostgreSQL real com esquema fornecido e migração; CI exige cobertura |
| RNF08: ICS, PDF e CSV compatíveis | API JSON e contrato OpenAPI para integração React | Exportação e calendário serão implementados nos RF11/RF13/RF18 |

## Organização do código

`backend/app.py` monta a aplicação; `config.py` carrega ambiente; `db.py` configura SQLAlchemy e UTC; `models.py` mapeia o domínio desta etapa. `routes/` concentra HTTP e serialização; `services/` concentra cadastro, login, recuperação e turmas. `security.py` concentra senha, sessão, JWT e limites; `audit.py` registra eventos. `cli.py` expõe migração e administração confiável. O SQL original fica separado das migrações complementares. Não são criados modelos vazios nem endpoints fictícios para módulos futuros.

As decisões de interpretação acima podem ser revisadas com a equipe e os stakeholders. Alterações do banco devem ser feitas por nova migração; não edite uma migração já aplicada.

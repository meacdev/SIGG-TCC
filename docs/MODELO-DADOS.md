# Modelo de dados atualizado (migração 009)

A migração `backend/sql/migrations/009_modelo_dados_atualizado.sql` alinha o banco ao `TCC_atualizado.sql` e ao Dicionário de Dados de 09/11/2026. Ela é incremental: **renomeia** tabelas e colunas (os dados, sequências, chaves e triggers são preservados) e acrescenta o que é novo. O `000_schema_fornecido.sql` continua sendo a base histórica; não importe o `TCC_atualizado.sql` diretamente.

## Aplicar

1. Faça backup do banco (`scripts/backup.ps1`).
2. Na raiz, com a conta de manutenção: `yarn db:upgrade` (ou `yarn dev` com `AUTO_MIGRATE=true`).
3. Ajuste as permissões da conta restrita para os novos nomes (exemplo em `OPERACAO.md`).

A migração roda em uma única transação. Se falhar, nada é alterado.

## Renomeações

| Antes | Depois |
| --- | --- |
| `docente`, `docente_area`, `docente_curso` | `professor`, `professor_area`, `professor_curso` |
| `aluno` | `estudante` |
| `trabalho` | `trabalho_tcc` (colunas `*_trabalho` → `*_trabalho_tcc`) |
| `reuniao_orientacao` | `ata_orientacao` |
| `rubrica`, `banca`, `avaliacao` | `rubrica_avaliacao`, `banca_defesa`, `avaliacao_banca` |
| `id_docente*`, `id_aluno`, `id_banca`, `id_rubrica`, `id_avaliacao` | `id_professor*`, `id_estudante`, `id_banca_defesa`, `id_rubrica_avaliacao`, `id_avaliacao_banca` |
| `membro_banca.id_docente` → `docente` | `membro_banca.id_avaliador` → nova tabela `avaliador` |

## Conversões de dados

- Titulação: `mestre` → `Mestre` (domínio `Especialista`, `Mestre`, `Doutor`).
- Modalidade: `artigo_publicado`/`artigo_a_submeter` → `modalidade_trabalho_tcc = 'artigo'` + `tipo_artigo_trabalho_tcc = 'publicado'/'a_submeter'`.
- Perfil `aluno` → `estudante`.

Registros antigos de `auditoria` continuam com `entidade_auditoria = 'trabalho'`/`'reuniao_orientacao'`: a auditoria é imutável. Registros novos usam `trabalho_tcc`/`ata_orientacao`.

## Novidades

- `usuario`: `cpf_usuario`, `telefone_usuario`, `email_validado_usuario`, `tentativas_login_usuario`, `bloqueado_ate_usuario`; nome limitado a 100 caracteres.
- `professor_curso.departamento_unidade_professor_curso` (obrigatório para coordenador: `conceder-perfil --perfil coordenador --departamento ...`).
- `etapa_trabalho.data_limite_etapa_trabalho`; `rubrica_avaliacao` com bloqueio/modificação; `banca_defesa` com modalidade, URL e manuscrito.
- Tabelas `avaliador`, `manuscrito_trabalho`, `sessao_usuario`, `token_usuario`.
- 49 CHECKs do dicionário (nomeados `ck_<tabela>_<regra>`).

## Desvios intencionais do script entregue

- **Tipos sem aspas.** O script declara `"VARCHAR(100)"`, `"NUMERIC(5,2)"` etc. O PostgreSQL rejeita esses tipos.
- **Índices com `WHERE`.** No script, os índices "vigente/ativa/aceita/presidente" não têm filtro, o que proibiria, por exemplo, mais de um membro por banca. Na migração:
  - `uq_presidente_banca_defesa`: `WHERE papel_membro_banca = 'presidente'`
  - `uq_rubrica_ativa_turma`: `WHERE situacao_rubrica_avaliacao = 'ativa'`
  - `uq_trabalho_ativo_estudante`: `WHERE situacao_trabalho_tcc = 'em_andamento'`
  - `uq_banca_vigente_etapa`: `WHERE situacao_banca_defesa <> 'cancelada'`
  - `uq_professor_curso_vigente`: `WHERE data_fim_professor_curso IS NULL`
  - `uq_correcao_aprovada` / `uq_entrega_final_aceita`: só a entrega aprovada/aceita é única
  - `uq_orientacao_*`: mantém o filtro da migração 006
- **Estruturas do projeto mantidas.** `sessao_autenticacao`, `recuperacao_senha`, `lote_cobranca`, colunas de versão (`versao_*`), `ativa_turma`, `palavras_chave_trabalho_tcc`, `id_matricula_atual` e os triggers de imutabilidade.
- **CHECKs sobre dados legados.** São criados `NOT VALID` e validados em seguida. Uma linha antiga que viole uma regra gera `WARNING` em vez de bloquear a atualização; linhas novas e alteradas são sempre verificadas.

## Regras do RF20/RF21 já implementadas

- **CPF e telefone (RF20.1).** `cpf_usuario` e `telefone_usuario` são opcionais no cadastro e na edição do perfil (`null` ou `""` apaga). O CPF aceita pontuação, é validado pelos dígitos verificadores e gravado com 11 dígitos; duplicado retorna `409 CPF_DUPLICADO`. O telefone aceita `+`, espaços, parênteses e hífens e é gravado só com dígitos (10 a 13, com DDD).
- **Bloqueio de login (RF21.1.3).** Cada senha errada soma 1 em `tentativas_login_usuario`. Na 5ª, `bloqueado_ate_usuario` recebe agora + 15 min e o login responde `423 CONTA_BLOQUEADA`, mesmo com a senha certa, até o prazo acabar. Expirado o prazo, a contagem recomeça; login correto e redefinição de senha zeram contagem e bloqueio. O bloqueio é auditado (`bloqueio_login`).
- **Política de senha (RF21.1.1).** 8 a 128 caracteres, com ao menos 1 letra maiúscula, 1 número e 1 caractere especial (qualquer caractere que não seja letra ou número, inclusive espaço). Vale para cadastro e redefinição; senhas antigas continuam aceitas no login.

## Ainda não usado pela API

- Validação e alteração de e-mail por token (`email_validado_usuario`, `token_usuario`, RF20.3.1). Hoje a troca de e-mail exige a senha atual e revoga as sessões, sem confirmação no novo endereço.
- `sessao_usuario`. A API continua usando `sessao_autenticacao`, que guarda expiração absoluta e o JTI do refresh token, e `recuperacao_senha` para o código de recuperação.

## Mudanças no contrato da API

- Campos JSON seguem os nomes novos: `titulacao_professor`, `url_lattes_professor`, `id_professor_responsavel`, `matricula_estudante`, `id_trabalho_tcc`, `id_ata_orientacao` etc.
- Objetos `professor`/`estudante` (antes `docente`/`aluno`) no usuário; `tipo_cadastro` aceita `professor`/`estudante`.
- Rotas `/professores` e `/professores-orientacao` (antes `/docentes` e `/docentes-orientacao`).
- Novas validações: nome de 3 a 100 caracteres, Lattes em `lattes.cnpq.br`, instituição obrigatória para professor externo.

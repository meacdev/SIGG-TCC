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

## Ainda não usado pela API

As colunas e tabelas abaixo já existem, mas as regras de negócio do RF20/RF21 ainda não foram implementadas:

- CPF e telefone no cadastro.
- Validação de e-mail por token (`email_validado_usuario`, `token_usuario`).
- Bloqueio de 15 min após 5 tentativas de login (`tentativas_login_usuario`, `bloqueado_ate_usuario`).
- Política de senha do RF21.1.1. A API ainda exige 12 a 128 caracteres.
- `sessao_usuario`. A API continua usando `sessao_autenticacao`, que guarda expiração absoluta e o JTI do refresh token.

## Mudanças no contrato da API

- Campos JSON seguem os nomes novos: `titulacao_professor`, `url_lattes_professor`, `id_professor_responsavel`, `matricula_estudante`, `id_trabalho_tcc`, `id_ata_orientacao` etc.
- Objetos `professor`/`estudante` (antes `docente`/`aluno`) no usuário; `tipo_cadastro` aceita `professor`/`estudante`.
- Rotas `/professores` e `/professores-orientacao` (antes `/docentes` e `/docentes-orientacao`).
- Novas validações: nome de 3 a 100 caracteres, Lattes em `lattes.cnpq.br`, instituição obrigatória para professor externo.

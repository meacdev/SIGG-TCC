# Contrato da primeira entrega

Prefixo: `/api/v1`. Todas as operações com corpo exigem `Content-Type: application/json`. Rotas protegidas exigem `Authorization: Bearer <access_token>`. No refresh, utilize o `refresh_token`; no logout, qualquer um dos dois. Campos desconhecidos no corpo são rejeitados. IDs são as chaves do banco, não índices de listas.

| Método | Rota | Acesso e finalidade |
| --- | --- | --- |
| POST | `/usuarios` | Público; cadastrar docente ou estudante |
| GET | `/usuarios/me` | Consultar o próprio cadastro e seu ETag |
| PATCH | `/usuarios/me` | Atualizar cadastro; exige `If-Match` |
| DELETE | `/usuarios/me` | Inativar cadastro e revogar sessões; exige `If-Match` e senha atual |
| POST | `/auth/login` | Público; autenticar e obter tokens e perfis |
| POST | `/auth/refresh` | Renovar usando refresh token; o anterior perde a validade |
| DELETE | `/auth/logout` | Revogar a sessão e todos os seus tokens |
| POST | `/auth/recuperacao-senha` | Público; solicitar código por e-mail |
| POST | `/auth/recuperacao-senha/verificar` | Público; trocar código por token de redefinição |
| POST | `/auth/recuperacao-senha/redefinir` | Público; redefinir senha e revogar todas as sessões |
| GET | `/cursos` | Público; cursos ativos para os seletores de cadastro |
| GET | `/periodos-letivos` | Autenticado; consultar períodos |
| GET | `/docentes?id_curso=1` | Gestor; responsáveis elegíveis para seu curso |
| POST | `/turmas` | Professor autorizado ou coordenador do curso; criar turma |
| GET | `/turmas` | Listar somente turmas sob sua gestão |
| GET | `/turmas/{id}` | Consultar turma sob sua gestão e obter ETag |
| PATCH | `/turmas/{id}` | Atualizar; exige `If-Match` |
| DELETE | `/turmas/{id}` | Inativar e invalidar código; exige `If-Match` |
| POST | `/turmas/{id}/codigo-acesso` | Gerar novo código, invalidando o anterior; exige `If-Match` |

As listas têm `page` (1 a 100000) e `per_page` (1 a 100, padrão 20), com `meta.page`, `meta.per_page`, `meta.total` e `meta.pages`. Turmas aceitam filtros `id_curso`, `periodo_letivo`, `nivel_turma` e `ativa_turma=true|false`. Sem filtro de situação, incluem turmas inativas.

## Cadastro e login

Exemplo docente: substitua o valor de `senha` por uma senha escolhida pelo usuário, com 12 a 128 caracteres. Não registre o corpo da requisição em logs.

```json
{
  "nome_usuario": "Nome do docente",
  "email_usuario": "docente@instituicao.edu.br",
  "senha": "<senha informada no formulário>",
  "tipo_cadastro": "docente",
  "tipo_docente": "interno",
  "titulacao_docente": "mestre",
  "areas_interesse": ["Engenharia de Software"],
  "url_lattes_docente": "https://lattes.cnpq.br/123456"
}
```

Titulações: `especialista`, `mestre`, `doutor`. Áreas e Lattes são opcionais. `instituicao_origem_docente` também é opcional. Um cadastro docente não concede automaticamente papéis administrativos.

Para estudante, use `tipo_cadastro: "aluno"`, `matricula_aluno` e `id_curso`, além de nome, e-mail e senha. Não envie campos docentes. O estudante recebe somente o papel `aluno`. A matrícula é texto, preservando zeros iniciais.

O login recebe `email_usuario` e `senha` e retorna:

```json
{
  "code": "UC_13_M01",
  "message": "Login realizado com sucesso!",
  "data": {
    "access_token": "<JWT>",
    "refresh_token": "<JWT>",
    "token_type": "Bearer",
    "expires_in": 1200,
    "usuario": { "id_usuario": 1, "nome_usuario": "Nome", "email_usuario": "docente@instituicao.edu.br", "perfis": ["professor_disciplina"] }
  }
}
```

Tokens de acesso duram 20 minutos por padrão. A sessão expira após 20 minutos sem requisições autenticadas válidas e, em qualquer caso, após 12 horas. A renovação só funciona enquanto a sessão estiver ativa. Substitua ambos os tokens a cada refresh. Não use timers de renovação ou polling para manter usuários inativos conectados.

Editar o e-mail exige `senha_atual` e revoga todas as sessões: solicite novo login após salvar. O e-mail é normalizado para minúsculas. O catálogo de mensagens do UC13 tinha prefixos copiados de outros UCs; a API utiliza `UC_13_M01`, `UC_13_M02` e `UC_13_CONTA_NAO_CADASTRADA`.

## Recuperação de senha

1. Envie `{"email_usuario":"..."}` para `/auth/recuperacao-senha`. A resposta `202` contém `data.id_recuperacao` e uma mensagem genérica, inclusive para contas inexistentes ou inativas.
2. O usuário recebe um código de dez dígitos por e-mail, válido por dez minutos. Envie `id_recuperacao` e `codigo` para `/auth/recuperacao-senha/verificar`. São permitidas cinco tentativas por recuperação. Um novo pedido invalida os anteriores.
3. Guarde `data.token_redefinicao` em memória. Envie esse token, `id_recuperacao`, `nova_senha` e `confirmacao_senha` para `/auth/recuperacao-senha/redefinir`.
4. O código e o token só podem ser utilizados uma vez. A senha é substituída e todas as sessões anteriores são revogadas. Retorne à tela de login.

O endpoint de solicitação permite um pedido por minuto e três por hora por IP. Os demais endpoints sensíveis também possuem limites. `503 EMAIL_INDISPONIVEL` indica falha ou ausência de configuração SMTP; não existe modo de expor códigos na resposta HTTP ou no log.

## Turmas e concorrência

```json
{
  "periodo_letivo": "2026/2",
  "codigo_turma": "ESTCOMP01",
  "nivel_turma": 1,
  "id_curso": 1,
  "id_docente_responsavel": 1
}
```

O período é validado e criado se ainda não existir. O código segue `EST<SIGLA><NUM>` e é normalizado para maiúsculas. A combinação código/período é única mesmo em turma inativa; níveis diferentes não autorizam reutilizá-la. Várias turmas distintas podem coexistir no período.

O responsável precisa ser docente interno ativo, usuário ativo, com papel vigente `professor_disciplina` e vínculo vigente com o curso. Um professor indica a si próprio; um coordenador pode indicar outro professor elegível do curso que coordena.

Na criação e na rotação, a resposta contém `data.codigo_acesso`: uma chave alfanumérica de 24 caracteres, válida por 30 dias por padrão. O banco guarda somente seu SHA-256. Consultas não devolvem código nem hash. Após perder o código original, gere outro. A autoinscrição por alunos pertence ao caso de uso de matrícula da próxima entrega.

`GET /turmas/1` retorna, por exemplo, `ETag: "<versao>"`. Envie exatamente esse valor em `If-Match` ao alterar, inativar ou rotacionar o código. O servidor bloqueia a linha durante a alteração. Cabeçalho ausente resulta em `428`; versão desatualizada resulta em `412`.

`PATCH` aceita os campos de criação, `ativa_turma` e `autoinscricao_ativa_turma`. Curso, nível e período não podem mudar após a existência de matrículas, preservando o histórico acadêmico. Uma turma inativada pode ser reativada com `ativa_turma: true`; gere então um novo código para habilitar autoinscrição. Inativar a turma preserva o registro, desabilita autoinscrição e elimina seu hash de acesso.

## Erros

```json
{
  "error": {
    "code": "VALIDACAO",
    "message": "Campo inválido.",
    "fields": { "nome_usuario": "Informe entre 1 e 200 caracteres." }
  }
}
```

`201`: criado; `204`: operação sem corpo; `401`: autenticação/token; `403`: permissão ou conta inativa no login; `404`: recurso inexistente ou turma fora do escopo; `409`: duplicata ou conflito de negócio; `412/428`: concorrência; `422`: validação; `429`: limite de tentativas; `503`: serviço/banco/e-mail indisponível. O cabeçalho `Retry-After` orienta quando repetir uma requisição limitada.

O frontend deve associar as mensagens aos campos, anunciar erros para leitores de tela, mascarar a senha e obter confirmação antes da inativação. Essas ações de interface não são implementadas pela API.

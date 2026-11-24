# SIGG-TCC

Sistema de Gestão de TCC: API REST em Python/Flask (`backend/`) e interface React/TypeScript (`frontend/`).

O sistema cobre cadastro e login com recuperação de senha por e-mail (UC01–UC02), turmas (UC03), matrículas (UC04), atas de orientação (UC05), trabalhos (UC06) e o monitoramento de prazos (UC13). Também cobre a organização de defesas, a avaliação pela rubrica oficial, a ata e os documentos da banca. A ordem de dependência dos módulos acadêmicos é **UC03 → UC04 → UC06 → UC05**. Detalhes em [UC03](docs/UC03.md), [UC04](docs/UC04.md), [UC05](docs/UC05.md), [UC06](docs/UC06.md), [UC13](docs/UC13.md) e [Defesas (TP03)](docs/TP03-DEFESAS.md).

Tecnologias: SQLAlchemy, PostgreSQL, Flask-JWT-Extended, Argon2id, python-dotenv, React, Vite e Vitest. A aplicação não cria tabelas ao iniciar: o esquema evolui por migrações SQL versionadas em `backend/sql/migrations/`. O banco segue o [modelo de dados atualizado](docs/MODELO-DADOS.md).

## Pré-requisitos

| Ferramenta | Versão |
| --- | --- |
| Python | 3.14 |
| PostgreSQL | 18, com o serviço iniciado |
| Node.js | 22.12 ou superior (a CI usa 24) |
| Yarn | 1.22.22, via Corepack (`corepack enable`) — veja [docs/YARN.md](docs/YARN.md) |

Todos os comandos abaixo são executados na **raiz do repositório**. Os scripts `yarn` também funcionam com `npm run`.

## Iniciar do zero

### 1. Instalar dependências

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
yarn install --frozen-lockfile
```

Instale o front-end pela raiz: o projeto usa um workspace Yarn com um único `yarn.lock`. Os scripts `yarn` chamam o Python de `.venv` diretamente, sem ativação manual. `SIGG_PYTHON` permite indicar outro executável.

### 2. Configurar o `.env`

```powershell
Copy-Item .env.example .env
yarn env:key
```

Edite `.env`:

- `DATABASE_URL`: conexão com o PostgreSQL, por exemplo `postgresql+psycopg://postgres:SENHA@localhost:5432/sigg_tcc`. Caracteres especiais da senha precisam de URL encoding ([como codificar](docs/INICIAR.md#arquivo-de-configuração-e-ambiente-python)).
- `JWT_SECRET_KEY`: cole somente a chave gerada por `yarn env:key`.
- `SMTP_*`: pode ficar vazio para cadastro e login locais; recuperação de senha e convites exigem SMTP real ([UC02](docs/UC02-LOGIN.md)).

As demais opções podem manter os valores do exemplo. O front-end não precisa de `.env` próprio no desenvolvimento ([frontend/.env.example](frontend/.env.example)). Nunca publique o `.env`. Confira o preenchimento sem exibir segredos:

```powershell
yarn env:check
```

### 3. Preparar o banco

1. Crie o banco `sigg_tcc` no pgAdmin ou com `createdb`.
2. **Somente em um banco novo e vazio**, importe `backend/sql/000_schema_fornecido.sql` pelo Query Tool do pgAdmin ou pelo psql. Esse arquivo é a cópia integral do SQL entregue, não uma migração. Se as tabelas já existem, não repita a importação.
3. Aplique as migrações, inicialize os perfis e crie ao menos um curso (o cadastro de estudante exige um curso ativo):

```powershell
yarn db:upgrade
yarn db:seed
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app criar-curso --codigo SI --nome "Sistemas de Informação"
yarn db:check
```

`db:upgrade` aplica, em uma transação e com lock, todas as migrações pendentes de `backend/sql/migrations/` (hoje 001 e 005 a 012). Migrações já aplicadas têm o checksum conferido. Faça backup antes de atualizar um banco com dados. A migração aborta, sem apagar registros, se houver e-mails que diferem só por maiúsculas ou códigos equivalentes no mesmo período: resolva essas duplicatas antes.

Crie cada curso uma única vez. `db:check` confere a conexão e a estrutura sem criar dados.

### 4. Iniciar a aplicação

```powershell
yarn dev
```

| Serviço | Endereço |
| --- | --- |
| Aplicação (Vite) | http://127.0.0.1:5173 |
| API (Flask) | http://127.0.0.1:5000/api/v1 |
| Contrato OpenAPI | http://127.0.0.1:5000/api/v1/openapi.json |
| Saúde | `/api/v1/health/live` e `/api/v1/health/ready` |

`yarn dev` confere o `.env` e o banco e sobe o Flask e o Vite juntos. `Ctrl+C` encerra os dois, e se um falhar o outro também é encerrado. As portas 5000 e 5173 precisam estar livres. Com `AUTO_MIGRATE=true` (padrão do exemplo) e banco em `localhost`, as migrações pendentes são aplicadas automaticamente antes da partida. Use `AUTO_MIGRATE=false` para controlá-las só com `yarn db:upgrade`. O SQL base nunca é importado automaticamente.

Se o PowerShell bloquear `yarn.ps1`, use `yarn.cmd dev`.

### 5. Primeiro professor e coordenador

Crie a conta docente pela tela de cadastro. Ela entra e edita o próprio perfil, mas não recebe poderes administrativos por autodeclaração. Um administrador com acesso ao terminal concede o papel e o vínculo com o curso:

```powershell
# Substitua e-mails, ID do curso e departamento pelos valores reais
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app conceder-perfil --email docente@instituicao.edu.br --perfil professor_disciplina --id-curso 1 --justificativa "Designação para ministrar TCC"
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app conceder-perfil --email coordenador@instituicao.edu.br --perfil coordenador --id-curso 1 --departamento "Departamento de Computação" --justificativa "Portaria de coordenação"
```

- `professor_disciplina` e `coordenador` exigem professor **interno** com cadastro ativo. `--departamento` é obrigatório para o coordenador quando o vínculo ainda não o possui.
- O professor gerencia as próprias turmas nos cursos em que tem o papel. O coordenador gerencia as turmas dos cursos que coordena e pode autorizar professores desses cursos.
- `--revogar` retira o papel do curso indicado. O perfil do usuário só expira quando não restar curso com esse papel. `--expira-em` aceita data ISO 8601 futura com fuso.
- O primeiro administrador também é criado aqui, com `--perfil administrador` e sem curso. Os demais são concedidos pela API do UC14 (`docs/UC14.md`).
- Toda concessão e revogação exige justificativa e gera auditoria com ator de sistema (`id_usuario=NULL`).

## Comandos

| Comando | Finalidade |
| --- | --- |
| `yarn dev` | Flask e Vite juntos |
| `yarn dev:backend` / `yarn dev:frontend` | Somente um dos servidores |
| `yarn env:key` / `yarn env:check` | Gerar chave JWT / verificar o `.env` |
| `yarn db:upgrade` / `yarn db:seed` / `yarn db:check` | Migrações / perfis / conferência do banco |
| `yarn test` | Vitest e depois pytest |
| `yarn test:frontend` / `yarn test:watch` / `yarn test:backend` | Testes separados |
| `yarn test:e2e` | Playwright com API descartável em SQLite (porta 5001) |
| `yarn build` | Compila o front-end em `frontend/dist` |
| `yarn start:backend` | API com Waitress em `127.0.0.1:5000` |

Comandos administrativos do Flask (`.\.venv\Scripts\python.exe -m flask --app backend.app:create_app <comando>`):

| Comando | Finalidade |
| --- | --- |
| `criar-curso --codigo X --nome "..."` | Cria um curso |
| `criar-periodo 2026/2` | Cria um período letivo (`AAAA/1` ou `AAAA/2`) |
| `conceder-perfil ...` | Concede ou revoga papéis (seção 5) |
| `enviar-notificacoes-academicas` | Processa a fila de e-mails de bancas e documentos; agende a execução periódica |

## Testes e verificação

```powershell
yarn test
.\.venv\Scripts\python.exe -m ruff check backend tests scripts
.\.venv\Scripts\python.exe -m ruff format --check backend tests scripts
.\.venv\Scripts\python.exe -m pytest --cov=backend --cov-report=term-missing
```

Sem configuração adicional, o pytest usa SQLite em memória. Para validar contra PostgreSQL, informe uma URL de banco **descartável**. A suíte cria e remove um schema aleatório por teste, importa o SQL base e executa as migrações reais:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://sigg_test@127.0.0.1:55439/sigg_test'
.\.venv\Scripts\python.exe -m pytest --cov=backend --cov-report=term-missing
Remove-Item Env:TEST_DATABASE_URL
```

O usuário de teste precisa de `CREATE SCHEMA`. Nunca use credenciais de produção. A CI executa as duas modalidades com meta mínima de 80% de cobertura.

Para os testes de navegador, instale o Chromium uma vez com `yarn workspace sigg-tcc-frontend playwright install chromium` e encerre `yarn dev` antes de `yarn test:e2e`.

## Integração com o front-end

Consulte [docs/API.md](docs/API.md), o contrato OpenAPI e [docs/FRONTEND.md](docs/FRONTEND.md). O cliente de referência [docs/frontend-client.ts](docs/frontend-client.ts) mantém tokens em memória, renova a sessão sob demanda e envia `If-Match`.

- As respostas usam `data`. Os erros usam `error.code`, `error.message` e, quando necessário, `error.fields`. As datas são ISO 8601 em UTC.
- Após o login, `data.usuario.perfis` define os menus exibidos. A API valida as permissões em cada requisição.
- Guarde o ETag da consulta e envie-o em `If-Match` nas alterações e exclusões. Um `412` indica alteração concorrente e exige recarregar o registro.
- O código de acesso da turma aparece só na criação ou na rotação.

## Produção e operação

O passo a passo de produção (Waitress, build estático, HTTPS, Redis, SMTP e conta restrita no PostgreSQL) está em [Configurar e iniciar](docs/INICIAR.md#colocar-em-produção). Usuário restrito, backup diário, restauração e desempenho estão em [docs/OPERACAO.md](docs/OPERACAO.md). Documentos gerados ficam em `PRIVATE_STORAGE_DIR` (padrão `instance/private`).

A rastreabilidade dos requisitos está em [docs/REQUISITOS.md](docs/REQUISITOS.md). Os cenários de validação estão em [docs/VALIDACAO.md](docs/VALIDACAO.md).

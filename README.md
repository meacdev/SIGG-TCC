# SIGG-TCC

API REST em Python/Flask para a primeira entrega do Sistema de Gestão de TCC. Implementa UC01 (cadastro e gestão do próprio cadastro), UC13 (login, sessão e recuperação de senha por e-mail) e UC02 (cadastro e gestão de turmas). O front-end React/TypeScript do UC01 está em `frontend/`, com cadastro, login de apoio, consulta, edição e inativação do próprio cadastro. Consulte [o guia do front-end](docs/FRONTEND.md) para executar e verificar a interface.

Utiliza SQLAlchemy, PostgreSQL, Flask-JWT-Extended, Argon2id e python-dotenv. A aplicação não cria nem altera tabelas ao iniciar. As mudanças do banco são explícitas e versionadas.

A branch `codex/yarn-uc01-uc03` consolida cadastro (UC01), login existente (UC02) e [interface de turmas (UC03)](docs/UC03.md) para revisão em develop. A numeração segue os DOCX atualizados. [O guia Yarn](docs/YARN.md) descreve instalação reproduzível na raiz, workspaces, comandos e a integração após aprovação. UCs 04/05/06 e 09/10/11 permanecem em branches próprias.

## Iniciar pela raiz

O guia [Configurar e iniciar](docs/INICIAR.md) explica `.env`, `.venv`, preparação do banco, execução conjunta e produção. Com dependências e banco preparados, execute `yarn dev` na raiz para iniciar back-end e front-end juntos. `yarn test` executa Vitest e pytest; `yarn test:watch` acompanha os testes do front-end. Os scripts também funcionam com `npm run`.

## Preparar o ambiente

Execute na raiz do repositório. Python 3.14 e PostgreSQL 18 são as versões de referência desta entrega.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Edite `.env`: configure `DATABASE_URL` para o banco existente, cole a chave gerada em `JWT_SECRET_KEY` e preencha os parâmetros SMTP para recuperação de senha. Nunca publique esse arquivo. Caracteres especiais da senha do PostgreSQL precisam de URL encoding. É possível usar um usuário PostgreSQL dedicado com `PGPASSFILE` em vez de incluir a senha na URL.

Com o banco já criado, **não importe novamente o esquema base**. Aplique somente a migração complementar e inicialize os perfis:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app db-upgrade
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app seed-perfis
```

O comando aplica migrações em uma transação, utiliza lock para evitar execução concorrente e verifica o checksum de migrações já executadas. Faça backup antes de atualizar um banco com dados. Se existirem e-mails que diferem somente por maiúsculas ou códigos equivalentes no mesmo período, resolva essas duplicatas antes da migração: ela aborta sem apagar registros.

Somente para um banco **novo e vazio**, importe primeiro `backend/sql/000_schema_fornecido.sql` pelo pgAdmin ou psql. Esse arquivo é uma cópia integral do SQL entregue; não é uma migração incremental.

## Executar

```powershell
# Desenvolvimento local
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app run --host 127.0.0.1 --port 5000

# Servidor WSGI, compatível com Windows
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:5000 --call backend.app:create_app
```

Base da API: `http://127.0.0.1:5000/api/v1`. Contrato: `GET /api/v1/openapi.json`. Saúde: `GET /api/v1/health/live` e `GET /api/v1/health/ready`.

## Primeiro docente e permissões

Crie uma conta docente pelo endpoint público de cadastro. Ela pode entrar e editar o próprio perfil, mas não recebe poderes administrativos por autodeclaração. Um administrador com acesso confiável ao terminal concede o papel e o vínculo com o curso:

```powershell
# Se o curso ainda não existir
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app criar-curso --codigo COMP --nome "Ciência da Computação"

# Substitua o e-mail e o ID pelos registros reais
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app conceder-perfil --email docente@instituicao.edu.br --perfil professor_disciplina --id-curso 1 --justificativa "Designação para ministrar TCC"
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app conceder-perfil --email coordenador@instituicao.edu.br --perfil coordenador --id-curso 1 --justificativa "Portaria de coordenação"
```

O professor gerencia suas próprias turmas nos cursos com vínculo vigente. O coordenador gerencia turmas dos cursos em que possui vínculo de coordenação vigente e pode indicar professores autorizados desses cursos. Docentes externos não recebem esses dois papéis. `orientador` e `avaliador` estão no catálogo para entregas futuras.

`conceder-perfil --revogar` expira o papel **global do usuário**; não é uma revogação limitada ao curso indicado. `--expira-em` aceita uma data ISO 8601 futura com fuso. Todas as concessões e revogações exigem justificativa e geram auditoria com ator de sistema (`id_usuario=NULL`).

## Integração React/TypeScript

Consulte `docs/API.md` e o contrato OpenAPI. `docs/frontend-client.ts` fornece um cliente de referência com tokens em memória, renovação sob demanda e envio de `If-Match`.

As respostas usam `data`; erros usam `error.code`, `error.message` e, quando necessário, `error.fields`. Datas são ISO 8601 em UTC. Após o login, `data.usuario.perfis` permite selecionar o painel no React; a API valida as permissões em cada requisição.

O frontend deve guardar o ETag retornado pela consulta e enviá-lo em `If-Match` nas alterações e exclusões. Erro `412` significa que outra alteração ocorreu e o registro precisa ser recarregado. O código de acesso da turma aparece somente na criação ou rotação; exiba um botão de cópia nesse momento.

## Verificar

```powershell
.\.venv\Scripts\python.exe -m ruff check backend tests scripts/generate_openapi.py
.\.venv\Scripts\python.exe -m ruff format --check backend tests scripts/generate_openapi.py
.\.venv\Scripts\python.exe -m pytest --cov=backend --cov-report=term-missing
```

Sem configuração adicional, os testes rápidos usam SQLite em memória. Para validar os mesmos fluxos contra PostgreSQL, configure uma URL de banco **descartável**; a suíte cria e remove um schema aleatório por teste, importa o SQL fornecido e executa a migração real:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://sigg_test@127.0.0.1:55439/sigg_test'
.\.venv\Scripts\python.exe -m pytest --cov=backend --cov-report=term-missing
Remove-Item Env:TEST_DATABASE_URL
```

O usuário de teste precisa de `CREATE SCHEMA`. Nunca use credenciais de produção para testes. A CI executa as duas modalidades, com meta mínima de 80% de cobertura.

## Escopo e operação

A análise e a rastreabilidade de todos os RF/RNF estão em `docs/REQUISITOS.md`. As diferenças entre SQL, dicionário e casos de uso estão registradas ali. Os cenários de teste e as medições locais estão em `docs/VALIDACAO.md`. A implementação dos módulos de orientação, bancas, notas, documentos, matrículas, relatórios e murais pertence às próximas entregas.

Consulte `docs/OPERACAO.md` para usuário PostgreSQL restrito, HTTPS, Redis, backup diário, restauração e avaliação de desempenho. Recuperação de senha exige SMTP configurado; os testes simulam o transporte. Disponibilidade, acessibilidade do React e metas de carga dependem de validação no ambiente de implantação.

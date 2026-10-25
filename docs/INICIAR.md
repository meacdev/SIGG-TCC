# Configurar e iniciar o SIGG-TCC

Execute os comandos deste guia na raiz `C:\Users\mateu\repos\SIGG-TCC`, na branch `feat/UC01-cadastro`. As branches `main` e `develop` não recebem o código automaticamente: o trabalho precisa ser integrado à branch escolhida pela equipe antes de utilizá-la para execução ou implantação.

## Arquivo de configuração e ambiente Python

`.env` é um **arquivo de configuração** na raiz. `.venv` é a **pasta do ambiente virtual Python**, também na raiz. A pasta `frontend/` contém a aplicação React. São três coisas diferentes.

O `.env` local analisado ainda continha a senha de exemplo na conexão e `JWT_SECRET_KEY` vazia. Nenhuma senha real foi exibida ou modificada. Preencha:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:SENHA_CODIFICADA@localhost:5432/sigg_tcc
JWT_SECRET_KEY=CHAVE_GERADA_NO_SEU_TERMINAL
APP_ENV=development
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
RATELIMIT_STORAGE_URI=memory://
```

No desenvolvimento inicial, `postgres` é o usuário criado pelo instalador; substitua-o caso tenha criado uma conta própria. `sigg_tcc` é o nome do banco; `5432` é a porta padrão. A senha é a do PostgreSQL, não a senha do Windows. `SENHA_CODIFICADA` e `CHAVE_GERADA_NO_SEU_TERMINAL` são explicações a substituir, não valores prontos.

Para codificar uma senha com caracteres especiais, execute o comando abaixo. Ele solicita a senha sem mostrá-la durante a digitação e imprime somente a versão a ser colada na URL do seu `.env`:

```powershell
.\.venv\Scripts\python.exe -c "from getpass import getpass; from urllib.parse import quote; print(quote(getpass('Senha do PostgreSQL: '), safe=''))"
```

Gere uma chave JWT aleatória:

```powershell
yarn env:key
```

Copie somente a linha da chave para `JWT_SECRET_KEY`. Não acrescente espaços ou os textos de apresentação do Yarn. Não publique o `.env`; ele é ignorado pelo Git nesta branch. Variáveis já definidas no terminal prevalecem sobre o arquivo.

SMTP pode permanecer vazio para cadastro e login locais. Recuperação de senha exige um serviço SMTP real. Os tempos de sessão e demais opções podem continuar com os valores do exemplo.

## Instalação inicial

As dependências já foram instaladas neste computador. Em outra máquina, prepare-as a partir da raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
npm.cmd --prefix frontend ci
```

O Yarn da raiz executa os comandos do projeto; as dependências do front-end continuam reproduzíveis pelo `frontend/package-lock.json` existente. Não é necessário criar outro lockfile ou executar `yarn install` dentro de `frontend/`. A raiz não acrescenta dependências JavaScript. O campo `packageManager` seleciona Yarn 1.22.22 via Corepack; `npm run dev` e os demais scripts também funcionam na raiz.

Ativação manual opcional do Python no PowerShell:

```powershell
cd C:\Users\mateu\repos\SIGG-TCC
.\.venv\Scripts\Activate.ps1
```

No Git Bash/UCRT64:

```bash
cd ~/repos/SIGG-TCC
source .venv/Scripts/activate
```

Os comandos Yarn usam o executável de `.venv` diretamente. Não dependem de ativação manual nem de alterar a política de execução do PowerShell. Se o PowerShell bloquear o atalho `yarn.ps1`, use `yarn.cmd dev` e `yarn.cmd test`. `SIGG_PYTHON` permite indicar outro executável Python quando necessário.

## Preparação do banco

O PostgreSQL precisa estar instalado e com seu serviço iniciado. `yarn dev` não instala nem inicia o serviço do PostgreSQL e não altera o esquema automaticamente.

1. No pgAdmin, conecte com a conta da instalação e crie o banco `sigg_tcc`.
2. **Somente no banco novo e vazio**, abra o Query Tool desse banco, carregue `backend/sql/000_schema_fornecido.sql` e execute o arquivo completo. Se já existem tabelas do projeto, não repita a importação.
3. Preencha o `.env` e execute na raiz:

```powershell
yarn env:check
yarn db:upgrade
yarn db:seed
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app criar-curso --codigo SI --nome "Sistemas de Informação"
yarn db:check
```

`db:upgrade` aplica as migrações complementares; `db:seed` inicializa os perfis. Crie cada curso somente uma vez. `db:check` consulta a prontidão da API e confere conexão e estrutura complementar, sem criar dados. O preenchimento correto do `.env` não cria o banco nem suas tabelas por si só. Os comandos administrativos usam a conta com permissões de manutenção; uma conta restrita de aplicação não deve executar migrações.

## Desenvolvimento e testes na raiz

```powershell
cd C:\Users\mateu\repos\SIGG-TCC
yarn dev
```

Abra `http://127.0.0.1:5173`. A API fica em `http://127.0.0.1:5000/api/v1`. O terminal mostra os dois servidores e `Ctrl+C` encerra ambos, incluindo os processos de recarga do Flask. Se um falhar, o outro também é encerrado. As portas 5000 e 5173 devem estar livres. A configuração básica é verificada antes da partida; ela não comprova a conexão com o banco, que deve ser conferida com `yarn db:check`.

| Comando na raiz | Finalidade |
| --- | --- |
| `yarn dev` | Inicia Flask e Vite juntos |
| `yarn dev:backend` | Somente o Flask local |
| `yarn dev:frontend` | Somente o Vite local |
| `yarn env:check` | Verifica preenchimento sem exibir segredos |
| `yarn env:key` | Gera uma chave JWT para você colar no `.env` |
| `yarn db:check` | Confere a conexão e as tabelas complementares |
| `yarn test` | Vitest e depois pytest, interrompendo se houver falha |
| `yarn test:frontend` | Executa Vitest uma vez |
| `yarn test:watch` | Vitest em modo interativo, acompanhando alterações |
| `yarn test:backend` | Executa pytest |
| `yarn test:e2e` | Navegador com API descartável, sem banco institucional |
| `yarn build` | Compila o front-end em `frontend/dist` |
| `yarn start:backend` | Executa a API com Waitress em loopback |

Para os testes de navegador, instale o Chromium uma vez com `npx --prefix frontend playwright install chromium` ou execute `npx playwright install chromium` de dentro de `frontend/`. Os testes precisam das portas 5001 e 5173 livres; encerre `yarn dev` antes de `yarn test:e2e`.

## Colocar em produção

Produção requer um servidor ou serviço de hospedagem, domínio/HTTPS, PostgreSQL, Redis, armazenamento de segredos e SMTP para a recuperação de senha. Não foi realizada publicação nem escolhido um provedor nesta etapa.

1. Integre o código aprovado à branch que a equipe usará para implantação e disponibilize essa versão no servidor.
2. Instale Python 3.14 e as dependências de `backend/requirements.txt`. Prepare o PostgreSQL com uma conta de manutenção e aplique o SQL base somente se for novo, seguido das migrações e perfis.
3. Crie uma conta restrita para a execução da API, conforme `docs/OPERACAO.md`. Troque `DATABASE_URL` para essa conta depois da manutenção. Não execute a aplicação pública como superusuário `postgres`.
4. Configure segredos reais e exclusivos no servidor, sem reutilizar o `.env` de desenvolvimento. Exemplo de campos a ajustar:

```dotenv
APP_ENV=production
DATABASE_URL=postgresql+psycopg://sigg_app:SENHA_CODIFICADA@HOST_DO_BANCO:5432/sigg_tcc
JWT_SECRET_KEY=SEGREDO_ALEATORIO_EXCLUSIVO_DA_PRODUCAO
CORS_ORIGINS=https://SEU_DOMINIO
RATELIMIT_STORAGE_URI=redis://HOST_DO_REDIS:6379/0
SMTP_HOST=HOST_DO_SMTP
SMTP_PORT=587
SMTP_USERNAME=USUARIO_DO_SMTP
SMTP_PASSWORD=SEGREDO_DO_SMTP
SMTP_FROM=REMETENTE_AUTORIZADO
SMTP_STARTTLS=true
SMTP_SSL=false
```

Os endereços e segredos acima são marcadores. Para Redis/SMTP gerenciados, use a autenticação, TLS e portas fornecidos pelo serviço. Os campos `VITE_...` são públicos no navegador: nunca coloque senha do banco, JWT ou SMTP neles.

5. Compile o front-end com `yarn build`, após instalar suas dependências. Mantenha `VITE_API_BASE_URL=/api/v1` se o site e a API compartilharem o domínio. Se utilizar outra URL pública de API, defina-a **antes do build**, em `frontend/.env.production` ou nas variáveis da etapa de compilação.
6. Sirva `frontend/dist` por um servidor de arquivos estáticos com HTTPS. Encaminhe o caminho `/api` para Waitress em `127.0.0.1:5000`, preservando `/api` no caminho encaminhado. `API_PROXY_TARGET` só configura o proxy do desenvolvimento; não configura o servidor de produção.
7. Inicie a API com `yarn start:backend` se Node/Yarn estiverem no servidor, ou diretamente com `.venv/bin/python -m waitress --listen=127.0.0.1:5000 --call backend.app:create_app` em Linux. No Windows, use `.venv\Scripts\python.exe` no lugar de `.venv/bin/python`. Configure um serviço/supervisor para reiniciar a API após reinicialização ou falha. O servidor HTTP, PostgreSQL e Redis também precisam de gerenciamento independente.
8. Teste `/api/v1/health/ready`, cadastro, login e recuperação de senha pelo domínio HTTPS. Configure backups, restauração e monitoramento conforme `docs/OPERACAO.md`.

O comando `yarn dev` é para desenvolvimento. O build do Vite é publicado como arquivos estáticos; `vite preview` não é um servidor de produção. A API de produção usa um servidor WSGI, aqui Waitress, em vez do servidor de desenvolvimento do Flask.

Referências: [Flask em produção](https://flask.palletsprojects.com/en/stable/deploying/), [Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/usage.html) e [publicação do Vite](https://vite.dev/guide/static-deploy.html).

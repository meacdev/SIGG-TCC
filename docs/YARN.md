# Yarn e base dos UCs 01 a 03

Branch `chore/yarn`, criada a partir de `feat/UC03-cadastrar-turmas`. Destino do PR: `develop`. Contém cadastro, login existente e gestão de turmas, sem os UCs 04/05/06 ou 09/10/11. A integração em develop e os merges de develop nas demais branches aguardam aprovação; não foram executados automaticamente.

## Instalação

Execute na raiz `C:\Users\mateu\repos\SIGG-TCC`, com Node 22.12+ (Node 24 na CI). O `packageManager` fixa Yarn 1.22.22. Se Corepack ainda não estiver disponível no computador:

```powershell
npm install --global corepack@0.34.6
corepack enable
corepack prepare yarn@1.22.22 --activate
```

Esses comandos são preparação do gerenciador; não precisam ser repetidos a cada execução. No PowerShell, `yarn.cmd` é uma alternativa caso o atalho `yarn.ps1` seja bloqueado. Depois:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
yarn install --frozen-lockfile
```

Em um ambiente já preparado, não recrie o `.env` nem o banco. Configure-os conforme `INICIAR.md`, aplique as migrações necessárias com `yarn db:upgrade` e inicie o PostgreSQL pelo serviço local. O Yarn não instala ou inicia o serviço do banco automaticamente.

Um único `yarn.lock` na raiz governa o workspace `frontend`. As versões vieram do lockfile npm anterior. `frontend/package-lock.json` foi substituído; não gere um segundo lockfile. A instalação pode colocar dependências em `node_modules` na raiz; os atalhos do projeto procuram nos dois locais.

## Comandos na raiz

| Comando | Resultado |
| --- | --- |
| `yarn dev` | Atualiza o banco local e inicia Flask e Vite; Ctrl+C encerra ambos |
| `yarn dev:backend` / `yarn dev:frontend` | Inicia cada parte separadamente |
| `yarn test` | Executa Vitest e pytest |
| `yarn test:watch` | Vitest em modo interativo |
| `yarn test:frontend` / `yarn test:backend` | Executa cada suíte separadamente |
| `yarn test:e2e` | Chromium com API e banco descartáveis |
| `yarn build` | Valida TypeScript e gera `frontend/dist` |
| `yarn env:check` / `yarn db:check` | Diagnostica configuração/conexão sem expor segredos |
| `yarn db:upgrade` / `yarn db:seed` | Aplica migrações explícitas/inicializa perfis |

Para instalar o navegador de teste uma vez: `yarn workspace sigg-tcc-frontend playwright install chromium`. Feche os servidores de desenvolvimento antes dos testes de navegador; eles usam suas próprias portas 5001/5173 e banco em memória. Tokens, credenciais ou registros de teste não são instalados no banco do usuário.

## Ordem dos PRs

Primeiro revisar esta branch em develop. UC03 pode ser revisado separadamente contra `feat/UC01-cadastro`; seus commits já estão incluídos nesta consolidação. Evite integrar UC03 novamente sem conferir a diferença. Para preservar as bases encadeadas, prefira merge com histórico; se houver squash, revise/retargete os PRs seguintes para evitar reapresentar commits já aprovados.

Depois da aprovação, integrar develop nas branches de UC03/04/06/05 e 09/10/11, resolver conflitos e repetir os testes. As funcionalidades novas entram na ordem UC04 → UC06 → UC05. As branches 09–11 possuem sobreposições de modelos, serialização, navegação e OpenAPI que exigirão resolução nessa integração. Não foi realizado push, merge ou criação de PR remoto nesta entrega.

## Migrações ao iniciar o desenvolvimento

Na raiz, `yarn dev` e `yarn dev:backend` aplicam as migrações pendentes antes de iniciar o servidor, quando `APP_ENV=development` e o PostgreSQL usa localhost ou IP de loopback. O comando existente mantém o histórico e os checksums: migrações já aplicadas não são repetidas. Se houver falha, o servidor não inicia.

A preparação inicial continua necessária uma vez: instalar as dependências Python e Yarn, configurar `.env`, iniciar o PostgreSQL, criar o banco e importar o SQL base somente se o banco estiver vazio. A conta usada precisa das permissões para executar as migrações. Não há criação automática do banco nem importação automática do SQL base.

Para desativar a atualização automática, adicione `AUTO_MIGRATE=false` ao `.env`. Bancos remotos, URLs com parâmetros e essa opção desativada usam somente a verificação de disponibilidade; execute `yarn db:upgrade` explicitamente para atualizar a estrutura. A verificação de disponibilidade não substitui a conferência do histórico de migrações.

`yarn install`, `yarn build`, `yarn dev:frontend` e `yarn start:backend` não aplicam migrações. Em produção, execute o upgrade como uma etapa explícita da implantação antes de iniciar a nova versão. São aplicados somente os arquivos presentes na branch atual; a migração 008 ficará disponível aqui após a integração do UC13.

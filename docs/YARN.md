# Yarn e base dos UCs 01 a 03

Branch `codex/yarn-uc01-uc03`, criada a partir de `feat/UC03-cadastrar-turmas`. Destino do PR: `develop`. Contém cadastro, login existente e gestão de turmas, sem os UCs 04/05/06 ou 09/10/11. A integração em develop e os merges de develop nas demais branches aguardam aprovação; não foram executados automaticamente.

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
| `yarn dev` | Inicia Flask e Vite; Ctrl+C encerra ambos |
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

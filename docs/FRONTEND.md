# Front-end do UC01

Aplicação React/TypeScript em `frontend/`, integrada à API Flask existente. O trabalho está na branch `feat/UC01-cadastro`. Cada caso de uso posterior deverá ter sua própria branch `feat/UCXX-nome-do-UC`, após autorização do solicitante.

## Executar com o back-end

Prepare o PostgreSQL, os perfis e a configuração do Flask conforme o README principal. O cadastro de estudante depende de pelo menos um curso ativo real, criado pelo comando `criar-curso` já existente.

Em um terminal na raiz:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app run --host 127.0.0.1 --port 5000
```

Em outro terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Abra `http://127.0.0.1:5173`. As rotas são `/#/cadastro`, `/#/entrar` e `/#/perfil`. Node.js 22.12 ou superior é necessário. O arquivo `frontend/.env.example` apresenta as opções; os valores padrão permitem desenvolvimento local sem criar outro arquivo de ambiente.

O proxy do Vite encaminha `/api` ao Flask em `127.0.0.1:5000`. Para outro servidor, configure `API_PROXY_TARGET`. `VITE_API_BASE_URL` permite definir a URL pública da API e é incorporada durante o build. Uma origem diferente em produção precisa ser autorizada pelo `CORS_ORIGINS` do back-end.

## Fluxos entregues

- Cadastro de estudante com nome, e-mail, senha, confirmação, matrícula textual e seleção de curso consultado na API, incluindo todas as páginas do catálogo.
- Cadastro de docente ou avaliador, interno ou externo, com titulação obrigatória e instituição, áreas de interesse e Lattes opcionais.
- Validação no navegador, mensagens de erro associadas aos campos, resumo anunciado para leitores de tela, senha inicialmente oculta e prevenção de envios repetidos enquanto a requisição está em andamento.
- Confirmação somente após criação na API, mostrando o código real do cadastro. O login seguinte é explícito.
- Login de apoio ao UC01, consulta e edição do próprio cadastro, tratamento de conflito de versão e inativação mediante confirmação e senha atual.
- Tokens somente em memória, renovação sob demanda e descarte da sessão após logout, inativação ou mudança de e-mail. Recarregar a página requer novo login.

O login foi incluído para permitir testar e utilizar as operações protegidas do UC01. Recuperação de senha, painéis acadêmicos e gestão de turmas não fazem parte desta interface.

## Decisões de integração

| Tema | Implementação |
| --- | --- |
| Titulação dos estudantes | Segue a API e a decisão já registrada em `docs/REQUISITOS.md`: estudantes informam matrícula/curso; titulação aplica-se a docentes. |
| Atores docentes | Orientadores, professores, coordenadores e membros de banca usam o cadastro docente. A interface não permite autoconceder papéis privilegiados. |
| E-mail repetido | Utiliza `409 UC_01_M04`, conforme o catálogo de mensagens, corrigindo a referência contraditória a M01 na RN03. |
| Timestamp | ETag real da API, enviado em `If-Match` ao editar ou inativar. Conflitos 412/428 exigem recarga explícita; não sobrescrevem silenciosamente o registro. |
| Exclusão | `DELETE /usuarios/me` inativa a conta e revoga as sessões no servidor; não elimina o histórico acadêmico. |
| Campos imutáveis | Tipo de cadastro, vínculo interno/externo, matrícula e curso não são enviados na edição, respeitando os campos permitidos pela API. |
| Campos opcionais | Vazios não bloqueiam o cadastro docente. Áreas são separadas por vírgula e enviadas como lista. |

## Verificação

```powershell
cd frontend
npm run build
npm test
npx playwright install chromium
npm run test:e2e
```

O teste de navegador inicia sua própria API em `127.0.0.1:5001`, usando **SQLite em memória**, chave de teste aleatória, curso de teste e rate limiter desativado. Não conecta ao banco configurado no `.env` e não altera dados da instituição. A porta 5173 deve estar livre. O Python padrão dos testes é o `.venv` da raiz; é possível substituí-lo com `SIGG_TEST_PYTHON`.

Os testes de navegador exercitam cadastro docente e discente, obrigatoriedade, duplicidade, consulta, edição, conflito com uma segunda sessão, troca de e-mail, senha incorreta, cancelamento e confirmação da inativação, além de largura de celular. Os testes unitários cobrem transformação dos campos, limites, erros HTTP, paginação, renovação de sessão e envio de ETag.

A suíte de navegador também verifica falhas de conexão, catálogo vazio, ausência de rolagem horizontal em larguras de 320, 390 e 768 pixels e regras automatizadas de acessibilidade WCAG 2.1 AA com axe-core. Isso não substitui homologação com os usuários ou uma avaliação manual completa de acessibilidade. `npm run format:check` verifica a formatação do código.

## Build para implantação

```powershell
npm run build
```

Publique o conteúdo de `frontend/dist` em um servidor de arquivos estáticos com HTTPS e encaminhe `/api` à aplicação Flask. O servidor de desenvolvimento do Vite não é o servidor de produção. As rotas com hash dispensam regras especiais de fallback. A aplicação Flask mantém seus cabeçalhos exclusivos de API; os arquivos da interface devem ser servidos separadamente.

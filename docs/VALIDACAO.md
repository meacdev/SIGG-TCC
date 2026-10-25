# Verificação da primeira entrega

Verificação local em 23/10/2026, com Python 3.14.7, PostgreSQL 18.6 e as dependências fixadas nos arquivos requirements. O banco original do usuário não foi conectado nem alterado. A cópia do SQL base foi conferida por SHA-256 contra o arquivo fornecido.

## Verificações funcionais

A suíte cobre cadastro docente/estudante, obrigatoriedade, duplicatas, hash Argon2id, campos opcionais, edição, inativação, e-mail, login e conta ativa, JWT inválido/expirado, refresh, logout, inatividade, recuperação por e-mail, limite de tentativas, uso único e revogação de todas as sessões após redefinição.

Também cobre cadastro e consulta de turmas, unicidade por período, várias ofertas simultâneas, validação de código/nível/período, papéis expirados, isolamento por curso/responsável, concessão administrativa, ETag/If-Match, inativação, rotação de código, CORS, formato de erros, limites de requisições e correspondência entre rotas HTTP e OpenAPI.

Os testes exclusivos de PostgreSQL verificam a migração real, sua reexecução, os bloqueios de alteração/exclusão da auditoria e quatro cenários concorrentes: refresh de uso único, edição com mesma versão, cadastro de e-mail duplicado e cadastro de turma duplicada.

A verificação final teve 66 testes aprovados no PostgreSQL e cobertura de 95,62%. Na modalidade rápida, 61 testes passaram e cinco testes específicos de PostgreSQL foram omitidos, com cobertura de 93,63%.

A meta de cobertura de 80% é obrigatória no pytest e na CI. A suíte rápida utiliza SQLite; a integração importa o esquema completo e aplica a migração em schemas descartáveis no PostgreSQL. Os registros de teste e os servidores temporários não integram a implantação.

Ruff verifica estilo e erros estáticos; `pip check` verifica dependências. A sintaxe dos dois scripts PowerShell foi analisada sem executá-los. Nenhum backup agendado ou tarefa do sistema foi instalado automaticamente.

## Ensaio de carga local

Ensaio HTTP com Waitress, 50 threads, 50 contas e sessões sintéticas distintas, PostgreSQL local descartável e rate limiter desabilitado para medir as operações. A base tinha dois cursos, um período e dados sintéticos pequenos. Foram feitas quatro operações por usuário em cada cenário, com 200 requisições por cenário.

| Operação | Requisições | Falhas | Latência média | p95 | Vazão observada |
| --- | --- | --- | --- | --- | --- |
| GET /api/v1/turmas | 200 | 0 | 0,4199 s | 0,9124 s | 97,18 req/s |
| POST /api/v1/turmas | 200 | 0 | 0,5988 s | 1,2781 s | 68,02 req/s |

Os dois cenários ficaram abaixo da meta de 2 s no p95. O resultado é uma referência de desenvolvimento: não mede todas as operações, cadastro/login concorrente com Argon2, rede externa, dados históricos volumosos, Redis ou disponibilidade. A infraestrutura final e os fluxos futuros precisam de nova medição; não se declara atendimento global do RNF01 a partir deste ensaio.

## Limites da validação

SMTP foi simulado nos testes: foi exercitada a construção da mensagem, uso de TLS, autenticação e falha de transporte, sem envio a pessoas reais. O envio real requer configuração e teste pela equipe. Na verificação inicial do back-end, o cliente TypeScript era somente um exemplo de integração. A interface React do UC01 foi acrescentada posteriormente, com a verificação registrada abaixo.

A proteção de auditoria foi verificada no PostgreSQL, mas proprietário/superusuário ainda pode alterar a infraestrutura. Retenção por cinco anos, backup diário, restauração em menos de uma hora, uptime, SUS e WCAG precisam de operação e validação específicas. O backend e a documentação fornecem as bases e procedimentos correspondentes.

## Front-end UC01

Verificação do front-end em 23/10/2026 na branch `feat/UC01-cadastro`:

| Verificação | Resultado |
| --- | --- |
| TypeScript e build de produção | Aprovados |
| Testes unitários de validação e cliente HTTP | 11 aprovados |
| Testes de navegador com Chromium e API Flask real em SQLite descartável | 5 aprovados |
| Regressão da API existente, SQLite | 61 aprovados; 5 exclusivos de PostgreSQL omitidos |
| Acessibilidade automatizada com axe-core | Nenhuma violação nos critérios WCAG 2.1 AA verificados em cadastro de estudante, cadastro docente e login |
| Responsividade | Sem rolagem horizontal nas larguras verificadas de 320, 390 e 768 pixels |
| Revisão visual | Capturas completas do cadastro de estudante e docente em desktop e do cadastro docente em celular inspecionadas |
| Formatação e integridade do diff | Aprovadas |

Os fluxos integrados exercitam cadastro docente sem opcionais, cadastro discente com curso real do catálogo de teste e zeros na matrícula, campos obrigatórios, senha inicialmente oculta, e-mail duplicado, consulta e edição, ETag desatualizado por alteração em outra sessão, troca de e-mail com novo login, confirmação/cancelamento da inativação, senha atual incorreta, bloqueio de conta inativa, falha de rede e catálogo vazio. Os testes também confirmam que tokens não são persistidos em localStorage/sessionStorage.

Esta verificação não conecta ao banco institucional e não repete a validação anterior em PostgreSQL. Testes automatizados de acessibilidade não substituem avaliação manual completa, teste com leitor de tela ou homologação de usabilidade com os participantes do projeto. O guia para executar está em `docs/FRONTEND.md`. UCs 09–11 não integram esta entrega; suas dependências estão em `docs/DEPENDENCIAS-UC09-UC11.md`.

## Comandos da raiz

Em 24/10/2026, foram verificados os atalhos de execução conjunta e diagnóstico:

- `yarn dev`: Flask e Vite iniciados com configurações temporárias de teste; `/api/v1/health/live` e a página inicial responderam com sucesso. A interrupção por Ctrl+C encerrou os servidores e liberou as portas 5000 e 5173. Esse ensaio não conectou ao PostgreSQL nem alterou o `.env` do usuário.
- `yarn env:check`: identificou a senha de exemplo e a chave JWT vazia, sem revelar credenciais.
- `yarn test`: 11 testes de Vitest e 64 testes de pytest aprovados; 5 exclusivos de PostgreSQL omitidos. Os três novos testes verificam diagnóstico de configuração, valores de exemplo e omissão de credenciais nas mensagens.
- Build do front-end, Ruff e integridade do diff aprovados.

Não foi criada infraestrutura de produção ou realizada implantação externa. `docs/INICIAR.md` documenta os passos e diferencia configuração local, manutenção do banco e execução pública com Waitress, servidor estático HTTPS e serviços auxiliares.

## Base Yarn dos UCs 01 a 03

Em 25/10/2026, a branch `codex/yarn-uc01-uc03`, baseada em `feat/UC03-cadastrar-turmas`, foi verificada separadamente para revisão em develop. Ela contém cadastro, login existente e interface de turmas; não inclui as funcionalidades posteriores.

Foram aprovados: instalação pela raiz com `yarn install --frozen-lockfile`, resolução de dependências hoistadas em `node_modules` da raiz, build, 11 testes Vitest, 64 testes SQLite (5 exclusivos de PostgreSQL omitidos), 6 testes de navegador, Ruff e formatação. O lockfile foi convertido a partir do npm anterior; as dependências diretas mantiveram as versões. A configuração da CI foi atualizada para Yarn; a execução remota da CI depende do futuro push/PR e não foi apresentada como concluída.

O comando `yarn dev` iniciou Flask e Vite com variáveis temporárias. A saúde básica da API e a página inicial retornaram HTTP 200; o encerramento por Ctrl+C liberou as portas 5000/5173. Esse ensaio não consultou o banco, não usou credenciais institucionais e não alterou o `.env`. O PostgreSQL temporário dos testes dos UCs 04/06/05 já foi encerrado e removido.

A sequência completa UC03 → UC04 → UC06 → UC05 foi verificada na branch do UC05: 94 testes PostgreSQL, cobertura de 95,15%, 85 testes rápidos com 9 omissões específicas de PostgreSQL, 11 Vitest e 9 testes de navegador. Os resultados detalhados acompanham essa branch. As branches continuam separadas, sem merge em develop antes de aprovação.

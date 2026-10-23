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

SMTP foi simulado nos testes: foi exercitada a construção da mensagem, uso de TLS, autenticação e falha de transporte, sem envio a pessoas reais. O envio real requer configuração e teste pela equipe. O cliente TypeScript é um exemplo de integração; a aplicação React e sua acessibilidade não foram implementadas ou verificadas nesta entrega.

A proteção de auditoria foi verificada no PostgreSQL, mas proprietário/superusuário ainda pode alterar a infraestrutura. Retenção por cinco anos, backup diário, restauração em menos de uma hora, uptime, SUS e WCAG precisam de operação e validação específicas. O backend e a documentação fornecem as bases e procedimentos correspondentes.

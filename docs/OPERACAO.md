# Implantação e continuidade

## Credenciais e banco

Use contas separadas para migração/administração e execução da API. A aplicação não deve operar como `postgres`, superusuário ou proprietária das tabelas. Configure o segredo JWT e a conexão por `.env` ou pelo gerenciador de segredos da implantação. Use `APP_ENV=production`, HTTPS e `RATELIMIT_STORAGE_URI=redis://...` compartilhado entre os processos. As dependências de Redis estão no extra de Flask-Limiter.

As migrações e os comandos administrativos precisam de privilégios de manutenção. Para executá-los, utilize uma sessão de terminal confiável com a conexão do proprietário em `DATABASE_URL`; depois inicie a API com a conexão restrita. Variáveis já presentes no ambiente prevalecem sobre `.env`.

Exemplo de permissões, a adaptar ao schema e ao nome real da conta, após a migração. Defina a senha pelo prompt `\password sigg_app` do psql, nunca em um arquivo SQL versionado:

```sql
CREATE ROLE sigg_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
GRANT CONNECT ON DATABASE sigg_tcc TO sigg_app;
GRANT USAGE ON SCHEMA public TO sigg_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT SELECT ON perfil, curso, docente_curso, usuario_perfil, matricula_turma TO sigg_app;
GRANT SELECT, INSERT, UPDATE ON usuario, docente, aluno, periodo_letivo, turma,
    sessao_autenticacao, recuperacao_senha TO sigg_app;
GRANT SELECT, INSERT ON area_conhecimento TO sigg_app;
GRANT SELECT, INSERT, DELETE ON docente_area TO sigg_app;
GRANT SELECT, INSERT ON auditoria, auditoria_alteracao TO sigg_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sigg_app;
REVOKE UPDATE, DELETE, TRUNCATE ON auditoria, auditoria_alteracao FROM sigg_app;
```

O script exportado usa TIMESTAMP sem fuso, enquanto o dicionário descreve TIMESTAMPTZ. A API configura a sessão PostgreSQL em UTC e normaliza as duas formas; a data acadêmica do vínculo docente é avaliada em America/Manaus. Registros históricos sem fuso precisam de revisão se tiverem sido gravados originalmente em horário local, antes de migrar dados de produção.

## Servidor e observabilidade

Execute Waitress em endereço privado ou loopback atrás de um proxy que termine TLS. Configure `CORS_ORIGINS` somente com as origens HTTPS do frontend. O modo production rejeita origens curinga/HTTP, rate limiting em memória e SMTP sem TLS. Não exponha o debugger Flask.

Se houver proxy reverso, configure a origem real apenas através de uma cadeia confiável. O código não aceita automaticamente X-Forwarded-For: ele seria forjável em acesso direto. Sem uma configuração de proxy confiável, o limite de tentativas considera o IP que conecta à aplicação; vários usuários atrás do mesmo proxy podem compartilhar o limite.

Monitore readiness, latência p95, taxa de erros, consumo do pool, Redis e SMTP. `health/live` independe do banco; `health/ready` verifica conexão e tabelas/colunas da migração. O cabeçalho `Server-Timing` informa a duração da requisição. Logs não devem incluir corpos, cabeçalhos Authorization, tokens, códigos de recuperação, senhas nem strings de conexão. Os erros da API omitem os detalhes internos.

Autorizações são consultadas no banco em cada requisição, incluindo vigência do papel, atividade do cadastro e vínculo com o curso. Sessões revogadas permanecem registradas; não execute limpeza de auditoria para reduzir o volume do banco. Planeje retenção de eventos por pelo menos cinco anos acadêmicos e armazenamento protegido dos backups.

## Backup diário

Configure `PGPASSFILE` ou `%APPDATA%\postgresql\pgpass.conf` com permissões de arquivo restritas. O script não recebe senha por argumento. Exemplo de execução manual:

```powershell
.\scripts\backup.ps1 -Database sigg_tcc -UserName sigg_backup -PgDump 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe'
```

Após validar o backup e configurar o mesmo acesso para a conta Windows que executará a tarefa, registre o agendamento diário:

```powershell
.\scripts\register-backup.ps1 -Database sigg_tcc -UserName sigg_backup -Time '02:00'
```

O agendamento não é executado durante a implementação. A tarefa é registrada para a conta Windows atual; para execução mesmo sem login, configure no Agendador de Tarefas uma conta de serviço com as permissões e credenciais necessárias. Transfira os dumps para armazenamento externo criptografado, mantenha retenção definida institucionalmente e alerte em falhas. Um arquivo apenas no mesmo computador não atende recuperação de desastre.

Para validar restauração, crie um banco separado e use `pg_restore --no-owner --no-privileges --dbname <banco_de_ensaio> <dump>`. Ajuste proprietário e permissões, confira contagens e auditoria e execute readiness e testes funcionais. Registre a duração do ensaio; a meta MTTR <1 h precisa ser demonstrada na infraestrutura real. Não use `--clean` contra o banco em uso.

## Desempenho

`scripts/load_test.py` mede latência HTTP de consultas ou cadastros de turmas com usuários concorrentes. Use somente contra um ambiente de teste com dados sintéticos, uma sessão autenticada autorizada e rate limiting ajustado para o ensaio. Nunca versionar o token. O resultado de uma consulta isolada não comprova a meta para todos os fluxos; inclua cadastro de usuários, Argon2, consultas com volume representativo e posteriormente PDFs.

```powershell
# Defina SIGG_LOAD_TOKEN a partir do login de teste, na sessão atual.
$env:SIGG_LOAD_URL = 'http://127.0.0.1:5000/api/v1/turmas'
.\.venv\Scripts\python.exe scripts/load_test.py --users 50 --requests 200
Remove-Item Env:SIGG_LOAD_TOKEN
```

Para cadastros, acrescente `--create-course-id 1 --teacher-id 1 --period 2026/2`. Esse modo grava turmas com códigos distintos e deve ser executado apenas em banco descartável. A meta é p95 ≤2 s e ausência de falhas; o script retorna erro se a meta não for atingida. A taxa de requisições, hardware, tamanho da base e configuração do servidor precisam acompanhar qualquer resultado publicado.

## Referências técnicas

A factory segue o padrão da [documentação oficial do Flask](https://flask.palletsprojects.com/en/stable/patterns/appfactories/). A revogação de access e refresh tokens considera as orientações de [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/en/stable/blocklist_and_token_revoking.html); nesta API, ambos compartilham uma sessão persistida, permitindo revogação conjunta no logout.

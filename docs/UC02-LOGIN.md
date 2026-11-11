# UC02 Login e recuperação de senha

Branch `feat/UC02-login-alt`, criada a partir de `feat/UC01-cadastro`. A referência funcional é `UC_02_LOGIN.docx`, versão 1 de 19/10/2026, enviado pelo solicitante. Esta branch não integra automaticamente develop, os demais UCs ou as alterações específicas de `chore/yarn`.

## Revisão do documento

| Item do UC02 | Situação e implementação |
| --- | --- |
| Pré-condição: usuário cadastrado | Autenticação exige conta existente. |
| Fluxo principal 1–2: e-mail e senha obrigatórios, botão Continuar | Campos validados na interface e na API; botão alinhado ao documento. |
| Fluxo principal 3: mensagem de sucesso | `Login realizado com sucesso!`, agora também apresentada na interface. |
| Fluxo principal 4: área principal relacionada ao login | Redireciona à área autenticada disponível na base UC01 (`#/perfil`), com os dados do próprio usuário. A navegação para os demais módulos depende da integração das respectivas branches; o documento não especifica dashboards ou rotas por perfil. |
| Fluxo alternativo 1–4: Esqueceu senha, confirmação do e-mail e envio do código | Incluído acesso no login e página de recuperação com envio pelo serviço SMTP existente. |
| Fluxo alternativo 5: código e Continuar | Incluída etapa de verificação antes de permitir a nova senha. |
| Fluxo alternativo 6–7: nova senha, confirmação e Confirmar | Incluídos os dois campos, validação e redefinição autenticada pelo token de recuperação. |
| Final do fluxo alternativo: mensagem e retorno ao login | `Senha redefinida com sucesso!`, retorno ao login e e-mail preenchido. Não autentica automaticamente após a troca. |
| Exceção: conta não existe | Mensagem `Conta não cadastrada, entre em contato com a secretaria.` com código `UC_02_M03`. |
| RN01: conta ativa | API bloqueia login e recuperação de contas inativas. |
| RN02: recuperação pelo e-mail cadastrado | Destinatário vem da conta cadastrada. SMTP indisponível resulta em erro; a interface não avança como se o envio tivesse ocorrido. |
| RN03: permissões definidas pela administração | Autenticação e permissões existentes foram preservadas; a recuperação não concede ou altera perfis. Controles dos demais módulos permanecem nas respectivas branches. |

O documento não define tamanho ou alfabeto do código. Conforme a correção do solicitante, foi preservado o formato existente: **10 dígitos numéricos**. Não foi implementado o formato inicialmente sugerido de quatro caracteres. Também foram preservadas as proteções existentes: hash do código e do token no banco, validade padrão de dez minutos, cinco tentativas por recuperação, limite de solicitações, invalidação por novo envio, uso único e revogação de todas as sessões após a troca. Códigos, tokens e senhas não são guardados no armazenamento do navegador.

O documento utiliza prefixos UC01 em nomes de fluxos e mensagens de um UC02. Para seguir seu catálogo estritamente, as respostas agora utilizam `UC_01_M01` e `UC_01_M02` para os sucessos e `UC_02_M03` para conta inexistente. Os antigos códigos `UC_13_M01`, `UC_13_M02` e `UC_13_CONTA_NAO_CADASTRADA` deixam de ser retornados. Consumidores que tratem esses identificadores precisam acompanhar a alteração; os endpoints e textos das mensagens foram mantidos.

Na seção de requisitos funcionais, o documento registra **“Criar RF para login”**, sem atribuir um número. Essa formalização permanece pendente na documentação de requisitos; não foi inventado um identificador. A dependência funcional é o cadastro de conta do UC01, já incluído na base desta branch.

## Configuração de envio

Edite o `.env` **na raiz do projeto**, usando os dados do provedor de e-mail da equipe:

```dotenv
SMTP_HOST=servidor-smtp-do-provedor
SMTP_PORT=587
SMTP_FROM=endereco-remetente-autorizado
SMTP_USERNAME=usuario-do-provedor
SMTP_PASSWORD=credencial-do-provedor
SMTP_STARTTLS=true
SMTP_SSL=false
RESET_CODE_MINUTES=10
```

Os valores acima são explicativos. Use porta, usuário, remetente e credencial fornecidos pelo provedor. Para um servidor que exija TLS implícito, configure a porta correspondente (normalmente 465), `SMTP_SSL=true` e `SMTP_STARTTLS=false`. Nunca publique o `.env`. Reinicie o back end após editar a configuração. Não é necessário criar uma nova migração: os endpoints e a tabela de recuperação já estavam implementados.

Na raiz, inicie o projeto com `npm run dev` ou abra separadamente com `npm run dev:backend` e `npm run dev:frontend`. Acesse `http://127.0.0.1:5173/#/entrar` e selecione **Esqueceu senha?**. A funcionalidade usa e-mail real somente quando SMTP estiver configurado; os testes usam envio capturado ou SMTP simulado, sem mandar mensagens a pessoas.

## Verificação

Os testes de API exercitam recuperação completa, expiração do código e do token, uso único, invalidação por novo pedido, cinco tentativas, conta inexistente/inativa, SMTP com STARTTLS/SSL, falha de envio e revogação das sessões. Os testes de navegador atravessam o fluxo completo com a API descartável, senha antiga recusada, nova senha aceita, mensagens, erros, limite de solicitações, retorno ao login e acessibilidade em celular. O servidor auxiliar de navegador expõe o e-mail capturado somente no arquivo de testes `frontend/e2e/serve_api.py`; essa rota não existe na aplicação normal.

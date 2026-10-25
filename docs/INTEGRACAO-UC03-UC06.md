# Integração dos UCs 03 a 06

A ordem adotada é UC03 → UC04 → UC06 → UC05. UC04 depende da turma; UC06 depende da matrícula para curso/nível; UC05 depende do trabalho, etapa e orientação aceita. Os DOCX atualizados são a referência de numeração. Os nomes antigos UC02/Turmas e UC13/Login da API permanecem compatíveis; não foram confundidos com os novos números das fichas.

| Branch | Base inicial | Escopo |
| --- | --- | --- |
| `feat/UC03-cadastrar-turmas` | `feat/UC01-cadastro` | Interface da API de turmas existente |
| `feat/UC04-matricular-estudantes` | `feat/UC03-cadastrar-turmas` | Interface/API de matrícula, autoinscrição e desligamento |
| `feat/UC06-registrar-trabalho` | `feat/UC04-matricular-estudantes` | Interface/API do trabalho e vínculo/aceite de orientação |
| `feat/UC05-registrar-ata-de-reuniao` | `feat/UC06-registrar-trabalho` | Interface/API de atas, histórico e assiduidade |
| `codex/yarn-uc01-uc03` | `feat/UC03-cadastrar-turmas` | Base dos UCs 01–03 e instalação/execução Yarn para PR em develop |

A branch do Yarn não inclui os UCs 04/05/06 ou 09/10/11. As funcionalidades posteriores continuam nas branches próprias. A base de desenvolvimento já possui cadastro, login, API de turmas e comandos da raiz; a branch de Yarn consolida a instalação com lockfile e workspaces. A branch da última funcionalidade contém UC03/04/06/05 para homologação integrada.

## Revisão e integração

1. Revisar o PR `codex/yarn-uc01-uc03` → `develop`, contendo UCs 01–03. Não foi feito merge automático antes da aprovação.
2. Após aprovação, integrar a `develop` atualizada nas branches dos UCs, resolver sobreposições e repetir os testes. Preferir merge que preserve o histórico dessas branches, pois as bases são encadeadas; squash exige revisão das diferenças para não reapresentar o mesmo código nos PRs seguintes.
3. Integrar UC04, depois UC06 e, por fim, UC05. Antes da base entrar em develop, os PRs podem apontar para a branch anterior da tabela para mostrar somente o incremento. Depois, retargetar para develop conforme os pré-requisitos forem integrados.
4. Integrar também a develop nas branches UC09/10/11 somente após aprovação, conforme solicitado. Há sobreposição em `backend/defense_models.py`, na serialização, no contrato OpenAPI e na navegação. Manter um único mapeamento por tabela; a fila acadêmica e o mapeamento documental de `notificacao` devem ser unificados nessa integração. Não copiar dois modelos independentes para a mesma tabela. Os novos campos e migrações 005–007 devem ser preservados junto de 002–004.

As branches UC09/10/11 existentes foram preservadas. Não foi presumida aprovação de develop, realizado push ou criado PR remoto. As mensagens de PR em Markdown acompanham esta entrega e podem ser copiadas para o GitHub.

## Dependências funcionais e decisões

- RF01/UC03: gestão de turmas e autorização por curso/responsável existentes na API.
- RF02/UC04: matrícula por professor ou código; curso compatível, chave vigente e histórico de remoção.
- RF03/UC06: trabalho próprio, modalidade e herança de nível da matrícula. Palavras-chave opcionais foram incluídas conforme a descrição.
- RF04: pré-requisito da seleção de orientação no UC06 e do registro no UC05. Seleção, notificação e resposta de aceite/recusa foram incluídas. Troca/remoção de orientação continua dependente do **RF05**, com autorização e justificativa, e não foi implementada silenciosamente pelo formulário do estudante.
- RF06: docentes ativos e seus perfis reais vêm do cadastro existente; a seleção não concede papéis globais.
- RF07/UC05: atas imutáveis, notificação às partes, histórico autorizado, contagem e alerta após mais de 30 dias.

O protótipo foi utilizado como referência de campos e fluxos; as interfaces mantêm a identidade visual React já entregue. O código de turma segue o padrão EST + sigla + número do levantamento/protótipo e do back end. Campos de nível/curso não aceitam autodeclaração contrária ao cadastro acadêmico. SMTP e homologação institucional continuam exigindo configuração real da equipe.

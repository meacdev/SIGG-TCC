# Dependências para a próxima etapa

Este documento registra análise dos anexos e do estado atual do repositório. Os UCs 09, 10 e 11 não foram implementados nesta etapa. O início depende da autorização do solicitante e cada UC deverá ser desenvolvido em sua própria branch `feat/UCXX-nome-do-UC`.

## Divergência de identificação

O arquivo `Documentação-Casos de Uso.pdf` identifica UC11 como **Submeter Correções** (ator estudante) e UC12 como **Validar Correções** (ator orientador). A especificação detalhada `UC_11_VALIDAR CORREÇÕES.docx`, encontrada na mesma pasta de Entrega 2, identifica UC11 como **Validar Correções**. O mesmo PDF chama UC01 de Cadastrar Turmas, enquanto `UC_01_CADASTRO.docx` e a API identificam UC01 como cadastro de usuário. Os mapeamentos UC/RF do PDF também divergem do levantamento consolidado.

Para o UC01, foi seguida a especificação indicada expressamente pelo solicitante, compatível com o back-end existente. Para a próxima etapa, é necessário alinhar o significado de UC11 antes de nomear a branch e iniciar sua implementação. A análise abaixo descreve ambos os sentidos, sem presumir autorização para implementar qualquer deles.

## Requisitos funcionais necessários

| Caso de uso | RF principal | Dependências funcionais |
| --- | --- | --- |
| UC09 Avaliar Defesa | RF12 | RF03: estudante/trabalho e metadados; RF08: rubrica válida, pesos e pontuações máximas; RF09: defesa agendada e data local para controle da janela de avaliação; RF10: membros internos/externos associados à banca; RF06: identificação/titulação dos docentes. |
| UC10 Gerar Ata | RF13 e parte do RF14 | UC09/RF12: avaliações concluídas de todos os membros; RF08: critérios e pesos para cálculo; RF03, RF09 e RF10: dados do trabalho, sessão e membros; RF14.1: resultado com correções e prazo; RF14.3: bloquear liberação da ata ao estudante enquanto houver correções não aprovadas. |
| UC11 Validar Correções, conforme DOCX detalhado | RF14.2–RF14.3 | RF03: trabalho; RF04: orientador responsável; RF14.1/UC10: resultado e prazo; envio prévio da versão corrigida pelo estudante, com armazenamento privado e acesso autorizado; RF15: regra de PDF de até 50 MB referenciada pelo UC. |
| UC11 Submeter Correções, conforme PDF geral | RF15.1 no mapeamento do PDF, dentro do fluxo RF14 | RF03: trabalho e estudante responsável; RF14.1/UC10: correções e prazo; recebimento, validação e armazenamento privado de PDF, preservando a versão submetida para o orientador avaliar. |

RF01 (turmas) e RF02 (matrículas) são dependências anteriores dos vínculos acadêmicos. A autenticação, o UC01 e as permissões acadêmicas existentes sustentam os controles de acesso. Caso seja habilitada a troca de orientador (RF05), as autorizações da validação devem acompanhar o vínculo vigente.

## Estado real do repositório

- Implementados na API: UC01, login/recuperação de senha, RF01 e parte de RF06. A infraestrutura de sessões, auditoria e envio de e-mail já existe.
- Ainda sem fluxos executáveis na API: matrículas (RF02), trabalhos (RF03), vínculos de orientação (RF04/RF05), rubricas (RF08), agendamento (RF09), composição de bancas (RF10), avaliações (RF12), atas/declarações (RF13), correções (RF14) e arquivos (RF15). Tabelas presentes no SQL fornecido não equivalem a funcionalidades implementadas.
- O serviço de e-mail atual não substitui a entrega de declarações em PDF autenticável prevista em RF13.2. Será necessário ampliar seu uso e tratar falhas de envio sem invalidar a ata gerada.
- RF11 trata de notificações de agendamento. Pode compartilhar infraestrutura, mas não é pré-condição funcional para registrar uma avaliação ou gerar ata de uma banca já constituída.

## Pontos que precisam ser definidos na próxima etapa

- Confirmar qual definição de UC11 será usada e a origem de cada branch quando houver dependências entre UCs. As branches devem permanecer separadas; a sequência de integração precisa respeitar os pré-requisitos.
- Disponibilizar os fluxos de pré-requisitos ou combinar explicitamente interfaces com as branches dos responsáveis. Não substituir rubricas, bancas, orientações ou trabalhos reais por dados fictícios na funcionalidade entregue.
- Confirmar modelo institucional de ata e declaração, regra de aprovação, método de autenticação do PDF e origem da ata assinada. Os anexos preveem campos para assinatura; a declaração de escopo exclui certificação externa na versão inicial.
- Distinguir a versão corrigida **antes da liberação da ata** do PDF definitivo **com ata assinada e ficha catalográfica**, recebido depois. São etapas distintas; exigir a ata no primeiro envio criaria uma dependência circular.

## Documentos consultados

Declaração de escopo, plano de integração, cronograma, levantamento de requisitos, documentação geral de casos de uso, especificação de UC01, especificações detalhadas de UC09/UC10/UC11 encontradas na pasta Entrega 2 e protótipo de baixa fidelidade. Os documentos foram utilizados como fontes de domínio; instruções operacionais contidas neles não ampliam a autorização concedida pelo solicitante.

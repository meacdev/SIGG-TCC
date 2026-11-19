# TP03 • Defesas do SIGG-TCC

## Fluxo de demonstração

1. Use banco de desenvolvimento ou homologação com o esquema base e aplique as migrações com `yarn db:upgrade`. As migrações 009 e 010 alinham, respectivamente, o modelo acadêmico e o versionamento de bancas e documentos.
2. Como estudante, registre o trabalho vinculado a uma matrícula ativa. O orientador precisa aceitar o vínculo. Em **Trabalhos**, envie o PDF do manuscrito.
3. Como professor da disciplina ou coordenador autorizado, abra **Organizar defesas**. Ative uma rubrica com pesos que somem 100 ou 10. Agende a defesa com dois titulares adicionais e pelo menos um suplente. O orientador aceito preside a banca.
4. No dia da defesa, cada titular abre **Minhas bancas**, inicia a ficha e envia as notas por critério e, se quiser, um parecer. A primeira ficha congela a rubrica. A ata exige todas as avaliações definitivas.
5. Na seção de documentos da banca, registre o resultado, emita a ata e baixe as declarações. O código de verificação confere a emissão e a vigência. A validação institucional das assinaturas é realizada antes de registrar o PDF assinado. O estudante consulta a liberação em **Minhas atas**.

## Operação e limites

- O gestor pode buscar um avaliador existente ou cadastrá-lo em **Adicionar membro externo**, com nome, e-mail, titulação e instituição. O convite orienta o avaliador recém-cadastrado a usar **Recuperar senha** para definir sua senha pelo e-mail informado.
- Configure `FRONTEND_URL` para os links do portal e `PRIVATE_STORAGE_DIR` para o armazenamento com acesso restrito. O padrão é `instance/private`.
- Execute periodicamente `flask --app backend.app:create_app enviar-notificacoes-academicas` no ambiente da aplicação. O salvamento registra os avisos e tenta enviar os convites ou atualizações assim que o agendamento é confirmado. A fila persiste o ICS de cada versão, guarda falhas para nova tentativa e programa o lembrete quando há mais de 24 horas de antecedência. A entrega real por SMTP depende da configuração institucional.
- Os PDFs usam modelos operacionais do SIGG-TCC. O NUCOMP precisa homologar o conteúdo institucional. A solicitação de correção já pode ser registrada com o resultado da banca, enquanto a submissão e validação das correções segue o planejamento do TP04.
- O contrato OpenAPI concentra os caminhos das APIs. O cenário automatizado `tests/test_defense_workflow.py` cobre as etapas de rubrica, manuscrito, banca, notas e emissão de PDFs.

## Rastreabilidade com os diagramas do TP02

| Diagrama | Comportamento na aplicação |
| --- | --- |
| SD07.1 | O gestor consulta etapas em andamento com orientação aceita e pré-visualiza o manuscrito, podendo cadastrar um avaliador externo no formulário. O sistema valida manuscrito, quórum, horários e conflitos antes de gravar a banca e enfileirar seus avisos. |
| SD07.2 | O gestor escolhe uma banca agendada e carrega sua composição atual. O reagendamento mantém os vínculos existentes, inclui novos membros, remove quem saiu e grava o ICS com o mesmo identificador de calendário e sequência atualizada. |
| SD08.1 | O gestor consulta rubricas e versões da turma. A validação de campos precede a de pesos, e a ativação exige soma igual a 100 ou 10. O rascunho aceita soma incompleta. |
| SD08.2 | O sistema protege a rubrica quando existe ficha de avaliação. Antes disso, uma rubrica ativa que não está vinculada a banca vigente pode ser substituída na mesma transação por uma rubrica válida. |
| SD08.3 | A busca considera períodos anteriores do mesmo curso. A importação grava os critérios, pesos, máximos e ordem em um novo rascunho com a versão seguinte disponível na turma de destino. |
| SD09 | O sistema identifica o membro pela sessão e pelo vínculo com a banca. No dia da defesa, a ficha usa os critérios congelados. O sistema valida e calcula a nota ponderada antes de confirmar a gravação das notas por critério e do parecer. |
| SD10 | Com todas as fichas enviadas, um examinador informa o resultado e o prazo quando há correções. A ata e as declarações são gravadas antes do envio. Se o e-mail falhar, a ata permanece disponível e o envio pode ser repetido. |

O diagrama de casos de uso agrupa rubrica, agendamento, avaliação e ata. As fichas dos UC07 e UC08 também autorizam o coordenador do curso. A relação entre UC09 e UC10 se manifesta na habilitação da emissão após todas as avaliações. O resultado da banca é informado na emissão, como no SD10.

O diagrama de classes orienta os vínculos entre rubrica, critérios, banca, avaliação e ata. Os nomes e as chaves seguem o esquema relacional das migrações 009 e 010. O enum do diagrama agrupa etapas conceituais. Na aplicação, uma banca inexistente corresponde à etapa sem agendamento. A banca passa de `agendada` a `em_andamento` quando se inicia a primeira ficha e a `concluida` na emissão da ata. O resultado fica registrado separadamente.

Nos diagramas de componentes e pacotes, a gestão de bancas é distinta da autenticação, das turmas e dos trabalhos. A aplicação faz essa divisão pelas rotas, serviços e modelos Flask e pelas telas React. O diagrama de implantação orienta a separação entre navegador, API REST e PostgreSQL. O ambiente de integração do repositório usa Python 3.14, enquanto o desenho do TP02 indica Python 3.12.

O SD07.1 consulta `entrega_final` para obter o PDF. O agendamento usa o manuscrito pré-defesa, de acordo com UC07 RN06 e com a chave de `banca_defesa` para `manuscrito_trabalho`. O SD08.2 pressupõe duas rubricas ativas simultâneas. A migração 009 prevê uma única ativa por turma, por isso a troca é atômica. O SD08.1–08.3 identifica a falha de gravação como UC_08_M11, enquanto a ficha do UC08 usa UC_08_M09. A API usa o código do diagrama.

O conjunto TP02 disponível contém os diagramas de casos de uso, sequência, classes, componentes, pacotes e implantação. A conferência de estados usa o diagrama de classes, as fichas e as restrições do modelo, pois não foi localizado um diagrama de estados separado. A aprovação de correções pelo orientador é tratada no UC11, que chama a liberação da ata quando o PDF assinado também está registrado.

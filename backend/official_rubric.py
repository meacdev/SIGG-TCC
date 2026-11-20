"""Rubrica oficial de avaliação de TCC (ECP), fixa conforme a planilha da disciplina.

A rubrica não é parametrizável: componentes, critérios, pesos, descritores e faixas de
conceito reproduzem a planilha "ECP_AVALIAÇÃO DE TCC". Cada avaliador marca um conceito
por critério e atribui a nota dentro da faixa desse conceito. A nota ponderada do
critério é nota x peso / 10 e a nota do avaliador é a soma das ponderadas (0 a 10).
"""

from decimal import Decimal

RUBRIC_NAME = "Rubrica oficial de avaliação de TCC"
MAXIMUM_GRADE = Decimal(10)
APPROVAL_MINIMUM = Decimal(6)
# Regimento: TCC 1 dispõe de 15 minutos de apresentação e TCC 2, de 20 minutos.
PRESENTATION_MINUTES = {1: 15, 2: 20}

COMPONENTS = {
    "parte_escrita": {"nome": "Parte Escrita", "pontos": "7.0"},
    "parte_oral": {"nome": "Parte Oral", "pontos": "3.0"},
}

# Ordered from the highest band; the upper bound of each lower band is exclusive.
CONCEPTS = {
    "exemplar": {"nome": "Exemplar", "minimo": "8.0", "maximo": "10.0"},
    "competente": {"nome": "Competente", "minimo": "6.0", "maximo": "7.9"},
    "necessita_trabalho": {"nome": "Necessita de Trabalho", "minimo": "0.0", "maximo": "5.9"},
}

CRITERIA_SOURCE = [
    {
        "chave": "relevancia_tema",
        "componente": "parte_escrita",
        "nome": "Relevância do Tema",
        "escopo": None,
        "peso": "0.5",
        "descritores": {
            "exemplar": "1. O tema tem relevância científica e aborda conteúdos e/ou "
            "pesquisas relacionadas ao estado da arte na área da "
            "Computação;\n"
            "2. O conteúdo do trabalho foi focado no tema e com profundidade "
            "adequada para um pleno entendimento do problema abordado;\n"
            "3. O tema conjuga de maneira não-trivial diferentes "
            "habillidades desenvolvidas pelo estudante ao longo do curso.",
            "competente": "1. A apresentação do tema não é embasada por argumentos que "
            "permitam destacar a sua relevância nem tampouco sua relação "
            "com a área da Computação;\n"
            "2. Em algumas ocasiões, não ficou clara a relação entre o "
            "conteúdo do trabalho e o tema proposto, podendo esta "
            "apresentação ter sido superficial ou pouco coesa para prover "
            "um bom entendimento do problema abordado;\n"
            "3. O tema conjuga múltiplas habilidades desenvolvidas pelo "
            "estudante ao longo do curso;",
            "necessita_trabalho": "1. Há uma dissociação entre o tema e o seu "
            "embasamento, de tal modo que não é possível "
            "identificar sua relevância e possíveis contribuições "
            "para a área da Computação;\n"
            "2. O conteúdo do trabalho foge ao tema proposto;\n"
            "3. O tema conjuga superficialmente habilidades "
            "pontuais desenvolvidas pelo estudante ao longo do "
            "curso.",
        },
    },
    {
        "chave": "metodologia",
        "componente": "parte_escrita",
        "nome": "Metodologia",
        "escopo": None,
        "peso": "2",
        "descritores": {
            "exemplar": "Metodologia está bem descrita, aderente aos objetivos propostos "
            "e com justificativas pautadas em critérios técnico-científicos.",
            "competente": "Metodologia está regular, pouco aderente aos objetivos "
            "propostos e com significativa necessidade de melhorias nas "
            "justificativas.",
            "necessita_trabalho": "Metodologia está severamente aquém da qualidade "
            "necessária e incompatível com o nível de formação "
            "almejado.",
        },
    },
    {
        "chave": "revisao_literatura",
        "componente": "parte_escrita",
        "nome": "Revisão da Literatura",
        "escopo": "Referencial Teórico, Trabalhos Correlatos, Referências Bibliográficas",
        "peso": "1",
        "descritores": {
            "exemplar": "1. O documento apresenta revisão bibliográfica focada no tema e "
            "de profundidade adequada para o entendimento do trabalho;\n"
            "2. Apresenta seção de trabalhos relacionados, em quantidade "
            "adequada e comparando qualitativa e quantitativamente as "
            "características e resultados dos trabalhos correlatos;\n"
            "3. Há entendimento das normas de ABNT, sobretudo é possível "
            "verificar o emprego correto para citações e indicações de "
            "referências correlatas.",
            "competente": "1. Demonstra fundamento, porém a capacidade conceitual e "
            "articulação teórico-metodológica (ou teórico-prática) carece "
            "de melhorias;\n"
            "2. Apresenta seção de trabalhos relacionados, com quantidade "
            "adequada, porém necessita de um aprofundamento nos aspectos "
            "comparativos de ordem qualitativa e quantitativa;\n"
            "3. As referências adotadas, em certa medida, são adequadas e "
            "com certa atualidade, mas não foram muito além em termos de "
            "representatividade.",
            "necessita_trabalho": "1. A revisão bibliográfica é superficial ao tema, "
            "carecendo de conceitos elementares para o "
            "entendimento do trabalho;\n"
            "2. Compreende poucos trabalhos correlatos ou é "
            "inexistente, sendo insuficiente para o tema "
            "considerado;\n"
            "3. As referências adotadas são pouco adequadas, "
            "antigas e/ou insuficientes para sustentar o trabalho. "
            "Também há indícios de desleixo com relação as normas "
            "da ABNT.",
        },
    },
    {
        "chave": "resultados_discussoes",
        "componente": "parte_escrita",
        "nome": "Resultados e Discussões",
        "escopo": None,
        "peso": "2",
        "descritores": {
            "exemplar": "Os resultados estão detalhados, mostram-se compatíveis com o "
            "prazo de desenvolvimento e condizentes com a metodologia "
            "apresentadas.",
            "competente": "Os resultados apresentados são regulares, mostrando-se "
            "limitados dado o prazo de desenvolvimento e/ou a metodologia "
            "apresentados.",
            "necessita_trabalho": "Não há evidências da obtenção dos resultados "
            "propostos para o prazo de desenvolvimento.",
        },
    },
    {
        "chave": "conclusoes",
        "componente": "parte_escrita",
        "nome": "Conclusões",
        "escopo": None,
        "peso": "0.5",
        "descritores": {
            "exemplar": "As conclusões apresentadas são fortemente coerentes com o "
            "trabalho desenvolvido e contemplam uma análise crítica e "
            "comparativa das suas vantagens e limitações.\n"
            "\n"
            "As sugestões para as próximas etapas do trabalho ou pesquisas "
            "futuras são resultado de uma reflexão bem pautadas em critérios "
            "técnico-científicos.",
            "competente": "As conclusões apresentadas são limitadas para descrever o "
            "trabalho desenvolvido, com grande potencial de melhoria na "
            "anállise crítica e comparativa das vantagens e limitações.\n"
            "\n"
            "As próximas etapas do trabalho precisam ser delicadamente "
            "revistas em face do cronograma disponível e/ou de critérios "
            "técnico-científicos.",
            "necessita_trabalho": "As considerações estão severamente aquém da qualidade "
            "necessária e são incompatíveis com o nível de "
            "formação almejado.",
        },
    },
    {
        "chave": "redacao",
        "componente": "parte_escrita",
        "nome": "Redação",
        "escopo": None,
        "peso": "1",
        "descritores": {
            "exemplar": "1. Escrito de forma organizada e sistemática, e há evidências "
            "de esforço dos autores para a elaboração de um texto que se "
            "preocupa com a compreensão do leitor;\n"
            "2. As informações são apresentadas de forma clara e "
            "explicitamente relacionadas aos aspectos que o texto dá "
            "suporte;\n"
            "3. Atende às boas práticas de comunicação escrita (linguagem, "
            "pontuação, ortografia, encadeamento das ideias, etc.); é "
            "organizado de forma lógica, facilitando a leitura, compreensão "
            "e localização de informações;\n"
            "4. Há aspectos a serem corrigidos e melhorados, mas o trabalho "
            "demonstra habilidade acima da média e atenção aos detalhes.",
            "competente": "1. O texto possui uma organização, porém apresenta algumas "
            "imprecisões que dificultam a compreensão do leitor;\n"
            "2. É possível observar qualidade técnica no texto, mas há "
            "perdas de conexões entre os aspectos que deveriam sustentar o "
            "trabalho;\n"
            "3. A apresentação das informações carece de melhorias, ou "
            "porque faltou clareza ou porque apresentou algumas lacunas na "
            "forma de relacionar explicitamente as informações aos "
            "aspectos estabelecidos na análise.\n"
            "4. O trabalho está na média, mas exigirá um pouco mais de "
            "esforço para deixá-lo no nível Exemplar.",
            "necessita_trabalho": "1. A escrita apresenta muitas faltas, dificultando a "
            "compreensão do leitor;\n"
            "2. O texto possui baixa qualidade técnica, com "
            "frequentes perdas de conexões entre os aspectos que "
            "deveriam sustentar o trabalho, podendo ser impreciso "
            "até mesmo no foco adotado;\n"
            "3. É pouco fundamentado, e demonstra muitas carências "
            "na capacidade conceitual e articulação teórico- "
            "metodológica (ou teórico-prática).\n"
            "4. O trabalho está severamente aquém da qualidade "
            "necessária para o nível de formação almejado.",
        },
    },
    {
        "chave": "organizacao",
        "componente": "parte_oral",
        "nome": "Organização",
        "escopo": "Sequência Lógica, Qualidade do Material e da Apresentação, Aproveitamento do "
        "Tempo",
        "peso": "1",
        "descritores": {
            "exemplar": "1. Organizou e encadeou as ideias com conectores adequados e "
            "diversificados, sem repetições;\n"
            "2. Apresentou conjunto de slides com adequado conteúdo de "
            "informações a serem comunicadas, ótima qualidade e padronização "
            "dos textos e imagens;\n"
            "3. A apresentação fluiu conforme uma ótima sequencia lógica de "
            "apresentação das informações;\n"
            "4. Realizou a apresentação em tempo igual ou muito próximo ao "
            "tempo total disponível.",
            "competente": "1. Organizou e encadeou as ideias com poucos conectores e/ou "
            "com repetições, mas sem comprometer a compreensão do "
            "conteúdo;\n"
            "2. Apesar de alguns slides com problemas de qualidade visual "
            "e padronização, não houve prejuízo à compreensão do "
            "conteúdo;\n"
            "3. Houve desvios na sua sequência lógica, mas o entendimento "
            "não foi prejudicado. Eventualmente houve desproporcionalidade "
            "na exposição de alguns conteúdos;\n"
            "4. A apresentação foi além ou aquém do tempo disponível, "
            "eventualmente houve leitura do conteúdo dos slides, mas tais "
            "aspectos não comprometeram a apresentação com um todo.",
            "necessita_trabalho": "1. Não organizou nem encadeou as ideias com uso de "
            "conectores, limitando-se a justapor ideias de forma "
            "desarticulada e confusa;\n"
            "2. Apresentou conjunto de slides com total ausência "
            "de qualidade visual e padronização, contendo excesso "
            "de texto e incluindo imagens de baixa qualidade ou "
            "ilegíveis. Houve grave prejuízo ao acompanhamento da "
            "apresentação e ao entendimento do conteúdo;\n"
            "3. A apresentação oral deu-se majoritariamente por "
            "meio da leitura dos slides. Houve ausência de "
            "proporcionalidade entre a importância e volume de "
            "cada assunto;\n"
            "4. Realizou a apresentação de forma negligente, "
            "sub-utilizando o tempo disponível ou extrapolando-o, "
            "o que neste segundo caso impediu a conclusão da "
            "apresentação.",
        },
    },
    {
        "chave": "dominio_assunto",
        "componente": "parte_oral",
        "nome": "Domínio do Assunto",
        "escopo": None,
        "peso": "1.5",
        "descritores": {
            "exemplar": "1- Organiza e encadeia as ideias com conectores adequados e "
            "diversificados, sem repetições.\n"
            "2- Expressa-se oralmente sem recurso à leitura dos slides.\n"
            "\n"
            "1. Adota uma atitude adequada, com gestos e expressões faciais "
            "coerentes e expressivos, que cativam a atenção do auditório e "
            "que reforçam a mensagem transmitida.\n"
            "2- Emprega um tom de voz audível e com entoação expressiva.\n"
            "3. Utiliza um estilo de linguagem (coloquial, literário ou "
            "técnico) adequado à (ao) situação/tema.",
            "competente": "1- Organiza e encadeia as ideias com recurso a conectores "
            "geralmente adequados, embora pouco diversificados e com "
            "repetições.\n"
            "2- Expressa-se oralmente recorrendo algumas vezes à leitura "
            "dos slides.\n"
            "\n"
            "1- Adota uma atitude geralmente adequada, com gestos e "
            "expressões faciais coerentes, ainda que pouco expressivas, "
            "que cativam pontualmente a atenção do auditório.\n"
            "2- Emprega um tom de voz audível e, pontualmente, com "
            "entoação expressiva.\n"
            "3. Utiliza um estilo de linguagem (coloquial, literário ou "
            "técnico) globalmente adequado à(ao) situação/tema, ainda que "
            "com falhas pontuais.",
            "necessita_trabalho": "1- Não organiza nem encadeia as ideias com recurso a "
            "conectores, limitando-se a justapor ideias de forma "
            "desarticulada e confusa.\n"
            "2- Expressa-se oralmente com recurso exclusivo à "
            "leitura dos slides.\n"
            "\n"
            "Adota uma atitude desadequada,\n"
            "negligente ou provocadora; ou emprega um tom de voz "
            "imperceptível ou estridente; ou utiliza um estilo de "
            "linguagem (coloquial, literário ou técnico) "
            "inadequado à(ao) situação/tema.",
        },
    },
    {
        "chave": "postura_banca",
        "componente": "parte_oral",
        "nome": "Postura perante a Banca",
        "escopo": None,
        "peso": "0.5",
        "descritores": {
            "exemplar": "1- Compreendeu perfeitamente às arguições conseguindo "
            "respondê-las de imediato om propriedade, segurança, usando "
            "termos técnicos-científicos corretos e adequados;\n"
            "\n"
            "2. Demonstrou atitude positiva perante a banca, colocando-se a "
            "disposição para responder questionamentos de forma coerente e "
            "respeitosa;\n"
            "\n"
            "3. Demonstrou maturidade em compreender as sugestões de "
            "melhorias e/ou apontamento de erros feitos pela banca;\n"
            "\n"
            "4. Aceitou as considerações dos avaliadores de maneira "
            "respeitosa e esclareceu suas dúvidas de forma clara, objetiva e "
            "com segurança;\n"
            "\n"
            "5. Não realizou interrupções fora do tempo;",
            "competente": "1. Precisou de intervenção do orientador para compreender "
            "algumas arguições, mas conseguiu responder de forma "
            "satisfatória;\n"
            "\n"
            "2. Demonstrou pouca resistência em aceitar as considerações "
            "da banca;\n"
            "\n"
            "3- Demonstrou compreender a maioria das sugestões de "
            "melhorias e possíveis erros apontados pela banca.\n"
            "\n"
            "5- Realizou mais de uma interrupção fora do tempo.",
            "necessita_trabalho": "1- Apesar da intervenção do orientador para "
            "compreender todas as arguições, não conseguiu "
            "respondê-las;.\n"
            "\n"
            "2- Demonstrou atitude negativa perante a banca, "
            "colocando-se em posição defensiva e/ou agressiva;\n"
            "\n"
            "3- Interrompeu diversas vezes os arguidores de forma "
            "desrespeitosa;\n"
            "\n"
            "4-Insistiu em defender suas ideias em relação ao "
            "trabalho, ainda que a banca tenha considerado "
            "insatisfatório.",
        },
    },
]

CRITERIA = [
    {
        **item,
        "descricao": item["escopo"] or "",
    }
    for item in CRITERIA_SOURCE
]


def concept_for(grade):
    """Return the concept whose band contains the grade (0 to 10)."""
    if grade >= Decimal(CONCEPTS["exemplar"]["minimo"]):
        return "exemplar"
    if grade >= Decimal(CONCEPTS["competente"]["minimo"]):
        return "competente"
    return "necessita_trabalho"


def presentation_minutes(level):
    return PRESENTATION_MINUTES.get(level)


def result_for(average, corrections):
    """RN05 (UC10): o resultado decorre da média final e da observação de alterações."""
    if Decimal(average) < APPROVAL_MINIMUM:
        return "reprovado"
    return "aprovado_com_correcoes" if corrections else "aprovado"


def criterion_signature(name, component, weight, descriptors):
    return (name, component, Decimal(str(weight)), descriptors or {})


OFFICIAL_SIGNATURE = [
    criterion_signature(c["nome"], c["componente"], c["peso"], c["descritores"]) for c in CRITERIA
]


def public_json():
    return {
        "nome": RUBRIC_NAME,
        "nota_maxima": str(MAXIMUM_GRADE),
        "aprovacao_minima": str(APPROVAL_MINIMUM),
        "tempo_apresentacao": {f"tcc{level}": m for level, m in PRESENTATION_MINUTES.items()},
        "conceitos": [{"chave": key, **value} for key, value in CONCEPTS.items()],
        "componentes": [
            {
                "chave": key,
                **value,
                "criterios": [
                    {
                        "nome": c["nome"],
                        "descricao": c["descricao"],
                        "peso": c["peso"],
                        "descritores": c["descritores"],
                    }
                    for c in CRITERIA
                    if c["componente"] == key
                ],
            }
            for key, value in COMPONENTS.items()
        ],
    }

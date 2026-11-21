from decimal import Decimal
from io import BytesIO

from flask import g
from pypdf import PdfReader
from sqlalchemy import select

from backend import official_rubric as official
from backend.db import db
from backend.defense_models import Criterio, Rubrica
from backend.models import Usuario
from backend.services import defense_management, defense_pdf


def test_official_rubric_is_fixed_and_read_only(client, teacher, created_class):
    headers = teacher["headers"]
    response = client.get("/api/v1/rubrica-oficial", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert data["aprovacao_minima"] == "6"
    assert data["tempo_apresentacao"] == {"tcc1": 15, "tcc2": 20}
    assert [(c["chave"], c["minimo"], c["maximo"]) for c in data["conceitos"]] == [
        ("exemplar", "8.0", "10.0"),
        ("competente", "6.0", "7.9"),
        ("necessita_trabalho", "0.0", "5.9"),
    ]
    written, oral = data["componentes"]
    assert (written["nome"], written["pontos"], oral["nome"], oral["pontos"]) == (
        "Parte Escrita",
        "7.0",
        "Parte Oral",
        "3.0",
    )
    assert [c["nome"] for c in written["criterios"]] == [
        "Relevância do Tema",
        "Metodologia",
        "Revisão da Literatura",
        "Resultados e Discussões",
        "Conclusões",
        "Redação",
    ]
    assert [c["nome"] for c in oral["criterios"]] == [
        "Organização",
        "Domínio do Assunto",
        "Postura perante a Banca",
    ]
    for component in data["componentes"]:
        assert sum(Decimal(c["peso"]) for c in component["criterios"]) == Decimal(
            component["pontos"]
        )
    assert client.get("/api/v1/rubrica-oficial").status_code == 401
    # UC08 no longer parametrizes criteria: creation, import and history endpoints are gone.
    prefix = f"/api/v1/turmas/{created_class.json['data']['id_turma']}/rubricas"
    payload = {"nome": "Livre", "situacao": "ativa", "criterios": []}
    assert client.post(prefix, headers=headers, json=payload).status_code in {404, 405}
    assert client.post(f"{prefix}/importacoes", headers=headers, json={}).status_code == 404
    assert client.get(f"{prefix}/anteriores", headers=headers).status_code == 404


def test_concept_bands_and_calculated_result():
    assert official.concept_for(Decimal("10")) == "exemplar"
    assert official.concept_for(Decimal("8.0")) == "exemplar"
    assert official.concept_for(Decimal("7.99")) == "competente"
    assert official.concept_for(Decimal("6")) == "competente"
    assert official.concept_for(Decimal("5.99")) == "necessita_trabalho"
    assert official.concept_for(Decimal("0")) == "necessita_trabalho"
    # RN05 (UC10): 6,0 aprova; observação de alterações gera aprovação com correções.
    assert official.result_for("6.00", "") == "aprovado"
    assert official.result_for("6.00", "Revisar figuras.") == "aprovado_com_correcoes"
    assert official.result_for("5.99", "Revisar figuras.") == "reprovado"
    assert official.result_for("9.10", "") == "aprovado"


def test_legacy_active_rubric_is_replaced_by_the_official_one(app, teacher, created_class):
    class_id = created_class.json["data"]["id_turma"]
    with app.test_request_context():
        g.user = db.session.get(Usuario, teacher["id_usuario"])
        legacy = Rubrica(
            id_turma=class_id,
            id_usuario_criacao=teacher["id_usuario"],
            nome_rubrica="Rubrica livre",
            situacao_rubrica="ativa",
            criterios=[
                Criterio(
                    nome_criterio_rubrica="Método",
                    peso_criterio_rubrica=Decimal(100),
                    pontuacao_maxima_criterio_rubrica=Decimal(10),
                    ordem_criterio_rubrica=1,
                )
            ],
        )
        db.session.add(legacy)
        db.session.commit()
        first = defense_management.official_rubric(class_id)
        db.session.commit()
        again = defense_management.official_rubric(class_id)
        assert first.id_rubrica == again.id_rubrica != legacy.id_rubrica
        statuses = dict(
            db.session.execute(select(Rubrica.nome_rubrica, Rubrica.situacao_rubrica)).all()
        )
        assert statuses == {"Rubrica livre": "inativa", official.RUBRIC_NAME: "ativa"}
        assert [c.componente_criterio_rubrica for c in first.criterios].count("parte_oral") == 3


def test_approval_sheet_is_appended_for_tcc2_and_articles():
    criteria = [
        {
            "id_criterio": index,
            "nome": c["nome"],
            "componente": c["componente"],
            "descricao": c["descricao"],
            "peso": c["peso"],
            "pontuacao_maxima": "10",
        }
        for index, c in enumerate(official.CRITERIA, 1)
    ]
    members = [
        {
            "id_docente": person,
            "nome": name,
            "papel": role,
            "rotulo": label,
            "titulacao": "doutor",
            "nota": "9.00",
            "subtotais": {"parte_escrita": "6.30", "parte_oral": "2.70"},
            "notas_por_criterio": {str(c["id_criterio"]): "9.00" for c in criteria},
            "conceitos_por_criterio": {str(c["id_criterio"]): "exemplar" for c in criteria},
        }
        for person, name, role, label in [
            (2, "Avaliadora Um", "examinador", "Primeiro Avaliador"),
            (3, "Avaliador Dois", "examinador", "Segundo Avaliador"),
            (1, "Orientadora", "presidente", "Orientador"),
        ]
    ]
    snapshot = {
        "aluno": "Estudante",
        "titulo": "Trabalho",
        "curso": "Engenharia de Computação",
        "data_local": "23/06/2026 às 10:00 (Manaus)",
        "local": "Sala 1",
        "nivel": 2,
        "orientador": "Orientadora",
        "media_final": "9.00",
        "resultado_label": "Aprovado",
        "criterios": criteria,
        "membros": members,
        "responsavel_disciplina": "Responsável",
        "coordenador_curso": "Coordenação",
        "data_defesa": "23/06/2026",
        "data_extenso": "23 de junho de 2026",
        "folha_aprovacao": True,
        "componentes": [{"chave": k, **v} for k, v in official.COMPONENTS.items()],
        "conceitos": {k: v["nome"] for k, v in official.CONCEPTS.items()},
    }
    reader = PdfReader(BytesIO(defense_pdf.render(snapshot, "codigo")))
    text = " ".join(page.extract_text() for page in reader.pages)
    assert "CURSO II" in text and "FOLHA DE APROVAÇÃO" in text
    assert "Presidente" in text and "Manaus, 23 de junho de 2026" in text
    # Ata: 3 members + course instructor + coordination; approval sheet: 3 members.
    assert len(reader.get_fields()) == 8

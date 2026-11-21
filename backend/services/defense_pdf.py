"""Flowing PDF layouts, escaped academic text and actual empty signature fields."""

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, TextStringObject
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def render(snapshot, code, examiner=None):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "AcademicBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    title = ParagraphStyle(
        "AcademicTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=21,
        alignment=TA_CENTER,
        spaceAfter=14,
        textColor=colors.black,
    )
    small = ParagraphStyle("AcademicSmall", parent=normal, fontSize=8, leading=11)
    heading = ParagraphStyle(
        "AcademicHeading", parent=normal, fontName="Helvetica-Bold", fontSize=11, spaceBefore=10
    )

    def para(value, style=normal):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=22 * mm,
        bottomMargin=23 * mm,
        title="Ata de Defesa" if examiner is None else "Declaração de Participação",
        author="SIGG-TCC - NUCOMP/UEA",
    )
    institution = (
        "Universidade do Estado do Amazonas - UEA\n"
        "Escola Superior de Tecnologia - EST\n"
        f"Curso de {snapshot['curso']}"
    )
    centered = ParagraphStyle("AcademicCentered", parent=normal, alignment=TA_CENTER)
    story = [para(institution, centered), Spacer(1, 4 * mm)]
    boxes = []

    class SignatureBox(Flowable):
        def __init__(self, name, field):
            Flowable.__init__(self)
            self.width, self.height = document.width, 21 * mm
            self.name, self.field = name, field
            self.label = Paragraph(escape(self.name).replace("\n", "<br/>"), small)

        def wrap(self, width, height):
            self.width = width
            _, self.label_height = self.label.wrap(width, height)
            self.height = self.label_height + 17 * mm
            return self.width, self.height

        def draw(self):
            canvas = self.canv
            canvas.setStrokeColor(colors.HexColor("#68756d"))
            bottom = self.label_height + 3 * mm
            canvas.rect(0, bottom, self.width, 10 * mm)
            self.label.drawOn(canvas, 0, 1 * mm)
            x, y = canvas.absolutePosition(0, bottom)
            boxes.append(
                (canvas.getPageNumber() - 1, self.field, [x, y, x + self.width, y + 10 * mm])
            )

    def grid(rows, widths, total_row=False):
        table = Table(
            rows, colWidths=[document.width * w for w in widths], repeatRows=1, hAlign="LEFT"
        )
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf1e9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d1c8")),
        ]
        if total_row:
            style.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f4f6f2")))
        table.setStyle(TableStyle(style))
        return table

    def comma(value):
        return str(value).replace(".", ",")

    if examiner is None:
        level = "II" if snapshot.get("nivel") == 2 else "I"
        story.append(
            para(f"ATA FINAL DE AVALIAÇÃO DE TRABALHO DE CONCLUSÃO DE CURSO {level}", title)
        )
        story.append(para("1. Dados de Identificação", heading))
        for label, value in [
            ("Nome do Aluno", snapshot["aluno"]),
            ("Título do Trabalho", snapshot["titulo"]),
            ("Professor Orientador", snapshot.get("orientador", "")),
            ("Defesa", snapshot["data_local"]),
            ("Local", snapshot["local"]),
        ]:
            story.append(para(f"{label}: {value}"))
        story.append(para("2. Notas dos Avaliadores", heading))
        rows = [[para("Avaliadores", small), para("Nome", small), para("Nota", small)]]
        for member in snapshot["membros"]:
            rows.append(
                [
                    para(member.get("rotulo", "Avaliador"), small),
                    para(member["nome"], small),
                    para(comma(member["nota"]), small),
                ]
            )
        rows.append(
            [
                para("MÉDIA FINAL", small),
                para("", small),
                para(comma(snapshot["media_final"]), small),
            ]
        )
        story.extend(
            [
                grid(rows, [0.3, 0.52, 0.18], total_row=True),
                Spacer(1, 4 * mm),
                para(f"Resultado: {snapshot['resultado_label']}", heading),
                para(
                    "Critério (RN05): média final maior ou igual a 6,0 aprova; com observação "
                    "de alterações, aprova com correções; abaixo de 6,0, reprova.",
                    small,
                ),
            ]
        )
        if snapshot.get("correcoes"):
            story.append(para(f"Observação de alterações: {snapshot['correcoes']}"))
        if snapshot.get("prazo"):
            story.append(para(f"Prazo para entrega das correções: {snapshot['prazo']}"))
        story.extend(
            [
                para("3. Assinaturas", heading),
                para(
                    "Campos reservados às assinaturas. A emissão deste arquivo "
                    "não constitui assinatura dos participantes.",
                    small,
                ),
            ]
        )
        for member in snapshot["membros"]:
            story.append(
                SignatureBox(
                    f"{member.get('rotulo', 'Avaliador')}: {member['nome']}",
                    f"assinatura_membro_{member['id_docente']}",
                )
            )
        story.append(para(f"Data: {snapshot.get('data_defesa', '')}"))
        story.append(
            SignatureBox(
                f"{snapshot.get('responsavel_disciplina', '')}\nProf(a). Responsável da Disciplina",
                "assinatura_responsavel_disciplina",
            )
        )
        story.append(
            SignatureBox(
                f"{snapshot.get('coordenador_curso', '')}\nCoordenação do Curso",
                "assinatura_coordenacao_curso",
            )
        )
        story.append(PageBreak())
        story.append(para("Anexo - Fichas de avaliação por avaliador", heading))
        story.append(
            para(
                "Rubrica oficial: o avaliador marca o conceito (Exemplar 8,0 a 10,0; Competente "
                "6,0 a 7,9; Necessita de Trabalho 0,0 a 5,9) e atribui a nota dentro da faixa. "
                "Nota ponderada = nota x peso / 10.",
                small,
            )
        )
        concepts = snapshot.get("conceitos", {})
        components = {c["chave"]: c for c in snapshot.get("componentes", [])}
        for member in snapshot["membros"]:
            story.append(para(f"{member.get('rotulo', 'Avaliador')}: {member['nome']}"))
            rows = [
                [
                    para("Critério", small),
                    para("Peso", small),
                    para("Conceito", small),
                    para("Nota", small),
                    para("Ponderada", small),
                ]
            ]
            total_weight = sum(float(c["peso"]) for c in snapshot["criterios"]) or 1
            for criterion in snapshot["criterios"]:
                key = str(criterion["id_criterio"])
                note = member["notas_por_criterio"][key]
                concept = member.get("conceitos_por_criterio", {}).get(key)
                share = (
                    float(note)
                    / float(criterion["pontuacao_maxima"])
                    * float(criterion["peso"])
                    * 10
                    / total_weight
                )
                component = components.get(criterion.get("componente"), {}).get("nome")
                rows.append(
                    [
                        para(
                            f"{component} - {criterion['nome']}"
                            if component
                            else criterion["nome"],
                            small,
                        ),
                        para(
                            comma(format(Decimal(str(criterion["peso"])).normalize(), "f")), small
                        ),
                        para(concepts.get(concept, "-"), small),
                        para(comma(note), small),
                        para(comma(f"{share:.2f}"), small),
                    ]
                )
            subtotal = ", ".join(
                f"{components.get(key, {}).get('nome', 'Critérios')}: {comma(value)}"
                for key, value in member.get("subtotais", {}).items()
            )
            rows.append(
                [
                    para(f"Nota do avaliador ({subtotal})" if subtotal else "Nota", small),
                    para("", small),
                    para("", small),
                    para("", small),
                    para(comma(member["nota"]), small),
                ]
            )
            story.extend(
                [grid(rows, [0.5, 0.1, 0.18, 0.1, 0.12], total_row=True), Spacer(1, 4 * mm)]
            )
        if snapshot.get("folha_aprovacao"):
            story.extend(
                [
                    PageBreak(),
                    para(institution, centered),
                    Spacer(1, 6 * mm),
                    para("FOLHA DE APROVAÇÃO", title),
                    para(snapshot["titulo"], centered),
                    Spacer(1, 3 * mm),
                    para(snapshot["aluno"], centered),
                    Spacer(1, 6 * mm),
                    para(
                        "Trabalho de Conclusão de Curso defendido e aprovado pela banca "
                        "avaliadora constituída pelos professores:"
                    ),
                ]
            )
            for member in sorted(snapshot["membros"], key=lambda m: m.get("papel") != "presidente"):
                role = "Presidente" if member.get("papel") == "presidente" else "Avaliador"
                titulacao = str(member.get("titulacao", "")).capitalize()
                story.append(
                    SignatureBox(
                        f"{member['nome']} ({titulacao})\n{role}",
                        f"folha_aprovacao_{member['id_docente']}",
                    )
                )
            story.append(Spacer(1, 4 * mm))
            story.append(para(f"Manaus, {snapshot.get('data_extenso', '')}"))
    else:
        story.append(para("Declaração de Participação em Banca", title))
        story.append(
            para(
                f"Declaramos que {examiner['nome']}, com titulação de {examiner['titulacao']}, "
                "participou como examinador(a) da banca de defesa do trabalho de conclusão "
                f"de curso de {snapshot['aluno']}, do curso de {snapshot['curso']}."
            )
        )
        story.extend(
            [
                para(f"Trabalho: {snapshot['titulo']}"),
                para(f"Defesa: {snapshot['data_local']}"),
                para(f"Local: {snapshot['local']}"),
                para(
                    "Esta declaração corresponde à participação e avaliação "
                    "registradas no SIGG-TCC."
                ),
            ]
        )
    story.extend(
        [
            Spacer(1, 7 * mm),
            para(f"Código de verificação: {code}", small),
            para(
                "Consulte o código no serviço de verificação de documentos do SIGG-TCC. "
                "A autenticidade do arquivo pode ser comparada pelo hash SHA-256 "
                "informado no serviço.",
                small,
            ),
        ]
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#536057"))
        canvas.drawString(22 * mm, 13 * mm, "SIGG-TCC - NUCOMP/UEA")
        canvas.drawRightString(A4[0] - 22 * mm, 13 * mm, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    if not boxes:
        return buffer.getvalue()
    writer = PdfWriter()
    writer.clone_document_from_reader(PdfReader(BytesIO(buffer.getvalue())))
    fields = ArrayObject()
    for page_index, field_name, rectangle in boxes:
        page = writer.pages[page_index]
        widget = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Widget"),
                NameObject("/FT"): NameObject("/Sig"),
                NameObject("/T"): TextStringObject(field_name),
                NameObject("/Rect"): ArrayObject([FloatObject(value) for value in rectangle]),
                NameObject("/P"): page.indirect_reference,
            }
        )
        reference = writer._add_object(widget)
        fields.append(reference)
        page.setdefault(NameObject("/Annots"), ArrayObject()).append(reference)
    writer._root_object[NameObject("/AcroForm")] = writer._add_object(
        DictionaryObject({NameObject("/Fields"): fields})
    )
    output = BytesIO()
    writer.write(output)
    return output.getvalue()

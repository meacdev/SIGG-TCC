"""Flowing PDF layouts, escaped academic text and actual empty signature fields."""

from io import BytesIO
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, TextStringObject
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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
    story = [
        para("Universidade do Estado do Amazonas", heading),
        para("NUCOMP - Sistema de Gestão e Governança de TCC", small),
        Spacer(1, 5 * mm),
    ]
    boxes = []

    class SignatureBox(Flowable):
        def __init__(self, name, member_id):
            Flowable.__init__(self)
            self.width, self.height = document.width, 21 * mm
            self.name, self.member_id = name, member_id
            self.label = Paragraph(escape(self.name), small)

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
                (canvas.getPageNumber() - 1, self.member_id, [x, y, x + self.width, y + 10 * mm])
            )

    if examiner is None:
        story.append(para("Ata de Defesa de Trabalho de Conclusão de Curso", title))
        for label, value in [
            ("Estudante", snapshot["aluno"]),
            ("Título", snapshot["titulo"]),
            ("Curso", snapshot["curso"]),
            ("Defesa", snapshot["data_local"]),
            ("Local", snapshot["local"]),
            ("Versão", snapshot["versao"]),
        ]:
            story.append(para(f"{label}: {value}"))
        story.append(para("Notas da banca examinadora", heading))
        rows = [
            [para("Examinador", small), para("Titulação", small), para("Nota individual", small)]
        ]
        for member in snapshot["membros"]:
            rows.append(
                [
                    para(member["nome"], small),
                    para(member["titulacao"].capitalize(), small),
                    para(member["nota"].replace(".", ","), small),
                ]
            )
        table = Table(
            rows,
            colWidths=[document.width * 0.55, document.width * 0.23, document.width * 0.22],
            repeatRows=1,
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf1e9")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d1c8")),
                ]
            )
        )
        story.extend(
            [
                table,
                Spacer(1, 4 * mm),
                para(f"Média final: {snapshot['media_final'].replace('.', ',')} / 10", heading),
                para(f"Resultado: {snapshot['resultado_label']}"),
            ]
        )
        if snapshot.get("prazo"):
            story.extend(
                [
                    para(f"Prazo para correções: {snapshot['prazo']}"),
                    para(f"Correções solicitadas: {snapshot['correcoes']}"),
                ]
            )
        story.append(para("Critérios utilizados", heading))
        for criterion in snapshot["criterios"]:
            story.append(
                para(
                    f"{criterion['nome']}: peso {criterion['peso']}, "
                    f"pontuação máxima {criterion['pontuacao_maxima']}. {criterion['descricao']}",
                    small,
                )
            )
        story.extend(
            [
                para("Assinaturas dos membros da banca", heading),
                para(
                    "Campos reservados às assinaturas. A emissão deste arquivo "
                    "não constitui assinatura dos participantes.",
                    small,
                ),
            ]
        )
        for member in snapshot["membros"]:
            story.append(SignatureBox(member["nome"], member["id_docente"]))
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
    for page_index, member_id, rectangle in boxes:
        page = writer.pages[page_index]
        widget = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Widget"),
                NameObject("/FT"): NameObject("/Sig"),
                NameObject("/T"): TextStringObject(f"assinatura_membro_{member_id}"),
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

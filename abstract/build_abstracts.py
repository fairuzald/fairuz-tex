from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"
OUTPUT.mkdir(parents=True, exist_ok=True)


NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2E6F95")
LIGHT_BLUE = colors.HexColor("#EAF2F7")
INK = colors.HexColor("#1B1F23")
MUTED = colors.HexColor("#5F6B75")

FONT_REGULAR = "AbstractDejaVu"
FONT_BOLD = "AbstractDejaVu-Bold"
FONT_ITALIC = "AbstractDejaVu-Oblique"

pdfmetrics.registerFont(
    TTFont(FONT_REGULAR, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
)
pdfmetrics.registerFont(
    TTFont(FONT_BOLD, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
)
pdfmetrics.registerFont(
    TTFont(FONT_ITALIC, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf")
)


def make_styles():
    styles = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "Eyebrow",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.2,
            leading=10,
            textColor=BLUE,
            alignment=TA_CENTER,
            spaceAfter=5 * mm,
        ),
        "title": ParagraphStyle(
            "Title",
            parent=styles["Title"],
            fontName=FONT_BOLD,
            fontSize=17.2,
            leading=21.5,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=9.5,
            leading=12,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=7 * mm,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontName=FONT_BOLD,
            fontSize=10.5,
            leading=13,
            textColor=NAVY,
            spaceBefore=1 * mm,
            spaceAfter=2.5 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=9.35,
            leading=13.35,
            textColor=INK,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=3.4 * mm,
        ),
        "keywords": ParagraphStyle(
            "Keywords",
            parent=styles["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=8.6,
            leading=11.4,
            textColor=INK,
            alignment=TA_LEFT,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=7.4,
            leading=9,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
    }


def draw_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    left = 18 * mm
    right = width - 18 * mm
    canvas.setStrokeColor(BLUE)
    canvas.setLineWidth(2.2)
    canvas.line(left, height - 16 * mm, right, height - 16 * mm)
    canvas.setStrokeColor(colors.HexColor("#C6D6E1"))
    canvas.setLineWidth(0.5)
    canvas.line(left, 15 * mm, right, 15 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT_REGULAR, 7.4)
    canvas.drawCentredString(
        width / 2,
        9.5 * mm,
        "Abstrak laporan tugas akhir individu | Institut Teknologi Bandung | 2026",
    )
    canvas.restoreState()


def keyword_box(text, styles):
    table = Table(
        [[Paragraph(text, styles["keywords"])]],
        colWidths=[174 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B8CBD8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    return table


def build_pdf(filename, eyebrow, title, author, section, paragraphs, keywords):
    styles = make_styles()
    path = OUTPUT / filename
    doc = BaseDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=23 * mm,
        bottomMargin=20 * mm,
        title=title,
        author=author,
        subject="Bilingual abstract for the OMNI-RAG individual knowledge-base study",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="abstract-frame",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="abstract", frames=[frame], onPage=draw_page)])

    story = [
        Paragraph(eyebrow, styles["eyebrow"]),
        Paragraph(title, styles["title"]),
        Paragraph(author, styles["subtitle"]),
        Paragraph(section, styles["section"]),
    ]
    story.extend(Paragraph(p, styles["body"]) for p in paragraphs)
    story.extend(
        [
            Spacer(1, 1.5 * mm),
            keyword_box(keywords, styles),
        ]
    )
    doc.build(story)
    return path


def main():
    author_id = "Moh Fairuz Alauddin Yahya | 13522057 | Program Studi Informatika, Institut Teknologi Bandung"

    indonesia = build_pdf(
        "abstract-indonesia.pdf",
        "OMNI-RAG | KONSTRUKSI BASIS PENGETAHUAN",
        "Pengembangan Pipeline Konstruksi Basis Pengetahuan pada Sistem OMNI-RAG Multi-Domain Berbasis Plugin pada Studi Kasus Peraturan Perundang-undangan dan User Manual",
        author_id,
        "ABSTRAK",
        [
            "Retrieval-Augmented Generation (RAG) bergantung pada basis pengetahuan yang mampu menemukan bukti relevan sebelum model bahasa menyusun jawaban. Tantangan ini semakin besar pada sistem multi-domain karena peraturan perundang-undangan bidang pendidikan di Indonesia dan manual pengguna produk Netgear memiliki hierarki, istilah, dan kebutuhan pencarian yang berbeda. Pemotongan yang mengabaikan struktur dapat memutus konteks atau menghilangkan identitas sumber, sedangkan logika pengindeksan dan pembentukan relasi yang terlalu khusus sulit diperluas.",
            "Penelitian ini mengembangkan dan mengevaluasi pipeline konstruksi basis pengetahuan berbasis plugin untuk OMNI-RAG. Artefak kanonik dan kontrak kompatibilitas yang sama memisahkan orkestrator dari empat strategi chunker, tiga strategi indexer, dan dua strategi knowledge graph, yaitu legal graph deterministik dan LLM graph. Chunk kanonik yang sama diproyeksikan menjadi indeks sparse, dense, atau hybrid serta menjadi legal graph opsional; profile, manifest, dan provenance mencatat pemilihan komponen dan menjaga keterlacakan. Eksperimen menggunakan sembilan manual Netgear (1.400 halaman; 200 baris pertanyaan bilingual dari 100 slot) dan korpus hukum berisi 256 dokumen dengan 25 pertanyaan terverifikasi, yang terdiri atas 49 dokumen referensi dan 207 dokumen noise terpilih secara stratified. Retrieval diukur pada K=30 dengan sweep K=5-60, sedangkan generation menggunakan sepuluh evidence teratas.",
            "Pada korpus manual, structure-aware hybrid mencapai Recall@30 sebesar 0,740 pada kelompok chunker, sedangkan structure-aware dense mencapai 0,785 pada kelompok indexer; skor correctness/faithfulness generation masing-masing adalah 0,788/0,958. Pada korpus hukum, legal-structure dense mencapai Recall@30 sebesar 0,6854 dan skor generation 0,690/0,972, sementara hybrid memperoleh MRR tertinggi sebesar 0,5439. Traversal legal graph hingga kedalaman dua mencapai neighborhood recall maksimum 1,000, tetapi metrik ini dibaca terpisah dari context-reference recall. Hasil menunjukkan bahwa pemeliharaan struktur dan pencocokan semantik meningkatkan cakupan evidence, sedangkan konfigurasi terbaik bergantung pada domain dan metrik yang diprioritaskan.",
        ],
        "Kata kunci: OMNI-RAG, Retrieval-Augmented Generation, konstruksi basis pengetahuan, chunking, indexing, knowledge graph, arsitektur plugin.",
    )

    english = build_pdf(
        "abstract-english.pdf",
        "OMNI-RAG | KNOWLEDGE-BASE CONSTRUCTION",
        "Developing a Plugin-Based Knowledge-Base Construction Pipeline for Multi-Domain OMNI-RAG: Case Studies in Indonesian Education Regulations and Netgear User Manuals",
        author_id,
        "ABSTRACT",
        [
            "Retrieval-augmented generation (RAG) relies on a knowledge base that can retrieve the right evidence before a language model composes an answer. This becomes difficult in a multi-domain setting: Indonesian education regulations and Netgear user manuals differ in hierarchy, terminology, and search behavior. Structure-agnostic chunking can break context or discard source identity, while domain-specific indexing and relation-building logic can be hard to extend.",
            "This work develops and evaluates a plugin-based knowledge-base construction pipeline for OMNI-RAG. Shared canonical artifacts and compatibility contracts decouple the orchestrator from four chunking strategies, three indexing strategies, and two knowledge-graph strategies: a deterministic legal graph and an LLM-based graph. The same canonical chunks feed sparse, dense, or hybrid indexes and an optional legal graph; profiles, manifests, and provenance record component selection and preserve traceability. We evaluate nine Netgear manuals (1,400 pages; 200 bilingual question instances derived from 100 slots) and a legal corpus of 256 documents with 25 verified questions, including 49 reference documents and 207 stratified noise documents. Retrieval is evaluated at K=30, with cutoffs swept from K=5 to K=60, while generation uses the top ten evidence items.",
            "On the manual corpus, structure-aware hybrid chunking obtains Recall@30 of 0.740, and structure-aware dense indexing reaches 0.785; the corresponding generation correctness/faithfulness scores are 0.788/0.958. On the legal corpus, legal-structure dense retrieval reaches 0.6854 and generation correctness/faithfulness scores 0.690/0.972, while hybrid indexing gives the highest legal MRR at 0.5439. Legal-graph traversal to depth two reaches neighborhood recall as high as 1.000, a measure reported separately from context-reference recall. The results show that preserving document structure and combining semantic matching with explicit relations can improve evidence coverage, but the best configuration depends on the domain and the metric prioritized.",
        ],
        "Keywords: OMNI-RAG, retrieval-augmented generation, knowledge-base construction, chunking, indexing, knowledge graph, plugin architecture.",
    )

    print(f"Created {indonesia}")
    print(f"Created {english}")


if __name__ == "__main__":
    main()

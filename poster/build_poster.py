"""Build the A1 thesis poster as a restrained, vector-first editorial layout.

The poster deliberately uses a small visual vocabulary: a paper background, a
navy header, one blue/teal accent system, thin rules, and data-led charts. The
layout is designed to read as a research argument rather than as a collection
of rounded UI cards.
"""

from pathlib import Path
from math import atan2, cos, sin

from reportlab.lib import colors
from reportlab.lib.pagesizes import A1
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PDF = ROOT / "output" / "pdf" / "OMNI-RAG_Poster_A1.pdf"
LOGO = ROOT / "src" / "images" / "itb-logo.png"

W, H = A1
M = 74
CONTENT_W = W - 2 * M

# A small, deliberate palette. The paper and warm highlight prevent the
# poster from looking like a generic dark AI dashboard.
PAPER = colors.HexColor("#F8F7F3")
NAVY = colors.HexColor("#09243D")
INK = colors.HexColor("#17344D")
BLUE = colors.HexColor("#1769A5")
TEAL = colors.HexColor("#0E9D9A")
CORAL = colors.HexColor("#DF764F")
WARM = colors.HexColor("#F3E9DD")
PALE_BLUE = colors.HexColor("#E8F0F5")
PALE_TEAL = colors.HexColor("#E2F1EF")
MUTED = colors.HexColor("#637586")
LINE = colors.HexColor("#C8D4DC")
GRID = colors.HexColor("#E6ECEF")
WHITE = colors.white

FONT = "PosterNoto"
FONT_BOLD = "PosterNoto-Bold"
FONT_ITALIC = "PosterNoto-Italic"
pdfmetrics.registerFont(TTFont(FONT, "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont(FONT_ITALIC, "/usr/share/fonts/truetype/noto/NotoSans-Italic.ttf"))


STYLES = {
    "body": ParagraphStyle(
        "poster_body", fontName=FONT, fontSize=17, leading=22.5,
        textColor=INK, spaceAfter=0,
    ),
    "body_small": ParagraphStyle(
        "poster_body_small", fontName=FONT, fontSize=14.2, leading=19,
        textColor=INK, spaceAfter=0,
    ),
    "body_white": ParagraphStyle(
        "poster_body_white", fontName=FONT, fontSize=15.2, leading=20.5,
        textColor=WHITE, spaceAfter=0,
    ),
    "small": ParagraphStyle(
        "poster_small", fontName=FONT, fontSize=12.3, leading=16,
        textColor=MUTED, spaceAfter=0,
    ),
}


def para(c, text, x, top, width, style="body"):
    p = Paragraph(text, STYLES[style])
    _, height = p.wrap(width, 1000)
    p.drawOn(c, x, top - height)
    return height


def rule(c, x1, y, x2, color=LINE, width=1.0):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, y, x2, y)


def v_rule(c, x, y1, y2, color=LINE, width=1.0):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x, y1, x, y2)


def section_label(c, number, title, x, top, dark=False):
    """Small editorial section marker, intentionally not a card heading."""
    text_color = WHITE if dark else NAVY
    label_color = colors.HexColor("#A9C9DF") if dark else BLUE
    c.setFillColor(label_color)
    c.setFont(FONT_BOLD, 12.5)
    c.drawString(x, top, number)
    c.setFillColor(text_color)
    c.setFont(FONT_BOLD, 22)
    c.drawString(x + 41, top - 1, title)
    rule(c, x, top - 22, x + 28, TEAL if not dark else colors.HexColor("#46C4BB"), 4)


def tag(c, text, x, y, width, fill=PALE_BLUE, text_color=BLUE):
    c.setFillColor(fill)
    c.rect(x, y, width, 25, fill=1, stroke=0)
    c.setFillColor(text_color)
    c.setFont(FONT_BOLD, 10.8)
    c.drawCentredString(x + width / 2, y + 8, text)


def arrow(c, x1, y1, x2, y2, color=BLUE, width=2.0):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)
    angle = atan2(y2 - y1, x2 - x1)
    size = 9
    p1 = (x2 - size * cos(angle - 0.45), y2 - size * sin(angle - 0.45))
    p2 = (x2 - size * cos(angle + 0.45), y2 - size * sin(angle + 0.45))
    path = c.beginPath()
    path.moveTo(x2, y2)
    path.lineTo(*p1)
    path.lineTo(*p2)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def flow_node(c, x, y, w, h, title, subtitle, fill=WHITE, accent=BLUE, title_color=INK):
    c.setFillColor(fill)
    c.setStrokeColor(accent)
    c.setLineWidth(1.2)
    c.rect(x, y, w, h, fill=1, stroke=1)
    c.setFillColor(accent)
    c.rect(x, y, 8, h, fill=1, stroke=0)
    c.setFillColor(title_color)
    c.setFont(FONT_BOLD, 14)
    c.drawCentredString(x + w / 2 + 4, y + h / 2 + 5, title)
    c.setFillColor(MUTED if fill != NAVY else colors.HexColor("#C8DCEA"))
    c.setFont(FONT, 11.5)
    c.drawCentredString(x + w / 2 + 4, y + h / 2 - 15, subtitle)


def metric(c, x, y, value, label, color=BLUE, width=150):
    c.setFillColor(color)
    c.setFont(FONT_BOLD, 29)
    c.drawString(x, y + 25, value)
    c.setFillColor(MUTED)
    c.setFont(FONT_BOLD, 11.2)
    p = Paragraph(label, ParagraphStyle("metric", fontName=FONT_BOLD, fontSize=11.2, leading=14, textColor=MUTED))
    p.wrap(width, 40)
    p.drawOn(c, x, y + 5)


def horizontal_bars(c, x, y, w, title, values, accent=TEAL, precision=3):
    """A clean chart with a single baseline and no chart container."""
    c.setFillColor(INK)
    c.setFont(FONT_BOLD, 15.2)
    c.drawString(x, y + 136, title)
    max_value = max(value for _, value in values)
    label_w = 178
    bar_x = x + label_w
    bar_w = w - label_w - 60
    for i, (label, value) in enumerate(values):
        yy = y + 96 - i * 32
        c.setFillColor(MUTED)
        c.setFont(FONT, 11.8)
        c.drawString(x, yy + 4, label)
        c.setFillColor(GRID)
        c.rect(bar_x, yy, bar_w, 17, fill=1, stroke=0)
        c.setFillColor(accent if i == 0 else BLUE)
        c.rect(bar_x, yy, bar_w * value / max_value, 17, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 12)
        c.drawRightString(x + w, yy + 3, f"{value:.{precision}f}")
    rule(c, bar_x, y + 13, bar_x + bar_w, LINE, 0.8)


def draw_header(c):
    header_h = 350
    bottom = H - header_h
    c.setFillColor(NAVY)
    c.rect(0, bottom, W, header_h, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, bottom, W, 10, fill=1, stroke=0)

    # Logo is placed on a quiet white field; the source mark is not altered.
    c.setFillColor(WHITE)
    c.rect(M, bottom + 108, 112, 150, fill=1, stroke=0)
    c.drawImage(ImageReader(str(LOGO)), M + 18, bottom + 128, width=76, height=110, preserveAspectRatio=True, mask="auto")

    x = M + 151
    c.setFillColor(colors.HexColor("#B5D0E3"))
    c.setFont(FONT_BOLD, 12.5)
    c.drawString(x, bottom + 286, "TUGAS AKHIR INDIVIDU  /  IF4092  /  2026")
    title = ("Pengembangan Pipeline Konstruksi Basis Pengetahuan pada Sistem OMNI-RAG "
             "Multi-Domain Berbasis Plugin pada Studi Kasus Peraturan Perundang-undangan "
             "dan User Manual")
    title_style = ParagraphStyle("header_title", fontName=FONT_BOLD, fontSize=31, leading=36, textColor=WHITE)
    p = Paragraph(title, title_style)
    _, ht = p.wrap(1030, 150)
    p.drawOn(c, x, bottom + 250 - ht)

    c.setFillColor(colors.HexColor("#D3E4EF"))
    c.setFont(FONT, 14.2)
    c.drawString(x, bottom + 116, "Pipeline konstruksi basis pengetahuan · evaluasi lintas domain")
    c.setFont(FONT_BOLD, 13.2)
    c.drawString(x, bottom + 87, "Moh Fairuz Alauddin Yahya  |  13522057  |  Teknik Informatika  |  Institut Teknologi Bandung")
    c.setFillColor(colors.HexColor("#B5D0E1"))
    c.setFont(FONT, 11.6)
    c.drawString(x, bottom + 61, "Pembimbing: Dr. Agung Dewandaru, S.T., M.Sc.  ·  I Wayan Gunada, S.H., M.H.")

    c.setFillColor(colors.HexColor("#6A8EAA"))
    c.setFont(FONT_BOLD, 10.5)
    c.drawRightString(W - M, bottom + 286, "KNOWLEDGE CONSTRUCTION")
    c.drawRightString(W - M, bottom + 267, "MODULAR RAG SYSTEMS")


def draw_story_band(c, top):
    h = 150
    y = top - h
    c.setFillColor(PAPER)
    c.rect(M, y, CONTENT_W, h, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(M, y, 8, h, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 12.5)
    c.drawString(M + 30, top - 29, "RESEARCH STORY")
    story_style = ParagraphStyle("story", fontName=FONT_BOLD, fontSize=25, leading=31, textColor=NAVY)
    p = Paragraph("Bagaimana satu sistem RAG dapat beradaptasi terhadap struktur dokumen yang berbeda tanpa mengubah jalur inti?", story_style)
    _, ph = p.wrap(970, 90)
    p.drawOn(c, M + 30, top - 48 - ph)
    v_rule(c, M + 1060, y + 24, top - 24, LINE, 1.2)
    c.setFillColor(MUTED)
    c.setFont(FONT_BOLD, 11.5)
    c.drawString(M + 1090, top - 37, "JAWABAN SINGKAT")
    para(c, "Representasi kanonik + kontrak plugin memungkinkan strategi chunking, indexing, dan knowledge graph dibandingkan sebagai faktor yang terpisah.", M + 1090, top - 55, 430, "body_small")
    return y


def draw_problem_objective(c, top):
    h = 246
    y = top - h
    col_gap = 54
    half = (CONTENT_W - col_gap) / 2
    left = M
    right = M + half + col_gap

    section_label(c, "01", "Masalah", left, top - 4)
    para(c, "Dokumen hukum dan manual produk menyimpan makna dalam struktur yang berbeda. Jika unit retrieval dipotong tanpa struktur, konteks yang dibutuhkan dapat tercerai; jika strategi dibuat spesifik di jalur inti, sistem sulit diperluas.", left, top - 47, half - 12, "body")
    tag(c, "PERATURAN", left, y + 44, 148, WARM, CORAL)
    tag(c, "USER MANUAL", left + 164, y + 44, 160, PALE_BLUE, BLUE)
    c.setFillColor(MUTED)
    c.setFont(FONT, 12.3)
    c.drawString(left, y + 21, "hierarki Pasal / Ayat  vs.  heading / prosedur / tabel")

    v_rule(c, M + half + col_gap / 2, y + 16, top - 4, LINE, 1.2)
    section_label(c, "02", "Tujuan penelitian", right, top - 4)
    para(c, "Membangun pipeline konstruksi basis pengetahuan yang dapat mengganti strategi per domain, lalu mengukur dampaknya dengan protokol one factor at a time (OFAT).", right, top - 47, half - 10, "body")
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 21)
    c.drawString(right, y + 66, "satu format artefak")
    c.setFillColor(TEAL)
    c.setFont(FONT_BOLD, 21)
    c.drawString(right + 220, y + 66, "→")
    c.setFillColor(NAVY)
    c.drawString(right + 252, y + 66, "banyak strategi")
    c.setFillColor(MUTED)
    c.setFont(FONT, 12.3)
    c.drawString(right, y + 30, "Perubahan komponen tidak memaksa perubahan orkestrator.")
    return y


def draw_pipeline(c, top):
    h = 323
    y = top - h
    section_label(c, "03", "Pendekatan modular", M, top - 4)
    para(c, "Dokumen diproses sekali menjadi artefak kanonik. Strategi yang dipilih kemudian membentuk proyeksi retrieval dan relasi antardokumen; downstream menerima bentuk data yang sama.", M + 230, top - 2, CONTENT_W - 230, "body_small")
    rule(c, M, top - 74, W - M, LINE, 1.1)

    node_y = y + 153
    widths = [195, 150, 260, 240, 170]
    gap = 35
    xs = [M]
    for width in widths[:-1]:
        xs.append(xs[-1] + width + gap)
    labels = [
        ("Dokumen", "legal + manual", WARM, CORAL),
        ("Parser", "native text", PALE_BLUE, BLUE),
        ("CanonicalDocument", "teks + hierarki", PALE_BLUE, BLUE),
        ("Chunker plugin", "4 strategi", PALE_TEAL, TEAL),
        ("CanonicalChunks", "retrieval + context", PALE_BLUE, BLUE),
    ]
    for x, width, (title, sub, fill, accent) in zip(xs, widths, labels):
        flow_node(c, x, node_y, width, 66, title, sub, fill=fill, accent=accent)
    for i in range(len(xs) - 1):
        arrow(c, xs[i] + widths[i] + 8, node_y + 33, xs[i + 1] - 10, node_y + 33, BLUE, 1.5)

    branch_x = xs[-1] + widths[-1] - 40
    lower_y = y + 44
    index_x = M + 590
    graph_x = M + 990
    flow_node(c, index_x, lower_y, 260, 66, "Indexer plugin", "sparse / dense / hybrid", fill=PALE_BLUE, accent=BLUE)
    flow_node(c, graph_x, lower_y, 245, 66, "Legal graph", "seed + traversal", fill=WARM, accent=CORAL)
    flow_node(c, W - M - 240, lower_y, 240, 66, "Evidence path", "retrieval + generation", fill=NAVY, accent=TEAL, title_color=WHITE)
    arrow(c, branch_x, node_y - 4, index_x + 130, lower_y + 74, BLUE, 1.5)
    arrow(c, branch_x, node_y - 4, graph_x + 120, lower_y + 74, CORAL, 1.5)
    arrow(c, index_x + 268, lower_y + 33, W - M - 250, lower_y + 33, BLUE, 1.5)
    arrow(c, graph_x + 253, lower_y + 33, W - M - 250, lower_y + 33, CORAL, 1.5)
    c.setFillColor(MUTED)
    c.setFont(FONT_BOLD, 12.4)
    c.drawString(M, y + 12, "Plugin = unit of strategy replacement; canonical artifacts = boundary of comparison.")
    return y


def draw_method(c, top):
    h = 265
    y = top - h
    section_label(c, "04", "Bagaimana diuji?", M, top - 4)
    para(c, "Eksperimen memakai OFAT: satu komponen berubah, sedangkan corpus, parser, embedding, cutoff, dan tahap hilir dipertahankan.", M + 230, top - 2, CONTENT_W - 230, "body_small")
    rule(c, M, top - 74, W - M, LINE, 1.1)

    col_gap = 34
    col_w = (CONTENT_W - 2 * col_gap) / 3
    xs = [M, M + col_w + col_gap, M + 2 * (col_w + col_gap)]
    headings = ["KORPUS", "FAKTOR UJI", "METRIK & KONTROL"]
    bodies = [
        ("9 manual Netgear", "1.400 halaman · 200 pertanyaan bilingual", "256 dokumen hukum", "25 pertanyaan terverifikasi"),
        ("Chunker", "sliding · recursive · structure-aware", "Indexer", "sparse · dense · hybrid", "Knowledge graph", "17 relasi berarah · 24 tak berarah"),
        ("K = 30", "sweep 5-60; generation K = 10", "Recall utama", "Precision · MRR · NDCG", "Generation", "correctness · faithfulness"),
    ]
    for i, x in enumerate(xs):
        c.setFillColor(BLUE if i != 1 else TEAL)
        c.setFont(FONT_BOLD, 11.5)
        c.drawString(x, top - 103, headings[i])
        yy = top - 133
        for j in range(0, len(bodies[i]), 2):
            c.setFillColor(INK)
            c.setFont(FONT_BOLD, 15)
            c.drawString(x, yy, bodies[i][j])
            c.setFillColor(MUTED)
            c.setFont(FONT, 12.5)
            c.drawString(x, yy - 20, bodies[i][j + 1])
            yy -= 62
        if i < 2:
            v_rule(c, x + col_w + col_gap / 2, y + 28, top - 86, LINE, 1.0)
    return y


def draw_results(c, top):
    h = 558
    y = top - h
    section_label(c, "05", "Bukti eksperimental", M, top - 4)
    para(c, "Pada K = 30, perbedaan paling jelas muncul pada cakupan retrieval. Tidak ada satu konfigurasi yang terbaik untuk semua metrik; domain dan tujuan tahap menentukan pilihan.", M + 270, top - 2, CONTENT_W - 270, "body_small")
    rule(c, M, top - 74, W - M, LINE, 1.1)

    gap = 50
    col_w = (CONTENT_W - 2 * gap) / 3
    xs = [M, M + col_w + gap, M + 2 * (col_w + gap)]
    horizontal_bars(c, xs[0], top - 275, col_w, "Chunker · manual", [("structure-aware hybrid", 0.740), ("sliding-window", 0.685), ("recursive", 0.625)], TEAL, 3)
    horizontal_bars(c, xs[1], top - 275, col_w, "Indexer · manual", [("structure-aware dense", 0.785), ("hybrid", 0.740), ("structure-aware sparse", 0.420)], BLUE, 3)
    horizontal_bars(c, xs[2], top - 275, col_w, "Indexer · hukum", [("legal-structure dense", 0.6854), ("hybrid", 0.6412), ("sparse", 0.6381)], CORAL, 4)
    for x in [M + col_w + gap / 2, M + 2 * col_w + 1.5 * gap]:
        v_rule(c, x, top - 298, top - 102, LINE, 1.0)

    lower_y = y + 76
    rule(c, M, lower_y + 126, W - M, LINE, 1.0)
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 15.2)
    c.drawString(M, lower_y + 101, "What changes downstream?")
    metric(c, M, lower_y + 30, "0.788", "manual correctness", BLUE, 175)
    metric(c, M + 245, lower_y + 30, "0.958", "manual faithfulness", TEAL, 175)
    metric(c, M + 490, lower_y + 30, "0.690", "legal correctness", CORAL, 175)
    metric(c, M + 735, lower_y + 30, "0.972", "legal faithfulness", TEAL, 175)

    gx = M + 1030
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 15.2)
    c.drawString(gx, lower_y + 101, "Legal graph · neighborhood recall")
    graph_values = [("dense", 0.9556), ("recursive", 0.9975), ("sliding", 1.0000), ("sparse", 0.9672), ("hybrid", 0.9975)]
    bar_x = gx
    bar_w = W - M - gx
    for i, (label, value) in enumerate(graph_values):
        yy = lower_y + 88 - i * 17
        c.setFillColor(MUTED)
        c.setFont(FONT, 10.6)
        c.drawString(bar_x, yy + 2, label)
        c.setFillColor(GRID)
        c.rect(bar_x + 68, yy, bar_w - 105, 10, fill=1, stroke=0)
        c.setFillColor(TEAL if label == "sliding" else BLUE)
        c.rect(bar_x + 68, yy, (bar_w - 105) * value, 10, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 10.5)
        c.drawRightString(W - M, yy + 1, f"{value:.4f}")
    c.setFillColor(MUTED)
    c.setFont(FONT, 10.7)
    c.drawString(gx, lower_y + 2, "Graph expands document neighborhood; separate from context-reference recall.")
    return y


def draw_takeaways(c, top):
    h = 225
    y = top - h
    c.setFillColor(NAVY)
    c.rect(M, y, CONTENT_W, h, fill=1, stroke=0)
    section_label(c, "06", "Temuan utama", M + 28, top - 28, dark=True)
    col_gap = 36
    col_w = (CONTENT_W - 2 * col_gap - 56) / 3
    x0 = M + 28
    items = [
        ("01", "Struktur menjaga cakupan", "Structure-aware chunking mengungguli fixed-window pada dua domain yang diuji."),
        ("02", "Dense menjaga coverage", "Dense memberi Recall@30 tertinggi pada manual dan korpus hukum; hybrid unggul pada MRR hukum."),
        ("03", "Modularitas membuatnya dapat diuji", "Artefak kanonik dan kontrak plugin mengisolasi perubahan komponen tanpa menulis ulang jalur inti."),
    ]
    for i, (num, title, body) in enumerate(items):
        x = x0 + i * (col_w + col_gap)
        c.setFillColor(TEAL if i == 0 else colors.HexColor("#4F7B9A"))
        c.rect(x, y + 121, 38, 25, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 11.5)
        c.drawCentredString(x + 19, y + 129, num)
        c.setFont(FONT_BOLD, 15.3)
        c.drawString(x + 52, y + 128, title)
        para(c, body, x, y + 105, col_w, "body_white")
    rule(c, M + 28, y + 67, W - M - 28, colors.HexColor("#4A6D87"), 0.8)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 15.1)
    c.drawString(M + 28, y + 37, "Konfigurasi terbaik bersifat kondisional: pilih komponen sesuai struktur domain dan metrik tahap yang diprioritaskan.")
    return y


def draw_footer(c):
    c.setFillColor(colors.HexColor("#DDE6EB"))
    c.rect(0, 0, W, 78, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 11.5)
    c.drawString(M, 46, "Teknik Informatika · Sekolah Teknik Elektro dan Informatika · Institut Teknologi Bandung")
    c.setFillColor(MUTED)
    c.setFont(FONT, 10.7)
    c.drawString(M, 25, "Sumber angka: laporan tugas akhir individu IF4092 (13522057), 2026. Nilai retrieval dilaporkan pada K = 30.")
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 11.5)
    c.drawRightString(W - M, 36, "MOH FAIRUZ ALAUDDIN YAHYA")


def build():
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUTPUT_PDF), pagesize=A1)
    c.setTitle("OMNI-RAG A1 Thesis Poster")
    c.setAuthor("Moh Fairuz Alauddin Yahya")
    c.setSubject("Knowledge-base construction pipeline for multi-domain OMNI-RAG")
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    draw_header(c)
    story_bottom = draw_story_band(c, H - 350 - 26)
    problem_bottom = draw_problem_objective(c, story_bottom - 34)
    pipeline_bottom = draw_pipeline(c, problem_bottom - 34)
    method_bottom = draw_method(c, pipeline_bottom - 34)
    result_bottom = draw_results(c, method_bottom - 34)
    draw_takeaways(c, result_bottom - 28)
    draw_footer(c)
    c.showPage()
    c.save()
    print(f"Created {OUTPUT_PDF}")


if __name__ == "__main__":
    build()

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A1
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.units import mm


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PDF = ROOT / "output" / "pdf" / "OMNI-RAG_Poster_A1.pdf"
LOGO = ROOT / "src" / "images" / "itb-logo.png"

W, H = A1
M = 48
G = 22
CONTENT_W = W - 2 * M

NAVY = colors.HexColor("#0B1F3A")
ROYAL = colors.HexColor("#0B5CAB")
TEAL = colors.HexColor("#16A6A6")
ORANGE = colors.HexColor("#E8902F")
INK = colors.HexColor("#17212B")
MUTED = colors.HexColor("#617181")
BG = colors.HexColor("#F4F7FA")
WHITE = colors.white
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_TEAL = colors.HexColor("#E5F5F4")
LIGHT_ORANGE = colors.HexColor("#FFF2E1")
BORDER = colors.HexColor("#D1DCE6")
GRID = colors.HexColor("#E3EAF0")

FONT = "PosterDejaVu"
FONT_BOLD = "PosterDejaVu-Bold"
FONT_ITALIC = "PosterDejaVu-Oblique"
pdfmetrics.registerFont(TTFont(FONT, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont(FONT_ITALIC, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"))


def styles():
    return {
        "body": ParagraphStyle(
            "body", fontName=FONT, fontSize=14.2, leading=18.4, textColor=INK,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "body_white": ParagraphStyle(
            "body_white", fontName=FONT, fontSize=13.4, leading=17.1, textColor=WHITE,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "small": ParagraphStyle(
            "small", fontName=FONT, fontSize=12.4, leading=15.8, textColor=INK,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "small_muted": ParagraphStyle(
            "small_muted", fontName=FONT, fontSize=11.7, leading=14.7, textColor=MUTED,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "small_white": ParagraphStyle(
            "small_white", fontName=FONT, fontSize=11.6, leading=14.7, textColor=WHITE,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "card_title": ParagraphStyle(
            "card_title", fontName=FONT_BOLD, fontSize=17.8, leading=21.5, textColor=NAVY,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "card_title_white": ParagraphStyle(
            "card_title_white", fontName=FONT_BOLD, fontSize=17.8, leading=21.5, textColor=WHITE,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "chart_title": ParagraphStyle(
            "chart_title", fontName=FONT_BOLD, fontSize=15.4, leading=18.4, textColor=NAVY,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "center": ParagraphStyle(
            "center", fontName=FONT_BOLD, fontSize=13.4, leading=16.0, textColor=INK,
            alignment=TA_CENTER, spaceAfter=0,
        ),
    }


S = styles()


def draw_para(c, text, x, top, width, style):
    p = Paragraph(text, style)
    _, h = p.wrap(width, 1000)
    p.drawOn(c, x, top - h)
    return h


def draw_card(c, x, y, w, h, fill=WHITE, stroke=BORDER, radius=12, line=1.0):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(line)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def draw_section(c, number, title, x, top, color=NAVY):
    c.setFillColor(TEAL)
    c.roundRect(x, top - 23, 26, 23, 6, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 12)
    c.drawCentredString(x + 13, top - 16.5, number)
    c.setFillColor(color)
    c.setFont(FONT_BOLD, 22)
    c.drawString(x + 38, top - 19, title)


def draw_arrow(c, x1, y1, x2, y2, color=ROYAL, width=2.0):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)
    import math

    angle = math.atan2(y2 - y1, x2 - x1)
    size = 9
    p1 = (x2 - size * math.cos(angle - 0.45), y2 - size * math.sin(angle - 0.45))
    p2 = (x2 - size * math.cos(angle + 0.45), y2 - size * math.sin(angle + 0.45))
    path = c.beginPath()
    path.moveTo(x2, y2)
    path.lineTo(*p1)
    path.lineTo(*p2)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def draw_node(c, x, y, w, h, title, subtitle=None, fill=LIGHT_BLUE, accent=ROYAL, title_size=14.0):
    draw_card(c, x, y, w, h, fill=fill, stroke=accent, radius=9, line=1.5)
    c.setFillColor(accent)
    c.roundRect(x, y, 7, h, 4, fill=1, stroke=0)
    c.setFillColor(NAVY if fill != NAVY else WHITE)
    c.setFont(FONT_BOLD, title_size)
    c.drawCentredString(x + w / 2 + 3, y + h / 2 + 7, title)
    if subtitle:
        c.setFillColor(MUTED if fill != NAVY else colors.HexColor("#D9E8F4"))
        c.setFont(FONT, 10.5)
        c.drawCentredString(x + w / 2 + 3, y + h / 2 - 12, subtitle)


def draw_chip(c, text, x, y, w, h=25, fill=LIGHT_BLUE, stroke=BORDER, text_color=NAVY, font=11.0):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, h / 2, fill=1, stroke=1)
    c.setFillColor(text_color)
    c.setFont(FONT_BOLD, font)
    c.drawCentredString(x + w / 2, y + h / 2 - 4, text)


def draw_metric(c, x, y, w, h, label, value, fill=LIGHT_BLUE, value_color=NAVY):
    draw_card(c, x, y, w, h, fill=fill, stroke=colors.HexColor("#C9D8E4"), radius=10, line=0.8)
    c.setFillColor(value_color)
    c.setFont(FONT_BOLD, 30)
    c.drawString(x + 16, y + h - 40, value)
    c.setFillColor(MUTED)
    c.setFont(FONT_BOLD, 11.5)
    c.drawString(x + 17, y + 16, label)


def draw_metric_text(c, x, y, w, h, label, value, fill=LIGHT_BLUE, value_color=NAVY):
    draw_card(c, x, y, w, h, fill=fill, stroke=colors.HexColor("#C9D8E4"), radius=10, line=0.8)
    c.setFillColor(value_color)
    c.setFont(FONT_BOLD, 20.5)
    c.drawString(x + 16, y + h - 34, value)
    c.setFillColor(MUTED)
    c.setFont(FONT_BOLD, 10.4)
    c.drawString(x + 17, y + 15, label)


def draw_bar_chart(c, x, y, w, h, title, bars, callout, callout_fill=LIGHT_TEAL, precision=3):
    draw_card(c, x, y, w, h, fill=WHITE, stroke=BORDER, radius=12, line=0.9)
    draw_para(c, title, x + 18, y + h - 17, w - 36, S["chart_title"])
    top = y + h - 68
    label_w = 170
    bar_x = x + label_w + 35
    bar_w = w - label_w - 90
    row_h = 52
    max_value = max(v for _, v in bars)
    for i, (label, value) in enumerate(bars):
        row_y = top - (i + 1) * row_h + 8
        draw_para(c, label, x + 18, row_y + 30, label_w - 12, S["small_muted"])
        c.setFillColor(colors.HexColor("#E9EFF4"))
        c.roundRect(bar_x, row_y + 7, bar_w, 20, 8, fill=1, stroke=0)
        c.setFillColor(TEAL if i == 0 else ROYAL)
        c.roundRect(bar_x, row_y + 7, bar_w * (value / max_value), 20, 8, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 13)
        c.drawRightString(x + w - 18, row_y + 10, f"{value:.{precision}f}")
    c.setFillColor(callout_fill)
    c.roundRect(x + 18, y + 14, w - 36, 27, 8, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 12.2)
    c.drawString(x + 30, y + 23, callout)


def draw_network(c, x, y, w, h):
    draw_card(c, x, y, w, h, fill=WHITE, stroke=BORDER, radius=12, line=0.9)
    draw_para(c, "Graph expands connected coverage", x + 18, y + h - 17, w - 36, S["chart_title"])
    c.setStrokeColor(colors.HexColor("#9BB8C9"))
    c.setLineWidth(1.5)
    nodes = {
        "reg": (x + 65, y + 61),
        "art": (x + 225, y + 82),
        "rev": (x + 225, y + 39),
        "ref": (x + 385, y + 61),
    }
    for a, b in [("reg", "art"), ("reg", "rev"), ("art", "ref"), ("rev", "ref")]:
        draw_arrow(c, *nodes[a], *nodes[b], color=colors.HexColor("#9BB8C9"), width=1.2)
    for key, label in [("reg", "Regulation"), ("art", "Article"), ("rev", "Amended article"), ("ref", "Referenced regulation")]:
        nx, ny = nodes[key]
        c.setFillColor(LIGHT_BLUE if key != "rev" else LIGHT_ORANGE)
        c.setStrokeColor(ROYAL if key != "rev" else ORANGE)
        c.setLineWidth(1.2)
        c.circle(nx, ny, 27, fill=1, stroke=1)
        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 9.5)
        c.drawCentredString(nx, ny - 3, label if len(label) <= 10 else label.split()[0])
    c.setFillColor(TEAL)
    c.setFont(FONT_BOLD, 22)
    c.drawString(x + 18, y + 18, "1.000")
    c.setFillColor(MUTED)
    c.setFont(FONT, 8.9)
    c.drawString(x + 95, y + 23, "connected-document coverage; separate from context-reference recall")


def draw_architecture(c, x, y, w, h):
    draw_card(c, x, y, w, h, fill=WHITE, stroke=BORDER, radius=14, line=1.0)
    draw_section(c, "04", "Proposed architecture - one canonical path, many strategies", x + 22, y + h - 22)

    control_y = y + h - 72
    c.setFillColor(LIGHT_TEAL)
    c.setStrokeColor(colors.HexColor("#B5DDDA"))
    c.setLineWidth(0.8)
    c.roundRect(x + 300, control_y - 18, w - 600, 31, 15, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 12.7)
    c.drawCentredString(x + w / 2, control_y - 7, "CONTROL LAYER  |  Profile  |  Manifest  |  Provenance  |  Compatibility contracts")

    row_y = y + h - 200
    nodes = [
        (x + 30, 150, "Raw documents", "legal + manuals", LIGHT_ORANGE, ORANGE),
        (x + 215, 120, "Parser", "native text", LIGHT_BLUE, ROYAL),
        (x + 370, 185, "CanonicalDocument", "source + hierarchy", LIGHT_BLUE, ROYAL),
        (x + 595, 255, "Plugin-based chunker", "4 strategies", LIGHT_TEAL, TEAL),
        (x + 895, 190, "CanonicalChunks", "retrieval + context", LIGHT_BLUE, ROYAL),
    ]
    for nx, nw, title, sub, fill, accent in nodes:
        draw_node(c, nx, row_y, nw, 70, title, sub, fill=fill, accent=accent, title_size=13.0)
    for (x1, w1), (x2, _) in zip([(n[0], n[1]) for n in nodes[:-1]], [(n[0], n[1]) for n in nodes[1:]]):
        draw_arrow(c, x1 + w1 + 8, row_y + 35, x2 - 9, row_y + 35)

    branch_y = y + 108
    index_x = x + 580
    kg_x = x + 890
    draw_node(c, index_x, branch_y, 255, 92, "Indexer plugin", "Sparse / Dense / Hybrid", fill=LIGHT_BLUE, accent=ROYAL, title_size=14.0)
    draw_node(c, kg_x, branch_y, 255, 92, "Knowledge graph plugin", "Legal graph / LLM graph", fill=LIGHT_ORANGE, accent=ORANGE, title_size=13.2)
    draw_arrow(c, x + 990, row_y - 8, index_x + 126, branch_y + 99, color=ROYAL)
    draw_arrow(c, x + 990, row_y - 8, kg_x + 126, branch_y + 99, color=ORANGE)
    retrieval_x = x + 1190
    draw_node(c, retrieval_x, branch_y + 15, 170, 62, "Retrieval / RAG", "evidence", fill=NAVY, accent=TEAL, title_size=13.0)
    draw_node(c, x + 1390, branch_y + 15, 145, 62, "Answer", "generated", fill=LIGHT_TEAL, accent=TEAL, title_size=13.0)
    draw_arrow(c, index_x + 255 + 8, branch_y + 46, retrieval_x - 8, branch_y + 46, color=ROYAL)
    draw_arrow(c, kg_x + 255 + 8, branch_y + 46, retrieval_x - 8, branch_y + 46, color=ORANGE)
    draw_arrow(c, retrieval_x + 170 + 8, branch_y + 46, x + 1390 - 8, branch_y + 46, color=TEAL)
    c.setFillColor(MUTED)
    c.setFont(FONT_BOLD, 12.8)
    c.drawString(x + 30, y + 27, "Same chunks -> different projections. New strategy = new plugin, not a core-orchestrator rewrite.")


def draw_setup(c, x, y, w, h):
    draw_card(c, x, y, w, h, fill=WHITE, stroke=BORDER, radius=14, line=1.0)
    draw_section(c, "05", "Experimental setup - two domains, one controlled protocol", x + 22, y + h - 22)
    inner_y = y + 24
    col_w = (w - 60) / 3
    # Dataset panel
    dx = x + 20
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 12.2)
    c.drawString(dx, inner_y + 166, "DATASETS")
    dataset_w = (col_w - 20) / 2
    draw_metric(c, dx, inner_y + 75, dataset_w, 78, "Netgear manuals", "9", fill=LIGHT_BLUE)
    draw_metric(c, dx + dataset_w + 10, inner_y + 75, dataset_w, 78, "legal documents", "256", fill=LIGHT_ORANGE)
    c.setFillColor(MUTED)
    c.setFont(FONT, 10.8)
    c.drawString(dx, inner_y + 48, "1,400 pages | 100 bilingual slots")
    c.drawString(dx + dataset_w + 10, inner_y + 48, "49 reference | 207 noise | 25 questions")
    # Protocol panel
    px = x + col_w + 28
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 12.2)
    c.drawString(px, inner_y + 166, "PROTOCOL")
    draw_chip(c, "K = 30", px, inner_y + 110, 92, 27, fill=LIGHT_TEAL, stroke=colors.HexColor("#B5DDDA"), font=12)
    draw_chip(c, "sweep K = 5-60", px + 106, inner_y + 110, 150, 27, fill=LIGHT_BLUE, stroke=colors.HexColor("#C9D8E4"), font=11.4)
    draw_chip(c, "generation K = 10", px, inner_y + 72, 160, 27, fill=LIGHT_BLUE, stroke=colors.HexColor("#C9D8E4"), font=11.4)
    draw_chip(c, "Recall primary", px + 174, inner_y + 72, 132, 27, fill=LIGHT_ORANGE, stroke=colors.HexColor("#EACFAD"), font=11.4)
    c.setFillColor(MUTED)
    c.setFont(FONT, 11)
    c.drawString(px, inner_y + 42, "Supporting metrics: Precision, MRR, NDCG")
    c.drawString(px, inner_y + 23, "Generation: correctness + faithfulness")
    # Strategy panel
    sx = x + 2 * col_w + 36
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 12.2)
    c.drawString(sx, inner_y + 166, "CONFIGURATION SPACE")
    draw_chip(c, "4 chunkers", sx, inner_y + 110, 125, 27, fill=LIGHT_TEAL, stroke=colors.HexColor("#B5DDDA"), font=12)
    draw_chip(c, "3 indexers", sx + 138, inner_y + 110, 125, 27, fill=LIGHT_BLUE, stroke=colors.HexColor("#C9D8E4"), font=12)
    draw_chip(c, "2 graph strategies", sx, inner_y + 72, 180, 27, fill=LIGHT_ORANGE, stroke=colors.HexColor("#EACFAD"), font=11.4)
    c.setFillColor(MUTED)
    c.setFont(FONT, 11)
    c.drawString(sx, inner_y + 42, "OFAT: change one component, hold the rest fixed")
    c.drawString(sx, inner_y + 23, "Direct retrieval path: reranker and graph disabled")


def draw_results(c, x, y, w, h):
    draw_card(c, x, y, w, h, fill=BG, stroke=BORDER, radius=14, line=1.0)
    draw_section(c, "06", "Experimental evidence - structure and semantics change coverage", x + 22, y + h - 22)
    chart_y = y + 178
    chart_h = 245
    chart_w = (w - 80) / 3
    draw_bar_chart(
        c, x + 20, chart_y, chart_w, chart_h,
        "Preserving structure improves retrieval coverage",
        [("Structure-aware hybrid", 0.740), ("Sliding baseline", 0.685)],
        "+0.055 Recall@30",
    )
    draw_bar_chart(
        c, x + 30 + chart_w, chart_y, chart_w, chart_h,
        "Semantic dense retrieval leads recall",
        [("Structure-aware dense", 0.785), ("Structure-aware hybrid", 0.740), ("Sparse baseline", 0.420)],
        "Dense vs sparse: +0.365 recall",
    )
    draw_bar_chart(
        c, x + 40 + 2 * chart_w, chart_y, chart_w, chart_h,
        "Domain-aware structure transfers to legal text",
        [("Legal-structure dense", 0.6854), ("Sparse baseline", 0.6381), ("Sliding baseline", 0.6345)],
        "Best legal Recall@30: 0.6854",
        callout_fill=LIGHT_ORANGE,
        precision=4,
    )

    bottom_y = y + 20
    bottom_h = 137
    gx = x + 20
    gen_w = 940
    draw_card(c, gx, bottom_y, gen_w, bottom_h, fill=WHITE, stroke=BORDER, radius=11, line=0.8)
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 13.4)
    c.drawString(gx + 18, bottom_y + bottom_h - 23, "Downstream generation remains strong")
    card_w = (gen_w - 58) / 2
    draw_metric_text(c, gx + 18, bottom_y + 20, card_w, 72, "manual correctness / faithfulness", "0.788 / 0.958", fill=LIGHT_BLUE)
    draw_metric_text(c, gx + 40 + card_w, bottom_y + 20, card_w, 72, "legal correctness / faithfulness", "0.690 / 0.972", fill=LIGHT_ORANGE)

    draw_network(c, x + 40 + gen_w, bottom_y, w - gen_w - 60, bottom_h)


def draw_takeaways(c, x, y, w, h):
    draw_card(c, x, y, w, h, fill=NAVY, stroke=NAVY, radius=14, line=0.8)
    draw_section(c, "07", "What did we learn?", x + 22, y + h - 22, color=WHITE)
    col_w = (w - 84) / 3
    items = [
        ("01", "Structure matters", "Structure-aware chunking increases context-reference coverage across both tested domains."),
        ("02", "Semantic retrieval matters", "Dense indexing substantially improves recall compared with the sparse baseline in the tested configurations."),
        ("03", "Modularity matters", "Canonical artifacts and plugin contracts enable new strategies without modifying the core orchestrator."),
    ]
    for i, (num, title, body) in enumerate(items):
        cx = x + 28 + i * (col_w + 14)
        c.setFillColor(TEAL if i == 0 else colors.HexColor("#4D7CA6"))
        c.roundRect(cx, y + 100, 42, 28, 7, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 12)
        c.drawCentredString(cx + 21, y + 110, num)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 15.2)
        c.drawString(cx + 54, y + 110, title)
        draw_para(c, body, cx, y + 90, col_w, S["body_white"])
    c.setStrokeColor(colors.HexColor("#587A99"))
    c.setLineWidth(0.8)
    c.line(x + 25, y + 66, x + w - 25, y + 66)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 15.3)
    c.drawString(x + 28, y + 37, "OMNI-RAG separates domain-specific knowledge construction from the core pipeline - making multi-domain RAG more extensible, traceable, and experimentally configurable.")


def draw_header(c):
    header_h = 270
    c.setFillColor(NAVY)
    c.rect(0, H - header_h, W, header_h, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, H - header_h, W, 8, fill=1, stroke=0)
    # White logo tile keeps the original ITB mark untouched.
    c.setFillColor(WHITE)
    c.roundRect(M, H - 208, 110, 142, 12, fill=1, stroke=0)
    c.drawImage(ImageReader(str(LOGO)), M + 16, H - 197, width=78, height=108, preserveAspectRatio=True, mask="auto")
    c.setFillColor(colors.HexColor("#B8D4EA"))
    c.setFont(FONT_BOLD, 12.5)
    c.drawString(M + 140, H - 58, "TA 2026  |  COMPUTER SCIENCE RESEARCH")
    title = "Pengembangan Pipeline Konstruksi Basis Pengetahuan pada Sistem OMNI-RAG Multi-Domain Berbasis Plugin pada Studi Kasus Peraturan Perundang-undangan dan User Manual"
    draw_para(c, title, M + 140, H - 77, W - M - 180, ParagraphStyle(
        "header_title", fontName=FONT_BOLD, fontSize=31, leading=36.5, textColor=WHITE,
        alignment=TA_LEFT,
    ))
    c.setFillColor(colors.HexColor("#D8E7F3"))
    c.setFont(FONT, 13.2)
    c.drawString(M + 140, H - 218, "Moh Fairuz Alauddin Yahya  |  13522057  |  Teknik Informatika  |  Institut Teknologi Bandung")
    c.setFillColor(colors.HexColor("#A9C4DD"))
    c.setFont(FONT, 11.7)
    c.drawString(M + 140, H - 241, "Pembimbing: Dr. Agung Dewandaru, S.T., M.Sc.  |  I Wayan Gunada, S.H., M.H.")


def build():
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUTPUT_PDF), pagesize=A1)
    c.setTitle("OMNI-RAG A1 Thesis Poster")
    c.setAuthor("Moh Fairuz Alauddin Yahya")
    c.setSubject("Knowledge-base construction pipeline for multi-domain OMNI-RAG")
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    draw_header(c)
    top_y = H - 302
    card_h = 248
    col_w = (CONTENT_W - 2 * G) / 3
    x1 = M
    x2 = M + col_w + G
    x3 = M + 2 * (col_w + G)
    # Problem card
    draw_card(c, x1, top_y - card_h, col_w, card_h)
    draw_section(c, "01", "Why is multi-domain RAG difficult?", x1 + 18, top_y - 18)
    draw_para(c, "<b>Different document domains require different knowledge construction strategies.</b>", x1 + 20, top_y - 64, col_w - 40, S["body"])
    draw_chip(c, "INDONESIAN LEGAL DOCUMENTS", x1 + 20, top_y - 144, col_w - 40, 28, fill=LIGHT_ORANGE, stroke=colors.HexColor("#EACFAD"), font=11.1)
    draw_chip(c, "PRODUCT USER MANUALS", x1 + 20, top_y - 181, col_w - 40, 28, fill=LIGHT_BLUE, stroke=colors.HexColor("#C9D8E4"), font=11.1)
    draw_para(c, "Hierarchical regulation -> article -> paragraph versus procedure -> table -> product term.", x1 + 20, top_y - 197, col_w - 40, S["small_muted"])
    # Objective card
    draw_card(c, x2, top_y - card_h, col_w, card_h)
    draw_section(c, "02", "What is the objective?", x2 + 18, top_y - 18)
    draw_para(c, "Develop an extensible knowledge construction pipeline for multi-domain RAG without modifying the core orchestrator when a new strategy or domain is introduced.", x2 + 20, top_y - 64, col_w - 40, S["body"])
    c.setFillColor(LIGHT_TEAL)
    c.setStrokeColor(colors.HexColor("#B5DDDA"))
    c.roundRect(x2 + 20, top_y - 208, col_w - 40, 54, 12, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 20)
    c.drawString(x2 + 38, top_y - 181, "new strategy = new plugin")
    c.setFillColor(MUTED)
    c.setFont(FONT, 11.3)
    c.drawString(x2 + 38, top_y - 199, "contracts keep the orchestrator stable")
    # Contribution card
    draw_card(c, x3, top_y - card_h, col_w, card_h)
    draw_section(c, "03", "What was developed?", x3 + 18, top_y - 18)
    draw_para(c, "A shared canonical representation turns one parsed document into interchangeable retrieval projections.", x3 + 20, top_y - 64, col_w - 40, S["body"])
    draw_metric(c, x3 + 20, top_y - 171, (col_w - 52) / 3, 67, "chunkers", "4", fill=LIGHT_TEAL, value_color=TEAL)
    draw_metric(c, x3 + 28 + (col_w - 52) / 3, top_y - 171, (col_w - 52) / 3, 67, "indexers", "3", fill=LIGHT_BLUE, value_color=ROYAL)
    draw_metric(c, x3 + 36 + 2 * (col_w - 52) / 3, top_y - 171, (col_w - 52) / 3, 67, "graph strategies", "2", fill=LIGHT_ORANGE, value_color=ORANGE)
    c.setFillColor(MUTED)
    c.setFont(FONT, 11.3)
    c.drawString(x3 + 20, top_y - 209, "Canonical artifact + provenance + plugin contracts")

    arch_y = 1280
    arch_h = 500
    draw_architecture(c, M, arch_y, CONTENT_W, arch_h)
    setup_y = 990
    setup_h = 263
    draw_setup(c, M, setup_y, CONTENT_W, setup_h)
    results_y = 442
    results_h = 518
    draw_results(c, M, results_y, CONTENT_W, results_h)
    take_y = 136
    take_h = 280
    draw_takeaways(c, M, take_y, CONTENT_W, take_h)

    # Footer: practical identity, not a references block.
    c.setFillColor(colors.HexColor("#D9E3EB"))
    c.rect(0, 0, W, 100, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 12.3)
    c.drawString(M, 62, "Undergraduate thesis poster  |  Program Studi Teknik Informatika  |  Sekolah Teknik Elektro dan Informatika")
    c.setFillColor(MUTED)
    c.setFont(FONT, 11.2)
    c.drawString(M, 39, "Data and results: laporan tugas akhir individu IF4092, 2026  |  Values shown at retrieval cutoff K = 30 unless noted.")
    c.drawRightString(W - M, 51, "Institut Teknologi Bandung")
    c.showPage()
    c.save()
    print(f"Created {OUTPUT_PDF}")


if __name__ == "__main__":
    build()

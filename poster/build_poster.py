"""Build the A1 research poster. Measurements in mm, text sizes in points."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

ROOT = Path(__file__).resolve().parent
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
for name, filename in [('Sans', 'DejaVuSans.ttf'), ('Sans-Bold', 'DejaVuSans-Bold.ttf'),
                       ('Sans-Italic', 'DejaVuSans-Oblique.ttf'),
                       ('Sans-BoldItalic', 'DejaVuSans-BoldOblique.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='Sans-Bold', italic='Sans-Italic', boldItalic='Sans-BoldItalic')
OUT = ROOT / 'Omni-RAG_Poster_13522057.pdf'
W, H = 594, 841
NAVY, TEAL, ORANGE = '#102C40', '#007E87', '#C26328'
INK, MUTED, BG, LINE = '#163143', '#536876', '#F3F6F7', '#D4E0E4'
c = canvas.Canvas(str(OUT), pagesize=(W*mm, H*mm))
c.setTitle('Omni-RAG | Poster Tugas Akhir | Moh Fairuz Alauddin Yahya')
c.setAuthor('Moh Fairuz Alauddin Yahya')

def box(x,y,w,h,color, radius=0):
    c.setFillColor(HexColor(color))
    if radius:
        c.roundRect(x*mm,(H-y-h)*mm,w*mm,h*mm,radius*mm,fill=1,stroke=0)
    else:
        c.rect(x*mm,(H-y-h)*mm,w*mm,h*mm,fill=1,stroke=0)

def text(x,y,w,s,size=22,color=INK,bold=False,leading=None,max_h=None):
    style=ParagraphStyle('p',fontName='Sans-Bold' if bold else 'Sans',fontSize=size,
        leading=leading or size*1.32,textColor=HexColor(color),spaceAfter=0)
    p=Paragraph(s,style)
    _,h=p.wrap(w*mm, H*mm)
    if max_h is not None and h>max_h*mm:
        raise ValueError(f'Text exceeds allocated height: {s[:75]} ({h/mm:.1f}>{max_h} mm)')
    p.drawOn(c,x*mm,(H-y)*mm-h)
    return h/mm

def rule(x,y,w,color=LINE):
    c.setStrokeColor(HexColor(color)); c.setLineWidth(0.6*mm)
    c.line(x*mm,(H-y)*mm,(x+w)*mm,(H-y)*mm)

def arrow(x1,y1,x2,y2,color=TEAL):
    from math import atan2, sin, cos
    c.setStrokeColor(HexColor(color)); c.setLineWidth(1.1*mm)
    c.line(x1*mm,(H-y1)*mm,x2*mm,(H-y2)*mm)
    a=atan2(y2-y1,x2-x1)
    for d in (-0.5,0.5):
        c.line(x2*mm,(H-y2)*mm,(x2-4*cos(a+d))*mm,(H-y2+4*sin(a+d))*mm)

def bars(x,y,w,values,accent):
    # All plots share a zero-to-one scale. Labels are placed above each bar.
    for i,(label,value) in enumerate(values):
        top=y+i*23
        text(x,top,w-28,f'<i>{label}</i>',19,max_h=9)
        text(x+w-26,top,26,f'{value:.3f}'.replace('.',','),21,bold=True,max_h=10)
        box(x,top+11,w,5,'#E1E9ED',2)
        box(x,top+11,w*value,5,accent if i==0 else '#859EAB',2)
    text(x,y+len(values)*23-3,w,'Skala batang 0-1 • semakin tinggi, semakin banyak referensi ditemukan',13,color=MUTED,max_h=14)

box(0,0,W,H,BG)
box(0,0,W,157,NAVY)
box(22,20,3,11,'#42D1CD')
text(30,20,435,'POSTER TUGAS AKHIR  /  INFORMATIKA ITB  /  2026',19,color='#9DE1E2',bold=True)
# Reuse the actual institutional mark, with no regenerated logo.
c.drawImage(str(ROOT.parent/'src/images/itb-logo.png'),535*mm,(H-59)*mm,
    width=36*mm,height=36*mm,preserveAspectRatio=True,mask='auto')
text(22,38,495,'Omni-RAG',70,color='#FFFFFF',bold=True,max_h=33)
text(22,72,550,'Konstruksi Basis Pengetahuan<br/>Berbasis <i>Plugin</i> untuk RAG <i>Multi-domain</i>',35,color='#FFFFFF',bold=True,max_h=39)
text(22,111,550,'Studi kasus peraturan perundang-undangan dan <i>User Manual</i>',23,color='#C9E0E9',max_h=13)
text(22,129,550,'Moh Fairuz Alauddin Yahya  •  13522057',23,color='#FFFFFF',bold=True,max_h=12)
text(22,143,550,'Program Studi Teknik Informatika · Sekolah Teknik Elektro dan Informatika · Institut Teknologi Bandung',15,color='#C9E0E9',max_h=10)

text(22,169,265,'01  Masalah',29,bold=True)
text(309,169,263,'02  Gagasan utama',29,bold=True)
text(22,187,263,'Pemotongan teks dapat memisahkan rincian dari konteksnya. Perbedaan struktur dan istilah juga membuat satu strategi pencarian belum tentu sesuai untuk semua <i>domain</i>.',23,max_h=45)
text(309,187,263,'Gunakan kontrak <i>canonical artifact</i> untuk menjaga identitas dan sumber. Strategi <i>chunker</i>, <i>indexer</i>, dan <i>knowledge graph</i> dapat diganti melalui <i>plugin</i>.',23,max_h=45)

box(22,244,550,171,'#FFFFFF',5)
text(32,254,530,'03  Satu sumber, tiga proses konstruksi',29,bold=True)
text(32,273,530,'<i>Retrieval-Augmented Generation</i> (RAG): mencari sumber yang relevan sebelum jawaban dibentuk',20,color=MUTED)
box(32,299,113,54,'#EEF3F6',3)
text(39,306,99,'MASUKAN',15,color=MUTED,bold=True)
text(39,317,99,'Dokumen kanonis',23,bold=True)
text(39,331,99,'Teks, struktur, dan <i>metadata</i>',17,max_h=19)
arrow(145,325,166,325)
box(168,299,138,54,'#E1F3F1',3)
text(176,306,121,'1 / <i>CHUNKING</i>',17,color=TEAL,bold=True)
text(176,318,121,'Bentuk unit informasi',23,bold=True)
text(176,332,121,'Jaga konteks dan identitas sumber',17,max_h=18)
arrow(306,325,330,309)
arrow(306,325,330,354)
box(334,292,225,41,'#E1F3F1',3)
text(342,298,209,'2 / <i>INDEXING</i>',17,color=TEAL,bold=True)
text(342,310,209,'Indeks <i>sparse</i>, <i>dense</i>, atau <i>hybrid</i>',22,max_h=17)
box(334,341,225,41,'#F9EDE3',3)
text(342,347,209,'3 / <i>KNOWLEDGE GRAPH</i>',17,color=ORANGE,bold=True)
text(342,359,209,'Bentuk entitas dan relasi dari <i>chunk</i> yang sama',21,max_h=19)
text(32,369,276,'<i>Profile</i> memilih komponen.<br/><i>Manifest</i> dan kontrak memeriksa kompatibilitas.',17,max_h=22)
rule(32,395,528)
text(32,399,528,'Pendukung percakapan: <i>Context PII</i> · <i>guardrail</i> · <i>history compactor</i> (tidak dieksperimenkan)',17,max_h=12)

text(22,429,550,'04  Hasil: strategi terbaik berbeda menurut korpus',29,bold=True)
text(22,447,550,'Evaluasi <i>retrieval-only</i> • satu komponen diubah pada setiap perbandingan • metrik utama <i>recall@K</i>',18,color=MUTED,max_h=12)

for x,accent in [(22,TEAL),(303,ORANGE)]:
    box(x,467,269,193,'#FFFFFF',4)
    box(x,467,269,2,accent)
text(32,478,249,'<i>User Manual</i> Netgear',27,color=TEAL,bold=True)
text(313,478,249,'Peraturan bidang pendidikan',26,color=ORANGE,bold=True)
text(32,496,249,'9 manual · 1.400 halaman<br/>200 pertanyaan dualbahasa dari 100 <i>intent</i>',19,max_h=24)
text(313,496,249,'255 dokumen · 217 kelompok peraturan (PSU)<br/>100 pertanyaan dari 25 PSU<br/>Pemilihan berstrata dengan PSU utuh',17,max_h=27)
text(32,524,249,'K = 45  /  <i>Structure-aware chunker</i>',18,color=MUTED,max_h=11)
text(313,524,249,'K = 25  /  <i>Legal structure-aware chunker</i>',18,color=MUTED,max_h=11)
bars(32,541,249,[('Dense',0.835),('Hybrid',0.745),('Sparse',0.465)],TEAL)
bars(313,541,249,[('Hybrid',0.670),('Dense',0.640),('Sparse',0.640)],ORANGE)
text(32,632,249,'Pencarian semantik membantu menemukan konteks melalui parafrasa dan lintas bahasa.',19,max_h=24)
text(313,632,249,'Gabungan istilah dan makna memberi cakupan tertinggi pada pertanyaan peraturan.',19,max_h=24)

box(22,672,550,59,'#E4EEF2',4)
text(32,681,121,'0,517',49,color=NAVY,bold=True,max_h=24)
text(32,707,121,'<i>KG recall</i> · K = 25',17,color=MUTED,max_h=10)
text(162,681,396,'Penelusuran relasi hukum',25,bold=True)
text(162,697,396,'<i>Sparse</i> tertinggi pada 30 pertanyaan relasi, diikuti <i>hybrid</i> (0,417). Ini mengukur penemuan sumber hubungan, bukan kualitas ekstraksi graf secara menyeluruh.',20,max_h=29)

box(0,745,594,96,NAVY)
text(22,755,550,'Struktur dipertahankan. Strategi disesuaikan.',30,color='#FFFFFF',bold=True)
text(22,774,550,'<i>Structure-aware chunker</i> mencapai <i>recall</i> 0,740 pada manual dan 0,64 pada peraturan (K = 25, dengan <i>indexer</i> tetap dalam setiap korpus). Kontrak <i>plugin</i> memungkinkan perluasan strategi tanpa mengubah orkestrator inti.',20,color='#E1EDF3',max_h=32)
text(22,809,550,'Batas evaluasi: korpus terbatas, nilai K antarkorpus berbeda, tanpa pengukuran kualitas jawaban akhir atau signifikansi statistik.',16,color='#AAC5D3',max_h=17)
text(22,831,550,'Sumber: Laporan TA, Bab III-V · Moh Fairuz Alauddin Yahya · 2026',13,color='#AAC5D3',max_h=7)
c.showPage()
c.save()
print(OUT)

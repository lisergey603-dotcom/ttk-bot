"""Генерирует фирменный образец ТТК (PDF) для бота.
Запуск из корня проекта: pip install reportlab && python tools/make_example_ttk.py
Превью: pdftoppm -png -r 100 -singlefile bot/assets/example_ttk.pdf bot/assets/example_ttk_preview
"""
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", F + "DejaVuSans-Bold.ttf"))

out = sys.argv[1] if len(sys.argv) > 1 else "bot/assets/example_ttk.pdf"
LOGO = sys.argv[2] if len(sys.argv) > 2 else "bot/assets/logo.png"
# Фирменные цвета «Техкарты PRO»
GREEN = colors.HexColor("#1f4d3a")
ORANGE = colors.HexColor("#e8a33d")
CREAM = colors.HexColor("#f4f1ea")
INK = colors.HexColor("#1f2a24")
MUTED = colors.HexColor("#59645e")
LINE = colors.HexColor("#94a89b")

base = ParagraphStyle("b", fontName="DV", fontSize=9, leading=11.6, textColor=INK)
h = ParagraphStyle("h", parent=base, fontName="DVB", fontSize=10, spaceBefore=6, spaceAfter=2, textColor=GREEN)
title = ParagraphStyle("t", parent=base, fontName="DVB", fontSize=13, alignment=1, leading=17, textColor=GREEN)
small = ParagraphStyle("s", parent=base, fontSize=8, textColor=MUTED)
right = ParagraphStyle("r", parent=base, alignment=2)


def page(c, d):
    W, H = A4
    # Шапка: кремовая полоса с логотипом и оранжевая линия
    c.saveState()
    c.setFillColor(CREAM)
    c.rect(0, H - 30 * mm, W, 30 * mm, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(0, H - 31.2 * mm, W, 1.2 * mm, stroke=0, fill=1)
    logo_h = 18 * mm
    c.drawImage(LOGO, 14 * mm, H - 24 * mm, height=logo_h, width=logo_h * 1010 / 230, mask="auto")
    c.setFont("DVB", 8.5)
    c.setFillColor(GREEN)
    c.drawRightString(W - 16 * mm, H - 13 * mm, "Telegram: @tehkarty_pro_bot")
    c.setFont("DV", 7.5)
    c.setFillColor(MUTED)
    c.drawRightString(W - 16 * mm, H - 17.5 * mm, "Разработка ТТК по ГОСТ 31987-2012")
    # Водяной знак
    c.setFont("DVB", 70)
    c.setFillColor(colors.Color(0.91, 0.64, 0.24, alpha=0.13))
    c.translate(W / 2, H / 2 - 15 * mm)
    c.rotate(40)
    c.drawCentredString(0, 0, "ОБРАЗЕЦ")
    c.restoreState()
    # Подвал
    c.setStrokeColor(LINE)
    c.setLineWidth(0.4)
    c.line(18 * mm, 13 * mm, W - 18 * mm, 13 * mm)
    c.setFont("DV", 7)
    c.setFillColor(MUTED)
    c.drawString(18 * mm, 9 * mm, "Образец документа для ознакомления. Данные рецептуры условные.")
    c.drawRightString(W - 18 * mm, 9 * mm, "Техкарты PRO · t.me/tehkarty_pro_bot")


def P(x):
    return Paragraph(x, ParagraphStyle("cell", parent=base, fontSize=8.5, leading=10.5))


def tbl(data, widths, header=True, total_row=False):
    t = Table(data, colWidths=widths)
    st = [
        ("FONT", (0, 0), (-1, -1), "DV", 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
    ]
    if header:
        st += [("FONT", (0, 0), (-1, 0), "DVB", 8.5), ("BACKGROUND", (0, 0), (-1, 0), GREEN),
               ("TEXTCOLOR", (0, 0), (-1, 0), CREAM)]
    if total_row:
        st += [("FONT", (0, -1), (-1, -1), "DVB", 8.5), ("BACKGROUND", (0, -1), (-1, -1), CREAM),
               ("TEXTCOLOR", (0, -1), (-1, -1), GREEN)]
    t.setStyle(TableStyle(st))
    return t


s = []
s.append(Paragraph("УТВЕРЖДАЮ<br/>Руководитель ________________ / ____________<br/>«___» ____________ 20__ г.", right))
s.append(Spacer(1, 6))
s.append(Paragraph("ТЕХНИКО-ТЕХНОЛОГИЧЕСКАЯ КАРТА № 12", title))
s.append(Paragraph("на блюдо «Сырники со сметаной»", ParagraphStyle("x", parent=title, fontName="DV", fontSize=11)))
s.append(Spacer(1, 4))
s.append(Paragraph("Разработана в соответствии с ГОСТ 31987-2012", ParagraphStyle("c", parent=small, alignment=1)))

s.append(Paragraph("1. Область применения", h))
s.append(Paragraph("Настоящая ТТК распространяется на блюдо «Сырники со сметаной», вырабатываемое и реализуемое "
                   "предприятием общественного питания «__________» (адрес: __________).", base))

s.append(Paragraph("2. Требования к сырью", h))
s.append(Paragraph("Продовольственное сырьё, пищевые продукты и полуфабрикаты должны соответствовать требованиям "
                   "нормативных документов и сопровождаться документами, подтверждающими их безопасность и качество.", base))

s.append(Paragraph("3. Рецептура (на 1 порцию)", h))
s.append(tbl([
    ["Наименование сырья", "Брутто, г", "Нетто, г"],
    ["Творог 9%", "125", "123"],
    ["Яйцо куриное", "12", "10"],
    ["Мука пшеничная в/с (в т. ч. на панировку)", "15", "15"],
    ["Сахар-песок", "10", "10"],
    ["Сахар ванильный", "0,5", "0,5"],
    ["Масса полуфабриката", "—", "158"],
    ["Масло подсолнечное рафинированное (для жарки)", "8", "8"],
    ["Выход сырников", "—", "150"],
    ["Сметана 20%", "30", "30"],
    ["ВЫХОД ГОТОВОГО БЛЮДА", "—", "150/30"],
], [100 * mm, 30 * mm, 30 * mm], total_row=True))

s.append(Paragraph("4. Технологический процесс", h))
s.append(Paragraph("Творог протирают, добавляют яйца, сахар, ванильный сахар и 2/3 муки, тщательно перемешивают. "
                   "Массу формуют в виде биточков толщиной 1,5–2 см, панируют в оставшейся муке. "
                   "Обжаривают на разогретом масле с двух сторон до образования румяной корочки, "
                   "доводят до готовности в жарочном шкафу при 180–200 °C 5–7 минут.", base))

s.append(Paragraph("5. Оформление, подача и реализация", h))
s.append(Paragraph("Сырники выкладывают на подогретую тарелку, сметану подают отдельно в соуснике. "
                   "Температура подачи — не ниже 65 °C. Условия и сроки хранения — в соответствии с действующими "
                   "санитарными правилами (СанПиН 2.3/2.4.4282-26).", base))

s.append(Paragraph("6. Органолептические показатели", h))
s.append(tbl([
    ["Показатель", "Характеристика"],
    ["Внешний вид", P("Изделия правильной округлой формы, без трещин, равномерно обжаренные")],
    ["Цвет", P("Корочки — золотисто-коричневый, на разрезе — от белого до кремового")],
    ["Консистенция", P("Мягкая, однородная, без комков")],
    ["Вкус и запах", P("Свойственные жареным творожным изделиям, без посторонних привкусов и запахов")],
], [40 * mm, 120 * mm]))

s.append(Paragraph("7. Пищевая и энергетическая ценность (на 1 порцию 150/30 г, расчётная)", h))
s.append(tbl([
    ["Белки, г", "Жиры, г", "Углеводы, г", "Энерг. ценность, ккал"],
    ["24,2", "23,4", "24,5", "405"],
], [35 * mm, 35 * mm, 35 * mm, 55 * mm]))

s.append(Spacer(1, 4))
s.append(Paragraph("Ответственный за оформление ТТК ________________ / ____________", base))

SimpleDocTemplate(out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=34 * mm,
                  bottomMargin=15 * mm, title="ТТК — образец · Техкарты PRO",
                  author="Техкарты PRO").build(s, onFirstPage=page, onLaterPages=page)
print("ok", out)

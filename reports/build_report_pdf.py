from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).with_name("reproducibility_report.md")
OUTPUT = Path(__file__).with_name("reproducibility_report.pdf")


def inline(text: str) -> str:
    value = html.escape(text, quote=False)
    value = re.sub(r"\[([0-9]+)\]", r"<super>[\1]</super>", value)
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="#16766f">\1</link>', value)
    value = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
    value = re.sub(r"&lt;(https?://[^&]+)&gt;", r'<link href="\1" color="#16766f">\1</link>', value)
    return value


def parse_table(lines: list[str], styles: dict) -> Table:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append([Paragraph(inline(cell), styles["table"]) for cell in cells])
    table = Table(rows, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f1ef")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173b3b")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c8d7d5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7faf9")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("ReportTitle", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=20, leading=24, textColor=colors.HexColor("#153d3c"),
                                alignment=TA_LEFT, spaceAfter=7),
        "h2": ParagraphStyle("Section", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=13, leading=16, textColor=colors.HexColor("#176a66"),
                             spaceBefore=10, spaceAfter=5, keepWithNext=True),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica",
                                fontSize=9, leading=12, textColor=colors.HexColor("#243434"),
                                spaceAfter=6, alignment=TA_LEFT),
        "meta": ParagraphStyle("Meta", parent=base["BodyText"], fontName="Helvetica",
                                fontSize=8.5, leading=11, textColor=colors.HexColor("#455b5a"),
                                spaceAfter=2),
        "table": ParagraphStyle("TableCell", parent=base["BodyText"], fontName="Helvetica",
                                fontSize=7.1, leading=8.5, textColor=colors.HexColor("#243434")),
        "reference": ParagraphStyle("Reference", parent=base["BodyText"], fontName="Helvetica",
                                     fontSize=8, leading=10, textColor=colors.HexColor("#243434"),
                                     spaceAfter=4),
    }
    story = []
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), styles["title"]))
        elif line.startswith("## "):
            if line.startswith(("## 3. Baseline method", "## 5. Why ablate", "## 7. Measured ablation", "## 8. Debug diary")):
                story.append(PageBreak())
            story.append(Paragraph(inline(line[3:]), styles["h2"]))
        elif line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            story.append(parse_table(table_lines, styles))
            story.append(Spacer(1, 6))
            continue
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(ListItem(Paragraph(inline(lines[i].strip()[2:]), styles["body"]), leftIndent=10))
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", start="-", leftIndent=14, bulletFontSize=7))
            story.append(Spacer(1, 3))
            continue
        elif line.startswith("**") and line.endswith("**"):
            story.append(Paragraph(inline(line), styles["meta"]))
        elif line.startswith("[1]") or line.startswith("[2]"):
            story.append(Paragraph(inline(line), styles["reference"]))
        else:
            story.append(Paragraph(inline(line), styles["body"]))
        i += 1

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d2dfdd"))
        canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#607371"))
        canvas.drawString(18 * mm, 10 * mm, "FTEC5660 | TradingAgents reproducibility")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=17 * mm, bottomMargin=21 * mm,
        title="TradingAgents Reproducibility Report",
        author="FTEC5660 Project",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    build()

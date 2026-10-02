"""
build_sdd_pdf.py
Compiles SDD.md into an IEEE 1016-2009 compliant PDF using ReportLab.
"""

import os
import re
import html
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to compute total page numbers dynamically
    and draw running header/footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Suppress header and footer on cover page
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Running Header
        header_text = "CampusResQ AI — Software Design Document (IEEE Std 1016-2009)"
        self.drawString(0.5 * inch, 10.5 * inch, header_text)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(0.5 * inch, 10.42 * inch, 8.0 * inch, 10.42 * inch)

        # Running Footer
        self.setFont("Helvetica", 8)
        self.drawString(0.5 * inch, 0.42 * inch, "CAMPUS EMERGENCY SYSTEM ARCHITECTURE — RESTRICTED DISTRIBUTION")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.0 * inch, 0.42 * inch, page_str)
        self.line(0.5 * inch, 0.52 * inch, 8.0 * inch, 0.52 * inch)

        self.restoreState()


def clean_markdown_inline(text):
    """Converts inline markdown formatting to ReportLab XML tags."""
    if not text:
        return ""
    
    text = html.escape(text.strip())

    # Replace bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)

    # Replace italic: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<i>\1</i>', text)

    # Replace inline code: `code`
    text = re.sub(
        r'`(.+?)`', 
        r'<font name="Courier-Bold" color="#0F172A" backColor="#F1F5F9">&nbsp;\1&nbsp;</font>', 
        text
    )

    # Clean markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'<b>\1</b>', text)

    # Clean math notation $$...$$ or $...$
    text = re.sub(r'\$\$([^\$]+)\$\$', r'<i>\1</i>', text)
    text = re.sub(r'\$([^\$]+)\$', r'<i>\1</i>', text)
    text = text.replace('\\text{', '').replace('}', '')
    text = text.replace('\\ge', '≥').replace('\\le', '≤').replace('\\times', '×')
    text = text.replace('\\rightarrow', '→').replace('\\to', '→')

    return text


def build_sdd_pdf(md_path, pdf_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch
    )

    available_width = 7.5 * inch  # 540 pt

    # Base Styles
    styles = getSampleStyleSheet()

    # Custom Palette
    c_primary = colors.HexColor("#0F294A")
    c_secondary = colors.HexColor("#1E40AF")
    c_slate_dark = colors.HexColor("#334155")
    c_body = colors.HexColor("#1E293B")
    c_border = colors.HexColor("#CBD5E1")
    c_bg_light = colors.HexColor("#F8FAFC")
    c_code_bg = colors.HexColor("#F1F5F9")
    c_diagram_badge = colors.HexColor("#0284C7")

    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=c_primary,
        spaceAfter=4
    )

    style_subtitle = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_secondary,
        spaceAfter=12
    )

    style_meta = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_slate_dark
    )

    style_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13.5,
        leading=16.5,
        textColor=c_primary,
        spaceBefore=11,
        spaceAfter=4,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13.5,
        textColor=c_secondary,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    style_h3 = ParagraphStyle(
        'SectionH3',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.0,
        leading=12.0,
        textColor=c_slate_dark,
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=11.2,
        textColor=c_body,
        spaceAfter=3.5
    )

    style_bullet = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=11.2,
        textColor=c_body,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    style_th = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white
    )

    style_td = ParagraphStyle(
        'TD',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.2,
        textColor=c_body
    )

    style_code = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=6.2,
        leading=7.6,
        textColor=colors.HexColor("#0F172A")
    )

    style_code_header = ParagraphStyle(
        'CodeHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.0,
        leading=8.5,
        textColor=colors.HexColor("#0369A1")
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Software Design Document (SDD)", style_title))
    story.append(Paragraph("CampusResQ AI: Multi-Agent AI Campus Emergency Coordinator", style_subtitle))

    meta_content = [
        [
            Paragraph("<b>Document Version:</b> 1.0.0", style_meta),
            Paragraph("<b>Status:</b> Approved / Baseline", style_meta)
        ],
        [
            Paragraph("<b>Date:</b> September 2026", style_meta),
            Paragraph("<b>Standard:</b> IEEE Std 1016-2009 (Software Design Descriptions)", style_meta)
        ]
    ]
    meta_table = Table(meta_content, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_light),
        ('BOX', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    in_code_block = False
    code_lines = []
    code_lang = ""

    in_table = False
    table_lines = []

    idx = 0
    total_lines = len(lines)

    while idx < total_lines:
        line = lines[idx]
        stripped = line.strip()

        # Handle Code Blocks ```
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = stripped.replace("```", "").strip().lower()
                code_lines = []
            else:
                in_code_block = False
                
                # Header label for the code box
                lang_label = code_lang.upper() if code_lang else "CODE / DIAGRAM"
                if "mermaid" in code_lang:
                    badge_title = f"📐 Architectural Specification ({lang_label})"
                elif "python" in code_lang:
                    badge_title = f"🐍 Implementation Logic ({lang_label})"
                elif "json" in code_lang:
                    badge_title = f"📋 Schema Contract ({lang_label})"
                else:
                    badge_title = f"🔧 Specification ({lang_label})"

                code_flowables = [
                    Paragraph(f"<b>{badge_title}</b>", style_code_header),
                    Spacer(1, 3)
                ]

                for cl in code_lines:
                    safe_cl = html.escape(cl).replace(" ", "&nbsp;") if cl else "&nbsp;"
                    code_flowables.append(Paragraph(f"<pre>{safe_cl}</pre>", style_code))

                code_table = Table([[code_flowables]], colWidths=[available_width])
                code_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), c_code_bg),
                    ('BOX', (0,0), (-1,-1), 0.5, c_border),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ]))
                story.append(code_table)
                story.append(Spacer(1, 5))
                code_lines = []
            idx += 1
            continue

        if in_code_block:
            code_lines.append(line.rstrip('\r\n'))
            idx += 1
            continue

        # Handle Tables
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
            idx += 1
            if idx < total_lines and lines[idx].strip().startswith("|") and lines[idx].strip().endswith("|"):
                continue
            else:
                # Process table
                table_rows = []
                for tr in table_lines:
                    if re.match(r'^\|[\s\-:]+(\|[\s\-:]+)+\|$', tr):
                        continue
                    cells = [c.strip() for c in tr.strip('|').split('|')]
                    table_rows.append(cells)

                if table_rows:
                    num_cols = max(len(r) for r in table_rows)
                    normalized_rows = []
                    for r_idx, r in enumerate(table_rows):
                        while len(r) < num_cols:
                            r.append("")
                        row_paras = []
                        is_header = (r_idx == 0)
                        for c in r:
                            clean_c = clean_markdown_inline(c)
                            p = Paragraph(clean_c, style_th if is_header else style_td)
                            row_paras.append(p)
                        normalized_rows.append(row_paras)

                    # Dynamic width assignment based on column count
                    if num_cols == 2:
                        col_widths = [140, available_width - 140]
                    elif num_cols == 3:
                        col_widths = [120, 240, available_width - 360]
                    elif num_cols == 4:
                        col_widths = [110, 150, 150, available_width - 410]
                    else:
                        col_widths = [available_width / float(num_cols)] * num_cols

                    t = Table(normalized_rows, colWidths=col_widths)
                    t_style = [
                        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('BOX', (0, 0), (-1, -1), 0.5, c_border),
                        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ]
                    for r_i in range(1, len(normalized_rows)):
                        if r_i % 2 == 0:
                            t_style.append(('BACKGROUND', (0, r_i), (-1, r_i), c_bg_light))

                    t.setStyle(TableStyle(t_style))
                    story.append(t)
                    story.append(Spacer(1, 5))

                table_lines = []
                continue

        # Skip top document title lines since styled cover is already injected
        if stripped.startswith("# Software Design Document") or \
           stripped.startswith("## CampusResQ AI") or \
           stripped.startswith("**Document Version:**") or \
           stripped.startswith("**Status:**") or \
           stripped.startswith("**Date:**") or \
           stripped.startswith("**Standard:**"):
            idx += 1
            continue

        # Horizontal Rule
        if stripped in ["---", "***", "___"]:
            story.append(HRFlowable(width="100%", thickness=0.6, color=c_border, spaceBefore=5, spaceAfter=5))
            idx += 1
            continue

        # Empty Line
        if not stripped:
            idx += 1
            continue

        # Headings
        if stripped.startswith("#### "):
            h_text = clean_markdown_inline(stripped[5:])
            story.append(Paragraph(h_text, style_h3))
            idx += 1
            continue
        elif stripped.startswith("### "):
            h_text = clean_markdown_inline(stripped[4:])
            story.append(Paragraph(h_text, style_h3))
            idx += 1
            continue
        elif stripped.startswith("## "):
            h_text = clean_markdown_inline(stripped[3:])
            story.append(Spacer(1, 3))
            story.append(Paragraph(h_text, style_h1))
            idx += 1
            continue
        elif stripped.startswith("# "):
            h_text = clean_markdown_inline(stripped[2:])
            story.append(Paragraph(h_text, style_h1))
            idx += 1
            continue

        # Lists / Bullets
        if stripped.startswith("- ") or stripped.startswith("* "):
            b_text = clean_markdown_inline(stripped[2:])
            p = Paragraph(f"• &nbsp;{b_text}", style_bullet)
            story.append(p)
            idx += 1
            continue

        # Numbered lists (e.g. "1. ")
        num_match = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if num_match:
            num = num_match.group(1)
            n_text = clean_markdown_inline(num_match.group(2))
            p = Paragraph(f"<b>{num}.</b> &nbsp;{n_text}", style_bullet)
            story.append(p)
            idx += 1
            continue

        # Normal Paragraph
        para_text = clean_markdown_inline(stripped)
        story.append(Paragraph(para_text, style_body))
        idx += 1

    # Build Document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {pdf_path}")

if __name__ == "__main__":
    src_md = r"c:\Users\vinag\Desktop\campusResQAI\SDD.md"
    out_pdf = r"c:\Users\vinag\Desktop\campusResQAI\CampusResQ_AI_SDD.pdf"
    build_sdd_pdf(src_md, out_pdf)

"""
Docx Exporter for PDFMathTranslate.
Exports translated PDF content into formatted Microsoft Word (.docx) documents.
Uses standard academic formatting: Times New Roman, Justified text, Headings, and Math formulas.
"""

import os
import re
from typing import List, Dict, Any, Optional
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


class DocxExporter:
    def __init__(self, font_name: str = "Times New Roman"):
        self.font_name = font_name
        self.doc = docx.Document()
        self._setup_page_and_styles()

    def _setup_page_and_styles(self):
        # Configure A4 page margins (1 inch / 2.54 cm all sides)
        sections = self.doc.sections
        for section in sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        # Base Normal Style
        normal_style = self.doc.styles["Normal"]
        normal_font = normal_style.font
        normal_font.name = self.font_name
        normal_font.size = Pt(12)
        normal_font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

        # Set Normal rFonts in XML for non-ASCII/Vietnamese support
        rPr = normal_style.element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        rFonts.set(qn("w:ascii"), self.font_name)
        rFonts.set(qn("w:hAnsi"), self.font_name)
        rFonts.set(qn("w:cs"), self.font_name)

    def add_heading(self, text: str, level: int = 1):
        heading_sizes = {1: Pt(18), 2: Pt(14), 3: Pt(12)}
        before_spaces = {1: Pt(14), 2: Pt(10), 3: Pt(6)}
        after_spaces = {1: Pt(6), 2: Pt(4), 3: Pt(3)}

        p = self.doc.add_paragraph()
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = before_spaces.get(level, Pt(6))
        p.paragraph_format.space_after = after_spaces.get(level, Pt(4))

        run = p.add_run(text)
        run.font.name = self.font_name
        run.font.size = heading_sizes.get(level, Pt(12))
        run.font.bold = True
        if level == 3:
            run.font.italic = True
        run.font.color.rgb = RGBColor(0x11, 0x18, 0x27)

    def add_paragraph_with_math(
        self,
        text: str,
        formulas: Optional[List[str]] = None,
        is_justified: bool = True,
        is_bold: bool = False,
        is_italic: bool = False,
        font_size: float = 11.5,
    ):
        parts = re.split(r"(\{\s*v\d+\s*\})", text)
        resolved_elements = []

        for part in parts:
            if not part:
                continue
            m = re.match(r"\{\s*v(\d+)\s*\}", part)
            if m and formulas is not None:
                vid = int(m.group(1))
                if 0 <= vid < len(formulas):
                    formula_content = formulas[vid]
                    if formula_content and formula_content.strip():
                        # If bullet symbol, keep as normal text
                        if formula_content.strip() in ["•", "·", "-", "*"]:
                            resolved_elements.append((formula_content.strip(), False))
                        else:
                            resolved_elements.append((f" {formula_content.strip()} ", True))
                continue
            resolved_elements.append((part, False))

        # If nothing resolved or only whitespace, return
        full_plain = "".join([elem[0] for elem in resolved_elements]).strip()
        if not full_plain:
            return

        p = self.doc.add_paragraph()
        p_format = p.paragraph_format
        if is_justified:
            p_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        else:
            p_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

        p_format.line_spacing = 1.15
        p_format.space_after = Pt(4.0)

        for content, is_math in resolved_elements:
            if is_math:
                math_run = p.add_run(content)
                math_run.font.name = "Cambria Math"
                math_run.font.italic = True
                math_run.font.size = Pt(font_size)
            else:
                run = p.add_run(content)
                run.font.name = self.font_name
                run.font.size = Pt(font_size)
                if is_bold:
                    run.font.bold = True
                if is_italic:
                    run.font.italic = True

    def add_image(self, image_bytes: bytes, max_width_inches: float = 5.8):
        """Add a centered, properly-scaled image/diagram to the Word document."""
        try:
            import io
            from PIL import Image

            img_stream = io.BytesIO(image_bytes)
            pil_img = Image.open(img_stream)
            w_px, h_px = pil_img.size
            img_stream.seek(0)

            # Estimate inches at 150 DPI
            w_inch = w_px / 150.0
            h_inch = h_px / 150.0

            # Scale to fit A4 page margins
            if w_inch > max_width_inches:
                scale = max_width_inches / w_inch
                w_inch = max_width_inches
                h_inch = h_inch * scale

            # Ensure image doesn't exceed printable height (7.5 inches)
            if h_inch > 7.5:
                scale = 7.5 / h_inch
                h_inch = 7.5
                w_inch = w_inch * scale

            p = self.doc.add_paragraph()
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(8.0)
            p.paragraph_format.space_after = Pt(8.0)
            run = p.add_run()
            run.add_picture(img_stream, width=Inches(w_inch))
        except Exception as e:
            pass

    def add_page_break(self):
        self.doc.add_page_break()

    def save(self, output_path: str):
        self.doc.save(output_path)


def export_pages_to_docx(pages_data: List[Dict[str, Any]], output_path: str):
    exporter = DocxExporter()

    for p_idx, page in enumerate(pages_data):
        paragraphs = page.get("paragraphs", [])
        formulas = page.get("formulas", [])
        images = page.get("images", [])

        # Build unified list of page elements sorted by reading order (y_top from top to bottom)
        elements = []
        for p in paragraphs:
            elements.append({
                "type": "paragraph",
                "data": p,
                "y_top": p.get("y_top", 0.0),
            })
        for img in images:
            elements.append({
                "type": "image",
                "data": img,
                "y_top": img.get("y_top", 0.0),
            })

        # Sort by vertical position on the page (top to bottom)
        elements.sort(key=lambda item: item["y_top"])

        for elem in elements:
            if elem["type"] == "image":
                img_data = elem["data"]
                img_bytes = img_data.get("bytes")
                if img_bytes:
                    exporter.add_image(img_bytes)
                continue

            # Handle paragraph
            para = elem["data"]
            text = para.get("text", "").strip()
            if not text:
                continue

            # Replace formula markers if they are in headings
            def replace_heading_formula(match):
                vid = int(match.group(1))
                if formulas and 0 <= vid < len(formulas):
                    return formulas[vid]
                return ""

            cleaned_text = re.sub(r"\{\s*v(\d+)\s*\}", replace_heading_formula, text).strip()
            if not cleaned_text:
                continue

            size = para.get("size", 10.0)
            is_justified = para.get("is_justified", True)

            if re.match(r"^\d+\.\d+\.\d+\b", cleaned_text):
                exporter.add_heading(cleaned_text, level=3)
            elif re.match(r"^\d+\.\d+\b", cleaned_text):
                exporter.add_heading(cleaned_text, level=2)
            elif re.match(r"^(Chương|Phần|Chapter|Part)\s+[IVXLCDM\d]+", cleaned_text, re.IGNORECASE):
                exporter.add_heading(cleaned_text, level=1)
            elif size >= 16.0:
                exporter.add_heading(cleaned_text, level=1)
            elif size >= 13.0:
                exporter.add_heading(cleaned_text, level=2)
            else:
                exporter.add_paragraph_with_math(
                    text=text,
                    formulas=formulas,
                    is_justified=is_justified,
                    font_size=11.5,
                )

        if p_idx < len(pages_data) - 1:
            exporter.add_page_break()

    exporter.save(output_path)
    return output_path

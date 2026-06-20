from fpdf import FPDF
from datetime import datetime
import re


class PDFExporter:
    def __init__(self):
        pass

    def export(self, markdown_notes, output_path, title="Tutorial Notes"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        left_margin = pdf.l_margin

        # Title
        pdf.set_x(left_margin)
        pdf.set_font("Helvetica", "B", 18)
        pdf.multi_cell(0, 12, self._clean_text(title))

        # Date
        pdf.set_x(left_margin)
        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 8, datetime.now().strftime("%B %d, %Y"))
        pdf.ln(5)

        lines = markdown_notes.split("\n")

        for line in lines:
            line = line.strip()

            if not line:
                pdf.ln(3)
                continue

            pdf.set_x(left_margin)

            if line.startswith("### "):
                pdf.set_font("Helvetica", "B", 12)
                pdf.ln(2)
                pdf.set_x(left_margin)
                pdf.multi_cell(0, 7, self._clean_text(line[4:]))
                pdf.ln(1)

            elif line.startswith("## "):
                pdf.set_font("Helvetica", "B", 14)
                pdf.ln(3)
                pdf.set_x(left_margin)
                pdf.multi_cell(0, 8, self._clean_text(line[3:]))
                pdf.ln(2)

            elif line.startswith("# "):
                pdf.set_font("Helvetica", "B", 16)
                pdf.ln(4)
                pdf.set_x(left_margin)
                pdf.multi_cell(0, 9, self._clean_text(line[2:]))
                pdf.ln(2)

            elif line.startswith("- ") or line.startswith("* "):
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, "    - " + self._clean_text(line[2:]))

            elif line.startswith("```"):
                continue

            else:
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, self._clean_text(line))

        pdf.output(output_path)
        return output_path

    def _clean_text(self, text):
        """Strip markdown symbols and force text into Latin-1 safe characters"""
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # bold
        text = re.sub(r"\*(.*?)\*", r"\1", text)        # italic
        text = re.sub(r"`(.*?)`", r"\1", text)           # inline code

        # Replace common Unicode punctuation with Latin-1 safe equivalents
        replacements = {
            "\u2018": "'", "\u2019": "'",   # smart single quotes
            "\u201c": '"', "\u201d": '"',   # smart double quotes
            "\u2013": "-", "\u2014": "-",   # en dash, em dash
            "\u2026": "...",                  # ellipsis
            "\u2022": "-",                     # bullet point
            "\u20ac": "EUR",                  # euro sign
        }
        for unicode_char, replacement in replacements.items():
            text = text.replace(unicode_char, replacement)

        # Final safety net: encode to latin-1, replacing anything still unsupported
        text = text.encode('latin-1', 'replace').decode('latin-1')
        return text
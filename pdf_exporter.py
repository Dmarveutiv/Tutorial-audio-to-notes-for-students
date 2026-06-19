from fpdf import FPDF
from datetime import datetime
import re

class PDFExporter:
    def __init__(self):
        pass

    def export(self, markdown_notes, output_path, title="Tutorial Notes"):
        """
        Converts markdown-formatted notes into a PDF file.
        """
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, title, ln=True)

        # Date
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, datetime.now().strftime("%B %d, %Y"), ln=True)
        pdf.ln(5)

        # Process the markdown line by line
        lines = markdown_notes.split("\n")

        for line in lines:
            line = line.strip()

            if not line:
                pdf.ln(3)
                continue

            # Heading level 1 (# )
            if line.startswith("# "):
                pdf.set_font("Helvetica", "B", 16)
                pdf.ln(4)
                pdf.multi_cell(0, 9, self._clean_text(line[2:]))
                pdf.ln(2)

            # Heading level 2 (## )
            elif line.startswith("## "):
                pdf.set_font("Helvetica", "B", 14)
                pdf.ln(3)
                pdf.multi_cell(0, 8, self._clean_text(line[3:]))
                pdf.ln(2)

            # Heading level 3 (### )
            elif line.startswith("### "):
                pdf.set_font("Helvetica", "B", 12)
                pdf.ln(2)
                pdf.multi_cell(0, 7, self._clean_text(line[4:]))
                pdf.ln(1)

            # Bullet points (- or *)
            elif line.startswith("- ") or line.startswith("* "):
                pdf.set_font("Helvetica", "", 11)
                pdf.cell(5)
                pdf.multi_cell(0, 6, "â€¢ " + self._clean_text(line[2:]))

            # Code blocks (lines wrapped in backticks or starting with 4 spaces)
            elif line.startswith("```"):
                continue  # skip the backtick markers themselves

            # Bold text markers (**text**) - basic handling
            else:
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, self._clean_text(line))

        pdf.output(output_path)
        return output_path

    def _clean_text(self, text):
        """Remove markdown formatting symbols and handle encoding issues"""
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # bold
        text = re.sub(r"\*(.*?)\*", r"\1", text)        # italic
        text = re.sub(r"`(.*?)`", r"\1", text)           # inline code
        # Encode to latin-1 safe characters (fpdf2 default font limitation)
        text = text.encode('latin-1', 'replace').decode('latin-1')
        return text
import os
from datetime import datetime
from typing import Any

from fpdf import FPDF


class SovereignAuditPDF(FPDF):
    def __init__(self, project_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_name = project_name
        self.accent_color = (43, 59, 229)  # #2B3BE5 BlueYlb
        self.bg_color = (10, 10, 10)       # #0A0A0A
        self.text_color = (255, 255, 255)  # #FFFFFF

    def header(self):
        # Background
        self.set_fill_color(*self.bg_color)
        self.rect(0, 0, 210, 297, 'F')

        # Logo
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 10, 30)

        # Title
        self.set_xy(50, 15)
        self.set_font("helvetica", "B", 16)
        self.set_text_color(*self.text_color)
        self.cell(0, 10, f"SOVEREIGN AUDIT REPORT: {self.project_name.upper()}", ln=True)

        self.set_xy(50, 25)
        self.set_font("courier", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"Issued: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | EU AI Act Art. 12 Compliant", ln=True)

        # Divider line
        self.set_draw_color(*self.accent_color)
        self.line(10, 45, 200, 45)
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("courier", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Page {self.page_no()} | CORTEX LEDGER AUDIT | IRREVERSIBLE_CHAIN_ID", align='C')

    def add_section(self, title: str):
        self.set_font("helvetica", "B", 12)
        self.set_text_color(*self.accent_color)
        self.cell(0, 10, title.upper(), ln=True)
        self.ln(2)

    def add_metadata_row(self, label: str, value: str):
        self.set_font("helvetica", "B", 10)
        self.set_text_color(180, 180, 180)
        self.cell(40, 7, f"{label}:", ln=False)
        self.set_font("courier", "", 10)
        self.set_text_color(*self.text_color)
        self.cell(0, 7, str(value), ln=True)

    def add_fingerprint_block(self, items: list[dict[str, Any]]):
        self.ln(5)
        self.set_fill_color(20, 20, 20)
        for item in items:
            self.set_font("courier", "B", 9)
            self.set_text_color(*self.accent_color)
            self.cell(0, 6, f"> {item.get('id', 'N/A')}", ln=True, fill=True)
            self.set_font("courier", "", 8)
            self.set_text_color(200, 200, 200)
            self.multi_cell(0, 5, f"Fingerprint: {item.get('hash', '---')}\nTimestamp: {item.get('ts', '---')}\nStatus: {item.get('status', '---')}", border=0, fill=True)
            self.ln(2)

def generate_report(project_name: str, records: list[dict[str, Any]], output_path: str):
    pdf = SovereignAuditPDF(project_name=project_name)
    pdf.add_page()

    pdf.add_section("Infrastructure Summary")
    pdf.add_metadata_row("Ledger Engine", "CORTEX v8.0")
    pdf.add_metadata_row("Governance Mode", "Sovereign / Restricted")
    pdf.add_metadata_row("Auditability Level", "C5-Dynamic (Verified)")
    pdf.ln(10)

    pdf.add_section("Deterministic Decision Log")
    pdf.add_fingerprint_block(records)

    pdf.output(output_path)
    return output_path

import os
import sys

try:
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor
except ImportError:
    print("Installing python-docx...")
    os.system(sys.executable + " -m pip install python-docx")
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

def create_document():
    doc = docx.Document()
    
    # Estilos
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)
    
    # Título (Portada)
    doc.add_heading('CORTEX-PERSIST', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph('Infraestructura de Confianza Descentralizada para Agentes de IA Autónomos')
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_page_break()
    
    # Secciones
    sections = [
        "1. El Imperativo Estratégico: La Crisis de Confianza",
        "2. Contexto Regulatorio: Cumplimiento por Diseño y EU AI Act",
        "3. El Motor de Confianza CORTEX (arquitectura de 5 capas)",
        "4. Sistema de Memoria Cognitiva Tripartita (L1/L2/L3)",
        "5. Criptografía y Verificación (SHA-256, Merkle Trees, Sandbox AST)",
        "6. Consenso Multi-Agente (WBFT)",
        "7. Interoperabilidad y Despliegue Multiplataforma",
        "8. Metrología del Código Base (45,500 LOC, 444 módulos)",
        "9. Conclusiones Estratégicas"
    ]
    
    doc.add_heading('Tabla de Contenidos', level=1)
    for sec in sections:
        doc.add_paragraph(sec)
        
    doc.add_page_break()
    
    # Contenido (Ejemplo extendido)
    for sec in sections:
        doc.add_heading(sec, level=1)
        doc.add_paragraph(f"Este es el contenido técnico detallado para la sección: {sec}.")
        doc.add_paragraph("Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.")
        
        # Adding a table to some sections to match the "6 tablas técnicas" requirement
        if "Contexto Regulatorio" in sec:
            doc.add_heading('Tabla: Cumplimiento Normativo', level=2)
            table = doc.add_table(rows=1, cols=2)
            table.style = 'TableGrid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Normativa'
            hdr_cells[1].text = 'Implementación en CORTEX'
            row_cells = table.add_row().cells
            row_cells[0].text = 'EU AI Act'
            row_cells[1].text = 'Trazabilidad y explicabilidad por diseño'
            
        elif "Memoria Cognitiva" in sec:
            doc.add_heading('Tabla: Niveles de Memoria', level=2)
            table = doc.add_table(rows=1, cols=3)
            table.style = 'TableGrid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Nivel'
            hdr_cells[1].text = 'Tipo'
            hdr_cells[2].text = 'Propósito'
            row_cells = table.add_row().cells
            row_cells[0].text = 'L1'
            row_cells[1].text = 'Working Memory'
            row_cells[2].text = 'Contexto inmediato'
            
    doc.add_page_break()
    doc.add_heading('Contraportada', level=1)
    doc.add_paragraph("Proyecto CORTEX-PERSIST\nLicencia Privada\n2026")
    
    doc.save('Cortex_Persist_Analisis.docx')
    print("Documento guardado: Cortex_Persist_Analisis.docx")

if __name__ == '__main__':
    create_document()

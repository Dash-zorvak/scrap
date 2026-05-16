#!/usr/bin/env python3
"""Generate professional PDF from Markdown plan document."""

import os
import sys

# Add project src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import markdown
from weasyprint import HTML, CSS

MD_FILE = "/Users/pro/Desktop/scrapeo-social/PLAN_EJECUTIVO.md"
OUTPUT_PDF = "/Users/pro/Desktop/scrapeo-social/PLAN_EJECUTIVO.pdf"

CSS_STYLES = """
@page {
    size: A4;
    margin: 2cm;
    @bottom-right {
        content: "Página " counter(page) " de " counter(pages);
        font-size: 9pt;
        color: #666;
    }
}

body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #333;
}

h1 {
    font-size: 24pt;
    color: #1a365d;
    border-bottom: 3px solid #1a365d;
    padding-bottom: 10px;
    margin-top: 30px;
    margin-bottom: 20px;
}

h2 {
    font-size: 16pt;
    color: #2c5282;
    border-bottom: 1px solid #cbd5e0;
    padding-bottom: 5px;
    margin-top: 25px;
    margin-bottom: 15px;
}

h3 {
    font-size: 13pt;
    color: #2d3748;
    margin-top: 20px;
    margin-bottom: 10px;
    font-weight: 600;
}

p {
    margin-bottom: 10px;
    text-align: justify;
}

ul, ol {
    margin-bottom: 15px;
    padding-left: 20px;
}

li {
    margin-bottom: 5px;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 9pt;
}

th {
    background-color: #edf2f7;
    color: #1a365d;
    padding: 10px;
    text-align: left;
    font-weight: bold;
    border: 1px solid #cbd5e0;
}

td {
    padding: 8px 10px;
    border: 1px solid #cbd5e0;
}

tr:nth-child(even) {
    background-color: #f7fafc;
}

tr:nth-child(odd) {
    background-color: #ffffff;
}

blockquote {
    border-left: 4px solid #2c5282;
    background-color: #f7fafc;
    color: #2d3748;
    padding: 15px;
    margin: 20px 0;
    font-style: normal;
}

code {
    background-color: #edf2f7;
    padding: 2px 5px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 9pt;
}

pre {
    background-color: #f7fafc;
    color: #2d3748;
    border: 1px solid #cbd5e0;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 8pt;
    margin: 15px 0;
    font-family: 'Courier New', Courier, monospace;
}

code {
    background-color: #edf2f7;
    color: #2d3748;
    padding: 2px 5px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 9pt;
    border: 1px solid #cbd5e0;
}

hr {
    border: none;
    border-top: 1px solid #cbd5e0;
    margin: 30px 0;
}

.emphasis {
    font-weight: bold;
    color: #1a365d;
}

.checkbox {
    color: #2c5282;
    font-weight: bold;
}
"""

def convert_md_to_html(md_content):
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'codehilite'])
    html_body = md.convert(md_content)

    html_full = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Plan Profesional - scrapeo-social</title>
</head>
<body>
{html_body}
</body>
</html>"""

    return html_full

def generate_pdf():
    print(f"Leyendo archivo: {MD_FILE}")

    with open(MD_FILE, 'r', encoding='utf-8') as f:
        md_content = f.read()

    print("Convirtiendo Markdown a HTML...")
    html_content = convert_md_to_html(md_content)

    print("Generando PDF...")

    # Write CSS to temporary file
    css_file = "/tmp/scrapeo_style.css"
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(CSS_STYLES)

    html_doc = HTML(string=html_content)
    html_doc.write_pdf(OUTPUT_PDF, stylesheets=[CSS(filename=css_file)])

    print(f"PDF generado exitosamente: {OUTPUT_PDF}")
    return OUTPUT_PDF

if __name__ == "__main__":
    generate_pdf()
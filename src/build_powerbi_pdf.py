"""Assemble the three validated Power BI page screenshots into a PDF."""

from __future__ import annotations

import shutil
from pathlib import Path

from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = [
    ROOT / "docs" / "powerbi_overview.png",
    ROOT / "docs" / "powerbi_product_channel.png",
    ROOT / "docs" / "powerbi_supply_cash.png",
]
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT_PDF = OUTPUT_DIR / "SmartphoneOperationsAnalytics.pdf"
POWERBI_COPY = ROOT / "powerbi" / "SmartphoneOperationsAnalytics.pdf"


def main() -> None:
    missing = [str(path) for path in SCREENSHOTS if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Power BI screenshots: {missing}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    page_size = (960, 540)  # 16:9 landscape in PDF points
    pdf = canvas.Canvas(str(OUTPUT_PDF), pagesize=page_size, pageCompression=1)
    pdf.setTitle("Smartphone Operations Analytics")
    pdf.setAuthor("J1mmymm")
    pdf.setSubject("Mobile sales, inventory, capacity and cash analytics dashboard")
    for screenshot in SCREENSHOTS:
        pdf.drawImage(str(screenshot), 0, 0, width=page_size[0], height=page_size[1], preserveAspectRatio=True)
        pdf.showPage()
    pdf.save()
    shutil.copy2(OUTPUT_PDF, POWERBI_COPY)
    print(f"Built PDF: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()

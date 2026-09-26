"""PDF text/table extraction helpers (pdfplumber)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PdfDoc:
    path: str
    text: str
    pages: list[str] = field(default_factory=list)
    # Tables found per page (list of rows, each row list[str])
    tables: list[list[list[str]]] = field(default_factory=list)


def extract_pdf(path: str, max_pages: int = 80) -> PdfDoc:
    """Extract text and simple tables from a PDF. pdfplumber is imported lazily."""
    import pdfplumber  # dependency — listed in requirements

    pages: list[str] = []
    tables: list[list[list[str]]] = []
    with pdfplumber.open(path) as pdf:
        n = min(len(pdf.pages), max_pages)
        for i in range(n):
            page = pdf.pages[i]
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            pages.append(t)
            try:
                for tbl in (page.extract_tables() or []):
                    if tbl:
                        tables.append(tbl)
            except Exception:
                pass
    text = "\n".join(pages)
    return PdfDoc(path=path, text=text, pages=pages, tables=tables)

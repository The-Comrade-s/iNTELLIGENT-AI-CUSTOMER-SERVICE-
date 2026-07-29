"""
utils/ocr_service.py

Extracts text from images (receipts, invoices, screenshots, business
cards) using pytesseract + Pillow. Both are optional dependencies --
if the Tesseract binary or the Python packages aren't present, this
returns a clear error instead of crashing the upload flow.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger("ics.ocr")

try:
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore

    _OCR_AVAILABLE = True
except ImportError:  # pragma: no cover - environment-dependent
    _OCR_AVAILABLE = False


@dataclass
class OCRResult:
    success: bool
    text: str = ""
    error: str = ""


def ocr_available() -> bool:
    return _OCR_AVAILABLE


def extract_text_from_image(image_bytes: bytes) -> OCRResult:
    if not _OCR_AVAILABLE:
        return OCRResult(
            False,
            error="OCR requires 'pytesseract' + 'Pillow' and the Tesseract binary installed on the host.",
        )
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return OCRResult(True, text=text.strip())
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("OCR extraction failed")
        return OCRResult(False, error=f"OCR failed: {exc}")


def structure_receipt_text(raw_text: str) -> dict:
    """Very lightweight structuring of OCR'd receipt/invoice text into
    a few common fields using regex heuristics. Real deployments
    would use a trained document-parsing model; this keeps the
    feature usable without one."""

    import re

    total_match = re.search(r"(total|amount due)[:\s]*\$?([\d,]+\.\d{2})", raw_text, re.IGNORECASE)
    date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", raw_text)

    return {
        "total": total_match.group(2) if total_match else None,
        "date": date_match.group(1) if date_match else None,
        "raw_text": raw_text,
    }

from __future__ import annotations

from pathlib import Path

import pymupdf
from rapidocr import RapidOCR

from app.errors import import_error
from app.models import DocumentPage, DocumentParseResult


MIN_TEXT_LAYER_LENGTH = 20
OCR_SCALE = 2


class PdfDocumentService:
    def __init__(self) -> None:
        self._ocr: RapidOCR | None = None

    def parse(self, path: Path, asset_id: str, project_root: Path) -> DocumentParseResult:
        try:
            document = pymupdf.open(path)
        except (pymupdf.FileDataError, OSError) as error:
            raise import_error(
                "DocumentParseError",
                f"无法打开 PDF: {path.name}",
                "pdf_parse",
                filename=path.name,
                reason=str(error),
            ) from error

        pages: list[DocumentPage] = []
        ocr_pages: list[int] = []
        try:
            for index, page in enumerate(document):
                text = page.get_text("text").strip()
                page_number = index + 1
                needs_ocr = len(text) < MIN_TEXT_LAYER_LENGTH
                if needs_ocr:
                    ocr_pages.append(page_number)
                    text = self._extract_ocr_text(page)
                    needs_ocr = not bool(text)
                pages.append(
                    DocumentPage(
                        page_number=page_number,
                        text=text,
                        needs_ocr=needs_ocr,
                    )
                )
        except Exception as error:
            raise import_error(
                "DocumentParseError",
                f"PDF 页面解析失败: {path.name}",
                "pdf_parse",
                filename=path.name,
                reason=str(error),
            ) from error
        finally:
            document.close()

        pages_needing_ocr = [page.page_number for page in pages if page.needs_ocr]
        if len(ocr_pages) == len(pages):
            pdf_type = "scanned"
        elif ocr_pages:
            pdf_type = "mixed"
        else:
            pdf_type = "text_based"

        if not pages_needing_ocr:
            status = "parsed"
        elif len(pages_needing_ocr) == len(pages):
            status = "ocr_required"
        else:
            status = "partial"

        markdown = "\n\n".join(
            f"## 第 {page.page_number} 页\n\n{page.text}"
            for page in pages
            if page.text
        )
        documents_dir = project_root / "documents"
        base_name = f"{path.stem}-{asset_id.removeprefix('asset-')[:8]}"
        markdown_path = documents_dir / f"{base_name}.md"
        json_path = documents_dir / f"{base_name}.json"
        engine = "pymupdf+rapidocr" if ocr_pages else "pymupdf"
        result = DocumentParseResult(
            asset_id=asset_id,
            pdf_type=pdf_type,
            engine=engine,
            status=status,
            page_count=len(pages),
            ocr_pages=ocr_pages,
            pages_needing_ocr=pages_needing_ocr,
            markdown_relative_path=(
                markdown_path.relative_to(project_root).as_posix() if markdown else None
            ),
            json_relative_path=json_path.relative_to(project_root).as_posix(),
            markdown_preview=markdown[:4000],
            pages=pages,
        )
        if markdown:
            markdown_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(
            result.model_dump_json(by_alias=True, indent=2),
            encoding="utf-8",
        )
        return result

    def _extract_ocr_text(self, page: pymupdf.Page) -> str:
        if self._ocr is None:
            self._ocr = RapidOCR()
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(OCR_SCALE, OCR_SCALE),
            alpha=False,
        )
        result = self._ocr(pixmap.tobytes("png"))
        return "\n".join(result.txts or ()).strip()

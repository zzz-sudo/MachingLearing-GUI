from __future__ import annotations

import io
from pathlib import Path
import zipfile

import pymupdf
from openpyxl import Workbook
from PIL import Image, ImageDraw, ImageFont

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FONT_PATH = Path("C:/Windows/Fonts/msyh.ttc")


def build_scan_image() -> bytes:
    image = Image.new("RGB", (1240, 1754), "white")
    drawing = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT_PATH), 42)
    drawing.text((100, 140), "扫描 PDF 测试报告", fill="black", font=font)
    drawing.text((100, 240), "本页只有图像，没有 PDF 文本层。", fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=72, optimize=True)
    return buffer.getvalue()


def build_digital_pdf() -> None:
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_text(
        (72, 90),
        "数字 PDF 测试报告\n上海区域销量为 128，销售额为 286420 元。\n本页包含可直接提取的中文文本层。",
        fontname="china-s",
        fontsize=14,
        lineheight=1.5,
    )
    document.save(FIXTURE_DIR / "digital_chinese_report.pdf")
    document.close()


def build_scanned_pdf() -> None:
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=build_scan_image())
    document.save(FIXTURE_DIR / "scanned_chinese_report.pdf")
    document.close()


def build_mixed_pdf() -> None:
    document = pymupdf.open()
    text_page = document.new_page(width=595, height=842)
    text_page.insert_text(
        (72, 90),
        "混合 PDF 第一页\n本页包含可直接提取的文本层，用于验证按页路由。",
        fontname="china-s",
        fontsize=14,
        lineheight=1.5,
    )
    scan_page = document.new_page(width=595, height=842)
    scan_page.insert_image(scan_page.rect, stream=build_scan_image())
    document.save(FIXTURE_DIR / "mixed_chinese_report.pdf")
    document.close()


def build_xlsx() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "销售数据"
    worksheet.append(["日期", "销量", "是否促销"])
    worksheet.append(["2026-08-01", 32, True])
    worksheet.append(["2026-08-02", 48, False])
    workbook.save(FIXTURE_DIR / "chinese_sales.xlsx")


def build_zip() -> None:
    with zipfile.ZipFile(
        FIXTURE_DIR / "chinese_archive.zip",
        "w",
        zipfile.ZIP_DEFLATED,
    ) as output:
        output.writestr(
            "数据/区域销售.csv",
            "区域,金额\n华东,120.5\n".encode("gb18030"),
        )


if __name__ == "__main__":
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    build_digital_pdf()
    build_scanned_pdf()
    build_mixed_pdf()
    build_xlsx()
    build_zip()

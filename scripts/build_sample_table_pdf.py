"""
输入格式: 无。输出类型: PDF 文件。
脚本功能: 在项目样例目录生成一个包含中文表格的可复制文本 PDF, 用于 PDF 表格解析回归测试。
作者: Kuroneko
English comment: Generate a deterministic, license-free table PDF fixture for parser tests.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "workspace" / "default" / "source" / "文档样例" / "销售汇总表.pdf"


def find_font() -> Path:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("未找到可生成中文 PDF 的 Windows 字体")


def main() -> None:
    font_path = find_font()
    pdfmetrics.registerFont(TTFont("ProjectChinese", str(font_path)))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    styles["Title"].fontName = "ProjectChinese"
    styles["Normal"].fontName = "ProjectChinese"
    data = [
        ["区域", "产品类别", "销量", "销售额"],
        ["华东", "办公用品", "128", "286420"],
        ["华南", "技术产品", "96", "319800"],
        ["华北", "家具", "74", "158600"],
    ]
    table = Table(data, colWidths=[35 * mm, 45 * mm, 30 * mm, 40 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "ProjectChinese"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f6f64")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b7c9c4")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef5f2")]),
    ]))
    document.build([Paragraph("销售汇总表", styles["Title"]), Spacer(1, 8), Paragraph("本文件为 CC0-1.0 确定性测试数据, 用于验证表格型 PDF 的解析和导出。", styles["Normal"]), Spacer(1, 12), table])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
PDF Tools — Create, merge, split, watermark, and convert PDFs (Unicode-aware).

Usage:
    python pdf_tools.py create <output.pdf> [--title "T"] [--author "A"] < input.md
    python pdf_tools.py merge <output.pdf> <file1.pdf> <file2.pdf> [...]
    python pdf_tools.py split <input.pdf> <output_dir/> [--pages 1-3,5,7-9]
    python pdf_tools.py watermark <input.pdf> <output.pdf> --text "CONFIDENTIAL"
    python pdf_tools.py header-footer <input.pdf> <output.pdf> --header "H" --footer "F"
    python pdf_tools.py info <input.pdf>
    python pdf_tools.py to-text <input.pdf> [--output output.txt]
"""

import argparse
import json
import os
import sys
from pathlib import Path


# ── Unicode font setup ──
# Search order: Noto Sans CJK → AR PL UMing → fallback warning
_CANDIDATE_FONTS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/arphic/ukai.ttc",
]
_FONT_FAMILY = None


def _init_unicode_font(pdf):
    """Register Unicode fonts with an fpdf2 FPDF instance. Returns family_name."""
    global _FONT_FAMILY
    if _FONT_FAMILY:
        return _FONT_FAMILY

    # Find font directory
    font_dirs = [
        "/usr/share/fonts/opentype/noto",
        "/usr/share/fonts/truetype/noto",
        "/usr/share/fonts/truetype/arphic",
    ]

    regular = None
    bold = None

    for d in font_dirs:
        base = Path(d)
        if not base.exists():
            continue
        # Noto Sans CJK
        for f in base.iterdir():
            name = f.name.lower()
            if "notosanscjk" in name and "regular" in name:
                regular = str(f)
            if "notosanscjk" in name and "bold" in name:
                bold = str(f)
        # Fallback: AR PL UMing
        if not regular:
            for f in base.iterdir():
                if "uming" in name.lower() or "ukai" in name.lower():
                    regular = str(f)

    if not regular:
        print("  ⚠️  No CJK font found. Chinese characters won't render.", file=sys.stderr)
        _FONT_FAMILY = "Helvetica"
        return "Helvetica"

    family = "CJK"
    try:
        pdf.add_font(family, "", regular)
        if bold:
            pdf.add_font(family, "B", bold)
        # Also add italic aliases (use regular for italic if no italic font)
        pdf.add_font(family, "I", regular)
        pdf.add_font(family, "BI", bold if bold else regular)
        _FONT_FAMILY = family
        pdf.set_font(family)
        return family
    except Exception as e:
        print(f"  ⚠️  Font error: {e}", file=sys.stderr)
        _FONT_FAMILY = "Helvetica"
        return "Helvetica"


# ── Helper: set up a fresh FPDF with Unicode ──
def _make_pdf():
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    _init_unicode_font(pdf)
    pdf.add_page()
    return pdf


# ── Helper: safe multi_cell with font fallback ──
def _write(pdf, text, font="", size=10, style="", color=(51, 51, 51), align="L", line_h=5.5):
    """Write text with proper font handling."""
    if font:
        pdf.set_font(font, style, size)
    else:
        pdf.set_font(_FONT_FAMILY or "Helvetica", style, size)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, line_h, text, align=align)
    pdf.ln(1)


# ═══════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════

def cmd_create(args):
    """Create a PDF from Markdown/text content (Unicode-safe)."""
    content = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not content and args.file:
        content = Path(args.file).read_text(encoding='utf-8')
    if not content:
        print("❌ No content provided. Pipe text or use --file.", file=sys.stderr)
        sys.exit(1)

    pdf = _make_pdf()
    family = _FONT_FAMILY or "Helvetica"

    # ── Title page ──
    if args.title:
        _write(pdf, args.title, size=20, style="B", color=(27, 58, 92), line_h=12, align="C")
        pdf.ln(2)

    if args.author:
        _write(pdf, args.author, size=11, style="I", color=(100, 100, 100), line_h=8, align="C")
        pdf.ln(4)

    if args.title or args.author:
        pdf.set_draw_color(46, 107, 164)
        pdf.set_line_width(0.5)
        y = pdf.get_y()
        pdf.line(20, y, 190, y)
        pdf.ln(6)

    # ── Content ──
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip() if lines[i].strip() else ""

        if not line:
            pdf.ln(3)
        elif line.startswith("### "):
            _write(pdf, line[4:], size=11, style="B", color=(27, 58, 92), line_h=6)
            pdf.ln(1)
        elif line.startswith("## "):
            _write(pdf, line[3:], size=13, style="B", color=(27, 58, 92), line_h=7)
            pdf.ln(1)
        elif line.startswith("# "):
            _write(pdf, line[2:], size=16, style="B", color=(27, 58, 92), line_h=8)
            pdf.ln(2)
        elif line.startswith("- ") or line.startswith("* "):
            text = line[2:]
            pdf.set_font(family, "", 10)
            # Bullet character
            pdf.cell(8, 6, chr(8226))
            _write(pdf, text, size=10, color=(51, 51, 51))
        elif line[0].isdigit() and ". " in line[:4]:
            _write(pdf, line, size=10, color=(51, 51, 51))
        elif line in ("---", "***", "___"):
            pdf.set_draw_color(187, 187, 187)
            pdf.set_line_width(0.3)
            y = pdf.get_y()
            pdf.line(20, y, 190, y)
            pdf.ln(4)
        else:
            _write(pdf, line, size=10, color=(51, 51, 51))
        i += 1

    # ── Page numbers in footer ──
    pdf.alias_nb_pages()
    for p in range(1, pdf.page_no() + 1):
        pdf.page = p
        pdf.set_y(-15)
        pdf.set_font(family, "I", 8)
        pdf.set_text_color(150, 150, 150)
        if args.footer:
            pdf.cell(0, 10, args.footer, align="L")
        pdf.cell(0, 10, f"- {p} -", align="R")

    pdf.output(args.output)
    print(f"✅ PDF created: {args.output} ({pdf.page_no()} pages)")
    return args.output


def cmd_merge(args):
    """Merge multiple PDFs into one."""
    from pypdf import PdfWriter, PdfReader

    writer = PdfWriter()
    total_pages = 0

    for path in args.files:
        if not Path(path).exists():
            print(f"⚠️  Skipping (not found): {path}", file=sys.stderr)
            continue
        try:
            reader = PdfReader(path)
            writer.append(path)
            total_pages += len(reader.pages)
            print(f"  + {Path(path).name} ({len(reader.pages)} pages)")
        except Exception as e:
            print(f"⚠️  Error with {path}: {e}", file=sys.stderr)

    with open(args.output, "wb") as f:
        writer.write(f)

    print(f"✅ Merged PDF: {args.output} ({total_pages} pages, {len(args.files)} files)")
    return args.output


def cmd_split(args):
    """Split PDF by page ranges."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(args.input)
    total = len(reader.pages)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.pages:
        page_set = set()
        for part in args.pages.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                page_set.update(range(int(start) - 1, int(end)))
            else:
                page_set.add(int(part) - 1)
        pages = sorted(p for p in page_set if 0 <= p < total)

        writer = PdfWriter()
        for p in pages:
            writer.add_page(reader.pages[p])
        safe_range = args.pages.replace(",", "-").replace("--", "-")
        out_path = out_dir / f"extracted-{safe_range}.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        print(f"✅ Extracted {len(pages)} pages → {out_path}")
    else:
        for p in range(total):
            writer = PdfWriter()
            writer.add_page(reader.pages[p])
            out_path = out_dir / f"page-{p + 1:03d}.pdf"
            with open(out_path, "wb") as f:
                writer.write(f)
        print(f"✅ Split {total} pages into {out_dir}/")


def cmd_watermark(args):
    """Add watermark text to every page."""
    from pypdf import PdfReader, PdfWriter
    from io import BytesIO

    wm = _make_pdf()
    family = _FONT_FAMILY or "Helvetica"

    # Add watermark text (rotated, centered)
    wm.set_font(family, "B", args.size)
    wm.set_text_color(200, 200, 200)
    # Use text rotation
    with wm.rotation(45, x=297, y=420):
        wm.set_xy(0, 0)
        wm.cell(595, 842, args.text, align="C", center=True)

    watermark_pdf = BytesIO()
    wm.output(watermark_pdf)
    watermark_pdf.seek(0)

    watermark_reader = PdfReader(watermark_pdf)
    watermark_page = watermark_reader.pages[0]

    reader = PdfReader(args.input)
    writer = PdfWriter()

    for page in reader.pages:
        page.merge_page(watermark_page, over=True)
        writer.add_page(page)

    with open(args.output, "wb") as f:
        writer.write(f)

    print(f"✅ Watermarked PDF: {args.output} ({len(reader.pages)} pages)")
    return args.output


def cmd_header_footer(args):
    """Add header and/or footer to every page."""
    from pypdf import PdfReader, PdfWriter
    from io import BytesIO

    overlay = _make_pdf()
    family = _FONT_FAMILY or "Helvetica"

    overlay.set_font(family, "I", 8)
    overlay.set_text_color(150, 150, 150)
    overlay.set_draw_color(200, 200, 200)

    if args.header:
        overlay.set_xy(40, 20)
        overlay.cell(515, 10, args.header, align="C")
        overlay.line(40, 30, 555, 30)

    if args.footer:
        overlay.set_xy(40, 820)
        overlay.cell(515, 10, args.footer, align="C")
        overlay.line(40, 815, 555, 815)

    overlay_pdf = BytesIO()
    overlay.output(overlay_pdf)
    overlay_pdf.seek(0)

    overlay_reader = PdfReader(overlay_pdf)
    overlay_page = overlay_reader.pages[0]

    reader = PdfReader(args.input)
    writer = PdfWriter()

    for page in reader.pages:
        page.merge_page(overlay_page, over=True)
        writer.add_page(page)

    with open(args.output, "wb") as f:
        writer.write(f)

    print(f"✅ Header/Footer added: {args.output} ({len(reader.pages)} pages)")
    return args.output


def cmd_info(args):
    """Show PDF metadata and page info."""
    from pypdf import PdfReader

    reader = PdfReader(args.input)
    meta = reader.metadata
    info = {
        "file": str(Path(args.input).resolve()),
        "pages": len(reader.pages),
        "size_kb": Path(args.input).stat().st_size / 1024,
        "metadata": {
            "title": meta.title if meta.title else None,
            "author": meta.author if meta.author else None,
            "subject": meta.subject if meta.subject else None,
            "creator": meta.creator if meta.creator else None,
            "producer": meta.producer if meta.producer else None,
        },
        "page_sizes": [],
    }

    print(f"\n📄 PDF Info: {Path(args.input).name}")
    print(f"{'=' * 50}")
    print(f"  Pages:   {info['pages']}")
    print(f"  Size:    {info['size_kb']:.1f} KB")
    print(f"  Title:   {info['metadata']['title'] or 'N/A'}")
    print(f"  Author:  {info['metadata']['author'] or 'N/A'}")
    print(f"  Subject: {info['metadata']['subject'] or 'N/A'}")
    print(f"  Creator: {info['metadata']['creator'] or 'N/A'}")
    print(f"  Producer:{info['metadata']['producer'] or 'N/A'}")

    # Page sizes
    sizes = {}
    for page in reader.pages:
        w = round(page.mediabox.width, 0)
        h = round(page.mediabox.height, 0)
        sz = f"{w:.0f}x{h:.0f}"
        sizes[sz] = sizes.get(sz, 0) + 1

    print("\n  Page sizes:")
    for sz, count in sorted(sizes.items()):
        print(f"    {sz} pt ({count} pages)")

    if args.json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
    return info


def cmd_to_text(args):
    """Extract text from PDF using pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(args.input)
    text_parts = []
    for i, page in enumerate(reader.pages, 1):
        page_text = page.extract_text()
        if page_text:
            text_parts.append(f"--- Page {i} ---\n{page_text}")
    text = "\n\n".join(text_parts) if text_parts else "(no extractable text)"
    text = text.strip()

    if args.output:
        Path(args.output).write_text(text, encoding='utf-8')
        print(f"✅ Text extracted to: {args.output}")
    else:
        print(text)
    return text


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="PDF Tools — Unicode-aware PDF operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p = sub.add_parser("create", help="Create PDF from Markdown/text")
    p.add_argument("output", help="Output PDF path")
    p.add_argument("--title", "-t", help="Document title")
    p.add_argument("--author", "-a", help="Author name")
    p.add_argument("--footer", help="Footer text")
    p.add_argument("--file", "-f", help="Read from file instead of stdin")

    # merge
    p = sub.add_parser("merge", help="Merge multiple PDFs")
    p.add_argument("output", help="Output PDF path")
    p.add_argument("files", nargs="+", help="Input PDF files")

    # split
    p = sub.add_parser("split", help="Split PDF by page range")
    p.add_argument("input", help="Input PDF path")
    p.add_argument("output", help="Output directory")
    p.add_argument("--pages", "-p", help="Page range (e.g. 1-3,5,7-9)")

    # watermark
    p = sub.add_parser("watermark", help="Add watermark text")
    p.add_argument("input", help="Input PDF path")
    p.add_argument("output", help="Output PDF path")
    p.add_argument("--text", required=True, help="Watermark text")
    p.add_argument("--size", type=int, default=36, help="Font size")

    # header-footer
    p = sub.add_parser("header-footer", help="Add header/footer")
    p.add_argument("input", help="Input PDF path")
    p.add_argument("output", help="Output PDF path")
    p.add_argument("--header", help="Header text")
    p.add_argument("--footer", help="Footer text")

    # info
    p = sub.add_parser("info", help="Show PDF metadata")
    p.add_argument("input", help="Input PDF path")
    p.add_argument("--json", action="store_true", help="JSON output")

    # to-text
    p = sub.add_parser("to-text", help="Extract text from PDF")
    p.add_argument("input", help="Input PDF path")
    p.add_argument("--output", "-o", help="Output text file")

    args = parser.parse_args()

    cmds = {
        "create": cmd_create,
        "merge": cmd_merge,
        "split": cmd_split,
        "watermark": cmd_watermark,
        "header-footer": cmd_header_footer,
        "info": cmd_info,
        "to-text": cmd_to_text,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 字体子集化工具

用途：扫描 PDF 实际使用的字符，对嵌入的 OpenType/TrueType 字体流做子集化，
      只保留用到的字形，大幅减小文件体积，同时保留矢量文字清晰度

典型场景：PyMuPDF 生成 PDF 时用 fontbuffer 嵌入了完整的 CJK 字体（10-20MB+），
          但实际只用了少量字符。子集化后可压到 100KB-1MB 级别

依赖：PyMuPDF (fitz), fontTools
"""
import os
import shutil
import tempfile
from io import BytesIO

import fitz
from fontTools import ttLib
from fontTools import subset


def _collect_text_chars(doc):
    """收集 PDF 中所有页面实际用到的字符"""
    chars = set()
    for page in doc:
        chars.update(page.get_text())
    # 加入基础空白和控制字符，保险起见
    chars.update(" \n\r\t\u00a0")
    return "".join(sorted(chars))


def _find_embedded_font_xrefs(doc):
    """找出 PDF 中所有 OpenType/TrueType 字体流的 xref"""
    font_xrefs = []
    for xref in range(1, doc.xref_length()):
        try:
            obj_str = doc.xref_object(xref)
            if obj_str is None:
                continue
            if "/Subtype /OpenType" in obj_str or "/Subtype/TrueType" in obj_str:
                data = doc.xref_stream(xref)
                if data and len(data) > 1024:
                    font_xrefs.append((xref, len(data)))
        except Exception:
            continue
    # 优先处理大字体
    font_xrefs.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in font_xrefs]


def _subset_font_data(font_data, text, verbose=False):
    """对单个字体数据做子集化，返回子集化后的字节"""
    # 判断是否为 TrueType Collection
    is_ttc = font_data[:4] == b"ttcf"

    with tempfile.NamedTemporaryFile(suffix=".otf", delete=False) as f:
        f.write(font_data)
        tmp_path = f.name

    try:
        if is_ttc:
            # TTC 需要先取出单个字体
            ttc_font = ttLib.TTFont(tmp_path, fontNumber=0)
            ttc_font.save(tmp_path)
            ttc_font.close()

        options = subset.Options()
        # 保守设置：保留布局表，提高兼容性
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.glyph_names = True
        options.notdef_outline = True
        options.recalc_bounds = True
        options.recalc_timestamp = True
        # 保留常用表，避免某些阅读器乱码
        options.drop_tables = ["DSIG", "VORG", "hdmx", "kern"]

        font = subset.load_font(tmp_path, options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(text=text)
        subsetter.subset(font)

        buf = BytesIO()
        font.save(buf)
        return buf.getvalue()
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def subset_pdf_fonts(pdf_path, output_path=None, verbose=False):
    """
    对 PDF 中嵌入的字体做子集化

    Args:
        pdf_path: 输入 PDF 路径
        output_path: 输出路径，默认覆盖原文件
        verbose: 是否打印详细信息

    Returns:
        dict: {original_size, subset_size, ratio, fonts_subsetted, char_count}
    """
    if output_path is None:
        output_path = pdf_path

    original_size = os.path.getsize(pdf_path)
    doc = fitz.open(pdf_path)

    # 必须保存到临时文件，再替换原文件。PyMuPDF 不支持覆盖原文件的非增量保存
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(tmp_fd)

    try:
        text = _collect_text_chars(doc)
        font_xrefs = _find_embedded_font_xrefs(doc)

        fonts_subsetted = 0
        for xref in font_xrefs:
            try:
                font_data = doc.xref_stream(xref)
                if not font_data:
                    continue

                subset_data = _subset_font_data(font_data, text, verbose=verbose)
                if subset_data and len(subset_data) < len(font_data):
                    doc.update_stream(xref, subset_data)
                    fonts_subsetted += 1
                    if verbose:
                        print("子集化字体 xref={}: {} KB -> {} KB".format(
                            xref, round(len(font_data)/1024,1), round(len(subset_data)/1024,1)))
            except Exception as e:
                if verbose:
                    print("字体 xref={} 子集化失败: {}".format(xref, e))
                continue

        # 保存到临时文件，彻底清理冗余对象
        doc.save(tmp_path, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()

    # 用临时文件替换目标文件
    if os.path.exists(output_path) and os.path.samefile(tmp_path, output_path):
        pass
    else:
        shutil.move(tmp_path, output_path)

    subset_size = os.path.getsize(output_path)
    ratio = (1 - subset_size / original_size) * 100 if original_size > 0 else 0

    return {
        "original_size": original_size,
        "subset_size": subset_size,
        "ratio": ratio,
        "fonts_subsetted": fonts_subsetted,
        "char_count": len(text),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 subset_fonts.py <输入.pdf> [输出.pdf]")
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    result = subset_pdf_fonts(src, dst, verbose=True)
    print()
    print("原始大小: {:.2f} MB".format(result["original_size"] / 1024 / 1024))
    print("子集化后: {:.2f} MB".format(result["subset_size"] / 1024 / 1024))
    print("压缩率: {:.1f}%".format(result["ratio"]))
    print("子集化字体: {} 个".format(result["fonts_subsetted"]))
    print("唯一字符: {} 个".format(result["char_count"]))

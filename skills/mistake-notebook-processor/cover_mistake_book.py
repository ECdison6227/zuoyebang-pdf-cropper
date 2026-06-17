#!/usr/bin/env python3
"""
错题本净化工 —— 遮盖品牌方案（保留原文字选择、不变排版）
"""
import fitz, re, os

INPUT = "/Users/edison/Desktop/作业帮-错题本-数学-20260514.pdf"

OUT_NAME = None  # 自动按 "学科-知识点" 命名

# ── 元信息 ──
basename = os.path.splitext(os.path.basename(INPUT))[0]
date_str = "2026.05.14"
subject = "数学"
title = "圆的面积与工程问题"
for part in basename.split("-"):
    if re.match(r"^\d{8}$", part):
        date_str = f"{part[:4]}.{part[4:6]}.{part[6:]}"
    elif part in ("数学", "物理", "化学", "英语", "语文", "生物"):
        subject = part

# ── 字体 ──
with open("/System/Library/Fonts/Supplemental/Songti.ttc", "rb") as f:
    CJK_DATA = f.read()
FONT = "MySongti"
MEASURE = fitz.Font(fontbuffer=CJK_DATA)
def tw(text, fs):
    return MEASURE.text_length(text, fontsize=fs)

PW, PH = 595, 842  # A4
MP = 28

# ── 逐页遮盖 ──
doc = fitz.open(INPUT)
for page in doc:
    # 物理删除顶部品牌区 + 底部页码
    page.add_redact_annot(fitz.Rect(0, 0, PW, 68), fill=(1, 1, 1))
    page.add_redact_annot(fitz.Rect(0, PH - 47, PW, PH), fill=(1, 1, 1))
    page.apply_redactions()

    # ── 页眉 ──
    page.insert_font(fontbuffer=CJK_DATA, fontname=FONT)
    hdr = f"{date_str}  |  {title}  |  {subject}"
    x = (PW - tw(hdr, 9)) / 2
    page.insert_text(
        (x, MP + 14), hdr,
        fontname=FONT, fontsize=9, color=(0.35, 0.35, 0.35),
    )
    tip = "提示：图形题用铅笔作图 | 卡住时检查未用条件 | 适当跳题"
    x = (PW - tw(tip, 7)) / 2
    page.insert_text(
        (x, MP + 28), tip,
        fontname=FONT, fontsize=7, color=(0.65, 0.65, 0.65),
    )

    # ── 页脚 ──
    ftr = "edsionc.top  |  2014184720@qq.com"
    x = (PW - tw(ftr, 8)) / 2
    page.insert_text(
        (x, PH - MP + 4), ftr,
        fontname=FONT, fontsize=8, color=(0.55, 0.55, 0.55),
    )

if OUT_NAME:
    output = os.path.join(os.path.dirname(INPUT), OUT_NAME)
else:
    output = os.path.join(os.path.dirname(INPUT), f"{subject}-{title}.pdf")
doc.save(output, garbage=4, deflate=True)
doc.close()
print(f"✅ 已生成：{output}")

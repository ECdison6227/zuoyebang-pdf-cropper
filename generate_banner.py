#!/usr/bin/env python3
"""生成 GitHub 仓库 banner - 作业帮蓝色风格 + PDF 切割主题"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1200, 400
img = Image.new('RGB', (W, H), '#FFFFFF')
draw = ImageDraw.Draw(img)

# 作业帮蓝背景渐变 (顶部深蓝到底部浅蓝)
for y in range(H):
    r = int(30 + (y / H) * 20)
    g = int(110 + (y / H) * 30)
    b = int(220 + (y / H) * 20)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# 尝试加载字体
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Songti.ttc", 48)
    font_sub = ImageFont.truetype("/System/Library/Fonts/Supplemental/Songti.ttc", 22)
    font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Songti.ttc", 16)
    font_100 = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
except:
    font_title = ImageFont.load_default()
    font_sub = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_100 = ImageFont.load_default()

# 绘制作业帮风格 logo：蓝底圆角方块 + 白色 "100"
logo_x, logo_y = 60, 140
logo_size = 120
corner = 24
# 阴影
draw.rounded_rectangle([logo_x + 6, logo_y + 6, logo_x + logo_size + 6, logo_y + logo_size + 6],
                       radius=corner, fill=(0, 0, 0, 60))
# 蓝色方块
draw.rounded_rectangle([logo_x, logo_y, logo_x + logo_size, logo_y + logo_size],
                       radius=corner, fill='#1E88E5', outline='#FFFFFF', width=3)
# 白色 "100"
draw.text((logo_x + 14, logo_y + 34), "100", fill='#FFFFFF', font=font_100)

# 右侧标题
title_x = logo_x + logo_size + 40
draw.text((title_x, 130), "作业帮错题处理套件", fill='#FFFFFF', font=font_title)
draw.text((title_x, 195), "PDF → 讲义 → 独立错题图片", fill='#E3F2FD', font=font_sub)

# 标签
tags = "数学 · 物理 · 化学  |  Python · PyMuPDF"
draw.text((title_x, 245), tags, fill='#BBDEFB', font=font_small)

# 右侧装饰：PDF + 剪刀 + 卡片
# PDF 图标
pdf_x, pdf_y = 820, 110
draw.rectangle([pdf_x, pdf_y, pdf_x + 100, pdf_y + 140], fill='#FFFFFF', outline='#1E88E5', width=3)
draw.line([(pdf_x, pdf_y + 35), (pdf_x + 100, pdf_y + 35)], fill='#1E88E5', width=2)
for i in range(4):
    y = pdf_y + 55 + i * 22
    draw.line([(pdf_x + 12, y), (pdf_x + 88, y)], fill='#90CAF9', width=1)

# 剪刀切割线
sx = 960
draw.line([(sx, 100), (sx, 330)], fill='#FFD700', width=4)
draw.ellipse([sx - 18, 92, sx + 18, 128], outline='#FFD700', width=3)
draw.ellipse([sx - 18, 302, sx + 18, 338], outline='#FFD700', width=3)

# 切出来的题目卡片
card_x = 1010
for i in range(3):
    cx = card_x + i * 55
    cy = 110 + (i % 2) * 15
    draw.rectangle([cx, cy, cx + 45, cy + 70], fill='#FFFFFF', outline='#1E88E5', width=1)
    draw.text((cx + 4, cy + 4), f"{i+1}", fill='#1E88E5', font=font_small)
    for j in range(3):
        y = cy + 22 + j * 12
        draw.line([(cx + 4, y), (cx + 41, y)], fill='#E3F2FD', width=1)

# 底部链接
ftr = "github.com/ECdison6227/zuoyebang-pdf-cropper"
draw.text((W - 420, 350), ftr, fill='#90CAF9', font=font_small)

# 保存
output = os.path.join(os.path.dirname(__file__), 'assets', 'banner.png')
os.makedirs(os.path.dirname(output), exist_ok=True)
img.save(output, 'PNG')
print(f"✅ banner 已生成: {output}")
print(f"   尺寸: {W}x{H}")

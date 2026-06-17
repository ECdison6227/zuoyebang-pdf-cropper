#!/usr/bin/env python3
"""
作业帮题单 PDF 题目裁剪器
从作业帮错题本 PDF 中自动裁剪出每道题目并保存为独立图片，支持跨页合并。

用法:
    python3 crop_questions.py <输入PDF> [输出目录]

特性:
    - 作业帮专用题目正则: 第X题、相似题X
    - 自动识别原始作业帮 PDF vs 已处理讲义 PDF
    - 硬编码品牌删除区域 (顶部 logo 68px, 底部页码 47px)
    - 自动跳过封面页 (含"错题整理笔记"/"掌握情况")
    - 跨页题目自动合并
    - 小问序号 (1)(2)①②③ 不误切
    - 知识点自动识别 (数学/物理/化学/生物)
"""
import fitz  # pymupdf
import re
import os
import sys
from PIL import Image

# ===== 作业帮硬编码配置 =====

# A4 页面尺寸 (作业帮标准)
PAGE_WIDTH = 595
PAGE_HEIGHT = 842

# 原始作业帮 PDF 品牌区域
ZYB_TOP_BRAND = 68       # 顶部 logo 区域 (logo 在 y≈52, 第一题在 y≈80)
ZYB_BOTTOM_FOOTER = 47   # 底部页码区域 (页码在 y≈802, 图片底边在 y≈789)

# 已处理讲义 PDF 的页眉页脚区域
PROCESSED_HEADER = 68    # 页眉+提示 (y=32~58, 题目从 y≈79 开始)
PROCESSED_FOOTER = 33    # 页脚 (y=809~820, 页面底边 842)

# 渲染 DPI
DPI = 300

# ===== 题目序号正则 =====
# 作业帮专用: 第X题、相似题X (主格式)
# 通用备选: 1. 1、 一、 (兼容非作业帮 PDF)
QUESTION_PATTERN = re.compile(
    r'^(?:'
    r'第\d+题'                              # 作业帮主格式: 第1题
    r'|相似题\d+'                           # 作业帮相似题: 相似题1
    r'|\d+[\.、．]'                         # 通用: 1. 1、 1．
    r'|[一二三四五六七八九十百]+[、．\.]'    # 通用: 一、二、
    r')'
)

# 小问序号 (不应作为独立题目分割点)
SUBQUESTION_PATTERN = re.compile(
    r'^(?:'
    r'[\(（]\d+[\)）]'                      # (1) （1）
    r'|[\(（][一二三四五六七八九十]+[\)）]'  # (一) （一）
    r'|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]'                 # 带圈数字
    r')'
)

# 封面页特征 (跳过这些页面)
COVER_PATTERN = re.compile(r'错题整理笔记|掌握情况|题目掌握|整理日期')

# 页脚特征正则
FOOTER_PATTERN = re.compile(
    r'—\s*第\d+页\s*—'
    r'|第\s*\d+\s*页'
    r'|\d{4}.*年'
    r'|版权|Copyright'
    r'|Page\s*\d+'
    r'|作业帮'
    r'|edsionc\.top'
)

# ===== 知识点识别字典 (复用自作业帮错题pdf处理 skill) =====
SUBJECT_TOPICS = {
    "数学": [
        ("立体几何", [r"四棱锥", r"三棱锥", r"三棱柱", r"正三棱柱", r"四棱柱",
                      r"二面角", r"线面角", r"面面垂直", r"线面垂直", r"面面平行",
                      r"线面平行", r"异面直线", r"空间向量", r"正方体", r"长方体",
                      r"棱台", r"截面"]),
        ("解析几何", [r"椭圆", r"双曲线", r"离心率", r"圆锥曲线",
                      r"焦点", r"准线", r"渐近线"]),
        ("三角函数", [r"正弦定理", r"余弦定理", r"三角恒等", r"三角函数",
                      r"正切", r"坡度", r"坡比"]),
        ("数列", [r"等差数列", r"等比数列", r"通项公式", r"前[nN]项和"]),
        ("概率统计", [r"概率", r"期望", r"方差", r"正态分布",
                      r"排列组合", r"二项式", r"频率分布", r"回归"]),
        ("导数与应用", [r"导数", r"极值", r"单调性", r"最值"]),
        ("平面向量", [r"平面向量", r"向量的模", r"数量积"]),
        ("不等式", [r"基本不等式", r"均值不等式", r"线性规划"]),
        ("集合与逻辑", [r"充要条件", r"集合"]),
        ("相似三角形", [r"相似三角形", r"相似比", r"∽"]),
        ("全等三角形", [r"全等", r"≌"]),
        ("圆", [r"⊙", r"圆周角", r"圆心角", r"扇形", r"弧长", r"弦长"]),
        ("切线", [r"切线", r"切点"]),
        ("二次函数", [r"二次函数", r"抛物线"]),
        ("一次函数", [r"一次函数"]),
        ("角", [r"周角", r"平角", r"直角", r"钝角", r"锐角", r"∠"]),
        ("线段", [r"线段", r"射线", r"直线"]),
        ("平行线", [r"平行线", r"平行"]),
        ("菱形", [r"菱形"]),
        ("正方形", [r"正方形"]),
        ("矩形", [r"矩形"]),
        ("平行四边形", [r"平行四边形", r"▱"]),
        ("梯形", [r"梯形"]),
        ("翻折对称", [r"翻折", r"折叠"]),
    ],
    "物理": [
        ("动量与冲量", [r"动量守恒", r"动量", r"冲量", r"碰撞"]),
        ("机械能", [r"机械能守恒", r"机械能", r"动能定理", r"弹性势能",
                    r"重力势能", r"功能关系"]),
        ("圆周运动", [r"圆周运动", r"向心力", r"向心加速度", r"向心", r"角速度"]),
        ("受力分析", [r"受力分析", r"摩擦力", r"弹力", r"动摩擦因数",
                      r"斜面", r"轻绳", r"轻杆", r"轻弹簧", r"轻质弹簧"]),
        ("万有引力", [r"万有引力", r"卫星", r"轨道", r"天体", r"第一宇宙速度"]),
        ("电场", [r"电场", r"电势能", r"电势差", r"电容", r"等势面",
                  r"匀强电场", r"库仑力"]),
        ("磁场", [r"磁场", r"安培力", r"洛伦兹力", r"磁感应强度"]),
        ("电磁感应", [r"电磁感应", r"感应电动势", r"法拉第", r"楞次",
                      r"磁通量", r"自感"]),
        ("电路", [r"闭合电路", r"欧姆定律", r"电阻", r"电动势",
                  r"串联", r"并联", r"电功率"]),
        ("交变电流", [r"交变电流", r"变压器", r"远距离输电"]),
        ("热学", [r"理想气体", r"热力学", r"分子动理论", r"等温",
                  r"等压", r"等容"]),
        ("光学", [r"折射", r"全反射", r"干涉", r"衍射", r"偏振"]),
        ("近代物理", [r"光电效应", r"半衰期", r"核反应", r"质能方程",
                      r"波粒二象性"]),
    ],
    "化学": [
        ("有机化学", [r"加成反应", r"取代反应", r"加聚反应", r"酯化反应",
                      r"消去反应", r"官能团", r"同分异构", r"有机物",
                      r"乙醇", r"乙酸", r"乙醛", r"乙酸乙酯",
                      r"甲烷", r"乙烯", r"乙炔", r"苯",
                      r"聚乙烯", r"聚丁二烯", r"高分子",
                      r"球棍模型", r"空间填充", r"结构简式"]),
        ("化学平衡", [r"化学平衡", r"平衡常数", r"转化率",
                      r"勒夏特列", r"可逆反应", r"平衡移动"]),
        ("电化学", [r"原电池", r"电解池", r"电镀", r"燃料电池",
                    r"干电池", r"蓄电池", r"电极反应",
                    r"负极", r"正极", r"阳极", r"阴极"]),
        ("物质结构", [r"电子排布", r"周期律", r"周期表",
                      r"杂化", r"共价键", r"离子键", r"氢键",
                      r"分子间作用力", r"正四面体", r"空间构型"]),
        ("化学反应原理", [r"反应热", r"焓变", r"盖斯定律",
                          r"反应速率", r"活化能", r"催化剂"]),
        ("离子反应", [r"离子方程式", r"离子共存", r"水解",
                      r"电离", r"沉淀溶解平衡"]),
        ("氧化还原", [r"氧化还原", r"氧化剂", r"还原剂",
                      r"化合价", r"电子转移"]),
        ("溶液", [r"溶解度", r"饱和溶液", r"物质的量浓度",
                  r"配制", r"滴定"]),
    ],
    "生物": [
        ("遗传与变异", [r"基因", r"遗传", r"DNA", r"染色体",
                        r"基因型", r"表现型", r"杂交", r"测交"]),
        ("细胞", [r"细胞膜", r"细胞核", r"线粒体", r"叶绿体",
                  r"有丝分裂", r"减数分裂"]),
        ("光合作用", [r"光合作用", r"光反应", r"暗反应", r"叶绿素"]),
        ("呼吸作用", [r"呼吸作用", r"有氧呼吸", r"无氧呼吸"]),
        ("神经调节", [r"神经调节", r"反射", r"突触", r"神经递质"]),
        ("体液调节", [r"激素", r"甲状腺", r"胰岛素", r"血糖调节"]),
        ("免疫调节", [r"免疫", r"抗体", r"抗原", r"淋巴细胞"]),
        ("生态系统", [r"生态系统", r"食物链", r"食物网",
                      r"能量流动", r"物质循环"]),
    ],
}


def detect_pdf_type(doc):
    """
    检测 PDF 类型:
    - 'processed_lecture': 已处理讲义 (有封面页, 含"错题整理笔记")
    - 'raw_zuoyebang': 原始作业帮 PDF (含"作业帮" logo)
    - 'generic': 通用 PDF
    """
    # 检查前两页文本
    for page_num in range(min(len(doc), 2)):
        text = doc[page_num].get_text("text")
        if COVER_PATTERN.search(text):
            return 'processed_lecture'
        if '作业帮' in text:
            return 'raw_zuoyebang'
    return 'generic'


def is_cover_page(page):
    """判断是否为封面页 (含"错题整理笔记"/"掌握情况"等特征)"""
    text = page.get_text("text")
    return bool(COVER_PATTERN.search(text))


def get_clip_rect(page, pdf_type):
    """
    根据PDF类型返回有效裁剪区域 (去除页眉页脚/品牌)
    返回 fitz.Rect
    """
    rect = page.rect
    width = rect.width
    height = rect.height

    if pdf_type == 'processed_lecture':
        # 已处理讲义: 顶部页眉 68px, 底部页脚 33px
        top = PROCESSED_HEADER
        bottom = height - PROCESSED_FOOTER
    elif pdf_type == 'raw_zuoyebang':
        # 原始作业帮: 顶部 logo 68px, 底部页码 47px
        top = ZYB_TOP_BRAND
        bottom = height - ZYB_BOTTOM_FOOTER
    else:
        # 通用: 自动检测页脚
        top = 0
        bottom = height
        footer_check = fitz.Rect(0, height * 0.93, width, height)
        footer_text = page.get_text("text", clip=footer_check).strip()
        if FOOTER_PATTERN.search(footer_text):
            blocks = page.get_text("blocks", clip=footer_check)
            if blocks:
                min_y = min(b[1] for b in blocks)
                bottom = min_y - 5

    return fitz.Rect(0, top, width, bottom)


def find_question_positions(page, clip_rect):
    """
    使用 dict 模式 line/span 级别提取查找题目序号位置。
    合并同行 span 后匹配, 排除小问序号。
    返回题目序号信息列表 (含 Y 坐标)。
    """
    page_dict = page.get_text("dict", clip=clip_rect)
    questions = []

    for block in page_dict['blocks']:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            spans_text = "".join(span['text'] for span in line['spans']).strip()

            if not spans_text:
                continue

            # 必须匹配题目序号
            if not QUESTION_PATTERN.match(spans_text):
                continue

            # 排除小问序号 (双重保险)
            if SUBQUESTION_PATTERN.match(spans_text):
                continue

            y_top = line['bbox'][1]
            questions.append({
                'text': spans_text,
                'y': y_top,
                'page': page.number
            })

    questions.sort(key=lambda q: q['y'])
    return questions


def get_text_in_region(page, clip_rect, top_y, bottom_y):
    """获取指定区域内的文本 (用于判断是否有内容/题目序号)"""
    region = fitz.Rect(clip_rect.x0, top_y, clip_rect.x1, bottom_y)
    text = page.get_text("text", clip=region).strip()
    return text[:200]


def find_content_bottom(page, clip_rect, start_y, max_bottom):
    """
    扫描页面文本，找到 start_y 以下的实际内容底部。
    用于不跨页且同页无下一题的题（如最后一题），避免截取整页空白。
    """
    max_content_bottom = start_y
    page_dict = page.get_text("dict", clip=clip_rect)
    for block in page_dict.get('blocks', []):
        if 'lines' not in block:
            continue
        for line in block['lines']:
            line_top = line['bbox'][1]
            line_bottom = line['bbox'][3]
            if line_top >= start_y - 30 and line_bottom <= max_bottom:
                max_content_bottom = max(max_content_bottom, line_bottom)
    return min(max_bottom, max_content_bottom + 30)


def detect_subject(pdf_path):
    """从文件名解析学科 (数学/物理/化学/英语/语文/生物)"""
    basename = os.path.basename(pdf_path)
    for subj in ("数学", "物理", "化学", "英语", "语文", "生物"):
        if subj in basename:
            return subj
    return "数学"  # 默认数学 (作业帮错题本以数学为主)


def extract_knowledge_points(full_text, subject="数学"):
    """从全文识别知识点 (用于报告)"""
    topics = SUBJECT_TOPICS.get(subject, SUBJECT_TOPICS["数学"])
    matched = []
    seen = set()
    for name, patterns in topics:
        for pat in patterns:
            if re.search(pat, full_text):
                if name not in seen:
                    matched.append(name)
                    seen.add(name)
                break
    return matched


def crop_questions(pdf_path, output_dir):
    """主函数: 裁剪 PDF 中的每道题目

    核心策略 (v2, 同步自 Electron 软件验证过的逻辑):
    1. 全局收集所有非封面页的题目序号标记, 按 (page_index, y) 排序。
    2. 对每个题, 跨页找下一个标记, 通过"下一页首个标记离页眉距离"判断是否跨页:
       - gap < 80px: 下一页开头就是新题, 当前题不跨页。
       - gap >= 80px: 当前题内容延续到下一页, 执行部分页拼接。
    3. 对不跨页且同页无下一题的题, 扫描文本找实际内容底部;
       若内容底部接近页底 (<120px), 保守截到内容区底部, 避免图片被切。
    """
    doc = fitz.open(pdf_path)
    os.makedirs(output_dir, exist_ok=True)

    # 检测 PDF 类型
    pdf_type = detect_pdf_type(doc)
    type_label = {
        'processed_lecture': '已处理讲义',
        'raw_zuoyebang': '原始作业帮',
        'generic': '通用'
    }.get(pdf_type, '通用')

    skipped_cover_pages = []
    full_text_for_kp = ""

    # 缓存每页渲染结果, 避免重复渲染
    page_cache = {}

    def get_page_data(page_index):
        """获取指定页的数据, 返回 (page, clip_rect, full_img, scale_y)"""
        if page_index in page_cache:
            return page_cache[page_index]
        page = doc[page_index]
        clip_rect = get_clip_rect(page, pdf_type)
        mat = fitz.Matrix(DPI / 72, DPI / 72)
        full_pix = page.get_pixmap(matrix=mat, clip=clip_rect)
        full_img = Image.frombytes("RGB", [full_pix.width, full_pix.height], full_pix.samples)
        scale_y = full_img.height / clip_rect.height
        page_cache[page_index] = (page, clip_rect, full_img, scale_y)
        return page_cache[page_index]

    # 全局收集题目序号标记
    all_markers = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        if is_cover_page(page):
            skipped_cover_pages.append(page_index + 1)
            continue

        page_obj, clip_rect, _, _ = get_page_data(page_index)
        full_text_for_kp += page.get_text("text", clip=clip_rect)
        questions = find_question_positions(page_obj, clip_rect)

        for q in questions:
            all_markers.append({
                'page_index': page_index,
                'y': q['y'],
                'text': q['text'],
                'clip_rect': clip_rect,
            })

    # 按 (page_index, y) 全局排序
    all_markers.sort(key=lambda m: (m['page_index'], m['y']))

    # 跨页判断阈值 (px): 下一页首个标记离页眉的距离
    CROSS_PAGE_THRESHOLD = 80
    # 内容底部接近页底阈值 (px): 接近时保守截到页底以保护图片
    BOTTOM_MARGIN_THRESHOLD = 120

    merged_crops = []

    for idx, marker in enumerate(all_markers):
        next_marker = all_markers[idx + 1] if idx + 1 < len(all_markers) else None

        page_index = marker['page_index']
        page, clip_rect, full_img, scale_y = get_page_data(page_index)

        # 当前页 region
        top = max(clip_rect.y0, marker['y'] - 28)

        if next_marker and next_marker['page_index'] == page_index:
            # 同页有下一题: 截到下一题号上方
            bottom = max(top + 64, next_marker['y'] - 8)
            is_cross_page = False
        else:
            # 判断当前题是否跨页到下一页
            is_cross_page = False
            if next_marker and next_marker['page_index'] > page_index:
                next_page_index = next_marker['page_index']
                _, next_clip_rect, _, _ = get_page_data(next_page_index)
                gap_to_next = next_marker['y'] - next_clip_rect.y0
                is_cross_page = gap_to_next >= CROSS_PAGE_THRESHOLD

            if is_cross_page:
                # 跨页题: 当前页部分截到内容区底部
                bottom = clip_rect.y1
            else:
                # 不跨页且同页无下一题: 找实际内容底部
                content_bottom = find_content_bottom(page, clip_rect, marker['y'], clip_rect.y1)
                # 若内容底部接近页底, 保守截到页底, 避免图片/绘图被切
                bottom = clip_rect.y1 if (clip_rect.y1 - content_bottom) < BOTTOM_MARGIN_THRESHOLD else content_bottom

        # 收集当前题的所有 region
        regions = [{
            'page_index': page_index,
            'top': top,
            'bottom': bottom,
        }]

        # 跨页续页: 中间页整页 + 下一页从顶部到下一题号
        if is_cross_page and next_marker and next_marker['page_index'] > page_index:
            next_page_index = next_marker['page_index']
            _, next_clip_rect, _, _ = get_page_data(next_page_index)

            # 中间页 (完全属于当前题)
            for mid_idx in range(page_index + 1, next_page_index):
                mid_page, mid_clip_rect, _, _ = get_page_data(mid_idx)
                regions.append({
                    'page_index': mid_idx,
                    'top': mid_clip_rect.y0,
                    'bottom': mid_clip_rect.y1,
                })

            # 下一页从顶部到下一题号
            cont_bottom = max(next_clip_rect.y0 + 64, next_marker['y'] - 8)
            regions.append({
                'page_index': next_page_index,
                'top': next_clip_rect.y0,
                'bottom': cont_bottom,
            })

        # 渲染并合并当前题的所有 region
        crop_images = []
        for region in regions:
            r_page, r_clip, r_full_img, r_scale = get_page_data(region['page_index'])
            top_px = int((region['top'] - r_clip.y0) * r_scale)
            bottom_px = int((region['bottom'] - r_clip.y0) * r_scale)
            top_px = max(0, top_px)
            bottom_px = min(r_full_img.height, bottom_px)
            if bottom_px <= top_px + 5:
                continue
            crop_images.append(r_full_img.crop((0, top_px, r_full_img.width, bottom_px)))

        if not crop_images:
            continue

        merged_img = crop_images[0]
        merged_from = f"第{regions[0]['page_index'] + 1}页"
        for ri in range(1, len(crop_images)):
            img_a = merged_img
            img_b = crop_images[ri]
            max_width = max(img_a.width, img_b.width)
            new_img = Image.new('RGB', (max_width, img_a.height + img_b.height), (255, 255, 255))
            new_img.paste(img_a, (0, 0))
            x_offset = (max_width - img_b.width) // 2
            new_img.paste(img_b, (x_offset, img_a.height))
            merged_img = new_img
            merged_from += f"-第{regions[ri]['page_index'] + 1}页"

        merged_crops.append({
            'image': merged_img,
            'page_num': regions[0]['page_index'] + 1,
            'question_text': marker['text'],
            'merged': len(regions) > 1,
            'merged_from': merged_from if len(regions) > 1 else None,
        })

    # 保存结果
    for idx, crop in enumerate(merged_crops):
        filename = f"题目_{idx + 1:02d}.png"
        filepath = os.path.join(output_dir, filename)
        crop['image'].save(filepath, 'PNG')

    # 识别学科和知识点
    subject = detect_subject(pdf_path)
    knowledge_points = extract_knowledge_points(full_text_for_kp, subject)

    # 生成报告
    report_lines = [
        f"源PDF文件: {os.path.basename(pdf_path)}",
        f"PDF类型: {type_label}",
        f"学科: {subject}",
        f"总页数: {len(doc)}",
        f"跳过封面页: {skipped_cover_pages if skipped_cover_pages else '无'}",
        f"裁剪题目总数: {len(merged_crops)}",
        f"识别知识点: {'、'.join(knowledge_points) if knowledge_points else '未识别'}",
        ""
    ]
    for idx, crop in enumerate(merged_crops):
        line = f"  题目_{idx + 1:02d}.png - 第{crop['page_num']}页"
        if crop.get('question_text'):
            line += f" [{crop['question_text']}]"
        if crop.get('merged'):
            line += f" (跨页合并: {crop['merged_from']})"
        report_lines.append(line)

    report_path = os.path.join(output_dir, "裁剪报告.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    doc.close()
    return len(merged_crops), report_path, knowledge_points


# ===== 执行 =====
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 crop_questions.py <输入PDF> [输出目录]")
        sys.exit(1)

    PDF_PATH = sys.argv[1]

    if len(sys.argv) >= 3:
        OUTPUT_DIR = sys.argv[2]
    else:
        # 默认输出目录: 输入PDF同目录下的 题目图片/ 文件夹
        pdf_dir = os.path.dirname(os.path.abspath(PDF_PATH))
        pdf_name = os.path.splitext(os.path.basename(PDF_PATH))[0]
        OUTPUT_DIR = os.path.join(pdf_dir, f"{pdf_name}_题目图片")

    count, report, kps = crop_questions(PDF_PATH, OUTPUT_DIR)
    print(f"裁剪完成！共提取 {count} 道题目。")
    print(f"知识点: {'、'.join(kps) if kps else '未识别'}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"报告已保存至: {report}")

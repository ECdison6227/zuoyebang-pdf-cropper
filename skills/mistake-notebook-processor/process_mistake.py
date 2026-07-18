#!/usr/bin/env python3
"""
处理作业帮错题本 PDF —— 遮盖品牌 + 封面页 + 自动识别知识点
"""
import fitz, re, os, sys, datetime, io, tempfile
from subset_fonts import subset_pdf_fonts
from fontTools import ttLib
from fontTools import subset as font_subset

# ── 参数校验 ──
if len(sys.argv) < 2:
    print("用法: python3 process_mistake.py <输入PDF>")
    sys.exit(1)

INPUT = sys.argv[1]

if not os.path.exists(INPUT):
    print(f"错误: 文件不存在 → {INPUT}")
    sys.exit(1)

if not INPUT.lower().endswith(".pdf"):
    print(f"错误: 不是 PDF 文件 → {INPUT}")
    sys.exit(1)

basename = os.path.splitext(os.path.basename(INPUT))[0]
date_str = None
subject = None
course_topic = None
lecture_num = None

parts = basename.split("-")
for p in parts:
    # 仅把看起来像真实日期的 8 位数字当日期，避免课程主题全是数字时被误解析
    m = re.search(r"(19\d{2}|20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", p)
    if m:
        d = m.group(0)
        date_str = f"{d[:4]}.{d[4:6]}.{d[6:]}"
    elif p in ("数学", "物理", "化学", "英语", "语文", "生物"):
        subject = p
    else:
        m_lec = re.search(r"第(\d+)讲", p)
        if m_lec:
            lecture_num = m_lec.group(1)
        elif p:
            # 第一个非学科非讲次的中间部分作为课程主题
            course_topic = p

# 无日期时使用今天
date_str = date_str or datetime.date.today().strftime("%Y.%m.%d")

# ── 读完整 PDF 分析知识点 + 提取题号 ──
doc_tmp = fitz.open(INPUT)
full_text = ""
problem_titles = []
pp = re.compile(r'^(第\d+题|相似题\d+)')
for page in doc_tmp:
    txt = page.get_text("text")
    full_text += txt
    for line in txt.split("\n"):
        line = line.strip()
        if pp.match(line) and line not in problem_titles:
            problem_titles.append(line)
doc_tmp.close()

SUBJECT_TOPICS = {
    "数学": [
        ("立体几何",    [r"四棱锥", r"三棱锥", r"三棱柱", r"正三棱柱", r"四棱柱",
                         r"二面角", r"线面角", r"面面垂直", r"线面垂直", r"面面平行",
                         r"线面平行", r"异面直线", r"空间向量", r"正方体", r"长方体",
                         r"棱台", r"截面"]),
        ("解析几何",    [r"椭圆", r"双曲线", r"离心率", r"圆锥曲线",
                         r"焦点", r"准线", r"渐近线"]),
        ("三角函数",    [r"正弦定理", r"余弦定理", r"三角恒等", r"三角函数",
                         r"正切", r"坡度", r"坡比"]),
        ("数列",        [r"等差数列", r"等比数列", r"通项公式", r"前[nN]项和"]),
        ("概率统计",    [r"概率", r"期望", r"方差", r"正态分布",
                         r"排列组合", r"二项式", r"频率分布", r"回归"]),
        ("导数与应用",   [r"导数", r"极值", r"单调性", r"最值"]),
        ("平面向量",    [r"平面向量", r"向量的模", r"数量积"]),
        ("不等式",      [r"基本不等式", r"均值不等式", r"线性规划"]),
        ("集合与逻辑",   [r"充要条件", r"集合"]),
        # 初中数学
        ("相似三角形",   [r"相似三角形", r"相似比", r"∽"]),
        ("全等三角形",   [r"全等", r"≌"]),
        ("圆",         [r"⊙", r"圆周角", r"圆心角", r"扇形", r"弧长", r"弦长"]),
        ("切线",       [r"切线", r"切点"]),
        ("二次函数",    [r"二次函数", r"抛物线"]),
        ("一次函数",    [r"一次函数"]),
        ("菱形",       [r"菱形"]),
        ("正方形",     [r"正方形"]),
        ("矩形",       [r"矩形"]),
        ("平行四边形",  [r"平行四边形", r"▱"]),
        ("梯形",       [r"梯形"]),
        ("翻折对称",    [r"翻折", r"折叠"]),
    ],
    "物理": [
        ("动量与冲量",   [r"动量守恒", r"动量", r"冲量", r"碰撞"]),
        ("机械能",      [r"机械能守恒", r"机械能", r"动能定理", r"弹性势能",
                         r"重力势能", r"功能关系"]),
        ("圆周运动",    [r"圆周运动", r"向心力", r"向心加速度", r"向心", r"角速度"]),
        ("受力分析",    [r"受力分析", r"摩擦力", r"弹力", r"动摩擦因数",
                         r"斜面", r"轻绳", r"轻杆", r"轻弹簧", r"轻质弹簧"]),
        ("万有引力",    [r"万有引力", r"卫星", r"轨道", r"天体", r"第一宇宙速度"]),
        ("电场",       [r"电场", r"电势能", r"电势差", r"电容", r"等势面",
                         r"匀强电场", r"库仑力"]),
        ("磁场",       [r"磁场", r"安培力", r"洛伦兹力", r"磁感应强度"]),
        ("电磁感应",    [r"电磁感应", r"感应电动势", r"法拉第", r"楞次",
                         r"磁通量", r"自感"]),
        ("电路",       [r"闭合电路", r"欧姆定律", r"电阻", r"电动势",
                         r"串联", r"并联", r"电功率"]),
        ("交变电流",    [r"交变电流", r"变压器", r"远距离输电"]),
        ("热学",       [r"理想气体", r"热力学", r"分子动理论", r"等温",
                         r"等压", r"等容"]),
        ("光学",       [r"折射", r"全反射", r"干涉", r"衍射", r"偏振"]),
        ("近代物理",    [r"光电效应", r"半衰期", r"核反应", r"质能方程",
                         r"波粒二象性"]),
    ],
    "化学": [
        ("有机化学",    [r"加成反应", r"取代反应", r"加聚反应", r"酯化反应",
                         r"消去反应", r"官能团", r"同分异构", r"有机物",
                         r"乙醇", r"乙酸", r"乙醛", r"乙酸乙酯",
                         r"甲烷", r"乙烯", r"乙炔", r"苯",
                         r"聚乙烯", r"聚丁二烯", r"高分子",
                         r"球棍模型", r"空间填充", r"结构简式"]),
        ("化学平衡",    [r"化学平衡", r"平衡常数", r"转化率",
                         r"勒夏特列", r"可逆反应", r"平衡移动"]),
        ("电化学",      [r"原电池", r"电解池", r"电镀", r"燃料电池",
                         r"干电池", r"蓄电池", r"电极反应",
                         r"负极", r"正极", r"阳极", r"阴极"]),
        ("物质结构",    [r"电子排布", r"周期律", r"周期表",
                         r"杂化", r"共价键", r"离子键", r"氢键",
                         r"分子间作用力", r"正四面体", r"空间构型"]),
        ("化学反应原理", [r"反应热", r"焓变", r"盖斯定律",
                         r"反应速率", r"活化能", r"催化剂"]),
        ("离子反应",    [r"离子方程式", r"离子共存", r"水解",
                         r"电离", r"沉淀溶解平衡"]),
        ("氧化还原",    [r"氧化还原", r"氧化剂", r"还原剂",
                         r"化合价", r"电子转移"]),
        ("溶液",       [r"溶解度", r"饱和溶液", r"物质的量浓度",
                         r"配制", r"滴定"]),
    ],
    "生物": [
        ("遗传与变异",   [r"基因", r"遗传", r"DNA", r"染色体",
                         r"基因型", r"表现型", r"杂交", r"测交"]),
        ("细胞",       [r"细胞膜", r"细胞核", r"线粒体", r"叶绿体",
                         r"有丝分裂", r"减数分裂"]),
        ("光合作用",    [r"光合作用", r"光反应", r"暗反应", r"叶绿素"]),
        ("呼吸作用",    [r"呼吸作用", r"有氧呼吸", r"无氧呼吸"]),
        ("神经调节",    [r"神经调节", r"反射", r"突触", r"神经递质"]),
        ("体液调节",    [r"激素", r"甲状腺", r"胰岛素", r"血糖调节"]),
        ("免疫调节",    [r"免疫", r"抗体", r"抗原", r"淋巴细胞"]),
        ("生态系统",    [r"生态系统", r"食物链", r"食物网",
                         r"能量流动", r"物质循环"]),
    ],
    "英语": [
        ("阅读理解",    [r"阅读", r"reading", r"passage"]),
        ("完形填空",    [r"完形", r"cloze"]),
        ("语法",       [r"语法", r"时态", r"虚拟语气", r"定语从句"]),
    ],
}

SUBJECT_RULES = {
    "数学": ["• 图形题：先用铅笔作图辅助思考",
             "• 卡住时：优先检查题目中未使用的条件",
             "• 思维难度过大：适当跳题，回头再补",
             "• 每题预留三栏解题区：过程 / 思路 / 知识点"],
    "物理": ["• 画图：受力分析图、运动过程图必画",
             "• 卡住时：优先列出已知量和未知量",
             "• 注意单位统一（SI），检查量纲",
             "• 每题预留三栏解题区：过程 / 思路 / 知识点"],
    "化学": ["• 写方程式先检查配平和反应条件",
             "• 有机题：关注官能团决定性质",
             "• 卡住时：回忆相关物质的特征反应",
             "• 每题预留三栏解题区：过程 / 思路 / 知识点"],
    "生物": ["• 遗传题：画遗传图解辅助分析",
             "• 实验题：注意自变量和因变量",
             "• 卡住时：回归课本基本概念",
             "• 每题预留三栏解题区：过程 / 思路 / 知识点"],
}

SUBJECT_TIPS = {
    "数学": "提示：图形题用铅笔作图 | 卡住时检查未用条件 | 适当跳题",
    "物理": "提示：画受力分析图 | 注意单位统一 | 适当跳题",
    "化学": "提示：方程式检查配平 | 关注官能团和反应条件 | 适当跳题",
    "生物": "提示：遗传题画遗传图解 | 回归课本概念 | 适当跳题",
}

TOPICS = SUBJECT_TOPICS.get(subject, [])

seen = set()
matched = []
for name, patterns in TOPICS:
    for pat in patterns:
        if re.search(pat, full_text):
            if name not in seen:
                matched.append(name)
                seen.add(name)
            break

subj = subject or "未知学科"
topic_str = "、".join(matched) if matched else (course_topic or "综合")

# ── 输出文件名：学科-课程主题-第x讲.pdf ──
if course_topic and lecture_num:
    outname = f"{subj}-{course_topic}-第{lecture_num}讲.pdf"
else:
    # 兼容旧命名
    date_compact = date_str.replace(".", "")
    outname = f"{subj}讲义-{date_compact}.pdf"

# 封面用的知识点标题
if len(matched) <= 3:
    cover_topics = topic_str
else:
    cover_topics = f"{topic_str}\n（共 {len(matched)} 个知识点）"

# ── 字体（跨平台查找 CJK 宋体）──
FONT_CANDIDATES = [
    # macOS
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    # Linux (常见发行版 / CentOS)
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
    # Windows
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/msyh.ttc",
]

def _is_sc_font(name):
    """根据名称表判断是否为简体中文（SC）字体，排除繁体（TC）/日文/韩文"""
    name = name.lower()
    # 精确匹配 SC / 简体关键字（避免 'sc' 子串误命中 NotoSansCJKjp 中的 'sc'）
    sc_keywords = (
        " cjk sc", " cjk-sc",              # Noto Sans CJK SC
        "songti sc", "stsongti-sc",        # 宋体-简
        "hiraginosansgb",                   # 冬青黑体简体
        "notosanscjksc", "notosansmonocjksc",  # Noto CJK SC PostScript
        "simplified", "简体", "简",
    )
    # 排除繁体、日文、韩文、港澳
    non_sc_keywords = ("jp", "kr", "hk", "tw", "tc", "traditional", "繁")
    if any(k in name for k in non_sc_keywords):
        return False
    return any(k in name for k in sc_keywords)


def _font_weight_score(name):
    """字体权重评分：优先常规体，其次粗体，避免黑体/细体"""
    name = name.lower()
    if "regular" in name or "normal" in name or "常规" in name:
        return 100
    if "bold" in name or "粗体" in name:
        return 80
    if "light" in name or "细体" in name:
        return 40
    if "black" in name or "黑体" in name:
        return 20
    return 60


def _find_sc_font_index(buf):
    """在 TTC 中查找简体中文（SC）字体索引，优先常规体，找不到返回 0"""
    try:
        ttc = ttLib.TTFont(buf, fontNumber=0)
        num_fonts = ttc.reader.numFonts
        ttc.close()
        best_idx = 0
        best_score = -1
        for i in range(num_fonts):
            try:
                font = ttLib.TTFont(buf, fontNumber=i)
                name_table = font.get("name")
                font_score = -1
                for rec in name_table.names:
                    if rec.nameID in (1, 4, 6):  # Family / Full / PostScript
                        try:
                            name = rec.toStr()
                            if _is_sc_font(name):
                                font_score = max(font_score, _font_weight_score(name))
                        except Exception:
                            pass
                font.close()
                if font_score > best_score:
                    best_score = font_score
                    best_idx = i
            except Exception:
                pass
        return best_idx
    except Exception:
        pass
    return 0


def extract_sc_font_from_ttc(data):
    """从 TTC 字体集合中提取简体中文（SC）字体，避免嵌入繁体/日文导致乱码"""
    if data[:4] != b"ttcf":
        return data
    try:
        buf = io.BytesIO(data)
        idx = _find_sc_font_index(buf)
        ttc = ttLib.TTFont(buf, fontNumber=idx)
        out = io.BytesIO()
        ttc.save(out)
        return out.getvalue()
    except Exception:
        return data


def subset_font_data(font_data, chars):
    """对字体数据做子集化，只保留指定字符，从源头减小体积并保证嵌入完整"""
    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as f:
        f.write(font_data)
        tmp_path = f.name
    try:
        options = font_subset.Options()
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.glyph_names = True
        options.notdef_outline = True
        options.recalc_bounds = True
        options.recalc_timestamp = True
        options.drop_tables = ["DSIG", "VORG", "hdmx", "kern"]

        font = font_subset.load_font(tmp_path, options)
        subsetter = font_subset.Subsetter(options)
        subsetter.populate(text=chars)
        subsetter.subset(font)

        buf = io.BytesIO()
        font.save(buf)
        return buf.getvalue()
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# ── 收集本 PDF 会用到的所有字符，用于字体子集化 ──
all_chars = set(full_text)
all_chars.update(" \n\r\t\u00a0•|/")

# 封面固定文案
all_chars.update(f"{subj}  错题整理笔记")
all_chars.update(f"整理日期：{date_str or '未知'}")
all_chars.update("注意要点：本次包含知识点：题目掌握情况：掌握未掌握需练习")
all_chars.update("edsionc.top  |  2014184720@qq.com")

# 学科提示与规则
for rules in SUBJECT_RULES.values():
    for r in rules:
        all_chars.update(r)
for tip in SUBJECT_TIPS.values():
    all_chars.update(tip)

# 知识点、题号
for kp in matched:
    all_chars.update(kp)
for pt in problem_titles:
    all_chars.update(pt)

# 页眉页脚（hdr_title 在下方计算，但主题已知）
hdr_title = f"{matched[0]}, {matched[1]} 等" if len(matched) > 2 else (topic_str if matched else "综合")
all_chars.update(f"{date_str}  |  {hdr_title}  |  {subj}")

char_string = "".join(sorted(all_chars))

# ── 加载并子集化 CJK 字体 ──
CJK_DATA = None
CJK_PATH = None
for _path in FONT_CANDIDATES:
    if os.path.exists(_path):
        CJK_PATH = _path
        with open(_path, "rb") as f:
            raw = f.read()
            CJK_DATA = extract_sc_font_from_ttc(raw)
        break

if CJK_DATA is None:
    print("错误: 未找到 CJK 字体文件。请安装以下任一字体：")
    print("  macOS:   系统自带 Songti.ttc")
    print("  Linux:   sudo apt install fonts-noto-cjk")
    print("  Windows: 系统自带 simsun.ttc")
    sys.exit(1)

# 从源头子集化：只保留本 PDF 实际用到的字符，体积小且嵌入完整
CJK_DATA = subset_font_data(CJK_DATA, char_string)

FONT = "MySongtiSC"
MEASURE = fitz.Font(fontbuffer=CJK_DATA)
def tw(text, fs):
    return MEASURE.text_length(text, fontsize=fs)

PW, PH = 595, 842
MP = 28
CW = PW - 2 * MP

# ── 创建封面 ──
cover = fitz.open()
cp = cover.new_page()
cp.insert_font(fontbuffer=CJK_DATA, fontname=FONT)

# 标题
title_text = f"{subj}  错题整理笔记"
fs = 22
x = (PW - tw(title_text, fs)) / 2
cp.insert_text((x, 150), title_text, fontname=FONT, fontsize=fs, color=(0, 0, 0))

# 日期
fs = 11
date_line = f"整理日期：{date_str or '未知'}"
x = (PW - tw(date_line, fs)) / 2
cp.insert_text((x, 185), date_line, fontname=FONT, fontsize=fs, color=(0.4, 0.4, 0.4))

# 分隔线
cp.draw_line((MP + 20, 215), (PW - MP - 20, 215), color=(0.8, 0.8, 0.8), width=0.5)

# 注意要点
sec_y = 240
fs = 11
cp.insert_text((MP, sec_y), "注意要点：", fontname=FONT, fontsize=fs, color=(0, 0, 0))
rules = SUBJECT_RULES.get(subj, SUBJECT_RULES["数学"])
for i, r in enumerate(rules):
    cp.insert_text((MP + 10, sec_y + 22 + i * 18), r,
                   fontname=FONT, fontsize=9, color=(0.3, 0.3, 0.3))

# 分隔线
line2_y = sec_y + 100
cp.draw_line((MP + 20, line2_y), (PW - MP - 20, line2_y), color=(0.8, 0.8, 0.8), width=0.5)

# 本次知识点
kp_y = line2_y + 28
cp.insert_text((MP, kp_y), "本次包含知识点：", fontname=FONT, fontsize=11, color=(0, 0, 0))
kcol_w = CW // 2
k_y = kp_y + 22
k_max_y = k_y
for i, kp in enumerate(matched):
    cx = MP + 10 + (i % 2) * kcol_w
    cy = k_y + (i // 2) * 17
    k_max_y = max(k_max_y, cy)
    cp.insert_text((cx, cy), f"• {kp}", fontname=FONT, fontsize=8, color=(0.3, 0.3, 0.3))

# ── 题目掌握情况（固定对齐）──
check_y = k_max_y + 28
box_sz = 9
box_gap = 4
col_w = CW // 2
# 三个框相对于列起始的固定 x 偏移
box_off = [44, 80, 116]

cp.insert_text((MP, check_y), "题目掌握情况：", fontname=FONT, fontsize=11, color=(0, 0, 0))
check_y += 20

for i, pt in enumerate(problem_titles):
    col = i % 2
    row = i // 2
    cx = MP + col * col_w
    cy = check_y + row * 18
    cp.insert_text((cx + 2, cy + 7), pt, fontname=FONT, fontsize=7.5, color=(0.3, 0.3, 0.3))
    for si, label in enumerate(["掌握", "未掌握", "需练习"]):
        bx = cx + box_off[si]
        cp.draw_rect(fitz.Rect(bx, cy, bx + box_sz, cy + box_sz),
                     color=(0.5, 0.5, 0.5), width=0.5)
        cp.insert_text((bx + box_sz + 2, cy + 7), label,
                       fontname=FONT, fontsize=7, color=(0.5, 0.5, 0.5))

# 页脚
ftr = "edsionc.top  |  2014184720@qq.com"
for p in cover:
    x = (PW - tw(ftr, 8)) / 2
    p.insert_text((x, PH - MP), ftr, fontname=FONT, fontsize=8, color=(0.55, 0.55, 0.55))

# ── 处理正文页 ──
doc = fitz.open(INPUT)

for page in doc:
    pw, ph = page.rect.width, page.rect.height
    # 用 redaction 真正删除原始页眉页脚（作业帮 logo / 页码）
    page.add_redact_annot(fitz.Rect(0, 0, pw, 68), fill=(1, 1, 1))
    page.add_redact_annot(fitz.Rect(0, ph - 47, pw, ph), fill=(1, 1, 1))
    page.apply_redactions()
    page.insert_font(fontbuffer=CJK_DATA, fontname=FONT)
    hdr = f"{date_str}  |  {hdr_title}  |  {subj}"
    x = (pw - tw(hdr, 9)) / 2
    page.insert_text((x, MP + 14), hdr, fontname=FONT, fontsize=9, color=(0.35, 0.35, 0.35))
    tip = SUBJECT_TIPS.get(subj, SUBJECT_TIPS["数学"])
    x = (pw - tw(tip, 7)) / 2
    page.insert_text((x, MP + 28), tip, fontname=FONT, fontsize=7, color=(0.65, 0.65, 0.65))
    ftr = "edsionc.top  |  2014184720@qq.com"
    x = (pw - tw(ftr, 8)) / 2
    page.insert_text((x, ph - MP + 4), ftr, fontname=FONT, fontsize=8, color=(0.55, 0.55, 0.55))

# ── 封面在前 ──
cover.insert_pdf(doc)
output = os.path.join(os.path.dirname(INPUT), outname)
counter = 0
while os.path.exists(output):
    counter += 1
    base, ext = os.path.splitext(outname)
    output = os.path.join(os.path.dirname(INPUT), f"{base}({counter}){ext}")
cover.save(output, garbage=4, deflate=True)
cover.close()
doc.close()

# ── 字体子集化：从源头减小文件体积 ──
try:
    result = subset_pdf_fonts(output, verbose=False)
    print(f"✅ {os.path.basename(output)}")
    print(f"   知识点: {topic_str}")
    print(f"   体积: {result['original_size']/1024/1024:.2f} MB → {result['subset_size']/1024/1024:.2f} MB (压缩 {result['ratio']:.1f}%)")
except Exception as e:
    print(f"✅ {os.path.basename(output)}")
    print(f"   知识点: {topic_str}")
    print(f"   字体子集化失败（不影响使用）: {e}")

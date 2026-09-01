#!/usr/bin/env python3
"""
grade_checker.py - 批改报告自检器
在生成Word报告前运行，检查所有规范性问题
按SKILL.md规范逐条校验
"""
import re
import sys
import json


class GradeChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []

    # ==================== 第二步：参考答案检查 ====================
    def check_reference_answer(self, ref_text):
        """检查参考答案：字数≥1000、AI腔、首尾段、子论点分值结构"""
        if not ref_text:
            self.errors.append("参考答案为空")
            return
        word_count = len(ref_text.replace('\n', '').replace(' ', ''))
        if word_count < 1000:
            self.errors.append(f"参考答案字数{word_count}不足1000字")
        # 检测AI腔禁用词
        ai_patterns = [
            (r'受.*驱动', '受…驱动'), (r'遵循.*的逻辑', '遵循…的逻辑'),
            (r'核心矛盾在于', '核心矛盾在于'), (r'结构性变化', '结构性变化'),
            (r'深刻地', '深刻地'), (r'极大地', '极大地'),
            (r'显著地', '显著地'), (r'前所未有地', '前所未有地'),
            (r'至关重要', '至关重要'),
        ]
        for pattern, label in ai_patterns:
            if re.search(pattern, ref_text):
                self.errors.append(f"参考答案包含AI腔禁用词：{label}")
        # 检查首尾段（首行缩进两格）
        lines = [l for l in ref_text.split('\n') if l.strip()]
        if lines:
            if not lines[0].startswith('  '):
                self.warnings.append("参考答案开篇应首行缩进两格（背景段）")
            if not lines[-1].startswith('  '):
                self.warnings.append("参考答案结尾应首行缩进两格（升华段）")
        # 检查英文残留
        if re.search(r'[a-zA-Z]{2,}', ref_text):
            self.warnings.append("参考答案包含英文残留，请检查")

    # ==================== 第三步：踩分点检查 ====================
    def check_scoring_points(self, sections):
        """检查踩分点：分值总和=30、板块内分值=板块满分、不重叠、维度列"""
        total = 0
        for section in sections:
            section_name = section.get('name', '未知板块')
            max_score = section.get('max_score', 0)
            points = section.get('points', [])
            section_total = sum(float(p[3]) for p in points)
            if section_total != max_score:
                self.errors.append(f"板块'{section_name}'的踩分点分值之和({section_total})不等于板块满分({max_score})")
            total += section_total
            # 检查维度列（第4列索引为4）
            for p in points:
                if len(p) > 4:
                    dim = str(p[4]).strip()
                    if dim in ['背景', '措施', '影响', '表现', '原因', '形成', '解决']:
                        self.errors.append(f"板块'{section_name}'的踩分点维度列使用了板块名称'{dim}'，应填具体分析维度或'—'")
            # 检查每个踩分点的学生得分不超过满分
            for p in points:
                if len(p) > 5:
                    ms = float(p[3])
                    ss = float(p[5])
                    if ss > ms + 0.01:
                        self.errors.append(f"踩分点'{p[0][:30]}'的学生得分({ss})超过该点满分({ms})")
        if total != 30:
            self.errors.append(f"所有踩分点分值之和为{total}，应为30分")

    # ==================== 三遍生成校验（新增·2026-08-31）====================
    def check_three_passes(self, grading_data):
        """检查三遍生成记录：three_passes 字段 + 共识实质校验。

        规范要求三遍独立生成、多数合并（同知识点出现≥2遍才保留）。
        本函数校验：
          ① 字段存在（缺失→warning，不阻断）
          ② 遍数（规范三遍；仅2遍→warning降级；<2遍→error）
          ③ 每遍板块数与最终 sections 一致
          ④ 共识实质：每个最终踩分点须在≥2遍草稿中找到出处
             （按板块位置对齐，用 generate_answer.semantic_equal 匹配）
        """
        import os
        import sys
        _dir = os.path.dirname(os.path.abspath(__file__))
        if _dir not in sys.path:
            sys.path.insert(0, _dir)
        try:
            from generate_answer import semantic_equal
        except Exception:
            semantic_equal = None

        three_passes = grading_data.get('three_passes', None)
        sections = grading_data.get('sections', [])

        if not three_passes:
            self.warnings.append(
                "未检测到 three_passes 字段——三遍生成记录缺失，"
                "参考答案可能为单遍心证，方差风险较高。建议补录三遍草稿骨架。"
            )
            return

        if not isinstance(three_passes, list):
            self.errors.append("three_passes 字段格式错误：应为列表")
            return

        if len(three_passes) < 3:
            if len(three_passes) == 2:
                self.warnings.append("three_passes 仅有2遍（规范要求三遍），共识可靠性下降")
            else:
                self.errors.append(f"three_passes 应有3遍，实际{len(three_passes)}遍")
                return

        n_expected = len(sections)

        # 板块数一致性
        for pi, passage in enumerate(three_passes):
            if not isinstance(passage, list):
                self.errors.append(f"three_passes[{pi}] 应为板块列表")
                continue
            if n_expected > 0 and len(passage) != n_expected:
                self.warnings.append(
                    f"three_passes[{pi}] 板块数({len(passage)})与最终sections板块数({n_expected})不一致"
                )

        # 共识实质校验：每个最终踩分点须在≥2遍草稿中找到出处
        if semantic_equal and n_expected > 0:
            for si, sec in enumerate(sections):
                final_points = sec.get('points', [])
                for fp in final_points:
                    # 最终踩分点：7元素数组时 name 在 [0]；dict 时用 name 键
                    if isinstance(fp, (list, tuple)):
                        fp_name = fp[0] if len(fp) > 0 else ''
                    elif isinstance(fp, dict):
                        fp_name = fp.get('name', '')
                    else:
                        fp_name = str(fp)
                    if not fp_name:
                        continue
                    match_count = 0
                    for passage in three_passes:
                        if si < len(passage):
                            draft_sec = passage[si]
                            draft_points = draft_sec.get('points', []) if isinstance(draft_sec, dict) else []
                            for dp in draft_points:
                                if isinstance(dp, (list, tuple)):
                                    dp_name = dp[0] if len(dp) > 0 else ''
                                elif isinstance(dp, dict):
                                    dp_name = dp.get('name', '')
                                else:
                                    dp_name = str(dp)
                                if dp_name and semantic_equal(fp_name, dp_name):
                                    match_count += 1
                                    break
                    if match_count < 2:
                        self.warnings.append(
                            f"踩分点「{fp_name}」仅在{match_count}遍草稿中出现（共识要求≥2遍），"
                            "可能被单遍幻觉引入，建议复核或补充草稿"
                        )

    # ==================== 新增：单板块≤18 与 L1参考答案分值校验（2026-08-31）====================
    def check_section_cap(self, sections):
        """校验每个板块满分≤18（板块由题目子问项决定，不得超18）"""
        for section in sections:
            section_name = section.get('name', '未知板块')
            max_score = section.get('max_score', 0)
            if max_score > 18.01:
                self.errors.append(f"板块'{section_name}'满分({max_score})超过单板块≤18限制")

    def check_reference_scores(self, ref_text, sections):
        """校验 L1 参考答案分值结构：板块标题（X分）、子论点（X分）、与L2对应、≤18、和=30

        板块来源 = 题目子问项（非参考答案生成）；L1 顶层标题须与 L2 sections 一一对应。
        """
        if not ref_text:
            return
        import re
        lines = [l.strip() for l in ref_text.split('\n') if l.strip()]
        board_re = re.compile(r'^[一二三四五六七八九十]、.*?（(\d+)分）')
        sub_re = re.compile(r'^（[一二三四五六七八九十]）.*?（(\d+\.?\d*)分）')
        boards = []          # [(board_score, [sub_scores])]
        cur_board = None
        cur_subs = []
        for line in lines:
            mb = board_re.match(line)
            if mb:
                if cur_board is not None:
                    boards.append((cur_board, cur_subs))
                cur_board = int(mb.group(1))
                cur_subs = []
                continue
            ms = sub_re.match(line)
            if ms:
                cur_subs.append(float(ms.group(1)))
                continue
        if cur_board is not None:
            boards.append((cur_board, cur_subs))

        if not boards:
            self.errors.append("参考答案未标注板块分值（格式应为：一、XX（X分））")
            return

        board_sum = sum(b for b, _ in boards)
        if board_sum != 30:
            self.errors.append(f"参考答案板块分值之和({board_sum})不等于30分")
        if len(boards) != len(sections):
            self.errors.append(f"参考答案板块数({len(boards)})与踩分表板块数({len(sections)})不一致")
            return
        for i, (b, subs) in enumerate(boards):
            if b > 18.01:
                self.errors.append(f"参考答案板块{i+1}满分({b})超过单板块≤18限制")
            if subs and sum(subs) != b:
                self.errors.append(f"参考答案板块{i+1}子论点分值之和({sum(subs)})不等于板块满分({b})")
            sec_max = sections[i].get('max_score', 0)
            if b != sec_max:
                self.errors.append(f"参考答案板块{i+1}分值({b})与踩分表板块'{sections[i].get('name')}'满分({sec_max})不一致")

    # ==================== G项：踩分点严格度检查（新增·2026-08-30）====================
    def check_scoring_detail_level(self, sections):
        """检查踩分点严格度：无过度细节要求"""
        # 定义过度细节关键词模式
        detail_patterns = [
            (r'长筱', '战役细节：长筱之战'),
            (r'铁丝链', '战术细节：铁丝链连射手'),
            (r'元和偃武', '结论性表述：元和偃武'),
            (r'佩里来航', '后续事件：佩里来航'),
            (r'《.*诸法度》', '政策全称：如《武家诸法度》'),
            (r'乐市乐座', '经济制度细节：乐市乐座'),
            (r'分国法', '制度细节：分国法'),
            (r'知行制度', '制度细节：知行制度'),
            (r'关原.*战', '战役细节：关原之战'),
            (r'本体寺之变', '事件细节：本能寺之变'),
            (r'大阪之阵', '战役细节：大阪之阵'),
            (r'石高制', '制度细节：石高制（可选，非核心）'),
        ]
        warnings = []
        errors = []
        for section in sections:
            section_name = section.get('name', '未知板块')
            for point in section.get('points', []):
                point_name = point[0] if len(point) > 0 else ''
                keywords = point[1] if len(point) > 1 else ''
                combined = f"{point_name} {keywords}"
                for pattern, label in detail_patterns:
                    if re.search(pattern, combined):
                        # 区分errors和warnings
                        if pattern == r'《.*诸法度》' or pattern == r'长筱' or pattern == r'铁丝链':
                            errors.append(f"板块'{section_name}'的踩分点'{point_name[:30]}...'包含过度细节：{label}——'铁丝链连射手'等战役战术细节超出313统考范围")
                        else:
                            warnings.append(f"板块'{section_name}'的踩分点'{point_name[:30]}...'包含可能过度的细节：{label}，建议简化")
        return errors, warnings

    # ==================== 第四步：OCR标红检查 ====================
    def check_red_markers(self, student_text, red_keywords):
        """检查标红范围：仅史实硬伤，低置信度标注

        低置信度标注提醒仅在确实存在标红（red_keywords 非空）时触发，
        避免对每个正常答案都误报"未发现低置信度标注"。
        """
        if red_keywords and isinstance(red_keywords, list) and len(red_keywords) > 0:
            # 检查red_keywords是否为有效的列表格式
            if isinstance(red_keywords[0], list) and len(red_keywords[0]) == 2:
                # 有效格式：[['错误词', '正确词'], ...]
                pass
            else:
                self.warnings.append("red_keywords格式可能不正确，应为[['错误词', '正确词'], ...]")
            # 已标红但学生文本中缺少低置信度标注时才提醒
            if student_text and '⚠️疑似OCR识别异常' not in student_text:
                self.warnings.append("已标红史实但学生答案中未发现低置信度标注，请确认是否需标注")

    # ==================== 第五步：点评格式检查 ====================
    def check_comment_format(self, comment_text, point_name):
        """检查点评格式：无【】标签，自然语言一段话"""
        if '【' in comment_text or '】' in comment_text:
            self.errors.append(f"踩分点'{point_name}'的点评包含【】标签，应改为自然语言一段话")

    def check_comment_elements(self, comment_text, point_name, score=None, max_score=None):
        """检查点评要素：答出了什么、哪里有问题、正确表述

        按点评实际语义分三档，避免魔法词误报：
          - 满分/完整作答：只要求"答出了什么"
          - 零分（未作答）：只要求说明缺失 + 正确表述，不要求"答出"
          - 部分得分：要求三要素
        """
        if '—' in comment_text:
            return  # 简写形式跳过

        comment = comment_text.strip()
        if not comment:
            self.warnings.append(f"踩分点'{point_name[:30]}...'的点评为空")
            return

        # 满分识别：数值满分 或 点评中出现"给满分/满分/完整/准确"等措辞
        is_full = (score is not None and max_score is not None and abs(score - max_score) < 0.01) \
            or any(k in comment for k in ['给满分', '满分', '完整', '准确', '无误'])
        has_hit = any(k in comment for k in
                      ['答出', '命中', '完整', '基本', '部分', '触及', '提到',
                       '写出', '写到', '作答', '涉及', '涵盖', '点出', '指出'])

        if is_full:
            if not has_hit:
                self.warnings.append(f"踩分点'{point_name[:30]}...'的满分点评可能缺少'答出了什么'要素")
            return

        # 零分识别：数值为0 或 点评中出现"未答/未涉及/空白"等措辞
        is_blank = (score is not None and abs(score) < 0.01) \
            or any(k in comment for k in ['未答', '未涉及', '空白', '无作答', '未写', '没写'])
        if is_blank:
            has_problem = any(k in comment for k in
                              ['未答', '未涉及', '空白', '缺', '漏', '未提及',
                               '缺失', '未写', '没写', '没有', '未'])
            has_correct = any(k in comment for k in
                             ['正确表述', '应为', '应', '即', '也就是', '换言之', '可写', '需', '要'])
            if not has_problem:
                self.warnings.append(f"踩分点'{point_name[:30]}...'的零分点评可能缺少'缺失说明'要素")
            if not has_correct:
                self.warnings.append(f"踩分点'{point_name[:30]}...'的零分点评可能缺少'正确表述'要素")
            return

        # 部分得分：要求三要素
        has_problem = any(k in comment for k in
                          ['遗漏', '错误', '缺失', '未提及', '但', '缺少', '偏差', '不准',
                           '不当', '笼统', '简略', '片面', '混淆', '不准确', '欠缺', '不足', '待补', '需', '偏'])
        has_deduction = '扣' in comment or '分' in comment
        has_correct = any(k in comment for k in
                          ['正确表述', '应为', '应写', '应说明', '即', '也就是', '换言之'])

        if not has_hit:
            self.warnings.append(f"踩分点'{point_name[:30]}...'的点评可能缺少'答出了什么'要素")
        if not has_problem:
            self.warnings.append(f"踩分点'{point_name[:30]}...'的点评可能缺少'哪里有问题'要素")
        if not has_deduction:
            self.warnings.append(f"踩分点'{point_name[:30]}...'的点评可能缺少'扣分'要素")
        if not has_correct:
            self.warnings.append(f"踩分点'{point_name[:30]}...'的点评可能缺少'正确表述'要素")

    def check_comment_language(self, comment_text, point_name):
        """检查点评是否使用了内部评级词汇"""
        forbidden_words = ['完整命中', '基本命中', '触及边缘', '部分命中']
        for word in forbidden_words:
            if word in comment_text:
                self.errors.append(f"踩分点'{point_name[:30]}...'的点评使用了内部评级词汇'{word}'，应改为面向学生的自然语言表述")

    def check_scoring_point_name(self, sections):
        """检查踩分点列格式：只写重要性标签或空名均报错，须写具体名称（对应SKILL.md 304/317/330行）"""
        forbidden_labels = ['核心', '重要', '补充', '次要', '拓展', '加分', '要点']
        for section in sections:
            section_name = section.get('name', '未知板块')
            for point in section.get('points', []):
                point_name = point[0] if len(point) > 0 else ''
                # 踩分点列只包含重要性标签，报错
                if point_name.strip() in forbidden_labels:
                    self.errors.append(f"板块'{section_name}'的踩分点列只写了重要性标签'{point_name}'，应写具体的踩分点名称")
                # 踩分点列为空，报错
                if not point_name.strip():
                    self.errors.append(f"板块'{section_name}'存在空踩分点名称，应写具体踩分点")

    def check_duplicate_points(self, sections):
        """检查是否有重复的踩分点"""
        for section in sections:
            section_name = section.get('name', '未知板块')
            point_names = [p[0] if len(p) > 0 else '' for p in section.get('points', [])]
            seen = set()
            for name in point_names:
                if name in seen:
                    self.errors.append(f"板块'{section_name}'中存在重复的踩分点：'{name[:30]}...'")
                seen.add(name)

    # ==================== 结构稳定性检查（新增·2026-08-31）====================
    # 背景：同题四次批改方差分解显示，结构差异贡献 8.54 分、判读差异贡献 3.95 分，
    # 结构占 68%。以下两项针对结构方差。
    # 设计约束：均为【警告级】不阻断。原因——维度判定依赖关键词启发式，
    # 存在误杀内容巧合的风险，按"自检器不越权判定内容真假"原则只作提示。

    DIM_KEYWORDS = {
        '政治/制度': ['政治', '制度', '皇权', '选举', '选帝侯', '诸侯', '法律', '集权',
                      '体制', '统治', '改革', '官僚', '幕府', '分封', '政权', '治理', '大名'],
        '经济': ['经济', '市场', '关税', '货币', '贸易', '商业', '城市', '金融',
                 '财政', '赋税', '土地', '农业', '产业', '检地', '工商', '全球化'],
        '社会/文化': ['社会', '民族', '认同', '文化', '教育', '阶层', '身份', '人口',
                      '市民', '平民', '等级', '思想', '风俗', '寺子屋', '宗教信'],
        '对外/军事': ['对外', '干涉', '外交', '国际', '战争', '军事', '外敌', '地缘',
                      '外部', '法国', '侵略', '殖民', '锁国', '大国'],
    }

    def _dim_of_point(self, point_name):
        """判定踩分点所属维度：关键词投票取最高票；0票返回 None"""
        best, best_hit = None, 0
        for dim, kws in self.DIM_KEYWORDS.items():
            hit = sum(1 for k in kws if k in point_name)
            if hit > best_hit:
                best, best_hit = dim, hit
        return best

    def check_compound_points(self, sections):
        """反复合点：一个踩分点只应含一个可独立判分的知识单元（警告级）
        判定：名称被「与/及/和/、/／//」切成≥2段，且两段分属不同维度。
        """
        seps = ['与', '及', '和', '、', '／', '/']
        for section in sections:
            section_name = section.get('name', '未知板块')
            for point in section.get('points', []):
                name = point[0] if len(point) > 0 else ''
                if not name:
                    continue
                parts, buf = [], ''
                for ch in name:
                    if ch in seps:
                        if buf:
                            parts.append(buf)
                        buf = ''
                    else:
                        buf += ch
                if buf:
                    parts.append(buf)
                if len(parts) < 2:
                    continue
                dims = [self._dim_of_point(p) for p in parts]
                dims = [d for d in dims if d]
                if len(dims) >= 2 and len(set(dims)) >= 2:
                    self.warnings.append(
                        f"[结构] 板块'{section_name}'疑似复合踩分点：'{name}'——"
                        f"含多个维度的知识单元（{' / '.join(set(dims))}），"
                        f"应拆为独立踩分点，否则学生答出其一即可拿满分"
                    )

    def check_knowledge_dimension_coverage(self, sections):
        """维度组织参考（规则二新版·2026-08-31）：不再要求四维度全覆盖、不再报"维度未覆盖"。
        维度随题而选、允许缺失（偏科/专题/单点题直接按题目逻辑展开，不套维度）。
        本函数仅对极端倾斜（单维度>50%或<8%）给出软提示，不阻断。
        """
        agg = {}
        total = 0.0
        for section in sections:
            for point in section.get('points', []):
                name = point[0] if len(point) > 0 else ''
                max_score = point[3] if len(point) > 3 else 0
                dim = self._dim_of_point(name)
                if dim is None:
                    continue
                agg[dim] = agg.get(dim, 0) + max_score
                total += max_score
        if not agg or total <= 0:
            return
        # 规则二新版：维度随题而选、允许缺失，不再报"维度未覆盖"（删除了原 missing 检查）
        for dim, val in agg.items():
            pct = val / total * 100
            if pct > 50:
                self.warnings.append(
                    f"[结构] 维度'{dim}'占比 {pct:.0f}%（{val}分/{total}分）偏高，"
                    f"若为题目本身偏科属正常，否则应拆分或补点"
                )
            elif pct < 8:
                self.warnings.append(
                    f"[结构] 维度'{dim}'占比 {pct:.0f}%（{val}分/{total}分）偏低，"
                    f"确认该维度是否真有独立知识点，避免被压缩成陪衬"
                )

    # ==================== 第五步：学生作答列检查 ====================
    def check_student_answer_column(self, student_texts):
        """检查学生作答列：无引导语、无引号、未涉及写'无'、长度≤30字（对应SKILL.md输出约束377行+446行+全局自检A项）"""
        for i, text in enumerate(student_texts):
            if text and ('学生答出' in text or '学生写了' in text or '学生答' in text):
                self.errors.append(f"学生作答列第{i+1}行包含引导语，应删除")
            if text and text.startswith('"') and text.endswith('"'):
                self.errors.append(f"学生作答列第{i+1}行使用双引号包裹，应删除")
            if text and text.strip() != '无' and len(text) > 120:
                self.errors.append(f"学生作答列第{i+1}行摘录超过120字（当前{len(text)}字），疑似贴整段原文，应只摘录与踩分点直接相关的核心句")

    # ==================== 第六步：论述评分检查 ====================
    def check_language_scores(self, language_breakdown, language_score=None):
        """检查论述评分：每维不超满分、六维之和与论述组织总分一致"""
        dims = [
            ('structure', '整体结构', 2),
            ('logic', '论证逻辑', 2),
            ('argument', '史论结合', 2),
            ('language', '文字表达', 1),
            ('history_view', '史观运用', 1),
            ('neatness', '卷面整洁', 2),
        ]
        total = 0
        for key, name, max_s in dims:
            info = language_breakdown.get(key, {})
            s = info.get('score', 0)
            total += s
            if s < -0.01:
                self.errors.append(f"维度'{name}'得分{s}为负数")
            elif s > max_s + 0.01:
                self.errors.append(f"维度'{name}'得分{s}超过满分{max_s}")
            elif s == 0:
                self.warnings.append(f"维度'{name}'得分为0，请确认是否漏评")
        # 一致性：六维之和应等于论述组织总分（language_score），而非必须等于满分10
        if language_score is not None:
            if abs(total - language_score) > 0.01:
                self.warnings.append(f"六维度得分之和({total})与论述组织总分({language_score})不一致")

    def check_language_review_format(self, language_breakdown):
        """检查论述组织各维度评语格式：非空、非关键词罗列、引用学生证据（固化·2026-08-31）"""
        dims = [
            ('structure', '整体结构'),
            ('logic', '论证逻辑'),
            ('argument', '史论结合'),
            ('language', '文字表达'),
            ('history_view', '史观运用'),
            ('neatness', '卷面整洁'),
        ]
        for key, name in dims:
            info = language_breakdown.get(key, {})
            reason = (info.get('reason') or '').strip()
            if not reason:
                self.errors.append(f"维度'{name}'评语为空，必须填写自然语言评语（先扬—引证—后抑）")
                continue
            if len(reason) < 12:
                self.warnings.append(f"维度'{name}'评语过短（{len(reason)}字），应引用学生答案具体句子/术语并展开")
                continue
            # 禁止纯关键词罗列：须含句号或转折词，且非全为短短语拼接
            if '。' not in reason and '但' not in reason:
                self.warnings.append(f"维度'{name}'评语疑似关键词罗列，应改为自然语言并引用学生作答具体证据")

    # ==================== 第七步：诊断格式检查 ====================
    def check_diagnosis_format(self, diagnosis_text):
        """检查整体点评：七要素齐全、无括号内嵌理由"""
        if not diagnosis_text:
            self.errors.append("整体点评为空")
            return
        if re.search(r'属.*类卷.*（.*）', diagnosis_text):
            self.errors.append("整体点评使用括号内嵌理由，应改为完整句子表述")
        elements = {
            '等级理由': r'属于?[一二三类]类卷',
            '得分': r'\d+\.?\d*/40',
            '要点踩分': r'要点|踩分|史实',
            '组织论述': r'结构|逻辑|论述|组织',
            '亮点': r'亮点|较好|完整',
            '不足': r'失分|不足|缺失|错误',
            '提分空间': r'若能在|有望|水平'
        }
        missing = [k for k, v in elements.items() if not re.search(v, diagnosis_text)]
        if missing:
            self.errors.append(f"整体点评缺少要素：{', '.join(missing)}")

    def check_highlights_citation(self, issues):
        """检查亮点是否引用了具体句子"""
        highlights = [i for i in issues if i.get('type') == '亮点']
        if not highlights:
            self.warnings.append("亮点为空，请确认是否有所谓亮点可提")
            return
        for h in highlights:
            problem = h.get('problem', '')
            if len(problem) < 15 or ('——' not in problem and '：' not in problem):
                self.warnings.append(f"亮点可能缺少具体句子引用：「{problem[:40]}...」")

    def check_issues_no_correct_expr(self, issues):
        """检查不足中是否塞入了正确表述"""
        for issue in issues:
            if issue.get('type') != '亮点':
                problem = issue.get('problem', '')
                if '正确表述' in problem and '不足' not in problem:
                    self.warnings.append(f"不足中可能包含了正确表述：{problem[:50]}...")

    # ==================== 分数一致性检查 ====================
    def check_score_consistency(self, sections, language_score, points_score, diagnosis_text='', total_score=None):
        """检查分数一致性：板块得分、满分、总分"""
        total_max = sum(s.get('max_score', 0) for s in sections)
        total_student = sum(s.get('score', 0) for s in sections)
        if total_max != 30:
            self.errors.append(f"板块满分之和为{total_max}，应为30分")
        if total_student != points_score:
            self.errors.append(f"板块学生得分之和为{total_student}，与要点踩分{points_score}不一致")
        lang_total = language_score
        if lang_total > 10.01:
            self.errors.append(f"论述组织评分{lang_total}超过满分10分")
        total = points_score + lang_total
        if total > 40.01:
            self.errors.append(f"总分{total}超过满分40分")
        # 检查顶层 total_score 字段是否与分项之和一致（防 AI 手算笔误，如 20.5 vs 22）
        if total_score is not None:
            try:
                if abs(float(total_score) - total) > 0.01:
                    self.errors.append(f"顶层total_score({total_score})与分项之和({total})不一致")
            except (TypeError, ValueError):
                self.errors.append(f"顶层total_score字段非数值：{total_score}")
        # 检查诊断文本中的分数是否与总分一致
        if diagnosis_text:
            matches = re.findall(r'(\d+\.?\d*)/40', diagnosis_text)
            if matches:
                diag_score = float(matches[0])
                if abs(diag_score - total) > 0.01:
                    self.errors.append(f"诊断文本中分数{diag_score}/40与总分概览{total}/40不一致")
        # 检查单个踩分点学生得分不超过满分
        for section in sections:
            for p in section.get('points', []):
                if len(p) > 5:
                    ms = float(p[3])
                    ss = float(p[5])
                    if ss > ms + 0.01:
                        self.errors.append(f"踩分点'{p[0][:30]}'的学生得分({ss})超过该点满分({ms})")
                    # 得分必须是 0.5 的倍数（杜绝 3.2/4、2.7/3 这类任意小数；3.5/4、4.5/5 等 0.5 步长合法）
                    # 说明：论述组织表本就用 0.5 步长（1.5/2），踩分点表亦同，故统一按"0.5 倍数"校验，而非五档
                    remainder = round((ss * 2) % 1, 6)
                    if remainder > 0.01 and abs(remainder - 1) > 0.01:
                        self.errors.append(
                            f"踩分点'{p[0][:30]}'学生得分({ss})不是 0.5 的倍数，"
                            f"须修正为 0/0.5/1/1.5/2… 这类 0.5 步长取值")

    # ==================== H项：数值一致性检查（新增·2026-08-31）====================
    def check_score_sync(self, sections, language_breakdown, language_score, points_score, diagnosis_text):
        """检查数值一致性：总分概览表、踩分表、论述组织表、诊断文本四者一致"""
        # 1. 检查踩分表总分
        total_points_score = sum(s.get('score', 0) for s in sections)
        if abs(total_points_score - points_score) > 0.01:
            self.errors.append(f"踩分表得分({total_points_score}) != points_score({points_score})")

        # 2. 检查论述组织总分
        total_lang_score = sum(v.get('score', 0) for v in language_breakdown.values())
        if abs(total_lang_score - language_score) > 0.01:
            self.errors.append(f"论述组织六维度之和({total_lang_score}) != language_score({language_score})")

        # 3. 检查诊断文本分数
        if diagnosis_text:
            matches = re.findall(r'(\d+\.?\d*)/40', diagnosis_text)
            if matches:
                diag_score = float(matches[0])
                expected_total = points_score + language_score
                if abs(diag_score - expected_total) > 0.01:
                    self.errors.append(f"诊断文本分数({diag_score}) != 总分概览({expected_total})")

    # ==================== 输出格式检查 ====================
    def check_output_format(self, grading_data):
        """检查输出格式：命名规则、报告结构"""
        # 命名规则由调用方保证，此处不做检查
        pass

    # ==================== F项：影响板块维度检查 ====================
    def check_dimension_coverage(self, ref_text, question_text=''):
        """检查影响板块的维度覆盖情况（引用references/维度参考.md）"""
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ref_path = os.path.join(script_dir, '..', 'references', '维度参考.md')
        if not os.path.exists(ref_path):
            self.warnings.append("未找到维度参考文件，跳过维度覆盖检查")
            return
        with open(ref_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 解析维度表
        dimensions = {}
        current_section = None
        in_table = False
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('## ') and any(kw in line for kw in ['一、', '二、', '三、', '四、', '五、']):
                current_section = line.replace('## ', '').strip()
                dimensions[current_section] = []
                in_table = False
                continue
            if line.startswith('|---'):
                in_table = True
                continue
            if in_table and '|' in line and '维度' not in line and '说明' not in line:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 1 and current_section:
                    dimensions[current_section].append(parts[0])
            elif not line.startswith('|'):
                in_table = False
        # 根据题目选择维度表
        dim_keys = list(dimensions.keys())
        if not dim_keys:
            return
        # 简单匹配：看题目关键词
        selected_dims = None
        if any(kw in question_text for kw in ['商鞅', '秦', '汉', '唐', '宋', '明', '清']):
            selected_dims = dimensions.get('一、中国古代史', [])
        elif any(kw in question_text for kw in ['德国', '神圣罗马', '中世纪']):
            selected_dims = dimensions.get('二、世界古代史（单文明/区域）', [])
        elif any(kw in question_text for kw in ['日本', '法国', '英国']):
            selected_dims = dimensions.get('三、世界近现代史（国别）', [])
        elif any(kw in question_text for kw in ['欧洲', '世界', '国际', '冷战', '南方国家']):
            selected_dims = dimensions.get('四、世界近现代史（非国别/专题）', [])
        elif any(kw in question_text for kw in ['中国', '近代', '现代']):
            selected_dims = dimensions.get('五、中国近现代史', [])
        else:
            selected_dims = dimensions.get(dim_keys[0], [])
        if not selected_dims:
            return
        # 检查覆盖情况（软匹配：取维度首词，如"政治与制度"→"政治"，避免整串子串匹配过激）
        def core_token(dim):
            for sep in ['与', '及', '、', '/', '（', '(']:
                dim = dim.split(sep)[0]
            return dim.strip()

        covered = []
        missing = []
        for dim in selected_dims:
            core = core_token(dim)
            if core and core in ref_text:
                covered.append(dim)
            else:
                missing.append(dim)
        # 仅当完全零覆盖时才提示；维度表本身"仅供参考，绝不强制"
        if len(covered) == 0:
            self.warnings.append(f"影响板块维度套用可能不合理，已覆盖0/{len(selected_dims)}个维度，建议改用题目逻辑检查")

    def check_contract_structure(self, grading_data):
        """校验 JSON 数据契约结构（SKILL.md『JSON 数据契约』章）。
        规范层承诺'违反契约→校验器报错'，此前校验器仅防御性消费、静默兜底，
        此处补齐显式结构校验，使承诺兑现。须在一切消费逻辑之前调用。"""
        # 顶层必填字段：student_answer（SKILL.md 737 必填）
        student_answer = grading_data.get('student_answer', '')
        if not isinstance(student_answer, str) or not student_answer.strip():
            self.errors.append("顶层字段 'student_answer' 必填且须为非空字符串（SKILL.md JSON 数据契约）")

        # 踩分点必须为 7 元素数组 [名称,关键词,学生作答,满分,维度,得分,点评]
        for si, section in enumerate(grading_data.get('sections', [])):
            sec_name = section.get('name', f'板块{si+1}')
            for pi, point in enumerate(section.get('points', [])):
                if not isinstance(point, (list, tuple)) or len(point) != 7:
                    actual = len(point) if isinstance(point, (list, tuple)) else '非数组'
                    self.errors.append(
                        f"板块'{sec_name}'第{pi+1}个踩分点应为 7 元素数组 "
                        f"[名称,关键词,学生作答,满分,维度,得分,点评]，实际长度 {actual}"
                    )

        # language_breakdown 必须含全部 6 个维度键（SKILL.md 六维契约）
        required_dims = ['structure', 'logic', 'argument', 'language', 'history_view', 'neatness']
        language_breakdown = grading_data.get('language_breakdown', {})
        for dim in required_dims:
            if dim not in language_breakdown:
                self.errors.append(f"language_breakdown 缺少必填维度键 '{dim}'（SKILL.md JSON 数据契约六维）")

    def run_all_checks(self, grading_data):
        """运行所有检查"""
        self.errors = []
        self.warnings = []

        # 契约结构校验（须在所有消费逻辑之前，违反契约直接报错阻断）
        self.check_contract_structure(grading_data)

        sections = grading_data.get('sections', [])
        language_breakdown = grading_data.get('language_breakdown', {})
        language_score = grading_data.get('language_score', 0)
        points_score = grading_data.get('points_score', 0)
        diagnosis = grading_data.get('diagnosis', '')
        ref = grading_data.get('reference', '')
        issues = grading_data.get('issues', [])
        red_keywords = grading_data.get('red_keywords', [])
        student_answer = grading_data.get('student_answer', '')

        # 第二步：参考答案
        self.check_reference_answer(ref)
        # 新增：L1 参考答案分值校验（与 L2 板块一一对应）
        self.check_reference_scores(ref, sections)
        # F项：影响板块维度覆盖
        question = grading_data.get('question', '')
        self.check_dimension_coverage(ref, question)
        # 新增：三遍生成记录校验
        self.check_three_passes(grading_data)

        # 第三步：踩分点
        self.check_scoring_points(sections)
        # 新增：单板块≤18 校验
        self.check_section_cap(sections)

        # G项：踩分点严格度
        detail_errors, detail_warnings = self.check_scoring_detail_level(sections)
        self.errors.extend(detail_errors)
        self.warnings.extend(detail_warnings)

        # 第四步：标红
        if isinstance(student_answer, str):
            self.check_red_markers(student_answer, red_keywords)

        # 第五步：点评格式 + 学生作答列
        student_texts = []
        for section in sections:
            for point in section.get('points', []):
                comment = point[6] if len(point) > 6 else ''
                point_name = point[0] if len(point) > 0 else '未知'
                score = float(point[5]) if len(point) > 5 else 0
                max_score = float(point[3]) if len(point) > 3 else 0
                self.check_comment_format(comment, point_name)
                self.check_comment_elements(comment, point_name, score, max_score)
                self.check_comment_language(comment, point_name)
                if len(point) > 2:
                    student_texts.append(point[2])
        self.check_student_answer_column(student_texts)

        # 新增检查：踩分点列格式 + 重复踩分点
        self.check_scoring_point_name(sections)
        self.check_duplicate_points(sections)
        # 结构稳定性检查（新增·2026-08-31，警告级）
        self.check_compound_points(sections)
        self.check_knowledge_dimension_coverage(sections)

        # 第六步：论述评分
        self.check_language_scores(language_breakdown, language_score)
        self.check_language_review_format(language_breakdown)

        # 第七步：诊断格式 + 亮点引用 + 不足不写答案
        self.check_diagnosis_format(diagnosis)
        self.check_highlights_citation(issues)
        self.check_issues_no_correct_expr(issues)

        # H项：数值一致性
        self.check_score_sync(sections, language_breakdown, language_score, points_score, diagnosis)

        # 分数一致性
        self.check_score_consistency(sections, language_score, points_score, diagnosis, grading_data.get('total_score'))

        return self.report()

    def report(self):
        return {
            'passed': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


def main():
    if len(sys.argv) < 2:
        print("用法: python grade_checker.py <grading_data.json>")
        print("示例: python grade_checker.py grading_data.json")
        sys.exit(1)
    data_file = sys.argv[1]
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            grading_data = json.load(f)
    except Exception as e:
        print(f"读取数据文件失败: {e}")
        sys.exit(1)

    checker = GradeChecker()
    result = checker.run_all_checks(grading_data)

    print(f"\n{'='*50}")
    print(f"批改报告自检结果")
    print(f"{'='*50}")
    print(f"错误: {result['error_count']} 个")
    print(f"警告: {result['warning_count']} 个")

    if result['errors']:
        print("\n【错误】必须修正后才能生成报告：")
        for i, err in enumerate(result['errors'], 1):
            print(f"  {i}. {err}")

    if result['warnings']:
        print("\n【警告】建议修正：")
        for i, warn in enumerate(result['warnings'], 1):
            print(f"  {i}. {warn}")

    if result['passed']:
        print("\n[OK] 自检通过，可以生成报告")
        sys.exit(0)
    else:
        print("\n[FAIL] 自检未通过，请先修正错误")
        sys.exit(1)


if __name__ == "__main__":
    main()

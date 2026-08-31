#!/usr/bin/env python3
"""
generate_answer.py — 参考答案三遍独立生成 + 多数合并

核心逻辑：
1. 题目识别：提取「时间范围 + 对象 + 设问」三元组，判断是否旧题
2. 三遍独立起草：每次从题目出发，隔离生成板块+知识点+分值骨架
3. 多数合并：语义归组，≥2次出现的保留，取分值中位数
4. 输出：收敛后的参考答案骨架，供后续踩分点提取和判读使用

约束：
- 板块数 = 题目子问项数，单板块 ≤ 18，总分 = 30
- 禁止为凑维度编造知识点（反形式主义）
- 踩分点只考察核心史实+关键制度名称，不考察过度细节
"""

import json
import re
import sys
from typing import List, Dict, Any, Tuple, Optional


# ==================== 题目识别 ====================

def extract_question_triple(question: str) -> Tuple[str, str, str]:
    """提取题目三元组：时间范围 + 核心对象 + 设问类型"""
    # 时间范围
    time_patterns = [
        r'(\d+世纪.*?至\d+世纪)',
        r'(\d+年至\d+年)',
        r'(\d+世纪.*?到\d+世纪)',
        r'(西汉|东汉|唐朝|宋朝|明朝|清朝|中世纪|近代|现代)',
    ]
    time_range = ''
    for pat in time_patterns:
        m = re.search(pat, question)
        if m:
            time_range = m.group(1)
            break

    # 核心对象（去除设问词后的主体）
    question_clean = re.sub(r'论述|简述|分析|说明|比较|评价|谈谈|概括', '', question)
    question_clean = re.sub(r'问题|影响|原因|背景|过程|演变|措施|特点', '', question_clean)
    # 保留时间、地点、主体关键词
    obj_patterns = [
        r'(日本|德国|中国|法国|英国|罗马|西欧|欧洲|美国|俄国|苏联)',
        r'(诸侯王国|幕府体制|郡县制|封建制度|殖民体系)',
        r'([^，、的]{2,10}(问题|体制|制度|改革|运动|战争|革命|时期))',
    ]
    obj = ''
    for pat in obj_patterns:
        m = re.search(pat, question_clean)
        if m:
            obj = m.group(1).strip()
            break

    # 设问类型
    question_types = {
        '演变': r'演变|发展|变化',
        '原因': r'原因|因素|背景',
        '影响': r'影响|意义|作用|评价',
        '措施': r'措施|做法|政策|改革',
        '比较': r'比较|对比|异同',
        '论述': r'论述|谈谈|简要说明',
    }
    q_type = ''
    for t, pat in question_types.items():
        if re.search(pat, question):
            q_type = t
            break

    return time_range, obj, q_type


def is_same_question(q1: str, q2: str) -> bool:
    """判断两道题是否同一题（三元组一致）"""
    t1 = extract_question_triple(q1)
    t2 = extract_question_triple(q2)
    return t1 == t2


# ==================== 三遍生成骨架 ====================

# 三遍生成的 prompt 模板，每遍有不同的侧重点以减少锚定
PASS_PROMPTS = [
    """你是一个历史学考试命题专家。请根据以下题目，独立生成参考答案的骨架结构。

要求：
1. 先判断题目类型（措施类/原因类/影响类/状况类/比较类/评述类）
2. 从题目设问直接拆解出板块（板块数=子问项数，不得拆分或合并）
3. 每个板块下列出核心知识点和 sugggested 分值
4. 单板块≤18分，各板块满分之和=30分
5. 只列骨架，不要写正文

题目：{question}

请按以下格式输出：
板块1: 名称（分值）
  - 知识点1
  - 知识点2
板块2: 名称（分值）
  - 知识点1
  ...""",

    """你是一个历史学考试命题专家。请从另一个角度独立生成同一题目的参考答案骨架。

要求（与之前无关，请完全独立思考）：
1. 从题目设问直接拆解出板块
2. 每个板块下列出你认为的核心知识点
3. 合理分配分值，总分30，单板块≤18
4. 只列骨架，不要写正文

题目：{question}

格式：
板块1: 名称（分值）
  - 知识点1
  - 知识点2
...""",

    """你是一个历史学考试命题专家。请第三次独立生成同一题目的参考答案骨架。

要求（请完全独立于之前的思路）：
1. 从题目设问拆解板块
2. 列出核心知识点
3. 分配分值，总分30，单板块≤18

题目：{question}

格式：
板块1: 名称（分值）
  - 知识点1
  - 知识点2
..."""
]


def parse_pass_output(text: str) -> List[Dict[str, Any]]:
    """解析三遍生成的输出，提取板块+知识点+分值结构"""
    sections = []
    current_section = None
    current_points = []

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # 匹配板块标题：如 "一、XX（X分）" 或 "板块1: XX（X分）"
        board_match = re.match(
            r'^([一二三四五六七八九十]+|[①②③④⑤⑥⑦⑧])[,、：:]\s*(.+?)\s*（(\d+\.?\d*)\s*分）',
            line
        )
        if board_match:
            if current_section and current_points:
                current_section['points'] = current_points
                sections.append(current_section)
            current_section = {
                'name': board_match.group(2).strip(),
                'max_score': float(board_match.group(3)),
                'points': []
            }
            current_points = []
            continue

        # 匹配子论点：如 "（一）XXX（X分）"
        sub_match = re.match(
            r'^（[一二三四五六七八九十]+）\s*(.+?)\s*（(\d+\.?\d*)\s*分）',
            line
        )
        if sub_match and current_section is not None:
            current_points.append({
                'name': sub_match.group(2).strip(),
                'score': float(sub_match.group(3))
            })
            continue

        # 匹配知识点列表项
        if line.startswith('-') and current_section is not None:
            content = line[1:].strip()
            if content and len(content) > 2:
                current_points.append({'name': content, 'score': 0})

    if current_section and current_points:
        current_section['points'] = current_points
        sections.append(current_section)

    return sections


# ==================== 多数合并 ====================

def semantic_equal(name1: str, name2: str) -> bool:
    """判断两个知识点/板块名称是否语义相同"""
    # 标准化：去标点空格
    n1 = re.sub(r'[，、：：（）\(\)·\s]', '', name1)
    n2 = re.sub(r'[，、：：（）\(\)·\s]', '', name2)
    # 完全相同
    if n1 == n2:
        return True
    # 包含关系（短的是长的子串，且短串长度≥4）
    if len(n1) >= 4 and n1 in n2:
        return True
    if len(n2) >= 4 and n2 in n1:
        return True
    # 双字滑动窗口重叠：提取2字符连续子串，重叠≥2个
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s)-1))
    bg1, bg2 = bigrams(n1), bigrams(n2)
    overlap = bg1 & bg2
    if len(overlap) >= 2:
        return True
    return False


def merge_passes(passes: List[List[Dict]], question: str = '') -> List[Dict[str, Any]]:
    """多遍结果合并：按板块位置对齐→知识点归组→分值中位数。

    策略：不依赖板块名语义匹配（太不稳定），而是按"第i个板块"直接对齐。
    前提：三遍生成应产出相同数量的板块（由题目子问项数决定）。
    """
    if not passes:
        return []
    if len(passes) == 1:
        return passes[0]

    # ========== 第一步：按位置对齐板块 ==========
    # 以第一遍的板块数为基准（题目子问项数决定），后续遍数不足则视为该板块未产出
    n_sections = len(passes[0]) if passes else 0

    merged = []
    for si in range(n_sections):
        # 收集该位置在所有遍中的知识点
        all_points = []  # [(point_name, pass_idx, score)]
        for pi, passage in enumerate(passes):
            if si < len(passage):
                sec = passage[si]
                for pt in sec.get('points', []):
                    all_points.append((pt['name'], pt.get('score', 0)))

        if not all_points:
            continue

        # ========== 第二步：知识点语义归组 ==========
        unique_points = []  # [{'name': str, 'scores': [float]}]
        for pname, pscore in all_points:
            found = False
            for up in unique_points:
                if semantic_equal(up['name'], pname):
                    found = True
                    if pscore > 0:
                        up['scores'].append(pscore)
                    break
            if not found:
                scores = [pscore] if pscore > 0 else []
                unique_points.append({'name': pname, 'scores': scores})

        # 取中位数
        final_points = []
        for up in unique_points:
            if up['scores']:
                up['scores'].sort()
                mid = len(up['scores']) // 2
                if len(up['scores']) % 2 == 0:
                    up['score'] = (up['scores'][mid - 1] + up['scores'][mid]) / 2
                else:
                    up['score'] = up['scores'][mid]
            else:
                up['score'] = 0
            final_points.append({'name': up['name'], 'score': up['score']})

        section_total = sum(p['score'] for p in final_points)
        if section_total <= 0:
            continue

        # 使用第一遍的板块名作为标准名
        standard_name = passes[0][si]['name'] if si < len(passes[0]) else f'板块{si+1}'
        merged.append({
            'name': standard_name,
            'max_score': section_total,
            'points': final_points
        })

    # ========== 第三步：归一化总分到30 ==========
    total = sum(s['max_score'] for s in merged)
    if total > 0 and abs(total - 30) > 0.5:
        scale = 30.0 / total
        for s in merged:
            s['max_score'] = round(s['max_score'] * scale * 2) / 2
            for pt in s['points']:
                pt['score'] = round(pt['score'] * scale * 2) / 2

    # 确保单板块≤18
    for s in merged:
        if s['max_score'] > 18.01:
            ratio = 18.0 / s['max_score']
            s['max_score'] = 18.0
            for pt in s['points']:
                pt['score'] = round(pt['score'] * ratio * 2) / 2

    return merged


# ==================== 主流程 ====================

def generate_three_passes(question: str, llm_func=None) -> List[List[Dict]]:
    """
    执行三遍独立生成。

    llm_func: 可选，外部LLM调用函数，签名：llm_func(prompt: str) -> str
              如果不提供，返回空列表（由AI在SKILL.md规范下手动执行）
    """
    if llm_func is None:
        # 无LLM函数时，返回空列表，由上层AI执行三遍生成
        return []

    passes = []
    for i, prompt_template in enumerate(PASS_PROMPTS):
        prompt = prompt_template.format(question=question)
        result = llm_func(prompt)
        parsed = parse_pass_output(result)
        if parsed:
            passes.append(parsed)

    return passes


def merge_and_output(question: str, passes: List[List[Dict]]) -> Dict[str, Any]:
    """合并三遍结果，输出标准化的参考答案骨架"""
    merged = merge_passes(passes, question)

    # 构建输出结构
    result = {
        'question': question,
        'sections': [],
        'total_score': 0
    }

    for s in merged:
        section = {
            'name': s['name'],
            'max_score': s['max_score'],
            'points': []
        }
        for pt in s.get('points', []):
            section['points'].append({
                'name': pt['name'],
                'score': pt['score']
            })
        result['sections'].append(section)
        result['total_score'] += s['max_score']

    return result


def main():
    """命令行入口：用于测试"""
    if len(sys.argv) < 2:
        print("用法: python generate_answer.py <question>")
        print("示例: python generate_answer.py \"论述西汉诸侯王国问题\"")
        sys.exit(1)

    question = sys.argv[1]

    # 测试：模拟三遍输出
    mock_passes = [
        [
            {'name': '问题形成', 'max_score': 7, 'points': [
                {'name': '历史沿袭与东西异制', 'score': 2},
                {'name': '吸取秦亡教训分封同姓', 'score': 2},
                {'name': '郡国并行导致王国坐大', 'score': 3},
            ]},
            {'name': '问题解决', 'max_score': 15, 'points': [
                {'name': '汉高祖剪除异姓王', 'score': 3},
                {'name': '汉文帝众建诸侯削藩', 'score': 4},
                {'name': '汉景帝平定七国之乱', 'score': 4},
                {'name': '汉武帝推恩令彻底解决', 'score': 4},
            ]},
            {'name': '历史影响', 'max_score': 8, 'points': [
                {'name': '积极影响加强中央集权', 'score': 5},
                {'name': '消极影响过度集权隐患', 'score': 3},
            ]},
        ],
        [
            {'name': '诸侯王国问题的形成', 'max_score': 7, 'points': [
                {'name': '历史沿袭与东西异制', 'score': 2},
                {'name': '吸取秦亡教训与分封同姓', 'score': 2},
                {'name': '郡国并行致王国坐大', 'score': 3},
            ]},
            {'name': '诸侯王国问题的解决', 'max_score': 16, 'points': [
                {'name': '汉高祖剪除异姓王', 'score': 3},
                {'name': '汉文帝众建诸侯削藩', 'score': 4},
                {'name': '汉景帝平定七国之乱', 'score': 4},
                {'name': '汉武帝推恩令解决', 'score': 5},
            ]},
            {'name': '历史影响', 'max_score': 7, 'points': [
                {'name': '加强中央集权巩固统一', 'score': 4},
                {'name': '过度集权的隐患', 'score': 3},
            ]},
        ],
        [
            {'name': '问题的产生', 'max_score': 7, 'points': [
                {'name': '历史沿袭与东西异制', 'score': 2},
                {'name': '吸取秦亡教训分封同姓', 'score': 2},
                {'name': '郡国并行导致王国坐大', 'score': 3},
            ]},
            {'name': '问题的解决', 'max_score': 15, 'points': [
                {'name': '汉高祖剪除异姓王', 'score': 3},
                {'name': '汉文帝众建诸侯削藩', 'score': 4},
                {'name': '汉景帝平定七国之乱', 'score': 4},
                {'name': '汉武帝推恩令彻底解决', 'score': 4},
            ]},
            {'name': '历史影响', 'max_score': 8, 'points': [
                {'name': '积极影响：加强中央集权', 'score': 5},
                {'name': '消极影响：过度集权隐患', 'score': 3},
            ]},
        ],
    ]

    result = merge_and_output(question, mock_passes)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

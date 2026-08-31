#!/usr/bin/env python3
"""
AI腔检测模块：检测文本中的禁用词和异常内容
不含"AI套话"类（根据用户要求移除）
"""

import re


# 禁用词库（不含AI套话）
FORBIDDEN_WORDS = {
    '现代社科腔': [
        '受…驱动', '遵循…的逻辑', '核心矛盾在于', '结构性变化',
        '双重驱动', '根本转变', '历史必然性', '底层逻辑', '结构性弱点'
    ],
    '过度修饰': [
        '深刻地', '极大地', '显著地', '前所未有地', '至关重要'
    ],
    '绝对化表述': [
        '完全', '彻底', '永远', '所有', '一切'
    ]
}

# 异常内容模式
ANOMALY_PATTERNS = [
    (r'[a-zA-Z]{2,}', '英文残留'),  # 连续2个以上英文字母
    (r'[^一-鿿 -~　-〿＀-￯—“”‘’]', '异常字符'),  # 非中英文字符
]


def detect_ai_voice(text):
    """检测文本中的AI腔"""
    issues = []

    # 检查禁用词
    for category, words in FORBIDDEN_WORDS.items():
        for word in words:
            if word in text:
                issues.append({
                    'category': category,
                    'word': word,
                    'type': 'forbidden_word'
                })

    # 检查异常内容
    for pattern, desc in ANOMALY_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            issues.append({
                'category': '异常内容',
                'word': matches[0],
                'type': 'anomaly',
                'description': desc
            })

    return issues


def generate_report(issues):
    """生成检测报告"""
    if not issues:
        return "AI腔检测：通过，未发现禁用词或异常内容"

    report = "AI腔检测报告：\n"
    for issue in issues:
        if issue['type'] == 'anomaly':
            report += f"- [{issue['category']}] 发现{issue['description']}：\"{issue['word']}\"\n"
        else:
            report += f"- [{issue['category']}] 发现禁用词：\"{issue['word']}\"\n"
    report += "\n处理方式：请手动修改上述内容后重新检测"
    return report


def check_and_report(text):
    """检查并返回结果"""
    issues = detect_ai_voice(text)
    if issues:
        return {
            'status': 'failed',
            'issues': issues,
            'report': generate_report(issues)
        }
    else:
        return {
            'status': 'passed',
            'issues': [],
            'report': "AI腔检测：通过，未发现禁用词或异常内容"
        }


if __name__ == '__main__':
    # 测试
    test_text = "中世纪德国深受利益驱动，结构性变化导致历史必然性，极大地影响了欧洲格局"
    result = check_and_report(test_text)
    print(result['report'])

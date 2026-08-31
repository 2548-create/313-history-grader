#!/usr/bin/env python3
"""
维度检查模块：检查参考答案是否覆盖了多个分析维度
引用 references/维度参考.md
"""

import os
import re


def load_dimension_reference():
    """加载维度参考.md"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ref_path = os.path.join(script_dir, '..', 'references', '维度参考.md')

    if not os.path.exists(ref_path):
        return {}

    with open(ref_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析Markdown表格
    dimensions = {}
    current_section = None
    in_table = False

    for line in content.split('\n'):
        line = line.strip()

        # 检测章节标题
        if line.startswith('## ') and ('一、' in line or '二、' in line or '三、' in line or '四、' in line or '五、' in line):
            current_section = line.replace('## ', '').strip()
            dimensions[current_section] = {}
            in_table = False
            continue

        # 检测表格分隔行
        if line.startswith('|---'):
            in_table = True
            continue

        # 检测表格数据行
        if in_table and '|' in line and '维度' not in line and '说明' not in line:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2:
                dim_name = parts[0]
                dim_desc = parts[1] if len(parts) > 1 else ''
                if current_section:
                    dimensions[current_section][dim_name] = dim_desc
        elif not line.startswith('|'):
            in_table = False

    return dimensions


def check_dimensions(reference_answer, question_type='原因类'):
    """检查参考答案的维度覆盖情况"""
    dim_refs = load_dimension_reference()

    if not dim_refs:
        return {
            'status': 'error',
            'message': '未找到维度参考文件'
        }

    # 根据题目类型选择维度表
    if '古代' in question_type or '中世纪' in question_type:
        target_section = '世界古代史'
    elif '近现代' in question_type and any(kw in question_type for kw in ['德国', '法国', '英国']):
        target_section = '世界近现代史（国别）'
    elif '中国' in question_type and '古代' in question_type:
        target_section = '中国古代史'
    elif '中国' in question_type and '近现代' in question_type:
        target_section = '中国近现代史'
    elif '近现代' in question_type and any(kw in question_type for kw in ['欧洲', '世界', '国际']):
        target_section = '世界近现代史（非国别）'
    else:
        # 尝试匹配最合适的维度表
        if '德国' in question_type or '神圣罗马' in question_type:
            target_section = '世界古代史'
        elif '商鞅' in question_type or '秦' in question_type:
            target_section = '中国古代史'
        else:
            target_section = list(dim_refs.keys())[0] if dim_refs else None

    if not target_section or target_section not in dim_refs:
        return {
            'status': 'unknown',
            'message': '未找到对应的维度表，建议改用题目逻辑检查要点完整性'
        }

    selected_dims = dim_refs[target_section]
    covered = []
    missing = []

    for dim_name, dim_desc in selected_dims.items():
        # 提取关键词进行匹配
        keywords = re.findall(r'[一-鿿]{2,4}', dim_name)
        found = False
        for kw in keywords:
            if kw in reference_answer:
                found = True
                break
        if found:
            covered.append(dim_name)
        else:
            missing.append(dim_name)

    # 判断合理性
    if len(covered) == 0:
        reasonableness = 'unreasonable'
        message = '维度套用不合理，建议改用题目逻辑检查要点完整性'
    elif len(missing) > len(covered):
        reasonableness = 'partially_reasonable'
        message = f'维度覆盖不完整，缺失{len(missing)}个维度，建议补充'
    else:
        reasonableness = 'reasonable'
        message = f'维度覆盖合理，已覆盖{len(covered)}个维度'

    return {
        'status': 'success',
        'section': target_section,
        'reasonableness': reasonableness,
        'message': message,
        'covered': covered,
        'missing': missing,
        'total': len(selected_dims)
    }


if __name__ == '__main__':
    # 测试
    test_text = "中世纪德国皇位选举制导致皇权衰弱，教皇干涉德意志统一，法国分化政策阻碍统一"
    result = check_dimensions(test_text, '世界古代史')
    print(f"状态：{result['status']}")
    print(f"合理性：{result['reasonableness']}")
    print(f"消息：{result['message']}")
    print(f"覆盖维度：{result['covered']}")
    print(f"缺失维度：{result['missing']}")

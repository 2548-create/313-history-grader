#!/usr/bin/env python3
"""Generate grading report from grading_data.json"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_word import EssayGrader

data_file = sys.argv[1] if len(sys.argv) > 1 else r'C:/Users/妄/AppData/Local/Temp/grading_data.json'
output_file = sys.argv[2] if len(sys.argv) > 2 else r'C:/Users/妄/AppData/Local/Temp/日本政治体制演变批改报告.docx'

with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

grader = EssayGrader()
grader.set_question(data['question'])
grader.set_student_answer(data['student_answer'], data.get('red_keywords', []))

# 约定（与 generate_word.py / grade_checker.py 一致）：
# language_breakdown 含全部6个维度（含 neatness/卷面整洁），
# set_grading_result 会把6维之和作为 language 并另行叠加 卷面 字段，
# 因此此处 卷面 必须置 0，避免卷面分被重复计入（否则总分虚高2分）。
lang_breakdown = data['language_breakdown']

result = {
    'sections': data['sections'],
    'language_breakdown': lang_breakdown,
    'issues': data.get('issues', []),
    'suggestions': data.get('suggestions', []),
    'diagnosis': data['diagnosis'],
    'reference': data['reference'],
    'points': data['points_score'],
    'language': 0,   # 被 set_grading_result 忽略（其内部按 language_breakdown 重算）
    '卷面': 0        # neatness 已计入 language_breakdown 六维之和，置0防重复
}

grader.set_grading_result(result)
grader.generate_word_report(output_file)
print(f'Report saved to: {output_file}')

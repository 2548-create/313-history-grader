#!/usr/bin/env python3
"""
史实校验模块：校验学生答案中的史实错误
"""

# 史实错误数据库（可扩展）
HISTORY_ERRORS = {
    '卡诺莎事件': {
        'correct_subject': '亨利四世',
        'correct_year': '1077年',
        'wrong_subjects': ['奥托一世', '奥托大帝', '亨利三世']
    },
    '金玺诏书': {
        'correct_year': '1356年',
        'correct_emperor': '查理四世',
        'wrong_years': ['1256年', '1456年', '1536年']
    },
    '沃尔姆斯宗教协定': {
        'correct_year': '1122年',
        'correct_emperors': ['亨利五世'],
        'wrong_emperors': ['奥托一世', '亨利四世']
    },
    '大空位时代': {
        'correct_period': '1254-1273年',
        'correct_event': '霍亨斯陶芬王朝绝嗣',
        'wrong_periods': ['1354-1373年', '1154-1173年']
    }
}


def check_facts(student_answer):
    """校验学生答案中的史实"""
    issues = []

    for fact_name, fact_info in HISTORY_ERRORS.items():
        if fact_name in student_answer:
            # 检查年份错误
            for wrong_year in fact_info.get('wrong_years', []):
                if wrong_year in student_answer:
                    issues.append({
                        'fact': fact_name,
                        'issue': '年份错误',
                        'wrong': wrong_year,
                        'correct': fact_info.get('correct_year', '未知')
                    })

            # 检查人物错误
            for wrong_subject in fact_info.get('wrong_subjects', []):
                if wrong_subject in student_answer:
                    issues.append({
                        'fact': fact_name,
                        'issue': '人物错误',
                        'wrong': wrong_subject,
                        'correct': fact_info.get('correct_subject', '未知')
                    })

            # 检查皇帝错误
            for wrong_emperor in fact_info.get('wrong_emperors', []):
                if wrong_emperor in student_answer:
                    issues.append({
                        'fact': fact_name,
                        'issue': '皇帝错误',
                        'wrong': wrong_emperor,
                        'correct': fact_info.get('correct_emperors', ['未知'])[0] if isinstance(fact_info.get('correct_emperors'), list) else fact_info.get('correct_emperors', '未知')
                    })

    return issues


def generate_report(issues):
    """生成史实校验报告"""
    if not issues:
        return "史实校验：通过，未发现明显史实错误"

    report = "史实校验结果：\n⚠ 发现潜在错误：\n"
    for issue in issues:
        report += f"- {issue['fact']}：{issue['issue']}「{issue['wrong']}」→ 应为「{issue['correct']}」\n"
    return report


def check_and_report(text):
    """检查并返回结果"""
    issues = check_facts(text)
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
            'report': "史实校验：通过，未发现明显史实错误"
        }


if __name__ == '__main__':
    # 测试
    test_text = "奥托一世卡诺莎之辱，1256年金玺诏书颁布"
    result = check_and_report(test_text)
    print(result['report'])

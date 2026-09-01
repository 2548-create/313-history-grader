# essay-grader · 313 历史学论述题批改 skill

自动批改 313 历史学统考论述题：生成参考答案与踩分点 → OCR 识别学生答案 → 逐点评分 → 输出 Word 学生反馈报告。

## 依赖
- Python 3.10+
- `pip install python-docx`

## 安装
将本目录放入你的 agent skills 目录，例如：
- WorkBuddy：`~/.workbuddy/skills/essay-grader/`
- Claude Code：`~/.claude/skills/essay-grader/`
- Codex：`~/.codex/skills/essay-grader/`

## 使用流程
1. 在对话中让 agent 按 `SKILL.md` 走完整批改流程，产出批改数据 JSON（数组格式，详见 `SKILL.md`）。
2. 校验：`python scripts/grade_checker.py 你的数据.json`
3. 生成 Word：`python scripts/generate_word.py 你的数据.json`

## 自定义输出路径
报告默认保存在 **skill 内的 `outputs/`**，与运行时所在目录（CWD）无关，分享给他人后落点稳定可预期。

- **改默认目录（持久）**：复制 `config.example.json` 为 `config.json`，修改 `output_dir`：
  - 留空 `""` → 用默认 `skill/outputs/`
  - 绝对路径 → 固定存该目录
  - 相对路径 → 以 skill 根为基准解析（如 `"../reports"`）
- **单次指定（覆盖）**：`python scripts/generate_word.py 数据.json -o /path/to/报告.docx`
- **优先级链**：`CLI -o` > `config.json.output_dir` > 默认 `skill/outputs/`
- **生成后 assistant 会主动告知路径**：Word 报告生成后，assistant 会在对话中**用自然语言写出报告的完整保存路径**，无需你手动去 `outputs/` 翻找。

## 分享 / 打包
- `outputs/`、`grading_data_*.json` 已被 `.gitignore` 忽略，不会带入仓库。
- `config.json` 为个人配置，同样被忽略；分享时保留 `config.example.json` 作为模板。

# essay-grader · 313 历史学论述题自动批改 skill

> 自动批改 313 历史学统考**论述题**：独立生成参考答案与踩分点 → OCR 识别学生手写/粘贴答案 → 逐点评分 → 输出 Word 学生反馈报告（含得分概览、逐点点评、六维论述评语、整体诊断）。
>
> 一句话：把一道论述题的题面 + 学生答案丢给 agent，它按 `SKILL.md` 走完整七步流程，最后给你一份可直接打印/发还的 Word 批改报告。

## 一行命令安装（公开仓库 v1.0.0）

```bash
# Windows
git clone --branch v1.0.0 https://github.com/2548-create/313-history-grader.git %USERPROFILE%\.workbuddy\skills\essay-grader

# macOS / Linux
git clone --branch v1.0.0 https://github.com/2548-create/313-history-grader.git ~/.workbuddy/skills/essay-grader
```

装完后**重启 agent 会话**，技能列表即出现 `essay-grader`，所有项目通用。（也支持 Claude Code `~/.claude/skills/`、Codex `~/.codex/skills/` 等目录，把目录名保持为 `essay-grader` 即可。）

## 依赖（AI 自动处理，用户无需关心）
- Python 3.10+（agent 的托管/隔离 Python 即满足）
- `python-docx`（**AI 会在首次运行时自动安装**，见下）

> 正常用法：你只管和 agent 对话，依赖安装由 AI 在隔离环境内自动完成，你不需要手动 `pip install`。

## 安装
将本目录放入你的 agent skills 目录，例如：
- WorkBuddy：`~/.workbuddy/skills/essay-grader/`
- Claude Code：`~/.claude/skills/essay-grader/`
- Codex：`~/.codex/skills/essay-grader/`

## 使用流程（推荐：交给 AI）
1. 在对话中直接说「批改这道题」并贴题/截图，agent 会按 `SKILL.md` 走完整流程并自动产出 Word 报告。
2. 环境准备（Python 版本检查 + 自动安装 `python-docx`）由 AI 在首次运行时静默完成，你无需任何操作。
3. 报告生成后，agent 会在对话中**用自然语言告知完整保存路径**。

### 进阶：手动运行（仅当你想自己跑脚本）
- 校验：`python scripts/grade_checker.py 你的数据.json`
- 生成 Word：`python scripts/generate_word.py 你的数据.json`
- 首次手动运行前需自备 Python 3.10+ 并执行 `pip install -r requirements.txt`。

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

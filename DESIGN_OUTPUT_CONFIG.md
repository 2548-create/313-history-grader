# 设计文档：essay-grader 输出路径可配置化（待实现）

> 状态：**设计已确认并落地（2026-09-01）**。涉及改动：SKILL.md（输出路径配置小节 + 强制告知路径步骤）、generate_word.py（默认锚定 skill 目录 + CLI -o/--config）、config.example.json（新建）、README.md（新建）、.gitignore（忽略用户 config.json）。三场景实测通过（默认 / --config / -o 均正确落盘）。
> 背景：用户计划将本 skill 分享给他人，需保证「保存路径」可配置、可移植，且不依赖单机目录结构。完整路径沟通设计 = ① config 让落点可预期 + ② SKILL.md 强制 AI 在对话中告知用户完整路径。

---

## 1. 背景与现状盘点（基于 2026-09-01 代码审查）

### 已具备的可移植基础（好）
- `scripts/generate_word.py` 的 `generate_word_report(self, output_path)` **不写死路径**，路径由调用方传入（第 271、456–459 行）。换机器不会因绝对路径崩溃。
- `SKILL.md` 第 137、253 行已明确禁止写死 `C:/Users/妄/...`，要求全部相对路径。
- `.gitignore` 已忽略 `outputs/*.docx`、`outputs/*.json`、`grading_data_*.json`（第 10–14 行）——同步/分享时不会把产物带进去。

### 缺口（分享给别人会失控）
1. **无配置机制**：保存路径完全由 AI 在对话中临时决定（本次传 `'outputs/xxx.docx'`）。
2. **默认相对 CWD 而非 skill 目录**：本次 `outputs/` 能落对，纯属当时 `cd` 进了 skill 目录；别人 CWD 不同时报告会散落。
3. **无 CLI `-o`**：用户无法在命令里指定输出位置。
4. **无分享文档**：缺 README 说明依赖（`python-docx`）、运行命令、自定义路径方法。

### 目标
- 分享给他人后，别人能**一行配置**改掉默认保存位置。
- 默认行为**稳定可预期**：无论调用方 CWD 在哪，默认都落在 skill 的 `outputs/`。

---

## 2. 设计决策（已与用户确认）
- **配置方式**：`config.json`（持久默认输出目录）+ CLI `-o`（单次临时覆盖）双保险。

---

## 3. 默认输出路径解析规则
- **解析基准**：以 **skill 根目录**为锚，不依赖 CWD。
  ```python
  SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  # __file__ = {SKILL_ROOT}/scripts/generate_word.py
  ```
- **默认落点**：`{SKILL_ROOT}/outputs/{filename}`。
- 这样无论调用方从哪个目录运行，默认输出恒定落在 skill 的 `outputs/`。

---

## 4. 配置（config.example.json 入库 + config.json 用户自定义）

提供 **`config.example.json`**（入库，作模板）与 **`config.json`**（运行时读取，用户自定义，**不入库**由 `.gitignore` 忽略）。分享时别人拿到的只有 example 模板，个人配置不污染仓库。

```json
// config.example.json（入库模板）
{
  "output_dir": "",
  "filename_template": "{topic}_{timestamp}.docx"
}
```
- `output_dir`：留空 = 用默认（`skill/outputs/`）；可填**绝对路径**或**相对 skill 根的路径**。
- `filename_template`：留空 = 用内置默认命名。`{topic}` 取自 `data["question"]` 清洗后前20字，`{timestamp}` 为 `YYYYMMDD_HHMMSS`。
- 加载：`load_config()` 先读 `config.example.json` 作默认，再用 `config.json` 覆盖（若存在）。

---

## 5. CLI 设计
```
python scripts/generate_word.py <input.json> [-o OUTPUT] [--config PATH]
```
- `-o / --output`：指定输出 docx 路径（绝对或相对），**优先级最高**。
- `--config`：指定自定义 config.json（默认读 `{SKILL_ROOT}/config.json`）。
- 均未提供 → 用 `config.json` 的 `output_dir` → 再回退默认 `skill/outputs/`。

---

## 6. 优先级链
```
CLI -o  >  config.json.output_dir  >  默认(skill/outputs/)
```

---

## 7. 分享准备（README.md 新建，必需）
README 须包含：
- **依赖**：Python 3.10+；`pip install python-docx`。
- **运行**：单题流程（生成 JSON → `grade_checker.py` 校验 → `generate_word.py` 渲染）。
- **自定义输出**：改 `config.json` 的 `output_dir` 字段，或用 CLI `-o`。
- **打包排除**：`outputs/`、`grading_data_*.json`（`.gitignore` 已覆盖，zip 时同样排除）。
- **跨平台注意**：Word 中文字体依赖打开方系统；脚本仅写 XML 样式名，生成不受影响。

---

## 8. 同步矩阵（多位一体）
| 文件 | 改动 | 类型 |
|------|------|------|
| `SKILL.md` | 输出规范章节补充「可配置输出」：默认基准=skill 目录、config.json 字段、CLI `-o`、优先级链 | 规范层 ● |
| `scripts/generate_word.py` | 默认路径基于 skill 目录解析；新增 `-o/--config` 参数；启动时读 `config.json` | 执行层 ● |
| `config.example.json` | 新建（入库模板），定义 `output_dir` / `filename_template`；`config.json` 运行时读取、不入库 | 配置层 ● |
| `README.md` | 新建，分享与依赖说明 | 文档层 ● |
| `scripts/grade_checker.py` | 无需改动（只校验数据，不触碰路径） | —— ○ |
| `.gitignore` | 已覆盖产物，确认无需改 | —— ○ |

> 若项目存在 `CHANGE_SYNC.md` 依赖矩阵，本表须同步登记。

---

## 9. 校验方式（实现后执行）
1. 跑现有 `validate_consistency.py`（若存在）全 PASS。
2. 三场景实测：
   - 默认（无 config、无 `-o`）：文件落 `skill/outputs/` ✓
   - 设 `config.json` 的 `output_dir` 为绝对路径：落该路径 ✓
   - CLI `-o` 指定：落指定路径 ✓
3. 确认 `.gitignore` 仍忽略产物，不污染仓库。

---

## 10. 状态
- [x] 设计已确认（2026-09-01）：config.example.json + config.json 分工、CLI `-o`、相对路径基准分工（CLI 相对 CWD / config 相对 skill 根）、空 dirname 防护。
- [x] 已落地（2026-09-01）：SKILL.md（规范层）/ generate_word.py（执行层：SKILL_ROOT 锚定 + CLI + 防护）/ config.example.json（配置层，入库）/ README.md（文档层）/ .gitignore（忽略 config.json）五处同步改动，符合多位一体。
- [ ] 当前遗留的中间文件 `grading_data_north_south_sui_tang_continuity.json`（skill 根目录，已被 `.gitignore` 忽略）可一并清理或移入 `outputs/`。

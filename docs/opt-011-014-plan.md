# SupportPilot D 类改进实施计划（OPT-011 ~ OPT-014）


> 📌 **状态：已归档（2026-10-05）** ｜ 本文档记录 `OPT-011` ~ `OPT-014` 的设计与实际执行过程。
> 最新状态见 `innovation.md` 与 [`OPTIMIZATION_GUIDE.md`](OPTIMIZATION_GUIDE.md)。
> **范围**：`innovation.md` D 分区「计划中」的 4 个优化点  
> **配套**：`innovation.md`（登记册，只放指针与状态）｜`post-optimization-and-release.md`（阶段 A~D 总纲）  
> **本文件定位**：**可执行 + 可打钩**的实施步骤记录。每完成一步就勾选并在行尾标注日期。  
> **最后更新**：2026-10-05

---

## 使用说明（进度怎么记录）

1. 每步前有 `- [ ]` 复选框，**完成即勾选**，并在行尾补 `（完成 M-D）`
2. 一项全部完成后，**同步做两件事**：① 本节末尾「完成标准」逐条打钩；② 回 `innovation.md` 把该 `OPT` 的状态改为 ✅ 并补「数据」字段
3. 步骤中途失败 → **不要删步骤**，在该步骤下加一行 `> ⚠️ 卡住（M-D）：原因…`
4. 涉及数字的步骤（如 S4 看域内上界），**必须把实测值写在步骤下**，不要只写"已完成"

## 进度总览

| 编号        | 优化点                                 | 工作量 | 依赖                              | 状态     |
| --------- | ----------------------------------- | --- | ------------------------------- | ------ |
| `OPT-011` | 扩充对照集（多意图 / 超短问句 / 口径冲突）            | 半天  | 无                               | ✅ 已完成（2026-10-05） |
| `OPT-012` | 答案质量评测 `run_answer_quality_eval.py` | 1 天 | **建议等 `OPT-006` 挂钩完成**（否则测不出效果） | 🟡 文件就绪，待跑（花 token） |
| `OPT-013` | 统一调用链路追踪（Tracing）                   | 1 天 | 无                               | ✅ 已完成（2026-10-05） |
| `OPT-014` | Prompt 外置为 YAML 场景包                 | 半天  | 无                               | ✅ 已完成（2026-10-05） |

**推荐顺序**：`OPT-011` → `OPT-014` → `OPT-013` → `OPT-012`

> 理由：011 最便宜且能让标定结论更可信；014 是纯重构、风险可控；013 改动面广（要动 3 个日志写入点）；012 依赖 OPT-006 先落地，否则测的是 Prompt 约束的单独效果。

---

## ★ 执行记录（2026-10-05）

> 本节记录**实际执行结果**。各步的复选框留给用户按 `opt-011-014-steps.md` 复跑时自行勾选核对。

### OPT-011 · 扩充对照集 → ✅ 完成

| 步骤 | 实际做了什么 | 实测结果 |
|---|---|---|
| S1 | 建 `evals/inspect_query.py` | 已建；额外支持 `--file`，规避中文命令行参数乱码 |
| S2 | 实测 7 条候选问题 | **纠正了一处推测**：「我买的会员退款是不是更快」原猜 `membership_policy.txt`，实测是 **`refund_policy.txt`**（0.3705） |
| S3 | 追加 7 条到 `rag_cases_hard.jsonl` | 18 → **25 条**（域内 17 + 域外 8） |
| S4 | 重跑 `probe_threshold.py` | 域内上界 **0.4438 → 0.4652**（+0.0214）；域外下界仍 0.5690；空隙 **0.1252 → 0.1038** |
| — | 判据判定 | 新上界 0.4652 ≤ 0.50 → ✅ **`0.50` 继续有效，无需改代码** |
| — | ★ 新发现 | **阈值 0.45 开始误杀（2/17）**，扩集前是 0/17 → **可用窗口下沿从 0.45 抬到 0.50**，`0.50` 从"区间中点"变成"区间下沿" |
| S5 | 重跑 `threshold_sweep.py` | 0.50 → 域内 **17/17**、域外漏过 **0/8**；官方集 6 档仍恒定 100% |
| S6 | 回归 `run_rag_eval.py` | Top1 4/4、Recall@3 4/4、No-answer 1/1 → **PASS** |
| S7 | 回写 `innovation.md` | ✅ 已完成 |

### OPT-014 · Prompt 外置 YAML → ✅ 完成

| 步骤 | 实际做了什么 | 实测结果 |
|---|---|---|
| S0/S1 | 核实 PyYAML；写进 `requirements.txt` | **yaml 6.0.3** 可用；`requirements.txt` 已加 `pyyaml` |
| S2 | 建 `prompts/support_agent.yaml` | 14 个 block，**每块单行**（关键：原字符串是隐式拼接，多一个换行就漂移） |
| S3 | 建 `src/supportpilot/prompt_loader.py` | 绝对路径 + `safe_load` + `"".join()` |
| S4 | ★ 逐字节等价性验证 | **IDENTICAL**：原字符串 878 字符 / YAML 拼接 878 字符 |
| S5 | 改 `agent.py` | `instructions=load_instructions()`；保留全部中文注释，末尾注释块改为"block id ↔ 防御目标"对照表 |
| S6 | 冒烟验证 | **ALL_OK**：5 个工具齐全、instructions 878 字符、与 loader 一致 |
| S7 | 回归 | `run_rag_eval.py` → PASS |
| S8 | 回写 `innovation.md` | ✅ 已完成 |

### OPT-013 · 统一链路追踪 → ✅ 完成

| 步骤 | 实际做了什么 | 实测结果 |
|---|---|---|
| S1 | 建 `observability/` 包 + `tracer.py` | ★ 用 `contextvars` 而非全局变量（async 交错执行不会串号） |
| S2 | 三个日志写入点注入 `trace_id` | `retriever.log_retrieval` / `shipping_workflow.save_workflow_log` / `run.save_approval_log` 全部改完 |
| S3 | `run.py` 每轮生成 `trace_id` | 放在 `input()` 之后、三条路由分支**之前**；并打印 `[trace_id] tr-xxxx` 方便抄 |
| S4 | 合成测试（零成本） | **ALL_OK**：单次检索 3 条记录全部带上 ID；**3051 条**历史记录因 `.get()` 容错被安全跳过 |
| S5 | `show_trace.py` 验证 | 两种用法都通过：不带参数列最近 ID；带 ID 还原链路（按时间合并输出） |
| S6 | 真实端到端 | ⏳ **留给用户**（会花 token）—— 按复现步骤 §4 步骤 6 跑一轮完整会话 |
| S7 | 回归 | `run_rag_eval.py` → PASS |
| S8 | 回写 `innovation.md` | ✅ 已完成 |

### OPT-012 · 答案质量评测 → 🟡 文件就绪，待跑

| 步骤 | 实际做了什么 | 实测结果 |
|---|---|---|
| S1 | 建 `evals/answer_cases.jsonl` | **7 条**：2 错误前提 + 1 政策边界 + 3 正常（含**反向验证**）+ 1 应拒答 |
| S2 | 建 `evals/run_answer_quality_eval.py` | async 版；三类断言；复用 `log_eval_failure`；按 tier 拆分统计 |
| S3~S7 | **待用户执行** | 会真实调用 DeepSeek API，**故意不在本轮代跑**，避免替用户花 token |

> ⚠️ **对原设计的一处扩展**：原计划只设计了 `must_contain` / `must_not_contain` 两类断言，
> 但「你们公司CEO是谁」这条需要"命中任一同义表述"（没有/未找到/无法/暂无），
> 单靠"全部包含"表达不了 → **新增了 `must_contain_any` 断言类型**。

---

# OPT-011 · 扩充对照集

## 目标与产出

- **目标**：对照集由 18 条扩到 **25 条**，补上"多意图混合 / 超短问句 / 政策口径冲突"三类真实用户表达
- **产出**：更新后的 `evals/rag_cases_hard.jsonl` + 刷新后的标定数据

## 前置检查

- [x] **S0-1** 确认当前基线：跑 `./.venv/Scripts/python.exe evals/probe_threshold.py`，记下当前**域内上界 0.4438 / 域外下界 0.5690**
- [x] **S0-2** 备份用例文件：`cp evals/rag_cases_hard.jsonl evals/rag_cases_hard.jsonl.bak`

## 实施步骤

- [x] **S1 · 新建查题小工具 `evals/inspect_query.py`**

  用途：**先看某条问题实际命中哪个文档，再决定 `expected_source` 怎么写**。这是 `OPT-004` 那个教训的直接产物（当时就是因为没先查、凭感觉标，把域内题标成了域外）。

  核心（约 25 行，照 `probe_threshold.py` 的头部写）：
  ```python
  """查看若干条问题实际命中的 top1 文档与距离（用于标注前核对）。"""
  import contextlib, io, os, sys
  from pathlib import Path

  ROOT_DIR = Path(__file__).resolve().parents[1]
  sys.path.insert(0, str(ROOT_DIR / "src"))
  os.chdir(ROOT_DIR)

  import supportpilot.rag.retriever as R

  R.MAX_DISTANCE = 99.0          # 关掉过滤，避免被阈值掩盖真实 top1
  for q in sys.argv[1:]:
      buf = io.StringIO()
      with contextlib.redirect_stdout(buf):
          res = R.search_knowledge_base(q, top_k=3)
      top1 = res[0] if res else None
      print("%-30s -> %-22s %.4f" % (q, top1["source"] if top1 else "无结果",
                                     top1["distance"] if top1 else 0.0))
  ```
  验证：`./.venv/Scripts/python.exe evals/inspect_query.py "退货" "退款"`
- [x] **S2 · 逐条实测候选问题**，确认 `expected_source`
  ```bash
  HF_ENDPOINT=https://hf-mirror.com ./.venv/Scripts/python.exe evals/inspect_query.py \
    "我订单 A1001 想退货，运费谁出？" \
    "我买的会员退款是不是更快" \
    "退货" "退款" "多久到" \
    "你们7天无理由，那我第8天退行不行？" \
    "我听说你们退款要一个月，是不是真的"
  ```
  **候选清单（`expected_source` 是推测，必须按实测结果修改）**：
  | # | query               | 推测 `expected_source`    | 推测 `tier`                 | 实测结果     |
  | - | ------------------- | ----------------------- | ------------------------- | -------- |
  | 1 | 我订单 A1001 想退货，运费谁出？ | `return_policy.txt`     | `in_domain_multi_intent`  |          |
  | 2 | 我买的会员退款是不是更快        | `membership_policy.txt` | `in_domain_multi_intent`  | ⚠️ 很可能不准 |
  | 3 | 退货                  | `return_policy.txt`     | `in_domain_short`         |          |
  | 4 | 退款                  | `refund_policy.txt`     | `in_domain_short`         |          |
  | 5 | 多久到                 | `refund_policy.txt`     | `in_domain_short`         | ⚠️ 很可能不准 |
  | 6 | 你们7天无理由，那我第8天退行不行？  | `return_policy.txt`     | `in_domain_boundary`      |          |
  | 7 | 我听说你们退款要一个月，是不是真的   | `refund_policy.txt`     | `in_domain_wrong_premise` |          |
  > ⚠️ **若实测 top1 与"你认为应该的答案"不符 → 以实测为准改期望值，不要改题目**。因为期望值要反映"库里的依据在哪"，不是"我希望它在哪"。  
  > 若实测 top1 明显不合理（比如"退货"命中了会员政策）→ 说明这是**检索质量问题**，此时应记一笔到 `innovation.md` 作为**新优化点**，但这条用例仍然按实测标。
- [ ] **S3 · 追加到 `evals/rag_cases_hard.jsonl`**（一行一条，**末尾换行**）
- [x] **S4 · 重跑标定，看域内上界是否被顶高**
  ```bash
  HF_ENDPOINT=https://hf-mirror.com ./.venv/Scripts/python.exe evals/probe_threshold.py
  ```
  **实测记录**：域内上界 = `______`　域外下界 = `______`　空隙 = `______`（完成 M-D）

  按判据决策（**这一步不能跳**，超短问句距离往往明显偏高）：
  | 新域内上界         | 结论            | 要做什么                                                            |
  | ------------- | ------------- | --------------------------------------------------------------- |
  | ≤ 0.50        | ✅ `0.50` 继续有效 | 不用改代码，直接进 S5                                                    |
  | 0.50 ~ 0.5690 | ⚠️ 阈值要上调      | 跑 `threshold_sweep.py` 重选值（取新空隙中点附近），改 `retriever.py`           |
  | > 0.5690      | ❌ 两类分布**重叠**  | 阈值方案失效 → 转 `OPT-013` 之前先评估"换 embedding / 加 rerank"（见复盘笔记 §6 Q8） |
- [ ] **S5 · 重跑阈值扫描**确认指标仍达标
  ```bash
  HF_ENDPOINT=https://hf-mirror.com ./.venv/Scripts/python.exe evals/threshold_sweep.py
  ```
- [ ] **S6 · 回归**：跑 `evals/run_rag_eval.py` 确认官方集未退化（应仍 4/4、4/4、1/1 PASS）  
  （若 `OPT-007` 已完成）再跑 `evals/run_rag_eval_hard.py`，确认难例集仍 PASS
- [ ] **S7 · 回写 `innovation.md`**：`OPT-011` 状态 → ✅，补「数据」字段（域内上界 / 域外下界 / 空隙 / 条数 18→25）

## 坑

| 坑                      | 规避                                                           |
| ---------------------- | ------------------------------------------------------------ |
| 凭感觉写 `expected_source` | **S2 必须先实测**（`OPT-004` 的教训）                                  |
| 追加后不重跑标定               | **S4 是必须步骤**，超短问句会顶高域内上界                                     |
| 加了用例却忘了 `tier` 字段      | `tier` 是排查用的分档标签，别省                                          |
| 新用例含订单号 `A1001` 被误判    | 检索评测只调 `search_knowledge_base`，**不涉及路由**，所以无影响。但若以后做端到端评测要注意 |

---

# OPT-012 · 答案质量评测

## 目标与产出

- **目标**：补上项目**缺失的答案质量层评测**——现有 `run_rag_eval.py` 只看检索结果，看不出"模型有没有被用户错误前提带跑"
- **产出**：`evals/answer_cases.jsonl` + `evals/run_answer_quality_eval.py`

## 前置检查

- [ ] **S0-1** 确认 `OPT-006`（答后校验）已挂钩到 `run.py`。**若未挂钩**，本评测只能测出 Prompt 约束（`OPT-005`）的单独效果——那也是有价值的，但要在结论里注明
- [ ] **S0-2** 确认 DeepSeek 余额。**成本估算**：每条用例 ≈ 1~~2 次模型往返（含工具调用），8 条 ≈ 10~~16 次调用。先在 3 条上试水
- [ ] **S0-3** 确认环境变量：`export HF_ENDPOINT=https://hf-mirror.com`（RAG 工具要下 embedding 模型）

## 实施步骤

- [ ] **S1 · 建 `evals/answer_cases.jsonl`（先 5 条起步）**
  ```jsonl
  {"query":"我听说你们退款要30天是真的吗","must_contain":["3","7"],"must_not_contain":["需要30天","确实是30天","30个工作日"],"expected_source":"refund_policy.txt","tier":"wrong_premise"}
  {"query":"签收8天还能无理由退货吗？","must_contain":["7"],"must_not_contain":["可以无理由"],"expected_source":"return_policy.txt","tier":"boundary"}
  {"query":"退款多久到账？","must_contain":["工作日"],"must_not_contain":[],"expected_source":"refund_policy.txt","tier":"normal"}
  {"query":"黑金会员有什么权益？","must_contain":[],"must_not_contain":["30天"],"expected_source":"membership_policy.txt","tier":"normal"}
  {"query":"你们公司CEO是谁？","must_contain":["没有","未找到","无法"],"must_not_contain":[],"expected_source":null,"tier":"no_answer"}
  ```
  > ⚠️ **`must_not_contain` 严禁写"是的"这种宽泛词** —— 正常回答里出现"是的"太常见，会大面积误伤。  
  > 要写**具体到会暴露错误的那串字**，例如 `"需要30天"` / `"确实是30天"` / `"30个工作日"`。  
  > （这一条同时修正了 `post-optimization-and-release.md` §3.7 里那个过宽的示例。）
- [ ] **S2 · 写 `evals/run_answer_quality_eval.py`**

  **结构照抄 `run_rag_eval.py`**（`ROOT_DIR` / `CASES_PATH` / `load_cases()` / 循环 / 汇总 / Quality Gate），**唯一区别是要 async**：
  ```python
  import asyncio, json, sys
  from pathlib import Path

  ROOT_DIR = Path(__file__).resolve().parents[1]
  sys.path.insert(0, str(ROOT_DIR / "src"))

  from agents import Runner
  from supportpilot.agent import create_support_agent
  from eval_logging import log_eval_failure

  CASES_PATH = ROOT_DIR / "evals" / "answer_cases.jsonl"

  async def evaluate_case(agent, case: dict) -> dict:
      query = case["query"]
      result = await Runner.run(agent, query)          # 单轮，不带历史
      answer = result.final_output or ""

      missing = [k for k in case.get("must_contain", []) if k not in answer]
      forbidden = [k for k in case.get("must_not_contain", []) if k in answer]
      passed = not missing and not forbidden

      if not passed:
          log_eval_failure(
              suite="answer_quality",
              case=query,
              expected={"contain": case.get("must_contain"),
                        "not_contain": case.get("must_not_contain")},
              actual=answer,
              details={"missing": missing, "forbidden": forbidden},
          )
      return {"query": query, "passed": passed, "answer": answer,
              "missing": missing, "forbidden": forbidden}

  async def main() -> None:
      agent = create_support_agent()
      cases = [json.loads(l) for l in CASES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
      results = [await evaluate_case(agent, c) for c in cases]

      passed = sum(1 for r in results if r["passed"])
      print("=" * 50)
      print("Answer Quality Eval")
      print("=" * 50)
      for r in results:
          print()
          print("-" * 50)
          print(f"Query: {r['query']}")
          print(f"Status: {'PASS' if r['passed'] else 'FAIL'}")
          if r["missing"]:
              print(f"  缺少关键词: {r['missing']}")
          if r["forbidden"]:
              print(f"  出现禁用词: {r['forbidden']}")
          print(f"Answer: {r['answer']}")
      print()
      print(f"Pass Rate: {passed}/{len(results)} = {passed / len(results):.2%}")

  if __name__ == "__main__":
      asyncio.run(main())
  ```
  **两个实现要点**：
  1. **`Runner.run(agent, query)` 传字符串即可**（SDK 的 `input` 支持 `str | list`），评测用单轮、不带历史，避免上一条用例污染下一条
  2. **每个用例独立算 pass**，不做"全部通过才 PASS 的总闸门" —— 因为答案质量本身就是概率性的，先看通过率
- [ ] **S3 · 3 条试水**（把 `answer_cases.jsonl` 临时截成 3 行），确认能跑通、断言逻辑对

  **实测记录**：通过率 = `__/3`（完成 M-D）
- [ ] **S4 · 恢复全量并正式跑**，记录通过率
- [ ] **S5 · 人工抽查（必做，不可省）**

  逐条读答案，判断三件事：
  - [ ] 有没有**指出用户前提有误**（而不是含糊回避）
  - [ ] 给出的数字**是否与政策原文一致**
  - [ ] 有没有**误伤正常问题**（比如把"退款多久到账"答成"您的说法有误"）  
    **实测记录**：人工判定通过 = `__/__`；自动化与人工不一致的条目 = `______`
  > ⚠️ **自动化断言必然与人工判断有偏差**。把偏差记下来，这就是面试里"我知道这套断言很粗糙，所以我加了人工抽查"的证据。
- [ ] **S6（可选）· 加 LLM 裁判**：把「问题 + 检索原文 + 模型答案」丢给另一个模型，让它判"答案是否与原文一致"。成本翻倍，收益有限，**建议先不做**
- [ ] **S7 · 回写 `innovation.md`**：`OPT-012` → ✅，补「数据」字段（用例数 / 自动化通过率 / 人工通过率）

## 坑

| 坑                              | 规避                                                  |
| ------------------------------ | --------------------------------------------------- |
| `must_not_contain` 写得太宽（如"是的"） | 只写**具体到会暴露错误的那串字**                                  |
| 脚本写成同步的                        | Agent 调用是 async，必须 `asyncio.run(main())`            |
| 用例之间串历史                        | 每条独立调 `Runner.run(agent, query)`，不共用 `conversation` |
| 忘了 `HF_ENDPOINT`               | RAG 工具要下 embedding 模型，会卡在下载                         |
| 一次跑全量烧太多                       | 先 3 条试水，再放量                                         |
| 只看自动化通过率                       | **人工抽查必须做**，并把偏差记下来                                 |


# OPT-014 · Prompt 外置为 YAML 场景包

## 目标与产出

- **目标**：把 `agent.py` 里那段超长隐式拼接的 `instructions` 拆成可配置的 YAML 场景包，改 Prompt 不再需要动源码
- **产出**：`prompts/support_agent.yaml` + `src/supportpilot/prompt_loader.py`；`agent.py` 改为调用 loader

## 前置检查（已核实）

- [x] `yaml` 可用：**PyYAML 6.0.3**（当前由 chromadb 间接带入）→ **不用装包**
- [ ] **S0 · 但 `requirements.txt` 里没有 `pyyaml`** → 必须显式加上，否则将来 chromadb 换依赖方式时会突然报 `ModuleNotFoundError`

## 实施步骤

- [ ] **S1 · `requirements.txt` 增加 `pyyaml`**
- [ ] **S2 · 把现有 instructions 原样搬进 `prompts/support_agent.yaml`**
  ```yaml
  name: SupportPilot

  # 按数组顺序拼接；想调整提示词顺序，改这里即可，不用动代码
  blocks:
    - id: identity
      text: "你是 SupportPilot，一名企业客服 AI Agent。请用简洁、专业、友好的方式回答用户问题。"

    - id: numbering
      text: "编号规则：A 开头的是订单号，例如 A1001；T 开头的是售后工单号，例如 T0001。"

    # ... 其余各段原样搬过来，一段一个 block
  ```
  > ⚠️ **必须"原样搬"**：现在的 instructions 是**相邻字符串字面量隐式拼接**，字与字之间**没有空格也没有换行**。  
  > 搬进 YAML 时如果手滑加了换行或空格，**prompt 内容就变了，模型行为可能跟着变**。所以 S4 的等价性验证是必须的。
- [ ] **S3 · 新建 `src/supportpilot/prompt_loader.py`**
  ```python
  """从 prompts/*.yaml 加载 Prompt 场景包。"""

  from pathlib import Path

  import yaml

  # ★ 用绝对路径（parents[2] = 项目根），避免又踩"必须在项目根运行"的坑
  PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"

  def load_instructions(name: str = "support_agent") -> str:
      path = PROMPT_DIR / f"{name}.yaml"
      if not path.exists():
          raise FileNotFoundError(f"Prompt 场景包不存在：{path}")

      data = yaml.safe_load(path.read_text(encoding="utf-8"))
      blocks = data.get("blocks") or []
      if not blocks:
          raise ValueError(f"Prompt 场景包没有 blocks：{path}")

      return "".join(block["text"] for block in blocks)
  ```
  **三个实现要点**：
  1. `parents[2]` —— 文件在 `src/supportpilot/prompt_loader.py`，`parents[0]=supportpilot`、`[1]=src`、`[2]=项目根`
  2. 用 `yaml.safe_load` 而非 `yaml.load`（后者能执行任意 Python 对象，有安全风险）
  3. `"".join(...)` —— **不要用 `"\n".join()`**，否则会引入原字符串没有的换行
- [ ] **S4 · 验证"拼接结果与原字符串完全一致"（关键步骤）**

  先记下原字符串，再对比新 loader 的输出：
  ```bash
  # ① 改动前，先把原 instructions 落盘存底
  ./.venv/Scripts/python.exe -c "
  import sys; sys.path.insert(0,'src')
  from supportpilot.agent import create_support_agent
  a = create_support_agent()
  open('data/logs/_instructions_before.txt','w',encoding='utf-8').write(a.instructions)
  print('len =', len(a.instructions))
  "

  # ② 改完 agent.py 后，导出新结果
  ./.venv/Scripts/python.exe -c "
  import sys; sys.path.insert(0,'src')
  from supportpilot.prompt_loader import load_instructions
  open('data/logs/_instructions_after.txt','w',encoding='utf-8').write(load_instructions())
  print('len =', len(load_instructions()))
  "

  # ③ 逐字节比较
  ./.venv/Scripts/python.exe -c "
  a = open('data/logs/_instructions_before.txt',encoding='utf-8').read()
  b = open('data/logs/_instructions_after.txt',encoding='utf-8').read()
  print('IDENTICAL' if a == b else f'DIFFERENT: len {len(a)} vs {len(b)}')
  "
  ```
  **实测记录**：`______`（完成 M-D）

  若输出 `DIFFERENT` → 逐段 diff 找出多/少的空白字符，修 YAML 后重跑，**直到 IDENTICAL 才继续**。
- [ ] **S5 · 改 `agent.py`**
  ```python
  from supportpilot.prompt_loader import load_instructions

  def create_support_agent():
      model = create_model()
      return Agent(
          name="SupportPilot",
          instructions=load_instructions(),     # ← 替换掉原来的超长字符串
          model=model,
          tools=[...],
      )
  ```
- [ ] **S6 · 验证"改 YAML 就能改行为，不用动代码"**

  随手改一句（例如把"请用简洁、专业、友好的方式回答"改成"请用非常简短的方式回答"），重启 `run.py`，观察回答风格变化。**这就是这个优化的全部价值证明。**

  **实测记录**：`______`（完成 M-D）
- [ ] **S7 · 回归**：跑 `evals/run_all_evals.py` + `evals/rag_answer_quality_eval.py`（若已建），确认行为没漂
- [ ] **S8 · 回写 `innovation.md`**：`OPT-014` → ✅

## 坑

| 坑                                  | 规避                                                                           |
| ---------------------------------- | ---------------------------------------------------------------------------- |
| 搬 YAML 时多/少了换行或空格 → prompt 静默变化    | **S4 逐字节等价性验证是硬门槛**                                                          |
| 用 `"\n".join()` 拼接                 | 用 `"".join()`                                                                |
| 用 `yaml.load`                      | 用 `yaml.safe_load`                                                           |
| `prompts/` 路径写成相对路径                | 用 `Path(__file__).resolve().parents[2]`                                      |
| 忘了把 `pyyaml` 写进 `requirements.txt` | 现在能跑只是因为它被 chromadb 间接带入，**别依赖这个巧合**                                         |
| 只改了 `agent.py` 却忘了同步 YAML 的内容      | loader 报错要"吵"——所以 `load_instructions` 里加了 `FileNotFoundError` / `ValueError` |

---

# 附：跨项注意事项

## A. 每项做完都要做的三件事

1. **回归**：`./.venv/Scripts/python.exe evals/run_all_evals.py`，确认 `5/5 PASS` + `Release Gate: READY`
2. **回写 `innovation.md`**：状态改 ✅、补「数据」字段（实测数字，不许写"效果更好"）、更新顶部统计表与日期
3. **本文件打钩**：勾选步骤 + 标注日期 + 填实测记录

## B. 关于文档位置的一个提醒

本文件和 `refactor-1-retrospective.md`、`rag-threshold-calibration.md` 目前都在**工作区根目录**（`日常学习/`），而 `innovation.md` 在**项目内**。

→ **上传 GitHub 前，应把这些文档移进项目**（例如建 `docs/` 目录），否则：

- `innovation.md` 里指向 `post-optimization-and-release.md` §3.6 的链接会**断掉**
- 面试官 clone 下来看不到实验证据

（`PORTFOLIO_CHECKLIST.md` §2 已列了这条待办。）

## C. 四项做完之后的简历增量

| 项         | 可写进简历的一句话                                             |
| --------- | ----------------------------------------------------- |
| `OPT-011` | 对照测试集覆盖多意图混合、超短问句、政策口径冲突等边界样本，扩至 25 条                 |
| `OPT-012` | 补齐项目缺失的答案质量层评测，验证生成层前提校验的实际有效率                        |
| `OPT-013` | 发现三个日志文件缺少关联字段、无法还原单次会话链路，为其注入统一 `trace_id` 并实现一键链路还原 |
| `OPT-014` | 将硬编码 Prompt 重构为 YAML 场景包，实现 Prompt 资产化与零代码调整          |

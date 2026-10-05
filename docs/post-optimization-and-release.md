# SupportPilot 后续改造与 GitHub 上线指南


> 📌 **状态：已归档（2026-10-05）** ｜ 本文档记录后续改造与 GitHub 上线的**过程方案**。
> 上线部分已在 v0.1.0 完成，最新状态见 `README.md` 与 [`OPTIMIZATION_GUIDE.md`](OPTIMIZATION_GUIDE.md)。
> **面向**：第一次做项目改造的开发者（假定没有 Git 协作、没有评测体系、没有 Prompt 工程经验）  
> **前置状态**：改造 1（RAG 阈值标定）已完成 —— `MAX_DISTANCE` 由 0.70 改为 0.50，域外漏过 6/8 → 0/8  
> **本指南对应**：`refactor-1-retrospective.md` §10「还没做完的」清单（4 项）+ GitHub 上线  
> **最后更新**：2026-10-04

---

## 0. 先搞清楚：这一步要达成什么

`refactor-1-retrospective.md` §10 列了 4 项待办。做完之后，你手上应该多出这三样**能拿给面试官看的东西**：

| 产出                    | 用途           | 来自哪一项 |
| --------------------- | ------------ | ----- |
| 一张「官方评测 vs 难例评测」并排数字表 | 简历数字 + 面试截图  | 10.3  |
| 一段「模型纠正用户错误前提」的对话录屏   | **最值钱的面试素材** | 10.1  |
| 一份 25+ 条的对照测试集        | 证明你会造测试集     | 10.2  |

**推荐执行顺序**（不是按清单编号，按"投入产出比 + 依赖关系"排的）：

| 顺序       | 项目                             | 工作量   | 为什么排这个位置                      |
| -------- | ------------------------------ | ----- | ----------------------------- |
| **阶段 A** | 10.3 完成 `run_rag_eval_hard.py` | 半天    | 只需改 3 行；它是后面所有验证的"尺子"，先有尺子才能量 |
| **阶段 B** | 10.1 生成层"前提校验"                 | 1~2 天 | **核心价值**；补上复盘笔记里定位出的那个真实缺口    |
| **阶段 C** | 10.2 扩充对照集                     | 半天    | 让测试集更可信；做完要回头重跑标定             |
| **阶段 D** | 10.4 阈值分档                      | ——    | **建议跳过**，见 §5                 |

---

## 1. 新手急救包（开工前必读 5 分钟）

### 1.1 三个你会反复用到的概念

| 概念                  | 一句话解释                                                             |
| ------------------- | ----------------------------------------------------------------- |
| **基线（baseline）**    | 改动**之前**跑一次记下的数字。没有基线，改完你没法证明自己改好了                                |
| **回归（regression）**  | 改完代码重跑一遍全部评测，确认**没把别的功能弄坏**。项目里就是 `python evals/run_all_evals.py` |
| **评测集（test cases）** | 一组"问题 + 标准答案"的样本，`evals/*.jsonl` 都是这种文件，一行一条 JSON                 |

### 1.2 铁律：每一次改动都走同一个循环

```
① 先跑基线，把数字抄下来
      ↓
② 改代码（一次只改一个变量）
      ↓
③ 跑同一条命令，跟基线对比
      ↓
④ 数字对了 → 提交；数字不对 → 回到 ②
```

> ⚠️ **反面教材**：改完直接说"我觉得没问题"。改造 1 已经证明过一次了 —— **官方评测 5 条在任何阈值下都是 100%**，光看它你永远发现不了问题。**得先确认你的尺子有能力变红。**

### 1.3 三条绝对不要做的事

1. **绝对不要改 `.env`**（里面是你的真实 API Key），也**绝对不要**把它提交上去
2. **绝对不要 `git add .`** 然后提交 —— `.venv/`（几百 MB）、`data/chroma/`、`supportpilot.db` 都会被塞进仓库
3. **绝对不要 `git push origin main`** —— 现在的 `origin` 是**原作者的仓库**，你推不上去（详见 §6.1）

---

## 2. 阶段 A：完成 `evals/run_rag_eval_hard.py`（半天）★先做这个

### 2.1 应达成的具体目标

让**同一套指标口径**分别跑"官方 5 条"和"难例 18 条"，拿到两列可对比的数字，并证明：

> **`MAX_DISTANCE = 0.70` 时难例集 FAIL，改成 0.50 后 PASS。**

这就是简历上那行数字的证据链。

### 2.2 现状（已核实）

`evals/run_rag_eval_hard.py` **已经存在了**，但它现在是个"哑弹" —— 它读的还是官方用例文件：

```python
CASES_PATH = ROOT_DIR / "evals" / "rag_cases.jsonl"      # ← 这里没改！
```

跑它等于把官方评测跑第二遍，**没有任何意义**。

### 2.3 要改哪 3 处

| # | 位置                                                        | 改成                                                                    |
| - | --------------------------------------------------------- | --------------------------------------------------------------------- |
| 1 | `CASES_PATH`                                              | `ROOT_DIR / "evals" / "rag_cases_hard.jsonl"`                         |
| 2 | 打印标题 `"RAG Eval"`                                         | `"RAG Eval (Hard)"`（输出里能一眼区分是哪个集）                                     |
| 3 | `log_eval_failure(suite="rag")` / `suite="rag_no_answer"` | 改成 `suite="rag_hard"` / `suite="rag_hard_no_answer"`（否则失败日志会和官方集混在一起） |

### 2.4 操作顺序

**第 1 步：先跑基线（证明现在 FAIL）**

临时把阈值改回旧值，看难例集会不会挂：

```bash
# 打开 src/supportpilot/rag/retriever.py，把 MAX_DISTANCE 改回 0.70
cd D:/workbuddy_workplace/日常学习/supportpilot-agent
HF_ENDPOINT=https://hf-mirror.com ./.venv/Scripts/python.exe evals/run_rag_eval_hard.py
```

**预期输出**（关键行）：

```
Top1 Accuracy: 10/10 = 100.00%
Recall@3: 10/10 = 100.00%
No-answer Accuracy: 2/8 = 25.00%      ← ★ 难例集把问题暴露出来了
==================================================
RAG Quality Gate
==================================================
Status: FAIL
```

> ⚠️ **注意**：`run_rag_eval_hard.py` 在 FAIL 时会 `sys.exit(1)`，这是**故意设计**的（方便以后接 CI）。终端可能显示命令"失败"，这是正常的。

**第 2 步：把阈值改回 0.50，再跑一次**

```bash
# 把 MAX_DISTANCE 改回 0.50，重新执行同一条命令
HF_ENDPOINT=https://hf-mirror.com ./.venv/Scripts/python.exe evals/run_rag_eval_hard.py
```

**预期输出**：

```
Top1 Accuracy: 10/10 = 100.00%
Recall@3: 10/10 = 100.00%
No-answer Accuracy: 8/8 = 100.00%     ← 8 条该拒答的全拦住了
Status: PASS
```

**第 3 步：把两列数字抄进报告**

| 评测集    | 条数 |   阈值 | Top1 | Recall@3 | No-answer | 结论                 |
| ------ | -: | ---: | ---- | -------- | --------- | ------------------ |
| 官方     |  5 | 0.70 | 100% | 100%     | 100%      | PASS（但**看不出参数问题**） |
| 官方     |  5 | 0.50 | 100% | 100%     | 100%      | PASS（无变化）          |
| **难例** | 18 | 0.70 | 100% | 100%     | **25%**   | **FAIL**           |
| **难例** | 18 | 0.50 | 100% | 100%     | **100%**  | **PASS**           |

### 2.5 验证方式

- ✅ 难例集在 0.70 下必须 **FAIL**（No-answer 25%）
- ✅ 难例集在 0.50 下必须 **PASS**（No-answer 100%）
- ✅ 官方集在两个阈值下**都不变**（100%/100%/100%）—— 这正好再次印证"官方集不敏感"
- ✅ 顺手确认 `python evals/run_all_evals.py` 仍然 `5/5 PASS`（说明你没弄坏官方链路）

### 2.6 注意事项

- ⚠️ **改完记得把 `MAX_DISTANCE` 改回 0.50**！做基线时改了 0.70，别忘了改回来，否则项目就退化了
- 想更稳妥：用 `git diff src/supportpilot/rag/retriever.py` 确认最终值是 0.50
- **别把 `run_rag_eval_hard.py` 加进 `run_all_evals.py` 的 SUITES 列表**，除非你打算让"难例不达标"也卡住发布门禁。作为独立脚本更灵活

---

## 3. 阶段 B：生成层"前提校验"（1~2 天）★★核心价值

### 3.1 应达成的具体目标

让系统面对**用户前提错误**的提问时，能**指出冲突并给出正确信息**，而不是顺着用户答、也不是拒答。

**目标行为（这就是你要录屏的那段）**：

```
用户：我听说你们退款要30天是真的吗

❌ 现状（可能出现的三种坏结果）
   坏 1：是的，我们退款一般需要 30 天。（被用户带跑 —— 最严重）
   坏 2：暂未找到相关政策。（拒答 —— 但库里明明有）
   坏 3：我们支持退款。（回避了数字，没回答问题）

✅ 目标
   不是的。退款在仓库验收后 1~3 个工作日内发起；银行卡退款到账通常为
   3~7 个工作日，第三方支付为 1~3 个工作日。您听说的 30 天与我们当前
   政策不符。
   来源：refund_policy.txt
```

### 3.2 为什么不能靠检索层（一句话讲清，面试要用）

> 检索层衡量的是**话题相关度**，而这里要判断的是**主张是否为真**。这条问题含"退款"二字，检索层**已经正确命中了** `refund_policy.txt`（距离 0.4438）—— **它没有失败**。想用阈值拦住它，可用窗口只有 `[0.4379, 0.4438)`、宽 0.0059，而 0.40 时真实问题已经误杀 4/10。**是工具选错了，不是参数没调好。**

### 3.3 三条实现路线（先选路线，再动手）

| 路线               | 做法                                                   | 改动量              | 效果              | 风险              |
| ---------------- | ---------------------------------------------------- | ---------------- | --------------- | --------------- |
| **1. Prompt 约束** | 在 Agent 的 instructions 里加规则："用户陈述与资料冲突时，先指出冲突再给正确信息" | **最小**（改 1 段字符串） | 中（模型不一定每次都听）    | 靠模型自觉，不稳定       |
| **2. 答后校验**      | 答案生成后，自动比对"用户提到的数字"与"检索到的原文"，不一致就打标记                 | 中（新增 1 个模块）      | 高（**确定性**，不靠模型） | 需要定义"比对什么数字"    |
| **3. 两段式生成**     | 先让模型从资料里抽一张"政策事实表"，再基于事实表作答                          | 大                | 最高              | 多一次 LLM 调用，成本翻倍 |

**推荐：路线 1 + 路线 2 组合。** 路线 1 便宜、覆盖大部分情况；路线 2 作为确定性兜底（面试时能讲"我没有把正确性完全托付给模型"）。路线 3 留作未来方向讲。

### 3.4 路线 1：改 Prompt（先做这个，30 分钟）

**要改的文件**：`src/supportpilot/agent.py`

现在 `instructions` 里已经有这两句：

```python
"涉及企业政策的问题，不要依赖模型自身常识回答，"
"只能基于知识库工具返回的资料回答。"
```

**紧跟在它后面插入这 4 句**：

```python
"如果用户的陈述中包含具体的数字、时间、比例或金额，"
"你必须把它与知识库资料中的说法逐一核对。"
"如果用户的前提与资料不一致，必须先明确指出用户的前提有误，"
"再给出资料中的正确信息，不要顺着用户的前提回答。"
```

> 💡 **`instructions` 是超长字符串隐式拼接**（相邻字符串字面量自动合并），所以你只要在中间插入新的字符串片段就行，不用管逗号和换行 —— 但**每句末尾的标点和分隔感要保留**，否则模型读起来会粘连。

**验证方式**（这一步必须手动测，因为评测集还没建）：

```bash
cd D:/workbuddy_workplace/日常学习/supportpilot-agent
HF_ENDPOINT=https://hf-mirror.com ./.venv/Scripts/python.exe run.py
注意：run.py文件中 SQLite 的 cursor.execute() 执行的 SQL 语句内部使用了 Python 格式的注释（#）将导致 SQLite 解析器无法识别，从而报语法错误（syntax error）。
```

然后依次输入这几句，观察回答（**这就是你录屏的素材**）：

| 输入                | 期望行为                    |
| ----------------- | ----------------------- |
| `我听说你们退款要30天是真的吗` | ✅ 指出 30 天不对，给出 3~7 个工作日 |
| `退款多久到账？`         | ✅ 正常回答（不要被新规则带偏）        |
| `签收8天还能无理由退货吗？`   | ✅ 指出 7 天无理由，第 8 天已超期    |
| `你们公司CEO是谁？`      | ✅ 仍然拒答（库里确实没有）          |

> ⚠️ **一定要测"不要被新规则带偏"**：加了"核对数字"的规则后，模型可能变得过于多疑，把正常问题也答成"您的说法有误"。**新规则必须有回归验证。**

### 3.5 路线 2：答后校验模块（确定性兜底）

**要新增的文件**：`src/supportpilot/verification/__init__.py` 和 `src/supportpilot/verification/fact_check.py`

**核心设计**（比"校验答案里的数字"更简单也更准）：

> 校验对象是 **"用户问题里提到的数字"**，不是"答案里的数字"。  
> 规则：**用户提到的数字，如果在检索到的知识库原文里找不到 → 说明用户可能记错了 → 打标记。**

这条规则同时覆盖两类问题：

- 「退款要 **30** 天」→ 原文里没有 30 → 冲突 ✓
- 「签收 **8** 天还能退吗」→ 原文写的是 7 天 → 冲突 ✓（这正是复盘笔记里说的「政策口径冲突」样本）

**函数骨架**（概念示意，你需要自己补全）：

```python
# src/supportpilot/verification/fact_check.py
"""生成层前提校验：检查用户陈述中的数字是否有知识库依据。"""

import re
from agents.items import ToolCallOutputItem


def extract_numbers(text: str) -> set[str]:
    """抽出文本中的数字（阿拉伯数字 + 常见中文数字）。"""
    # 提示：除了 \d+，别忘了「三十天」这种中文数字写法
    ...


def collect_kb_text(result) -> str:
    """从 Runner 结果里捞出知识库工具返回的原文。

    可直接照抄 run.py 里 find_approval_request_from_run 的遍历方式：
        for item in result.new_items:
            if not isinstance(item, ToolCallOutputItem): continue
            text = item.output
            if isinstance(text, str): ...
    """
    ...


def find_unverified_numbers(user_query: str, kb_text: str) -> list[str]:
    """返回「用户提到、但知识库资料里找不到」的数字列表。"""
    ...
```

**在 `run.py` 里挂钩**（第 541 行 `answer = result.final_output` **之后**）：

```python
answer = result.final_output

# ★ 新增：生成层前提校验
kb_text = collect_kb_text(result)
unverified = find_unverified_numbers(user_message, kb_text)
if unverified:
    log_premise_conflict(user_message, unverified, kb_text)   # 写日志，便于事后统计
    print(f"\n[FactCheck] 用户提到的 {unverified} 在知识库资料中未找到，可能前提有误。")
```

**搭好之后，做一次"验证它真的会报"的测试**：

| 输入                | 期望 `[FactCheck]` 输出       |
| ----------------- | ------------------------- |
| `我听说你们退款要30天是真的吗` | `用户提到的 ['30'] 在知识库资料中未找到` |
| `退款多久到账？`         | 无输出（没问题）                  |

**期望输出日志**：新建 `data/logs/premise_conflict.jsonl`，字段建议 `timestamp / query / unverified_numbers / sources`。


### 3.6 路线 2 的进阶（可选）：自动重生成

**一句话**：检测到"用户提到的数字在资料里找不到"时，不只是打个标记，而是**把冲突信息塞回对话，让模型重新回答一次**。

> 实现前必须先核实：`RunResult` 有没有"完整输入视图"的方法。本项目实测 `agents==0.22.3` 提供 `RunResult.to_input_list(mode="preserve_all")` → **可用**。

#### 3.6.1 触发条件（5 个条件必须**全部**满足）

这是整个设计里最关键的部分。条件放宽一格，就会变成"每次用户提到数字都重生成"，白烧 token。

| # | 条件              | 判据                                                | 为什么必须有                                          |
| - | --------------- | ------------------------------------------------- | ----------------------------------------------- |
| 1 | **检出可疑数字**      | `find_unverified_numbers(user_input, kb_text)` 非空 | 基本前提                                            |
| 2 | **模型确实顺着说了**    | 可疑数字出现在 `answer` 里                                | ★ 最重要。如果模型压根没提这个数字（比如它只答"请参见政策文档"），重生成毫无意义      |
| 3 | **本轮不是审批路径**    | `approval_request is None`                        | ★ 写操作**绝不能重答**——重跑可能再次调用 `create_ticket`。审批分支优先 |
| 4 | **知识库确实检索到了内容** | `kb_text` 非空                                      | 资料为空时"用户数字找不到"是废话，该走的是拒答流程而不是重生成                |
| 5 | **未超重试上限**      | `retry_count < MAX_REGEN`（建议 `1`）                 | 防止"答错 → 重答 → 还错 → 再重答"死循环                       |

**把 5 个条件封成一个闸门函数**，这样 `run.py` 里只用写几行：

```python
# src/supportpilot/verification/fact_check.py（追加）

def should_regenerate(
    user_query: str,
    answer: str,
    kb_text: str,
    has_approval_request: bool,
    retry_count: int,
    max_regen: int = 1,
) -> tuple[bool, list[str]]:
    """5 个触发条件全部满足才重生成。返回 (是否重生成, 可疑数字)。"""
    if retry_count >= max_regen:                  # 条件 5
        return False, []
    if has_approval_request:                      # 条件 3
        return False, []
    if not kb_text:                               # 条件 4
        return False, []
    suspicious = find_unverified_numbers(user_query, kb_text)   # 条件 1
    if not suspicious:
        return False, []
    if not any(number in answer for number in suspicious):      # 条件 2
        return False, []
    return True, suspicious
```

> 条件 2 用简单的 `in` 字符串判断就够（数字很短，不会误匹配到别的词）。**它的作用是"放过"而不是"拦截"**：模型自己没跟着说错，就不用重生成。

#### 3.6.2 处理流程（7 步）

```
① 初次  result_1 = await Runner.run(agent, conversation)
②       answer_1 = result_1.final_output
③ 校验  kb_text     = collect_kb_text(result_1)
        suspicious  = find_unverified_numbers(user_input, kb_text)
④ 闸门  should_regenerate(...) 五个条件逐一判断
          └─ 不满足 → 直接跳到 ⑦，用 answer_1 继续原有流程
⑤ 重生成 correction  = 修正消息（见 3.6.3）
        result_2    = await Runner.run(
                          agent,
                          result_1.to_input_list() + [correction],
                      )
        answer_2    = result_2.final_output
⑥ 复核  ★ 只复核「解决了没有」，不再触发第二次重生成
        suspicious_2 = find_unverified_numbers(user_input, collect_kb_text(result_2))
        resolved     = not any(n in answer_2 for n in suspicious_2)
⑦ 收尾  用 answer_2（或 answer_1）继续原有流程 + 写日志
```

**★ 第 ⑤ 步为什么用 `result_1.to_input_list()`，而不是 `conversation`？**

这是整个实现里最容易写错的地方：

| 传什么                            | 模型能看到什么                                     | 后果                                             |
| ------------------------------ | ------------------------------------------- | ---------------------------------------------- |
| `conversation`                 | 只有纯文本的 user / assistant 消息，**不含上一次的工具调用记录** | 模型不知道刚才检索到了什么，**得重新调一次工具** → 多一次工具调用 + 多一次模型往返 |
| **`result_1.to_input_list()`** | 完整输入视图，**包含工具调用与工具产出**                      | 模型直接看到刚才检索到的政策原文，**不用再检索**                     |

**这就是"重生成"和"重问一遍"的本质区别。** 用 `to_input_list()` 才是真正的"基于同一份资料重答"。

#### 3.6.3 修正消息怎么写

```python
correction = {
    "role": "user",
    "content": (
        f"[系统校验] 请注意：用户提到的数字 {suspicious} "
        f"在知识库资料中找不到依据。"
        f"请只依据上一步检索到的资料原文重新回答；"
        f"如果用户的前提与资料冲突，必须先明确指出用户的前提有误，"
        f"再给出资料中的正确数字。"
        f"不要调用任何写操作工具。"
    ),
}
```

三个要点：

1. **点明"依据上一步检索到的资料原文"** —— 引导模型复用已有的工具产出，而不是重新检索
2. **明确要求"指出前提有误"** —— 否则模型可能只是含糊回避，答案看着改了但其实没纠正
3. **加"不要调用任何写操作工具"** —— 兜底防止重生成期间误触发 `create_ticket`（条件 3 已经挡了一层，这是第二层）

#### 3.6.4 关键数据 / 状态的更新（最容易出错的地方）

| 对象                                 | 怎么处理                                  | 为什么                                                                     |
| ---------------------------------- | ------------------------------------- | ----------------------------------------------------------------------- |
| `result`                           | **必须替换**为重生成后的 `result_2`             | 后面 `find_approval_request_from_run(result)` 依赖它；**不替换会漏掉重生成期间新产生的审批请求** |
| `answer`                           | 替换为 `answer_2`                        | 展示和写入历史都用它                                                              |
| `conversation`                     | **只追加最终答案**；草稿 `answer_1` **不写**      | 否则历史里会留下两条互相矛盾的 assistant 消息，污染后续轮次                                     |
| 临时修正消息                             | **用完即弃，不要 `append` 进 `conversation`** | ① "系统校验"不是用户真实说的话；② 会占用 `MAX_HISTORY_MESSAGES = 10` 的名额，把真正的对话挤掉        |
| `retry_count`                      | **本轮局部变量**，不跨轮持久化                     | 每个用户输入独立计算；用全局计数器会把后续轮次也卡住                                              |
| `data/logs/premise_conflict.jsonl` | 追加一条完整记录                              | 事后统计"检出率 / 修复率"，也是面试可展示的数据                                              |
| **数据库**                            | **完全不碰**                              | 前提校验只做"读 + 提示 + 重答"，**零写操作**。这是它与 HITL 闸门的分工边界                          |

`premise_conflict.jsonl` 建议字段：

```json
{
  "timestamp": "2026-10-05T16:30:00",
  "query": "我听说你们退款要30天是真的吗",
  "suspicious_numbers": ["30"],
  "kb_sources": ["refund_policy.txt"],
  "attempts": 2,
  "resolved": true,
  "answer_before": "……我们需要 30 天……",
  "answer_after": "不是的。退款在仓库验收后 1~3 个工作日内发起，银行卡退款通常 3~7 个工作日到账……"
}
```

> **`attempts` 和 `resolved` 两个字段是关键** —— 它们让你能回答面试官"这套校验的有效率是多少""有多少条最终没修好"，而不是只能说"我加了个校验"。

#### 3.6.5 怎么与整体流程衔接（3 个衔接点）

**衔接点 1 · 插入位置**

```python
        result = await Runner.run(agent, conversation)      # run.py 第 525 行
        answer = result.final_output                         # 第 541 行
        # ─────────────── ★ 自动重生成插在这里 ★ ───────────────
        approval_request = find_approval_request_from_run(result)   # 第 545 行
        if approval_request is not None:
            answer = handle_agent_write_approval(approval_request)
        print(f"SupportPilot：{answer}")
        conversation.append({"role": "assistant", "content": answer})   # 第 564 行
```

**必须在 `find_approval_request_from_run` 之前** —— 这样审批检查用的是重生成后的 `result`，不会漏检。

**衔接点 2 · 与三条路由分支的关系**

`run.py` 的 `while` 循环里有三条分支，**只有第三条**会走到重生成逻辑：

| 分支                     | 是否受影响 | 说明                          |
| ---------------------- | ----- | --------------------------- |
| `/shipping A1004` 调试命令 | ❌     | 第 485 行就 `continue` 了，根本到不了 |
| 自然语言触发 Workflow        | ❌     | 第 510 行 `continue`          |
| **普通请求 → Agent**       | ✅     | 唯一受影响的分支                    |

**衔接点 3 · 与 HITL 审批的关系（优先级 + 边界）**

|         | HITL 审批闸门                                     | 前提校验重生成        |
| ------- | --------------------------------------------- | -------------- |
| 管的层     | 生成层**之后**、执行层                                 | **生成层内部**      |
| 触发对象    | 写操作（`create_ticket` / `update_ticket_status`） | 政策问答的数字冲突      |
| 有无副作用   | **有**（写数据库）                                   | **无**（只读 + 重答） |
| 是否幂等    | 靠 `find_open_ticket_by_order_and_type` 保证     | 天然幂等           |
| **优先级** | **高** —— 一旦检出审批请求，直接接管，**不重生成**               | 低              |

实现顺序固定为：**先判审批 → 有审批就跳过重生成 → 否则才做前提校验**。

**完整挂钩代码**（把 `run.py` 第 541~547 行之间那段替换成下面这样）：

```python
        # Agent 最终自然语言回答
        answer = result.final_output

        # 直接检查本轮 Tool 的原始输出，看有没有写操作审批请求
        approval_request = find_approval_request_from_run(result)

        # ── ★ 生成层前提校验 + 自动重生成 ──────────────────────
        kb_text = collect_kb_text(result)
        suspicious: list[str] = []
        attempts = 0
        answer_before = answer

        should_regen, suspicious = should_regenerate(
            user_query=user_input,
            answer=answer,
            kb_text=kb_text,
            has_approval_request=(approval_request is not None),
            retry_count=attempts,
            max_regen=1,
        )

        if should_regen:
            attempts += 1
            correction = {
                "role": "user",
                "content": (
                    f"[系统校验] 请注意：用户提到的数字 {suspicious} "
                    f"在知识库资料中找不到依据。"
                    f"请只依据上一步检索到的资料原文重新回答；"
                    f"如果用户的前提与资料冲突，必须先明确指出用户的前提有误，"
                    f"再给出资料中的正确数字。"
                    f"不要调用任何写操作工具。"
                ),
            }

            try:
                result = await Runner.run(          # ★ result 必须替换
                    agent,
                    result.to_input_list() + [correction],   # ★ 不是 conversation
                )
                answer = result.final_output
            except Exception as exc:
                print(f"\n[FactCheck] 重生成失败，沿用原答案：{exc}")
                answer = answer_before

            # 复核：只判断解决了没有，不再递归重生成
            kb_text_after = collect_kb_text(result)
            remaining = find_unverified_numbers(user_input, kb_text_after)
            resolved = not any(n in answer for n in remaining)

            log_premise_conflict(
                query=user_input,
                suspicious=suspicious,
                kb_text=kb_text_after or kb_text,
                attempts=attempts,
                resolved=resolved,
                answer_before=answer_before,
                answer_after=answer,
            )
            print(f"\n[FactCheck] 检出可疑数字 {suspicious}，已重生成，resolved={resolved}")
        # ──────────────────────────────────────────────────

        if approval_request is not None:
            answer = handle_agent_write_approval(approval_request)
```

配套 import：

```python
from supportpilot.verification.fact_check import (
    collect_kb_text,
    find_unverified_numbers,
    should_regenerate,
)
from supportpilot.verification.conflict_log import log_premise_conflict
```

> `log_premise_conflict` 建议单独放 `src/supportpilot/verification/conflict_log.py`（写 `data/logs/premise_conflict.jsonl`），参照 `retriever.py` 里 `log_retrieval` 的写法即可——开 `parents=True` 建目录 + `ensure_ascii=False` 追加一行 JSON。

#### 3.6.6 注意事项

1. **成本会翻倍**：一次重生成 = 一次额外模型往返（通常还带工具调用），实际 token 消耗约 1.5~2 倍。建议 `MAX_REGEN = 1`，且只对**政策问答**启用
2. **必须留三个"放弃"出口**：条件 3（审批）/ 4（无资料）/ 5（超次数），缺任何一个都可能出事
3. **不要用 `conversation` 重跑** —— 见 3.6.2 的 ★，这是最常见的实现错误
4. **复核不做递归**：第 ⑥ 步只判断"解决了没有"，**绝不**再触发一次重生成
5. **先跑一周 MVP（只打标记不重生成）**，看日志里 `suspicious_numbers` 的准确率，再决定要不要开启重生成。**误报率决定它值不值得做**

### 3.7 怎么"验证"这件事做完了（关键）

**新建答案质量评测**：`evals/answer_cases.jsonl` + `evals/run_answer_quality_eval.py`

用例格式建议：

```json
{"query":"我听说你们退款要30天是真的吗","must_contain":["3","7"],"must_not_contain":["需要30天","确实是30天","30个工作日"],"expected_source":"refund_policy.txt","tier":"wrong_premise"}
```

> ⚠️ **修订（2026-10-05）**：`must_not_contain` **不要写"是的"这类宽泛词** —— 正常回答里出现"是的"太常见，会大面积误伤。必须写**具体到会暴露错误的那串字**（如「需要30天」「30个工作日」）。

三层验证，**从粗到细都做**：

| 层次                | 做法                                         | 成本                   | 可靠性         |
| ----------------- | ------------------------------------------ | -------------------- | ----------- |
| **① 关键词断言**（自动化）  | 断言答案包含正确数字、不包含"附和错误前提"的具体字串（见下方修订提示）       | 低（但要真实调 API，花 token） | 粗糙，会有误判     |
| **② 人工抽查**（必须做）   | 逐条读答案，人眼判断"有没有指出冲突"                        | 零成本                  | 高           |
| **③ LLM 当裁判**（进阶） | 把「用户问题 + 检索原文 + 模型答案」丢给 LLM，让它判"答案是否与原文一致" | 多一次调用                | 较高，但裁判自己也会错 |

> ⚠️ **重要提醒**：`run_answer_quality_eval.py` 会**真实调用 DeepSeek API**，**每条用例都花 token**。先小批量（5~8 条）跑通，再扩量。跑之前确认余额。

### 3.8 注意事项（新手最容易踩的坑）

1. **一次只改一个变量**：先把 Prompt 改好、测好，再加 fact_check 模块。两个一起改，出了问题你不知道是谁的锅
2. **必须做"反向验证"**：新规则有没有让正常问题答错？至少要测 10 条正常问题
3. **`run.py` 是主循环，改动风险最高**。改之前先 `git add -A && git commit -m "wip: before premise check"` 存一个还原点
4. **别把"校验"做成"拦截"**：MVP 只打标记 + 日志，**不要**因为校验不通过就吞掉答案。先观察效果再决定要不要强制干预
5. **成本意识**：每多一次 LLM 调用，成本就翻倍。路线 3（两段式）对实习项目来说性价比不高

---

## 4. 阶段 C：扩充对照集（半天）

### 4.1 要补哪三类（各给示例，可直接用）

**要改的文件**：`evals/rag_cases_hard.jsonl`（现在是 18 条，目标 25+ 条）

| 类型         | 示例                    | 期望 `expected_source`                                            | 建议 `tier`                | 测什么                      |
| ---------- | --------------------- | --------------------------------------------------------------- | ------------------------ | ------------------------ |
| **多意图混合**  | `我订单 A1001 想退货，运费谁出？` | `return_policy.txt`                                             | `in_domain_multi_intent` | 既含订单号又考政策，测路由会不会乱        |
| **超短问句**   | `退货` / `多久到` / `能退吗`  | `return_policy.txt` / `refund_policy.txt` / `return_policy.txt` | `in_domain_short`        | 极简输入下检索稳不稳（**最容易掉分的一类**） |
| **政策口径冲突** | `你们7天无理由，那我第8天退行不行？`  | `return_policy.txt`                                             | `in_domain_boundary`     | 政策边界，考察是否答"原则上不支持"       |

> 💡 再补一条**错误前提变体**，验证 3.1 里那个结论不是孤例：  
> `{"query":"我听说你们退款要一个月，是不是真的","expected_source":"refund_policy.txt","tier":"in_domain_wrong_premise"}`

### 4.2 操作顺序

1. **先跑基线**：`./.venv/Scripts/python.exe evals/probe_threshold.py`，记下当前域内上界 **0.4438** / 域外下界 **0.5690**
2. **追加新用例**到 `evals/rag_cases_hard.jsonl`（一行一条，`expected_source` 为 `null` 表示"该拒答"）
3. **重跑标定**：`./.venv/Scripts/python.exe evals/probe_threshold.py`
4. **看域内上界有没有被顶高**

### 4.3 验证方式（这步最容易漏！）

> ⚠️ **改了测试集，必须重跑标定，确认 0.50 还成立。**

超短问句（"退货"两个字）的距离**很可能比 0.4438 更高** —— 因为信息量太少，向量更"飘"。如果新的域内上界涨到 0.52，那 **0.50 这个阈值就站不住了**，你得重新选值。

**判据**：

| 新域内上界              | 结论                                                          |
| ------------------ | ----------------------------------------------------------- |
| 仍 ≤ 0.50           | ✅ 0.50 继续有效，不用动                                             |
| 在 0.50 ~ 0.5690 之间 | ⚠️ 阈值要往上调（比如 0.55），重新跑 `threshold_sweep.py` 选新值             |
| > 0.5690           | ❌ 两类分布**重叠**了，阈值方案失效 → 去读复盘笔记 §6 的 Q8（换模型 / 加 rerank / 改判定） |

**同时跑一次**：`./.venv/Scripts/python.exe evals/run_rag_eval_hard.py`，确认新用例没让 Quality Gate 挂掉。

### 4.4 注意事项

- **`expected_source` 填错会污染整个实验** —— 这一点你已经踩过一次了（复盘笔记 §7：那条"错误前提"题被标成了域外，导致空隙从 0.1252 变成假象的 0.0059）。**填之前问自己：知识库里到底有没有这条问题的依据？**
- 判断标准&#x662F;**"库里有没有依据"**，不&#x662F;**"用户说得对不对"**
- 新增用例后，`data/logs/threshold_probe.json` 会被覆盖 —— 想留旧数据先手动备份

---

## 5. 阶段 D（可选）：阈值分档 —— **建议跳过**

### 5.1 复盘笔记 §10 原话

> "**阈值是静态的** —— 没有按 query 类型（政策问答 / 订单查询）分别设阈值"

### 5.2 为什么建议不做（先讲清楚再决定）

1. **订单查询根本不过 RAG** —— 它走的是 `get_order_status` 这个 Tool，查 SQLite。给它设 RAG 阈值没有意义
2. **分档会引入新参数，而新参数又需要新的标定实验** —— 你现在有 18 条数据支撑 1 个阈值，分档后每条路径可能只有几条数据，**统计上站不住**
3. **收益边际递减**：改造 1 已经把拒答能力从 25% 提到 100%，分档能榨出的空间很小

### 5.3 如果一定要做，怎么做（低成本版本）

**只按"query 长度"分两档**，而不是按业务类型分：

```python
# src/supportpilot/rag/retriever.py 概念示意
MAX_DISTANCE = 0.50          # 默认
MAX_DISTANCE_SHORT_QUERY = 0.55   # 超短问句（≤4 字）信息量少，放宽一点

def effective_max_distance(query: str) -> float:
    return MAX_DISTANCE_SHORT_QUERY if len(query.strip()) <= 4 else MAX_DISTANCE
```

然后**必须重跑** `threshold_sweep.py` 验证两档各自的误杀/漏过。

> 💡 **更好的用法**：不做，但**在面试里主动讲出来** —— "这个方案我知道它的边界：阈值是全局静态的，没区分 query 长度；但分档需要更多数据支撑，以现在的 25 条样本量做分档统计不可靠，所以我先不做。" **主动说清"我知道但我不做以及为什么"，比硬做一个半成品更专业。**

---

## 6. GitHub 上线：上传前准备 + 完整流程

### 6.1 ⚠️ 三件必须先搞清楚的事（已核实）

#### 🔴 第一件：你现在的 `origin` 指向的是**原作者的仓库**

```
origin  https://github.com/Chenmaolin-maker/supportpilot-agent.git
```

这意味着：

- 你**没有**这个仓库的写权限 → `git push` 会直接 403
- **即使有权限也不该推** —— 那是别人的仓库
- 你本地那 10 个 commit **全是原作者的**，你自己的改动**还一个都没提交**

→ 必须先在 GitHub 上建**你自己的**仓库，然后**改 remote**（见 6.3 Step 4）。

#### 🔴 第二件：项目**没有 LICENSE**

已核实，根目录下没有 `LICENSE` 文件，**原作者的仓库也没放许可证**。法律上"没有许可证"= **默认保留所有权利**，严格来说公开再发布整个副本是有风险的。

**三种处理方式，按稳妥程度排序**：

| 方案        | 做法                                                                     | 适合        |
| --------- | ---------------------------------------------------------------------- | --------- |
| **A（推荐）** | 在 README **顶部显著位置**写明："本项目为学习目的复现，原始项目来自 [链接]，原作者 XXX。我在此基础上完成了以下改造：…" | 简历项目、公开仓库 |
| **B**     | 仓库先设为 **Private**，面试时临时加面试官为协作者                                        | 想更保守      |
| **C**     | 去原仓库提 issue 说明你在做复现并会注明来源                                              | 想更规范      |

> ✅ **实习简历项目通常 A 就够了。** 关键是**别假装是纯原创** —— 面试官一眼就能看出是知名复现项目，主动说明来源反而显得诚实、且能顺势讲你的改造点。

#### 🟡 第三件：`.env` 里有你的**真实 DeepSeek API Key**

好消息：`git log --all -- .env` 输出为空 → **它从未被提交过** ✓

但它是个定时炸弹，上传前**必须再确认一次**。如果哪次不小心 `git add .` 传上去了，**唯一的补救是立刻去 DeepSeek 后台吊销那个 Key 并重新生成** —— 爬到 GitHub 上的 Key 几分钟内就会被机器人扫走。

### 6.2 上传前检查清单（逐项勾）

**清理**

- [x] 删掉垃圾文件 `innovation`（已核实，是个 **0 字节的空文件**，估计是哪次 shell 重定向写歪了留下的）
- [x] 确认 `__pycache__/` 不在 git 里（`.gitignore` 已覆盖 ✓）
- [x] `data/logs/` 和 `data/chroma/` 不该进仓库（`.gitignore` 已覆盖 ✓）

**安全检查（最重要）**

- [x] `git status` 逐行看一遍，确认没有意外文件
- [x] 确认 `.gitignore` 覆盖这些：

```
.venv/
.env
__pycache__/
*.pyc
.pytest_cache/
.vscode/
supportpilot.db
data/chroma/
data/logs/
```

- [x] **全历史搜索 Key**（复制粘贴运行）：

```bash
cd D:/workbuddy_workplace/日常学习/supportpilot-agent
git log --all -p | grep -n "sk-" | head
```

输出**必须为空**。有输出 = 立刻停止上传，先处理泄漏。

**内容准备**

- [ ] 新增 `LICENSE`（如果你自己的新增部分是原创，可以加 MIT；但 README 里要说明整体来源）
- [ ] 改 `README.md`：**顶部加一段「复现说明 + 我的改造」**
- [ ] 确认 `evals/probe_threshold.py` / `threshold_sweep.py` / `rag_cases_hard.jsonl` 三个新文件会被提交

### 6.3 完整上传流程（8 步）

#### Step 1 · 先存个还原点

```bash
cd D:/workbuddy_workplace/日常学习/supportpilot-agent
git status
rm -f innovation                       # 删掉那个 0 字节垃圾文件
```

#### Step 2 · 分组提交本地改动（别用 `git add .`）

按"逻辑相关性"分 3~4 个 commit，**这样面试官翻你的提交记录能看懂你做了什么**：

```bash
# ① 阈值标定的核心改动
git add src/supportpilot/rag/retriever.py
git commit -m "feat(rag): calibrate MAX_DISTANCE from 0.70 to 0.50"

# ② 评测集与实验脚本
git add evals/rag_cases_hard.jsonl evals/probe_threshold.py evals/threshold_sweep.py
git commit -m "test(rag): add 18 hard cases and threshold calibration scripts"

# ③ 调试工具
git add show_db.py
git commit -m "chore: add read-only DB and log viewer"
```

> ⚠️ `evals/eval_report.md`、`chunker.py`、`embedder.py`、`ticket_tools.py` 这几个文件也显示被修改过。**先 `git diff <文件>` 看清楚改了什么**，确认是你要的改动再提交；不确定就先不提交。

#### Step 3 · 在 GitHub 网页建**你自己的**空仓库

1. 打开 <https://github.com/new>
2. Repository name：`supportpilot-agent`（或加个后缀区分，如 `supportpilot-agent-portfolio`）
3. **不要勾** "Add a README file"、**不要勾** ".gitignore"、**不要勾** "license"

> ⚠️ 勾了任何一个，远端就会有一个你本地没有的 commit，首次 `push` 会报 `non-fast-forward` 错误。

#### Step 4 · 改 remote（关键一步）

**做法 A（推荐）** —— 把原作者仓库改名为 `upstream` 保留，新建自己的 `origin`：

```bash
git remote rename origin upstream
git remote add origin https://github.com/<你的用户名>/supportpilot-agent.git
git remote -v          # 确认：origin 是你自己的，upstream 是原作者的
```

> 💡 **保留 `upstream` 的好处**：日后原作者更新了，你可以 `git fetch upstream` 看有什么新东西。

**做法 B（简单）** —— 直接改地址：

```bash
git remote set-url origin https://github.com/<你的用户名>/supportpilot-agent.git
```

#### Step 5 · 首次推送

```bash
git branch -M main
git push -u origin main
```

**这一步会卡在认证上**，见 6.4。

#### Step 6 · 网页验收

打开你的仓库页面，确认：

- [ ] 文件齐全（`src/`、`evals/`、`run.py`、`README.md`…）
- [ ] **看不到 `.env`** ← 最重要
- [ ] **看不到 `.venv/`、`data/chroma/`、`supportpilot.db`**
- [ ] 能看到 `evals/rag_cases_hard.jsonl` 等新文件

#### Step 7 · 补 README 和 LICENSE

在网页上直接编辑 `README.md`，**在标题下面插入这段**（把括号内容替换掉）：

```markdown
> **关于本项目**：本仓库是学习目的的复现项目，原始项目来自
> [Chenmaolin-maker/supportpilot-agent](https://github.com/Chenmaolin-maker/supportpilot-agent)。
> 我在复现基础上完成了以下改造：
> - **RAG 检索阈值标定**：将 `MAX_DISTANCE` 由 0.70 调整为 0.50。
>   构造 18 条域内/域外对照测试集，实测域内距离上界 0.4438、域外下界 0.5690，
>   存在 0.1252 的分离空隙；域外漏过由 6/8（75%）降至 0/8，域内召回零损失。
> - **发现官方评测集对 `MAX_DISTANCE` 零敏感**（0.40~0.70 指标恒定 100%），
>   据此补齐了评测集的灵敏度盲区。
> - 新增 `evals/probe_threshold.py`、`evals/threshold_sweep.py`、`evals/rag_cases_hard.jsonl`。
```

#### Step 8 · 打 tag（让项目看起来更完整）

```bash
git tag -a v0.1.0 -m "复现完成 + 改造1：RAG 检索阈值标定"
git push origin v0.1.0
```

### 6.4 认证怎么过（新手最卡的一步）

GitHub 早就**不支持账号密码**推送了。推荐用 **Personal Access Token (PAT)**：

1. 登录 GitHub → 右上角头像 → **Settings**
2. 左侧拉到最底 → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**
4. Note 填 `local-push`，Expiration 选 90 天，**勾选 `repo` 权限**
5. 点生成 → **复制那串 token**（⚠️ 只显示一次，关掉页面就再也看不到）
6. 回到终端 `git push`，提示输入用户名时填**你的 GitHub 用户名**，密码处**粘贴这个 token**（不是你的登录密码）
7. 想免得每次都输：

```bash
git config --global credential.helper manager
```

### 6.5 常见报错速查

| 报错                                                            | 原因                         | 怎么修                                                                                                                                   |
| ------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `remote: Permission to Chenmaolin-maker/... denied` (403)     | **你还在往原作者的仓库推**            | 没做 Step 4，回去改 remote                                                                                                                  |
| `failed to push some refs ... non-fast-forward`               | 建仓库时勾了 README，远端多了个 commit | `git pull --rebase origin main` 后再 `push`                                                                                             |
| `Support for password authentication was removed`             | 用了登录密码                     | 改用 PAT（见 6.4）                                                                                                                         |
| `fatal: remote origin already exists`                         | 重复 `git remote add`        | 改用 `git remote set-url origin <新地址>`                                                                                                  |
| `error: failed to push some refs (pre-receive hook declined)` | 仓库设置或分支保护                  | 检查 Settings → Branches                                                                                                                |
| `Filename too long`                                           | Windows 路径长度限制             | `git config --global core.longpaths true`                                                                                             |
| **上传后网页上看到 `.env`**                                           | 🚨 灾难                      | ① **立刻去 DeepSeek 后台吊销并重建 Key**；② `git rm --cached .env`；③ 确认 `.gitignore` 有 `.env`；④ 历史里的 Key 仍在，需要 `git filter-repo` 或联系 GitHub 支持清理 |

---

## 7. 一页速查卡

### 命令

```bash
cd D:/workbuddy_workplace/日常学习/supportpilot-agent
export HF_ENDPOINT=https://hf-mirror.com      # 每次新终端都要设

# 官方评测（5 条）
./.venv/Scripts/python.exe evals/run_rag_eval.py
# 难例评测（18 条）★ 阶段 A 要做出来的
./.venv/Scripts/python.exe evals/run_rag_eval_hard.py
# 全部评测（回归）
./.venv/Scripts/python.exe evals/run_all_evals.py
# 阈值标定探针
./.venv/Scripts/python.exe evals/probe_threshold.py
# 阈值扫描
./.venv/Scripts/python.exe evals/threshold_sweep.py
# 手动对话测试
./.venv/Scripts/python.exe run.py
```

### 文件改动地图（按阶段）

| 阶段     | 改动/新增的文件                                                                                                                                                                             |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **A**  | 改 `evals/run_rag_eval_hard.py`（3 处）                                                                                                                                                  |
| **B**  | 改 `src/supportpilot/agent.py`（加 4 句 instructions）；新增 `src/supportpilot/verification/fact_check.py`；改 `run.py`（挂钩）；新增 `evals/answer_cases.jsonl` + `evals/run_answer_quality_eval.py` |
| **C**  | 改 `evals/rag_cases_hard.jsonl`（+7 条）；重跑标定                                                                                                                                            |
| **D**  | 跳过（或只改 `retriever.py`）                                                                                                                                                               |
| **上线** | 删 `innovation`；改 `README.md`；新增 `LICENSE`；改 git remote                                                                                                                               |

### 一页数字（直接背）

- 域内上界 **0.4438** / 域外下界 **0.5690** / 空隙 **0.1252** / 空隙中点 **0.5064**
- 原阈值 **0.70**：域外漏过 6/8（75%），难例集 **No-answer 25% → FAIL**
- 新阈值 **0.50**：域外漏过 0/8，域内误杀 0/10，难例集 **No-answer 100% → PASS**
- 官方 5 条在任何阈值下恒定 **100%**（= 它没有能力变红）

### 三条铁律

1. 不要改 `.env`，不要提交 `.env`
2. 不要 `git add .`，不要 `git push origin main`（origin 是原作者的）
3. 改测试集 → **必须重跑标定**；新规则 → **必须反向验证**

# SupportPilot Portfolio Checklist

最终目标：让 SupportPilot 同时具备可运行、可解释、可评估、可展示和可公开发布的求职项目形态。

> **本仓库为学习目的的复现 + 改进项目**，原始项目来自 [Chenmaolin-maker/supportpilot-agent](https://github.com/Chenmaolin-maker/supportpilot-agent)。
> 全部优化点统一登记在 `innovation.md`（编号 `OPT-001` ~ `OPT-014`），叙事与复现入口见 `docs/OPTIMIZATION_GUIDE.md`。

## 1. GitHub 发布

- [x] 本地 Git 仓库已初始化
- [x] `main` 分支存在
- [x] `.env` 未纳入 Git 跟踪
- [x] `supportpilot.db` 未纳入 Git 跟踪
- [x] `data/chroma/` 未纳入 Git 跟踪
- [x] `data/logs/` 未纳入 Git 跟踪
- [x] Git 历史和源码未发现真实 API key
- [x] `origin` 指向自己的仓库，原作者仓库保留为 `upstream`
- [x] **README 顶部标注复现来源与原仓库链接**（含 14 项改进摘要表）
- [x] **`LICENSE` 已添加**（MIT，含来源说明）
- [x] 清理非源码文件（错位的 `src/verification/`、`evals/_candidates.txt` 已删除）
- [ ] 完成 GitHub 登录认证（Personal Access Token）
- [ ] 推送 `main` 分支
- [ ] 推送版本 tag（`v0.1.0`）
- [ ] 在 GitHub 页面确认 README 正常渲染

## 2. 项目文档

- [x] README 包含项目背景和目标
- [x] README 包含架构图和核心流程
- [x] README 包含安装、配置和启动命令
- [x] README 包含完整 Eval 命令
- [x] README 标注 controlled smoke-test / regression dataset 限定
- [x] `.env.example` 与实际配置变量一致
- [x] `requirements.txt` 已提交（含 `pyyaml`）
- [x] **`innovation.md` 优化点登记册**（含结构、分区、命名与格式规范）
- [x] **`docs/OPTIMIZATION_GUIDE.md` 已建立**（面向开源读者的整合指南）
- [x] **6 份过程文档已纳入 `docs/`**，交叉引用已同步修正
- [x] **README 增加「复现来源与改进说明」章节**，逐条引用 `OPT-NNN`

## 3. 产品能力展示

- [x] 订单查询
- [x] 工单查询
- [x] 工单创建
- [x] 工单状态修改
- [x] 企业政策 RAG
- [x] Shipping Workflow
- [x] HITL 审批
- [x] 工单幂等控制
- [x] Trace、Approval、Failure、Regression 日志
- [x] **生成层前提校验（路线 1：Prompt 约束）** —— `OPT-005`
- [x] **生成层前提校验（路线 2：确定性答后校验）** —— `OPT-006`

## 4. Eval 与质量口径

**官方受控回归套件（25 条 / 5 套）**

- [x] RAG Eval：Top1 `4/4`、Recall@3 `4/4`、No-answer `1/1`（合计 5 条）
- [x] Workflow Eval：`4/4` PASS
- [x] HITL Eval：`4/4` PASS
- [x] Agent Tool Eval：`4/4` PASS
- [x] Intent Route Eval：`8/8` PASS
- [x] Unified Eval：`5/5` Suites PASS（**25** 个 controlled cases）
- [x] Release Gate：**READY**

**新增：RAG 难例评测与阈值标定** —— `OPT-001` ~ `OPT-004` / `OPT-007` / `OPT-011`

- [x] 难例对照测试集 **25 条**（域内 17 + 域外 8，带 `tier` 难度分档）
- [x] 阈值标定实验完成：`MAX_DISTANCE` `0.70` → **`0.50`**
- [x] 标定工具链已建立（`evals/probe_threshold.py`、`evals/threshold_sweep.py`、`evals/inspect_query.py`）
- [x] 实测域内上界 **0.4652** / 域外下界 **0.5690** / 分离空隙 **0.1038**
- [x] 域外漏过 **6/8（75%）→ 0/8**，域内误杀 **0/17**
- [x] 发现官方评测集对该参数**零敏感**（0.40~0.70 三指标恒定 100%）
- [x] 修正对照集的一处组别标注错误（自我纠错）
- [x] `evals/run_rag_eval_hard.py` 可用，与官方集同一指标口径
- [x] **难例集 Quality Gate 对照实测**：`0.70` 下 No-answer `2/8 = 25%` **FAIL** → `0.50` 下 `8/8 = 100%` **PASS**

**新增：答案质量层与前提校验** —— `OPT-005` / `OPT-006` / `OPT-012`

- [x] 答案质量评测层已建立（`evals/answer_cases.jsonl` 7 条 + `run_answer_quality_eval.py`）
- [x] 答案质量评测 **7/7 = 100%**（`boundary` 1/1、`no_answer` 1/1、`normal` 3/3、`wrong_premise` 2/2）
- [x] 前提校验端到端：检出 **2/2**、误报 **0/12**
- [x] 前提校验纯函数单测 **17/17**（`tests/test_fact_check.py`，零成本）
- [x] 所有指标均注明为 controlled regression / smoke-test 结果

**新增：可观测性** —— `OPT-013`

- [x] `trace_id` 串联 4 个日志（检索 / 工作流 / 审批 / 前提校验）
- [x] `show_trace.py` 可按 `trace_id` 还原单次会话完整链路

## 5. 改造与创新

> 与 `innovation.md` 一一对应。面试前逐条过一遍，每条都能讲出「问题 → 做法 → 数据 → 边界」。

| 编号        | 优化点                      | 层面   | 状态  |
| --------- | ------------------------ | ---- | --- |
| `OPT-001` | RAG 检索阈值标定：0.70 → 0.50   | 检索层  | ✅   |
| `OPT-002` | 难例对照测试集：5 条 → 25 条        | 评测层  | ✅   |
| `OPT-003` | 阈值标定工具链（probe + sweep）   | 评测层  | ✅   |
| `OPT-004` | 修正对照集标注错误（自我纠错）          | 评测层  | ✅   |
| `OPT-005` | 生成层前提校验 · Prompt 约束      | 生成层  | ✅   |
| `OPT-006` | 生成层前提校验 · 确定性答后校验        | 生成层  | ✅   |
| `OPT-007` | 统一难例评测脚本                 | 评测层  | ✅   |
| `OPT-008` | 只读数据库 / 日志查看器            | 工程层  | ✅   |
| `OPT-009` | VSCode 开发环境配置            | 工程层  | ✅   |
| `OPT-010` | 注释从"复述语法"改为"解释意图"        | 工程层  | ✅   |
| `OPT-011` | 扩充对照集（多意图 / 超短问句 / 口径冲突） | 评测层  | ✅   |
| `OPT-012` | 答案质量评测                   | 评测层  | ✅   |
| `OPT-013` | 统一调用链路追踪（Tracing）        | 可观测层 | ✅   |
| `OPT-014` | Prompt 外置为 YAML 场景包      | 工程层  | ✅   |

## 6. Demo 展示顺序

建议使用以下顺序录制或现场演示：

1. 启动 Agent，展示普通政策问答（带来源引用）。
2. 展示订单查询，说明业务数据来自 Tool 和 SQLite。
3. 展示物流异常 Workflow，说明确定性规则和幂等检查。
4. 展示 HITL：先 reject，证明数据库不发生写入。
5. 再 approve，证明写操作在人工批准后执行。
6. **★ 展示前提校验**：提问「我听说你们退款要30天是真的吗」，展示模型**指出用户前提有误并给出正确数字**（3~7 个工作日），同时控制台打印 `[FactCheck]` 标记。
7. **★ 展示阈值改造对比**：跑 `evals/probe_threshold.py` 展示距离分布与标定表；跑 `evals/run_rag_eval_hard.py` 展示难例集 PASS。
8. **★ 展示链路还原**：抄下一轮对话的 `[trace_id]`，用 `show_trace.py` 还原文档、工作流与审批的完整链路。
9. 运行统一 Eval，展示 `5/5 PASS` 和 `Release Gate = READY`。

> **第 4、5、6 步是整个演示的高潮。** 绝大多数候选人的演示到第 2 步就没了；能演到"主动纠正用户错误前提"这一层的极少。

## 7. 简历与面试统一表述

- [ ] 简历使用 AI 产品经理版或技术向 AI PM 版项目描述
- [ ] 统一使用：RAG Top1 官方集 `100%`（`4/4`）
- [ ] 统一使用：`5` 类 Eval、**`25`** 个 controlled cases
- [ ] 统一使用：`5/5 Eval Suites PASS`、`Release Gate = READY`
- [ ] **统一使用（新增）**：`MAX_DISTANCE` `0.70 → 0.50`，域外漏过 **`6/8 (75%) → 0/8`**，域内误杀 **`0/17`**
- [ ] **统一使用（新增）**：域内上界 `0.4652` / 域外下界 `0.5690` / 分离空隙 `0.1038`
- [ ] **统一使用（新增）**：**`25`** 条难例对照集（域内 17 + 域外 8）
- [ ] **统一使用（新增）**：发现官方评测集对 `MAX_DISTANCE` **零敏感**（`0.40~0.70` 指标恒定 `100%`）
- [ ] **统一使用（新增）**：前提校验端到端 检出 `2/2`、误报 `0/12`；答案质量评测 `7/7`
- [ ] 不声称生产准确率 100%
- [ ] 不声称用户解决率、效率提升或成本下降，除非后续有真实数据
- [ ] **不把"改了阈值"讲成"系统变好了"** —— 要讲清检索层的边界：错误前提这类问题检索层无解，已分层到生成层处理

## 8. 最终收官标准

SupportPilot 可视为完成收官，当以下条件全部满足：

- [ ] `origin` 指向自己的仓库，`main` 分支与 tag `v0.1.0` 已推送
- [ ] GitHub 仓库可正常打开和阅读，README 已标注复现来源
- [x] `innovation.md` 中所有条目的「数据」字段都已填上实测数字（无 `⏳ 待补`）
- [x] `OPT-006` 答后校验模块实现完成并产出 `data/logs/premise_conflict.jsonl`
- [x] `OPT-007` 难例评测脚本完成，拿到 `0.70` FAIL → `0.50` PASS 的对照结果
- [ ] README 启动说明可被新用户复现
- [ ] Demo 能完整展示 Agent、Workflow、HITL、前提校验与可观测性
- [ ] 简历、README、`innovation.md`、`docs/OPTIMIZATION_GUIDE.md` 使用**同一套指标**

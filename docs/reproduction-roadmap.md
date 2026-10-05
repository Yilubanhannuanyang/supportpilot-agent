# SupportPilot 从零复现路线图（新手版）


> 📌 **本文档是面向新手的复现总纲**（环境搭建 → 业务理解 → 分步复现 → 自主改造）。
> 想直接看「这一版改了什么、怎么验证」，请读 [`OPTIMIZATION_GUIDE.md`](OPTIMIZATION_GUIDE.md)。
> 文档中的「你」均指读者本人。
> 面向对象：只有学校期末考试级 Python 基础，没用过虚拟环境 / Git / 向量数据库 / LLM API  
> 目标：完整跑通 `https://github.com/Chenmaolin-maker/supportpilot-agent`，做 2-3 个差异化改造，包装成可写进简历的项目  
> 目标岗位：中小厂 Agent / LLM 应用开发实习

---

## 0. 先读这一页（5 分钟）

### 0.1 这个项目到底是什么

一句话：**一个「企业智能客服」的 AI Agent 后端**。用户用自然语言问客服问题，系统能查订单、查工单、查企业政策、开售后工单，并且**开单这类改动数据的危险操作必须经过人工点「批准」才会真的执行**。

它的技术含量不在"会聊天"，而在**把大模型圈在可控的框子里**：

| 能力                             | 通俗解释                                 |
| ------------------------------ | ------------------------------------ |
| Tool Calling（工具调用）             | 模型自己不会查数据库，但它会"喊"程序去查，程序查完把结果交给它     |
| RAG（检索增强生成）                    | 答政策问题前先去企业文档里翻资料，翻到才答，翻不到就说不知道       |
| Deterministic Workflow（确定性工作流） | 物流超时这种有明确规则的流程，用 if/else 写死，不让模型自由发挥 |
| HITL（Human-in-the-loop，人工介入）   | 写操作（建工单、改状态）必须人工点批准                  |
| Observability（可观测性）            | 每一步都写日志，出问题能查是哪一步断的                  |
| Multi-layer Eval（多层评测）         | 5 套测试脚本，跑通了才允许发版                     |

**规模**：真实代码约 2000 行以内，11 个 Python 源文件。对新手来说"能读懂"是第一位的，这个体量刚好。

### 0.2 你需要提前准备的清单

**必须有的账号 / 工具**

| 项目               | 说明                                     | 费用  |
| ---------------- | -------------------------------------- | --- |
| Python 3.12      | 版本不能凑合，README 明确要求                     | 免费  |
| DeepSeek API Key | 注册 platform.deepseek.com，实名后创建 API Key | 见下方 |
| Git              | 用来克隆仓库，也是简历技能项                         | 免费  |
| 代码编辑器            | VS Code 最合适（新手友好）                      | 免费  |
| 磁盘空间             | 依赖 + Embedding 模型，预留 5GB 以上            | —   |

**费用说明（请以官网实时页面为准）**

- DeepSeek **注册通常有赠送额度**（历史上是百万级 tokens、30 天有效），足够你完整复现 + 反复调试。先注册看有没有，没有再充值。
- 充值**建议先充 10 元人民币**，不要多充。原因：这个项目单次对话消耗极小（prompt 短、工具返回也短），10 元足够你跑几百次对话 + 几十轮全量评测。
- DeepSeek 按 tokens（模型的"字数"计量单位）计费，输入和输出分开算，输出更贵。它的 API 有几档模型，便宜的档位和贵的档位价差有几十倍。
- **不要一上来就用贵档模型**。这个项目的任务（意图判断、工具选择）用便宜档完全够。等你要做改造、需要更强推理时再切。
- **Embedding 模型是本地跑的，不花钱**，但要下载约 100MB 的模型文件。

**必须提前知道的一件事：网络**

`sentence-transformers` 默认从 HuggingFace 下载模型，国内直连经常超时。提前准备好镜像环境变量（第 1.6 节会给命令）。

### 0.3 你**不需要**准备的东西

- ❌ 不需要 GPU。Embedding 模型很小（small 档），CPU 跑得动。
- ❌ 不需要 Docker、K8s、Nginx 这些运维东西。
- ❌ 不需要自己搭向量数据库服务器。这个项目用的是 ChromaDB 的**本地文件模式**，数据就存在一个文件夹里。
- ❌ 不需要 PostgreSQL。它用 Python 内置的 SQLite（一个文件就是一个数据库）。

### 0.4 复现总览

| 阶段 | 内容   | 产出                      |
| -- | ---- | ----------------------- |
| 一  | 环境准备 | `python run.py` 能启动     |
| 二  | 业务理解 | 能对着代码讲清 6 个环节           |
| 三  | 分步复现 | 5 个模块逐个跑通 + 5 套评测全 PASS |
| 四  | 自主改造 | 3 个差异化增强点               |
| 五  | 简历包装 | 项目描述 + 面试问答稿            |

---

## 1. 阶段一：环境准备

### 1.1 安装 Python 3.12

**做什么**：装一个 3.12.x 的 Python（3.12.0 到 3.12.10 都行）。

**为什么不能用你现在的 Python**：如果你系统里是 3.8 或 3.13，项目的依赖（尤其 `sentence-transformers`、`onnxruntime`）可能没有对应版本的预编译包，会退化成"从源码编译"，那基本等于失败。**3.12 是这个项目官方验证过的版本。**

Windows 上到 python.org 下载 3.12 的安装包，安装时务必勾选 `Add Python to PATH`。

**验证**：

```bash
python --version
```

预期输出：`Python 3.12.x`

**⚠️ 你电脑上有多个 Python 版本，这本身就是个陷阱。** 先把它们全部列出来，心里有数：

```bash
py -0p
```

**核心规则（务必记住）：`pip install` 装进哪个 Python，取决于你敲的 `python` 到底是谁，而不是你"想要"哪个版本。** 第 1.2 节会用完整路径把这个不确定性彻底消除。

> 💡 **补充：`py -3.12` 这种写法不一定可用。** 它只在 py 启动器能识别该版本 tag 时有效。如果 3.12 是通过 `uv` 安装的，tag 会显示成 `Astral/CPython3.12.14` 这种形式，跑 `py -3.12` 会直接报 `No suitable Python runtime found`——**必须用完整路径调用**。

---

### 1.2 建立虚拟环境

**虚拟环境是什么（类比）**：像给每个项目单独发一个**工具箱**。项目 A 要螺丝刀，项目 B 要扳手，如果都用同一个大工具箱，两个项目的工具会打架（比如 A 要 pydantic 第 1 版，B 要第 2 版，装在一起必崩）。虚拟环境就是每个项目一个独立小箱子，互不干扰。

**为什么必须做**：这个项目的依赖里包含 `pydantic`、`openai` 这类"版本敏感"的库，且 `requirements.txt` **没有锁死版本号**。一旦污染全局环境，你以后修都修不好。

**命令（逐条执行）**：

```bash
cd D:/你的工作目录
mkdir supportpilot-agent
cd supportpilot-agent
```

**⚠️⚠️ 下一步是最容易出错的地方，千万别照抄 README 里那句 `python -m venv .venv`。**

`python -m venv .venv` 用的是"PATH 里排第一的那个 python"。如果你的 PATH 第一位是 miniconda（很常见），它会闷声不响地给你建一个 **Python 3.8 的环境**——然后所有依赖都装不上。

> **这是已经在真实机器上验证过的事故**，报错长这样，且**极难从字面看出病因**：
>
> ```
> ERROR: Ignored the following yanked versions: 0.0.1
> ERROR: Could not find a version that satisfies the requirement openai-agents (from versions: none)
> ERROR: No matching distribution found for openai-agents
> ```
>
> 看起来像"镜像没有这个包"，实际上是"你的 Python 太老，pip 筛完一个不剩"。

**正确做法：显式写出 3.12 解释器的完整路径。**

```bash
cd D:/你的工作目录/supportpilot-agent

# 把下面这个路径换成你自己机器上 3.12 的实际路径
& "C:/path/to/Python312/python.exe" -m venv .venv
```

Git Bash 写法（不加 `&`）：

```bash
"C:/path/to/Python312/python.exe" -m venv .venv
```

**不知道怎么填路径？** 跑 `py -0p`，找到 `-V:3.12` 那一行，把右边的路径整个抄过来。例如本机实测可用的路径是：

```
C:\Users\jiangjunbao\AppData\Roaming\uv\python\cpython-3.12.14-windows-x86_64-none\python.exe
```

**逐条作用**：

- `python.exe -m venv .venv` —— 用**这个指定的解释器**在当前目录建一个叫 `.venv` 的虚拟环境文件夹。`.venv` 是社区惯例命名，VS Code 能自动识别。

**建完立刻验证（这一步不能省）**：

```bash
./.venv/Scripts/python.exe --version      # Git Bash
.\.venv\Scripts\python.exe --version      # PowerShell / CMD
```

**必须显示 `Python 3.12.x`。如果不是，立刻删掉 `.venv` 重建，不要抱侥幸心理往下走**——后面每一个报错都会把你指向错误的方向。

**发现版本错了怎么重来**：

```bash
# 先改名备份（比直接删安全，可回退）
mv .venv .venv-废弃的旧版本

# 再用正确路径重建
"C:/path/to/Python312/python.exe" -m venv .venv
./.venv/Scripts/python.exe --version       # 再验一次
```

---

#### ❓ 常见困惑：`conda env list` 里看不到 `.venv`，是不是没建成功？

**不是。这是新手最容易绕进去的一个坑。**

```powershell
conda env list
# 输出只有 base / langchain1.2 / minist / qwen ...
# 完全没有 .venv 的影子
```

**原因**：`conda` 只认它自己创建的环境。`.venv` 是 Python 标准库 `venv` 创建的**另一种**虚拟环境，两者是两套独立体系，**互相看不见**。

> 类比：`conda env list` 是你家小区物业的花名册，`.venv` 是你自己租的办公室——物业花名册上当然没有它，但它确实存在。

**正确的三种验证方式（任选一个）**

PowerShell（你当前用的）：

```powershell
# 方式 1：看目录里有没有这个文件夹
Get-ChildItem -Force -Directory .venv*

# 方式 2：看它的配置文件（这是虚拟环境的"身份证"）
Get-Content .venv\pyvenv.cfg
# 应看到 version = 3.12.x 以及 home = ...cpython-3.12.x...

# 方式 3：最直接 —— 问它自己的 python 版本
.\.venv\Scripts\python.exe --version
```

Git Bash：

```bash
ls -d .venv*
cat .venv/pyvenv.cfg
./.venv/Scripts/python.exe --version
```

`pyvenv.cfg` 是这个虚拟环境最权威的证据，内容长这样：

```ini
home = C:\...\cpython-3.12.14-windows-x86_64-none
include-system-site-packages = false
version = 3.12.14
executable = C:\...\cpython-3.12.14-windows-x86_64-none\python.exe
command = C:\...\python.exe -m venv D:\...\supportpilot-agent\.venv
```

**最后一行 `command=` 记录了它是用什么命令建出来的**——如果这里显示的是 3.8 的路径，说明你抓错解释器了。

---

#### 💡 PowerShell 专属：其实你可以不激活虚拟环境

激活虚拟环境，本质只是把 `.venv\Scripts` 临时插到 PATH 最前面。**你也可以直接用完整路径调用它，效果完全一样，还能免掉执行策略的麻烦**：

```powershell
.\.venv\Scripts\python.exe run.py
```

`run.py` 内部有 `sys.path.insert(0, SRC_DIR)`，所以能正确 import 到 `src/` 下的项目代码。**这条路最不容易出错，推荐新手直接用。**

**如果激活时报"禁止运行脚本"**：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

`-Scope Process` 只对当前窗口生效，关掉就失效，比改全局策略安全得多。

---

#### 让 VSCode 正确使用这个虚拟环境

建好 `.venv` 之后，VSCode 可能还记着旧解释器，或者压根不知道该用哪个。两件事要做。

**① 建一个 `.vscode/settings.json`**（放项目根目录；`.gitignore` 已忽略 `.vscode/`，不会提交）

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
  "python.terminal.activateEnvironment": true,
  "python.analysis.extraPaths": ["./src"],
  "python.autoComplete.extraPaths": ["./src"],
  "files.encoding": "utf8",
  "python.testing.pytestEnabled": false
}
```

每一条的作用：

| 配置                                   | 作用                          | 不加会怎样                                                  |
| ------------------------------------ | --------------------------- | ------------------------------------------------------ |
| `defaultInterpreterPath`             | 指定用 `.venv` 里的 Python 3.12  | VSCode 可能挑到系统或 conda 的旧 Python                         |
| `terminal.activateEnvironment`       | 新开终端自动激活 `.venv`            | 终端里敲 `python` 用的是全局版本                                  |
| **`analysis.extraPaths: ["./src"]`** | **让 Pylance 认识 `src/` 下的包** | `from supportpilot.agent import ...` **满屏红线**，但程序其实跑得通 |
| `autoComplete.extraPaths`            | 同上，管自动补全                    | 补全提示不出来                                                |
| `files.encoding: utf8`               | 项目全是中文，防乱码                  | Windows 默认可能按 GBK 处理                                   |
| `testing.pytestEnabled: false`       | 关掉 pytest 自动发现              | 项目没有 `tests/` 目录，VSCode 会一直提示"未找到测试"                   |

> 💡 **标粗那条是重点。** 这个项目用的是 `src/` 布局，代码里写的是 `from supportpilot.agent import ...`。VSCode 的静态分析器默认**不知道 `src/` 是源码根目录**，于是会把每一个 import 都标成红线——**但代码其实完全跑得通**（`run.py` 里有 `sys.path.insert(0, SRC_DIR)` 兜底）。
>
> **不知道这一点的人，会以为项目是坏的，然后去乱改代码。** 加上这行红线就消失了。

**② 重启 VSCode，再手动确认一次**

`defaultInterpreterPath` **只在"这个工作区还没手动选过解释器"时生效**。如果你之前选过，它会被忽略，必须手动覆盖：

1. 按 `Ctrl + Shift + P` 打开命令面板
2. 输入 `Python: Select Interpreter`
3. 选 `Enter interpreter path...` → `Find...`
4. 定位到：`D:\workbuddy_workplace\日常学习\supportpilot-agent\.venv\Scripts\python.exe`

**验证成功的标志**：VSCode 右下角状态栏显示

```
Python 3.12.14 ('.venv': venv)
```

**③ 检查 VSCode 打开的是哪个文件夹**

必须打开**项目根目录** `supportpilot-agent`，**不能打开它的上级目录** `日常学习`。原因有两个：

- `.venv` 就在项目根目录下，打开上级目录 VSCode 扫不到它
- `data/chroma`、`data/knowledge` 这些全是**相对路径**，从上级目录运行会**静默失败**（不报错，但检索不到任何东西）

**激活虚拟环境**：

Git Bash（你当前用的）：

```bash
source .venv/Scripts/activate
```

PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

CMD：

```cmd
.venv\Scripts\activate.bat
```

**怎么知道激活成功了**：命令行提示符前面会多出 `(.venv)`。

> ⚠️ **新手最容易犯的错**：关了终端窗口，虚拟环境就"没了"（其实还在，只是没激活）。**每次新开终端，都要重新激活一次**，然后再跑任何 Python 命令。判断方法就是看有没有 `(.venv)` 前缀。

---

### 1.3 拿到代码

**方式 A：Git 克隆（推荐，顺便练 Git）**

```bash
git clone https://github.com/Chenmaolin-maker/supportpilot-agent.git temp
```

然后把 `temp` 里的文件全部移到 `supportpilot-agent` 根目录（因为你已经在这个目录建了 `.venv`），再删掉空的 `temp`。

**方式 B（更简单）**：直接在 GitHub 页面点 `Code` → `Download ZIP`，解压后把内容放进你的工作目录。够用。

**顺便看一眼 `.gitignore`**：它写了哪些文件不进 Git。预期输出 `.env`、`supportpilot.db`、`data/chroma/`、`data/logs/` 都在里面——这告诉你哪些是"本地生成物"，也告诉你**密钥绝对不能提交**。

---

### 1.4 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

第一条：升级 pip 自己（老版本 pip 装新包会报奇怪的错）。  
第二条：按清单装全部依赖。

**requirements.txt 里的 7 个包是干嘛的**：

| 包                       | 作用                                                  |
| ----------------------- | --------------------------------------------------- |
| `openai-agents`         | **核心**。Agent 框架，提供 `Agent`、`Runner`、`function_tool` |
| `python-dotenv`         | 读取 `.env` 文件里的密钥到环境变量                               |
| `pydantic`              | 数据校验（Agent SDK 的底层依赖）                               |
| `pytest`                | 测试框架（注意：项目其实没用它，见 6.6）                              |
| `chromadb`              | 向量数据库（本地文件模式）                                       |
| `sentence-transformers` | 把文字转成向量（embedding）                                  |
| `onnxruntime`           | 加速推理后端                                              |


**预期耗时**：5-15 分钟。`chromadb` 和 `onnxruntime` 体积大，还会拉一堆 `numpy`、`torch` 系的依赖，慢是正常的。

> 如果卡在某个包，先换国内镜像源：
>
> ```bash
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

> ⚠️ **懒人注意**：`sentence-transformers` 会连带装 PyTorch，可能几个 GB。这是本项目最大的空间占用来源。

---

### 1.5 申请 API Key 并配置 `.env`

**第一步：拿 Key**

1. 打开 platform.deepseek.com，注册 + 实名
2. 进"API Keys"页面，创建新 Key
3. **创建后立刻复制保存**——页面关闭就再也看不到完整 Key 了
4. 看一下账户余额/赠送额度

**第二步：创建配置文件**

仓库里只有 `.env.example`（模板），**没有 `.env`**。你必须自己建。

在项目根目录新建文件 `.env`（注意前面有个点，没有扩展名），内容：

```
DEEPSEEK_API_KEY=sk-你刚复制的那一串
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
OPENAI_API_KEY=随便填或留空
```

**⚠️ `.env` 是"纯配置文件"，不是命令行 —— 这是新手最容易踩、且报错最有误导性的一个坑**

它只有一条规则：**每行一个 `KEY=VALUE`，除此之外什么都不能写**。

**真实事故（实测遇到的）**：把启动命令和 Key 粘到了同一行，中间漏了换行：

```
.\.venv\Scripts\python.exe run.pyDEEPSEEK_API_KEY=sk-＜此处是真实密钥＞
                                    ↑ 漏了换行，两行粘一起了
```

结果 python-dotenv 解析出的变量名是 `.\.venv\Scripts\python.exe run.pyDEEPSEEK_API_KEY`——**这根本不是合法变量名**，于是 `DEEPSEEK_API_KEY` 读出来是 `None`，验证命令打印"没读到"。

**这个报错极具误导性**：表面看像是 Key 填错了，实际是文件里混进了一行垃圾。所以——**遇到"没读到"，第一件事是把整个 `.env` 用编辑器打开逐行看，而不是怀疑 Key 有问题。**

**几条铁律**：

| 规则                | 反例（会出错）                                           |
| ----------------- | ------------------------------------------------- |
| 一行一个变量            | `KEY1=a KEY2=b` 挤在一行                              |
| `=` 两边不要加空格       | `DEEPSEEK_API_KEY = sk-xxx`                       |
| 不要写 `export`      | `export DEEPSEEK_API_KEY=sk-xxx`                  |
| 值不要加引号            | `KEY="sk-xxx"`                                    |
| 不要在值后面写注释         | `KEY=sk-xxx  # 我的key`（注释会被当成值的一部分）                |
| 不要混入任何命令行         | `.\.venv\Scripts\python.exe run.py` ← **这个绝对不能有** |
| 文件放项目根目录          | `load_dotenv()` 默认从当前工作目录找 `.env`                 |
| 保存为 UTF-8（不带 BOM） | 记事本另存为时选错成"UTF-8 带 BOM"                           |

**验证（建完立刻跑，必须显示"读到了"）**：

```bash
cd D:/workbuddy_workplace/日常学习/supportpilot-agent
./.venv/Scripts/python.exe -c "from dotenv import load_dotenv; import os; load_dotenv(); k=os.getenv('DEEPSEEK_API_KEY'); print('Key 读到了' if k and k.startswith('sk-') else '没读到')"
```

**输出"没读到"，按这个顺序排查**：

1. 用编辑器打开 `.env`，**逐行看有没有多余内容**（最常见，占九成）
2. 确认文件名真的是 `.env` 而不是 `.env.txt`（Windows 默认隐藏扩展名）
3. 确认文件在**项目根目录**，且命令也是从项目根目录执行的
4. 文件编码是 UTF-8（用十六进制看开头，如果以 `ff fe` 开头就是 UTF-16，会解析失败）

**为什么要这么配**：

- `DEEPSEEK_BASE_URL` —— DeepSeek 提供了一个"和 OpenAI 长得一模一样"的接口。所以代码里可以用 OpenAI 的客户端，只是把地址指向 DeepSeek。这叫 **OpenAI 兼容接口**，是行业惯例，好处是将来换模型厂商只改这一行。
- `DEEPSEEK_MODEL` —— ⚠️ **这一行是最大的不确定性，我已实测过**。DeepSeek 在 2026 年多次调价和改名。**实测结论：`deepseek-chat` 目前仍然可用**，但它是**别名**——API 响应里的 `model` 字段返回的是 `deepseek-flash`，也就是说实际调用的是 Flash 档模型。如果哪天这个别名被废弃、报 `model not found`，就去 DeepSeek 官方文档的"模型列表"页查当前推荐的名字替换这一行。**想知道自己到底在用哪个模型，就看响应的 `model` 字段，别只看你请求时写了什么。**
- `OPENAI_API_KEY` —— 代码里没实际用到，留着是为了兼容。填 `sk-placeholder` 都能跑。
- `config.py` 里有一行 `set_tracing_disabled(True)` —— 这是把 Agent SDK 默认要上传到 OpenAI 的追踪数据关掉。**没有这行，你会因为没配 OpenAI Key 而报错**。作者已经处理好了，你不需要动。

**验证**：文件保存后，在项目根目录跑：

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); k=os.getenv('DEEPSEEK_API_KEY'); print('Key 读到了' if k and k.startswith('sk-') else '没读到')"
```

---

### 1.6 提前下载 Embedding 模型

**Embedding 是什么（类比）**：把一句话变成一串数字（比如 512 个小数）。语义相近的句子，变出来的数字串也相近。这样就能用"数字距离"来找"意思最像"的文档。

**为什么要提前单独下载**：模型有 100MB 左右，在第一次检索时下载，如果失败，预期输出一个跟"检索"完全无关的报错，很难排查。提前下载能把问题隔离出来。

**命令（国内务必带镜像）**：

Git Bash：

```bash
export HF_ENDPOINT=https://hf-mirror.com
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('BAAI/bge-small-zh-v1.5'); print('模型加载成功，维度：', m.get_sentence_embedding_dimension())"
```

PowerShell：

```powershell
$env:HF_ENDPOINT="https://hf-mirror.com"
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('BAAI/bge-small-zh-v1.5'); print('模型加载成功，维度：', m.get_sentence_embedding_dimension())"
```

**预期输出**：类似 `模型加载成功，维度： 512`

**注意**：`HF_ENDPOINT` 这个环境变量**只在当前终端窗口有效**。你后面每次开新终端跑项目，如果报网络错，就重新 export 一次。想省事可以在 `.env` 里也写一份（虽然 `dotenv` 不会自动导给 HuggingFace，但方便你自己复制）。

---

### 1.7 目录结构与模块职责

这是我按仓库真实代码整理的，照着 `ls` 对一遍：

```
supportpilot-agent/
├── run.py                          ← 程序入口（命令行交互 + 意图路由 + 人工审批）
├── requirements.txt                依赖清单
├── .env.example / .env             配置模板 / 你的真实配置
├── .gitignore
├── AGENTS.md                       开发规范（作者写给 AI 协作者的）
├── PORTFOLIO_CHECKLIST.md          作者自用的"求职项目收官清单"★值得读
├── README.md
│
├── data/
│   ├── knowledge/                  ★ 知识库原始文档（4 个 .txt）
│   │   ├── refund_policy.txt       退款政策
│   │   ├── return_policy.txt       退换货政策
│   │   ├── shipping_policy.txt     物流政策
│   │   └── membership_policy.txt   会员权益
│   ├── chroma/                     向量库落盘目录（首次 ingest 后生成）
│   └── logs/                       所有日志（JSONL 格式）
│       ├── rag_retrieval.jsonl     RAG 每次检索记录
│       ├── workflow_trace.jsonl    Workflow 执行轨迹
│       ├── approval_log.jsonl      人工审批审计日志
│       ├── eval_failures.jsonl     评测失败用例
│       └── eval_regression.jsonl   回归历史
│
├── src/supportpilot/               ★ 核心代码（13 个文件）
│   ├── __init__.py
│   ├── config.py                   读 .env → 创建 DeepSeek 模型客户端
│   ├── agent.py                    Agent 定义：人设 prompt + 挂载 5 个工具
│   ├── db.py                       SQLite：建表 + 种子数据 + 6 个数据访问函数
│   ├── rag/
│   │   ├── chunker.py              读 txt → 切成知识片段（chunk）
│   │   ├── embedder.py             文字 → 向量（教学用，ingest 里复用了逻辑）
│   │   ├── ingest.py               ★ 建库：把 chunk 写进 ChromaDB
│   │   └── retriever.py            ★ 检索：查 ChromaDB + 距离阈值过滤 + 日志
│   ├── tools/
│   │   ├── order_tools.py          get_order_status（只读）
│   │   ├── ticket_tools.py         create_ticket / get_ticket_status / update_ticket_status
│   │   └── kb_tools.py             search_knowledge_base（把 RAG 包装成工具）
│   └── workflows/
│       └── shipping_workflow.py    ★ 物流异常确定性流程 + 幂等 + HITL 状态机
│
└── evals/                          ★ 5 套评测（共 26 个用例）
    ├── rag_cases.jsonl + run_rag_eval.py            5 个（含 1 个"不该答"用例）
    ├── workflow_cases.jsonl + run_workflow_eval.py  4 个
    ├── hitl_cases.jsonl + run_hitl_eval.py          5 个
    ├── agent_tool_cases.jsonl + run_agent_tool_eval.py  4 个
    ├── route_cases.jsonl + run_route_eval.py        8 个
    ├── eval_logging.py                              评测日志公共模块
    ├── run_all_evals.py                             ★ 一键跑全部
    └── eval_report.md                               自动生成的报告
```

**三层架构一句话总结**：

- `tools/` 和 `db.py` = **手**（真正干活、真正碰数据）
- `agent.py` = **嘴和脑子**（理解人话、决定喊哪只手）
- `workflows/` = **流程手册**（有明确规则的活儿，不交给脑子自由发挥）

---

### 1.8 三个自检命令（阶段一验收）

按顺序跑，三个都过，说明环境没问题。

```bash
# 自检 1：数据库建表 + 种子数据（4 条测试订单 A1001~A1004）
python -c "import sys; sys.path.insert(0,'src'); from supportpilot.db import init_db; init_db(); print('数据库初始化完成')"
```

预期：生成 `supportpilot.db` 文件，打印"数据库初始化完成"。

```bash
# 自检 2：建知识库（⚠️ 这一步 README 没写，但不做后面必崩）
## 1. 显式设置当前终端的环境变量，把 src 目录加入 Python 搜索路径$env:PYTHONPATH="src" 2. 以模块化的方式运行 supportpilot/rag 目录下的 ingest.py 文件python -m supportpilot.rag.ingest
$env:PYTHONPATH="src"; python -m supportpilot.rag.ingest
```

预期：打印 `已写入 N 个 chunks。`（N 大概在 10-20 之间）

```bash
# 自检 3：单独测检索，不花钱、不调模型
## 1. 显式设置当前终端的环境变量，把 src 目录加入 Python 搜索路径$env:PYTHONPATH="src" 2. 以模块化的方式运行 supportpilot/rag 目录下的 retriever.py 文件python -m supportpilot.rag.retriever
 $env:PYTHONPATH="src"; python -m supportpilot.rag.retriever
```

然后手动输入问题，比如：`退款多久到账`  
预期：打印若干行 `[Retriever] distance=0.xxxx, source=xxx.txt, passed=True/False`，然后列出检索到的内容。

> ⚠️ **自检 2 和 3 必须在项目根目录执行**。因为 `retriever.py` 里写的是相对路径 `data/chroma`、`data/knowledge`。在别的目录跑，它会"很乖地"创建一个空目录然后告诉你"没找到知识库内容"——不报错，但结果是错的。这是新手最容易被骗过去的地方。

---

## 2. 阶段二：业务理解

> 先别急着写代码。**这一节决定了你面试时是"我照着教程跑了一遍"还是"我懂这个系统"**。

### 2.1 真实客服场景长什么样

想象一家电商公司的客服中心。用户发来一句话，背后其实有 6 类完全不同的处理方式：

| 用户说的话             | 真实该走的流程                  | 难点                               |
| ----------------- | ------------------------ | -------------------------------- |
| "我的订单 A1001 到哪了？" | 查订单系统                    | 要识别出订单号，不能瞎猜                     |
| "退款一般几天到账？"       | 查企业政策文档                  | **不能靠模型"我记得大概是7天"——必须翻文档，还要给出处** |
| "物流太慢了，都 3 天没发货了" | 走物流异常流程 → 判断是否超时 → 可能要开单 | 有明确规则、有副作用、不能重复开单                |
| "帮我开个售后工单"        | 开单 = **改动数据**            | 危险操作，必须人工批准                      |
| "你们家股票代码是多少？"     | 知识库里没有                   | 必须承认不知道，不能编                      |
| "我要投诉！转人工！"       | 转人工                      | 兜底策略                             |

**传统客服机器人 vs 这个项目的差别**：传统做法是把这些都塞进一个巨大的 prompt 里让模型自己看着办。结果是——它会编订单号、会凭记忆编政策、会"热心"地帮你改了工单状态。**这个项目的所有设计，都是为了堵这几个洞。**

它的 6 条设计原则（README 里有，我从代码里验证过确实落实了）：

1. **LLM 负责理解，代码负责规则** —— 超时判断是 `hours_since_payment > 48`，不是问模型
2. **业务数据必须走工具，不能走模型记忆**
3. **企业政策必须走 RAG，不能凭常识**
4. **高危写操作必须人工批准**
5. **先可观测，再谈自主**
6. **先评测通过，再谈发版**

### 2.2 核心链路：6 个环节

```
用户输入
  │
  ├─ ① 意图识别与路由 ──→ 是"物流异常"吗？
  │                        ├─ 是 → 走 ⑥ 确定性工作流
  │                        └─ 否 → 进入 ② Agent
  │
  ② Agent 编排（模型理解意图，决定喊哪个工具）
  │
  ├─ ③ 知识库检索 RAG ──→ 政策类问题走这里
  │
  ├─ ④ 工具调用 ──→ 查订单 / 查工单
  │
  ├─ ⑤ 写操作 → 人工审批闸门（HITL）→ 通过才写数据库
  │
  └─ ⑦ 答案生成与兜底 → 附来源引用；找不到就明说找不到
```

**对照代码**：

| 环节         | 文件                                                              | 关键函数 / 代码                                                                                                |
| ---------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| ① 意图识别与路由  | `run.py`                                                        | `should_run_shipping_workflow()` 关键词匹配；`extract_order_id()` 正则 `A\d+`；`/shipping A1004` 调试命令             |
| ② Agent 编排 | `agent.py`                                                      | `create_support_agent()`，一大段中文 `instructions` + 挂载 5 个 `tools`                                           |
| ②-模型接入     | `config.py`                                                     | `create_model()`，指向 DeepSeek                                                                             |
| ③ 知识库检索    | `rag/chunker.py` → `embedder.py` → `ingest.py` → `retriever.py` | `MAX_DISTANCE = 0.7` 是阈值；`top_k=3`                                                                       |
| ③-工具封装     | `tools/kb_tools.py`                                             | `@function_tool search_knowledge_base()`                                                                 |
| ④ 只读工具     | `tools/order_tools.py`、`tools/ticket_tools.py`                  | `get_order_status`、`get_ticket_status`                                                                   |
| ⑤ 写操作审批闸门  | `tools/ticket_tools.py`                                         | 返回 `[APPROVAL_REQUIRED]` 标记字符串，**而不是直接写库**                                                               |
| ⑤-审批执行     | `run.py`                                                        | `find_approval_request_from_run()` 从工具原始输出里捞出审批请求 → `handle_agent_write_approval()` 让用户输入 approve/reject |
| ⑥ 确定性工作流   | `workflows/shipping_workflow.py`                                | `run_shipping_workflow()` 状态机：查订单 → 查政策 → 判超时 → 幂等检查 → HITL                                              |
| ⑥-幂等控制     | `db.py` + workflow                                              | `find_open_ticket_by_order_and_type()`：同一订单未解决的同类工单只开一张                                                  |
| ⑦ 答案与兜底    | `agent.py`                                                      | instructions 里"知识库没找到就说暂未找到相关政策，不要自行编造"；"必须在回答末尾增加来源信息，来源只能用工具真实返回的"                                     |
| ⑧ 可观测性     | 三个 `.jsonl`                                                     | `rag_retrieval.jsonl` / `workflow_trace.jsonl` / `approval_log.jsonl`                                    |
| ⑨ 多层评测     | `evals/`                                                        | 5 套共 26 个用例，`run_all_evals.py` 一键跑                                                                       |


### 2.3 术语类比表（首次出现的术语都用这个理解）

| 术语                        | 类比                                 | 在这个项目里的具体体现                            |
| ------------------------- | ---------------------------------- | -------------------------------------- |
| **LLM / 大模型**             | 一个很会说话但**没有记忆、不能碰你数据库**的实习生        | DeepSeek 的 `deepseek-chat`             |
| **Token**                 | 模型的"计价字数单位"，中文大概 1 个字 ≈ 1 个 token  | 决定你的 API 账单                            |
| **Prompt / instructions** | 给实习生发的《岗位说明书》                      | `agent.py` 里那一大段中文                     |
| **Agent**                 | 会自己思考"我该用哪个工具"的实习生，而不是固定流程的脚本      | `create_support_agent()` 返回的对象         |
| **Tool Calling**          | 实习生喊："帮我查一下订单 A1001"，然后程序去查        | `@function_tool` 装饰的函数                 |
| **RAG**                   | **开卷考试**：先翻书再答题，而不是闭卷靠背            | `rag/` 整个文件夹                           |
| **Chunk / 切片**            | 把一本书撕成方便查阅的小纸条                     | `chunker.py`，本项目按段落切并给每段加上标题           |
| **Embedding / 向量**        | 把每张纸条换算成一串"语义坐标"，意思近的坐标就挨得近        | `BAAI/bge-small-zh-v1.5`               |
| **向量数据库**                 | 专门存这些"语义坐标"、能快速找"离我最近的"的仓库         | ChromaDB，落盘在 `data/chroma/`            |
| **距离阈值 MAX_DISTANCE**     | 及格线。距离太大 = 压根不相关，宁可说"没找到"          | `0.7`，超过就丢弃                            |
| **Workflow / 工作流**        | **流程图**：有明确规定、按步骤走、不让实习生自由发挥       | `shipping_workflow.py`                 |
| **HITL / 人工介入**           | 涉及"要签字"的操作，必须主管点批准                 | `[APPROVAL_REQUIRED]`                  |
| **幂等 / Idempotency**      | 同一件事重复做 10 次，结果和做 1 次一样（不会开 10 张单） | `find_open_ticket_by_order_and_type()` |
| **Observability**         | 行车记录仪。出事能回放                        | `.jsonl` 日志                            |
| **Eval / 评测**             | 期末考卷。改代码后重跑，防止"改好一个弄坏两个"（回归）       | `evals/` 5 套 26 题                      |
| **Release Gate**          | 及格线，全过才允许发版                        | 报告里的 `READY`                           |
| **JSONL**                 | 一种日志格式：一行一条 JSON，方便追加和逐行读          | 所有日志                                   |

---

## 3. 阶段三：分步复现

**核心方法**：每个模块都走「**做什么 → 为什么 → 如何验证**」三步。**每个模块验证通过再进下一个**，不要贪快。

---

### M0：底座（`config.py` + `db.py`）

**做什么**：让"模型能连上"和"数据能存"这两件底层事跑通。

**为什么先做这个**：所有上层能力都依赖这两件事。如果这里坏了，后面每一个模块报的错都会长得一样（连接失败 / 表不存在），你会查不出来。

**你要读的代码**：

- `config.py` 全文只有 25 行，务必逐行读。重点看 `AsyncOpenAI` 是怎么被"骗"去连 DeepSeek 的。
- `db.py` 的 `init_db()`：注意它建了 `orders` 和 `tickets` 两张表，插入了 4 条种子订单。注意 `ensure_orders_schema` 里那段 `ALTER TABLE ... ADD COLUMN hours_since_payment` —— 这是**数据库迁移**：老版本的表没有这个字段，代码发现没有就补上。这是真实的工程细节。

**验证**：

```bash
python -c "import sys; sys.path.insert(0,'src'); from supportpilot.db import init_db; init_db(); print('OK')"
```

然后用 Python 随手读一条数据（这是你自己加的验证，不花钱）：

```bash
python -c "import sys; sys.path.insert(0,'src'); from supportpilot.db import get_order_from_db; print(get_order_from_db('A1001'))"
```

**预期**：打印出张三、无线蓝牙耳机、已付款、等待仓库发货、预计 2 天内发货、72 小时。

> 这一步同时帮你确认了 `hours_since_payment=72` → 72 > 48，**所以 A1001 是"超时未发货"的订单**。记住这个数字，M4 会用到。

---

### M1：知识库与 RAG（最能体现技术深度，建议花最多时间）

这是整个项目**唯一真正的 AI 算法环节**，也是面试必问。拆成 4 小步，每步单独验证。

#### M1.1 切片 `chunker.py`

**做什么**：把 `data/knowledge/` 里 4 个 txt 切成小片段。

**为什么**：

- 一整篇政策文档塞给模型太浪费（贵、慢、还容易干扰）
- 切成小片段，检索时只把最相关的 3 片给模型，**又准又便宜**
- 它还做了一件聪明事：把第一行当"标题"，**把标题拼到每个片段前面**。这样片段被单独拎出来时，你依然知道它属于哪份政策

**关键参数**：`chunk_size=200`、`overlap=40`（重叠是为了防止答案刚好被切断）

**验证**：

```bash
$env:PYTHONPATH="src";python src/supportpilot/rag/chunker.py
```

**预期**：打印 `共生成 N 个 chunks。`，然后逐个列出 ID、来源、内容。预期输出每个片段开头都重复着同一份政策标题。

> 💡 **动手改一下再跑**：把 `chunk_size` 改成 100，看 chunks 数量怎么变。亲手体会"切片粒度"这个概念，面试时你就有真话可说了。

#### M1.2 向量化 `embedder.py`

**做什么**：把每个片段变成一串数字。

**为什么单独有这个文件**：它是个**教学文件**，代码里没被主流程调用（`ingest.py` 自己重建了 embedding 函数）。它的价值是让你打印出"文字变成数字"的实际结果。

**验证**：

```bash
$env:PYTHONPATH="src"; python -m supportpilot.rag.embedder
```

实际：

```
Chunk 数量：21
Embedding 数量：21
单个

第一个 Chunk：
SupportPilot 商城会员政策

1. 普通会员享受基础售后服务。

第一个 Embedding 前 15 个数字：
[-0.0061717  -0.02393849  0.07263745  0.03441189 -0.00678008 -0.05315965
 -0.08542333  0.0061838   0.00560234 -0.00053202  0.06050297 -0.3238906
  0.01982283 -0.00243555 -0.01560238]
```

看到那串小数，你就真正理解了"向量"是什么。

#### M1.3 建库 `ingest.py`

**做什么**：把片段 + 向量 + 来源文件名，一起写进 ChromaDB。

**为什么用 `upsert` 而不是 `insert`**：`upsert` = update + insert，**重复跑不会产生重复数据**。这就是幂等思想在数据层的体现。

**验证**：

```bash
$env:PYTHONPATH="src"; python -m supportpilot.rag.ingest
```

**预期**：`已写入 N 个 chunks。` + 模型名 + 路径。

**再验证一次**：把同一个命令**再跑一遍**，然后检查 `data/chroma/` 目录大小没有翻倍、检索结果里没有重复内容。这证明幂等生效了。

#### M1.4 检索 `retriever.py`（★核心）

**做什么**：用户问题 → 向量 → 在库里找最近的 3 个 → **过滤掉距离 > 0.7 的** → 返回。

**为什么要有阈值（这是本模块最重要的设计）**：  
如果用户问"你们股票代码多少"，库里没有相关内容，但向量检索**一定会返回 3 个"最接近"的**（哪怕它们毫不相关）。没有阈值，模型就会拿着不相干的片段硬编一个答案——这就是幻觉。`MAX_DISTANCE = 0.7` 就是那道闸门：**不合格的片段直接扔掉，宁可返回空**。

**验证**：

```bash
$env:PYTHONPATH="src"; python -m supportpilot.rag.retriever
```

分别输入这三类问题，观察 `distance` 和 `passed` 的变化：

| 输入           | 预期现象                                                      |
| ------------ | --------------------------------------------------------- |
| `退款多久到账`     | 有 `passed=True` 的片段，source 是 `refund_policy.txt`，距离约 0.28 |
| `退货运费谁承担`    | 命中 `return_policy.txt`，距离约 0.31                           |
| `你们公司创始人是谁？` | **全部 `passed=False`**（距离约 0.74），最后打印"未找到足够相关的知识库内容"       |

第三类就是"兜底"能力的证据。

> ⚠️ **但这里有个陷阱，实测结果和直觉完全相反（我在真实环境跑出来的，不是推理）：**
>
> 上面那个能成功拒答的例子，**同一个问题换个说法就立刻失效**——注意「创始人」和「CEO」问的是同一件事：
>
> | 提问               | top1 距离 | 结果                      |
> | ---------------- | ------: | ----------------------- |
> | 你们公司**CEO**是谁？   |  0.6307 | ❌ 漏过（**同义改写，掉下阈值**）     |
> | 你们公司**创始人**是谁？   |  0.7424 | ✅ 被拦掉（官方用例）             |
> | 你们公司**股票代码**是多少？ |  0.6396 | ❌ **漏过**，返回了 3 条毫不相关的政策 |
> | 今天天气怎么样？         |  0.6897 | ❌ 漏过                    |
> | 北京到上海高铁要多久？      |  0.5690 | ❌ 漏过                    |
>
> 前两行才是关键证据：**同一意图、换了个说法，距离就从 0.7424 掉到 0.6307**，跨过 0.70 这条线，一个拦得住一个漏过。
>
> **`MAX_DISTANCE = 0.7` 这道闸门是偏松的。** 实测 8 条"该拒答"的问题里，**6 条漏过（75%）**。
>
> 官方评测那个 No-answer 100%，是因为它唯一的拒答用例距离恰好 0.7424，**只比阈值高 0.04，属于运气好，不是能力**。
>
> **完整实验数据、最优阈值推导、落地改动和简历表述，见同目录下的 `rag-threshold-calibration.md`。**
>
> 💡 **这是整个项目里能挖到的最有价值的发现**，也是你区别于"照着教程跑一遍"的关键。它同时证明三件事：你真的动手跑了、你会批判性地看结果、你懂用数据说话。

**同时观察**：每检索一次，`data/logs/rag_retrieval.jsonl` 就多一行。打开看看格式——这就是最简单的可观测性。

**M1 验收**：三类问题表现符合预期 + 日志有记录。

---

### M2：工具层与 Agent 编排

#### M2.1 只读工具

**做什么**：把 Python 函数"包装"成模型能调用的工具。

**为什么需要包装**：

1. `@function_tool` 装饰器会读取函数的**类型标注**（`order_id: str`）和 **docstring**，自动生成一份 JSON Schema 给模型看。模型就是靠这个知道"有这么个工具、需要什么参数"的。
2. 函数里的**校验逻辑是关键**：`get_order_status` 会检查订单号是不是以 `A` 开头，`get_ticket_status` 会检查是不是 `T` 开头且后面是数字。**这层校验必须写，因为模型可能传进来任何东西。**

**为什么要打印 `[Tool] 收到订单查询请求：xxx`**：这是给人看的调试痕迹。你在终端里能直观看到"模型确实调了工具、传了什么参数"。这一行在你排查"为什么模型不调工具"时是救命的。

**验证**（不花钱、不调模型，直接调函数）：

```bash
python -c "import sys; sys.path.insert(0,'src'); from supportpilot.tools.order_tools import get_order_status; print(get_order_status.on_invoke_tool if hasattr(get_order_status,'on_invoke_tool') else get_order_status)"
```

> 这行只是看对象类型。更实用的验证是**直接跑 M3 的对话**，然后观察终端有没有出现 `[Tool]` 打印。新手不必纠结于单独调工具，M3 会统一验证。

**结果**

`<agents.tool._FailureHandlingFunctionToolInvoker object at 0x00000239965B80E0>`

M2.2 写操作工具：审批闸门藏在哪（★这是本项目最巧妙的设计）

**做什么**：`ticket_tools.py` 里的 `create_ticket` 和 `update_ticket_status`，**它们不写数据库**。

**为什么**：读一下 `create_ticket` 的返回值你就明白了——它返回的是一个**字符串**：

```
[APPROVAL_REQUIRED]
action=create_ticket
order_id=A1001
issue_type=物流超时
description=...
```

**它只把"我想干这件事"写成一张"申请单"交给上层，自己不执行。**

这不是偷懒，这是**权限设计**：工具层没有写数据库的权限，写权限被牢牢锁在 `run.py` 的审批流程里。模型就算被诱导、就算胡说，**它最多只能发出一张申请单，改不了数据**。

**关键联动**：`agent.py` 的 instructions 里明确写了——"如果工具返回 `[APPROVAL_REQUIRED]`，不要自行声称操作已完成，也不要伪造工单号或状态。直接把工具返回的审批请求交给系统处理。" 这是**用提示词配合代码，双重保险**。

**验证**：M3 里跑一遍"帮我建工单"，看它是不是弹出审批提示而不是直接说"已建好"。

#### M2.3 Agent 编排 `agent.py`

**做什么**：把模型 + 5 个工具 + 一大段人设说明拼成一个 Agent。

**为什么 prompt 要写那么长**：读一遍那段中文，你会发现它在防 6 种具体的事故：

1. 防模型反复跟用户确认"你说的 A1001 是订单号吗"→ 明确编号规则
2. 防模型编造订单信息 → "只能基于工具返回的数据"
3. 防模型凭常识答政策 → "不要依赖模型自身常识回答，只能基于知识库工具返回的资料"
4. 防模型编造引用来源 → "来源只能使用知识库工具真实返回的 source"
5. 防模型在信息不全时硬开单 → "如果创建工单所需信息不完整，请先向用户询问缺失的信息"
6. 防模型假称操作完成 → 上面那条 `[APPROVAL_REQUIRED]` 规则

**这就是所谓的 Prompt Engineering 在真实项目里的样子：不是让模型更聪明，而是给它划红线。**

**验证**：见 M3。

---

### M3：接口层与多轮对话记忆（`run.py`）

> ⚠️ **先纠正一个常见误解**：这个项目**没有 Web 接口**（没有 FastAPI、没有 HTTP 服务）。README 里说的"接口层"，实际就是 `run.py` 这个**命令行交互程序**。这一点你必须知道，因为它直接决定第 4 章要改造什么。

**做什么**（`run.py` 干三件事）：

**① 意图路由**（在模型之前就拦一道）

```python
should_run_shipping_workflow(text)  # 关键词匹配：物流异常/没发货/发货太慢...
extract_order_id(text)             # 正则 A\d+ 提取订单号
```

**为什么要在模型前面加这一道**：因为"物流超时"有明确规则、有副作用，**交给模型自由发挥不稳**。用代码提前判定，直接走确定性流程。这就是 README 里那条原则——"LLM 负责理解，代码负责确定性规则"。

> 💡 **这里有个可以聊的面试点**：关键词匹配很脆。"快递怎么还不来"就匹配不上。你可以在第 4 章把它升级成"用模型做分类"，这就是一个真实的 trade-off 讨论。

**② 写操作审批循环**

```python
approval_request = find_approval_request_from_run(result)  # 从工具原始输出里捞出申请单
answer = handle_agent_write_approval(approval_request)     # 交互式 approve/reject
```

注意 `find_approval_request_from_run` 直接遍历 `result.new_items` 去找 `ToolCallOutputItem` —— **它读的是工具的原始输出，不是模型转述的文本**。为什么？因为模型可能在转述时"美化"申请单（漏字段、改措辞）。**直接读原始输出，才不会被模型污染。** 这是个很专业的细节，值得在面试里讲。

**③ 多轮记忆（⚠️ 现实比你想的简单）**

```python
MAX_HISTORY_MESSAGES = 10
conversation = conversation[-MAX_HISTORY_MESSAGES:]
```

就这 3 行。它维护一个 `[{role, content}, ...]` 列表，**每次只把最近 10 条扔给模型**。

**这意味着**：

- ❌ 没有摘要压缩（长对话会被硬截断，丢掉早期信息）
- ❌ 不落库（关掉程序就全忘了）
- ❌ 没有会话隔离（只有单用户单会话）

**这不是缺陷，是"最小可用实现"。** 你能看出它的局限并说出改进方案，比假装它很完善强得多——这正是第 4 章的改造点之一。

**如何验证（★本节最重要的实战环节）**

**准备**：两个终端都要激活虚拟环境。当前终端执行：

```bash
export HF_ENDPOINT=https://hf-mirror.com
python run.py
```

**按顺序测这 6 个场景，每个都记下现象**：

| # | 输入                            | 验证的是                 | 预期现象                                                       |
| - | ----------------------------- | -------------------- | ---------------------------------------------------------- |
| 1 | `退款一般几天到账`                    | RAG + 来源引用           | 答出政策内容，**末尾带来源文件名**                                        |
| 2 | `订单 A1001 到哪了`                | 工具调用                 | 终端出现 `[Tool] 收到订单查询请求：A1001`，答出张三的订单                       |
| 3 | `帮我查下订单 A9999`                | 工具错误处理               | 答"未找到该订单"，**不编造**                                          |
| 4 | `你们公司股票代码是多少`                 | 兜底 / 反幻觉             | 明确说知识库里没有，**不编**                                           |
| 5 | `帮我给 A1001 创建物流超时工单，描述是三天没发货` | HITL                 | 弹出 `Agent 写操作需要人工审批`，先输 `reject`，确认没建单；**再测一遍输 `approve`** |
| 6 | `订单 A1001 物流异常，一直没发货`         | Workflow + 幂等 + HITL | 进入 Workflow，打印 `[Trace]` 轨迹；因 72 > 48 判为超时 → 要求审批          |
| 7 | 场景 6 通过后，**再发一次同样的话**         | **幂等**               | 打印"已存在未解决的物流工单 T0001，本次不重复创建"                              |


**场景 5 和 7 是全场亮点**，请务必亲手跑通并截图。它们分别证明了"权限闸门"和"幂等控制"两个真本事。

**同时观察这三个文件**（每次操作后都长一行）：

- `data/logs/rag_retrieval.jsonl` —— 场景 1、4
- `data/logs/workflow_trace.jsonl` —— 场景 6、7（里面有完整 `trace` 数组，能看出每一步）
- `data/logs/approval_log.jsonl` —— 场景 5、6（有 `decision: approved/rejected`）

---

#### ★ 怎么"确认没建单"：三种查看数据库的方式

场景 5 要你"先 reject，确认没建单"，但前提是你知道**去哪看**。

数据库文件：**`supportpilot.db`**（项目根目录，SQLite 格式——一个文件就是一个完整的数据库，不需要装任何数据库服务）

它有**两张表**，作用完全不同，千万别搞混：

| 表             | 内容                           | 会不会变                               |
| ------------- | ---------------------------- | ---------------------------------- |
| `orders` 订单表  | 初始化时写入的 4 条种子数据（A1001~A1004） | **永远不变**，审批动不了它                    |
| `tickets` 工单表 | 售后工单                         | **★ 这才是 reject / approve 真正影响的东西** |

> 很多人问"在哪看订单"——订单就是那 4 条固定数据，是**测试用的背景数据**，你看它永远不会变。真正要盯的是 `tickets` 表。

**方式 1：用项目里的 `show_db.py`（推荐）**

项目根目录已经放好这个只读小工具：

```powershell
.\.venv\Scripts\python.exe show_db.py
```

它会一次性打印：**订单表 + 工单表 + 人工审批日志 + 工作流轨迹**。测试前后各跑一次，对比工单表条数就够了。

**方式 2：一行命令只查工单数**

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('supportpilot.db'); print('工单数:', c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0])"
```

**方式 3：VSCode 插件看图形界面**

装 `SQLite Viewer` 插件，然后直接点开 `supportpilot.db`，能像 Excel 一样浏览表和数据。对新手最直观。

---

#### 场景 5 的正确验证姿势（五步走）

```
① 先看初始状态
   .\.venv\Scripts\python.exe show_db.py
   → 记下 tickets 当前条数（大概率是 0）

② 运行 run.py，触发建单，在审批提示处输入 reject

③ 再看一次
   → tickets 条数必须【还是原来那个数】     ← 这就是"reject 零写入"的铁证
   → approval_log.jsonl 应多一条 决定=rejected

④ 再跑一次，这次在审批提示处输入 approve

⑤ 再看第三次
   → tickets 条数变成【N+1】               ← 这才是"审批通过才写入"的铁证
   → approval_log.jsonl 多一条 决定=approved，成功=True
```

**这五步走完，你就拿到了一组完整的"安全闸门确实有效"的证据链**，可以直接截图放进简历或演示视频。绝大多数候选人的项目演示连数据库都不打开看一眼——这就是你和他们的差距。

---

### M4：确定性工作流 + HITL（`shipping_workflow.py`）

**做什么**：物流异常处理的完整状态机。

**为什么用 Workflow 而不是让 Agent 自己决定**：这个流程有 5 步且顺序固定、有副作用、不能被重复执行。交给自由 Agent Loop 会不稳定。**用 `dataclass` 保存状态 + 一串固定函数按顺序调用 = 可预测、可测试、可回放。**

**流程（对照代码读）**：

```
run_shipping_workflow(order_id)
  ├─ check_order()               查订单，写进 state
  ├─ check_shipping_policy()     用 RAG 查物流政策（硬编码了一个问句）
  ├─ evaluate_shipping_delay()   确定性规则：hours_since_payment > 48 吗？
  └─ create_shipping_ticket()
        ├─ 订单存在吗？
        ├─ 完成超时判断了吗？
        ├─ 超时了吗？没超时 → completed，结束
        ├─ 幂等：find_open_ticket_by_order_and_type() → 有单 → 复用，结束
        └─ 都没有 → 进入 awaiting_approval（★ 不写库）
              ├─ approve_shipping_ticket() → 状态改回 delay_checked → 重新走 create → 这次才写库
              └─ reject_shipping_ticket()  → 状态置 rejected → 不写库
```

**三个设计细节值得你重点读**：

1. **`ShippingWorkflowState` 用 `@dataclass`**：所有中间结果（订单、政策、是否超时、工单号、审批状态）都显式存在一个对象里，而不是散在局部变量。好处：可以打日志、可以断点续跑、可以测试。
2. **`trace` 列表 + `save_workflow_log()`**：每一步都 `add_trace()`，最后把完整轨迹写进 JSONL。**这就是 Observability 的具体实现。** 出问题时你打开 `workflow_trace.jsonl`，能一行行看出"它走到第几步断的"。
3. **审批不是"暂停程序等人"，而是"状态机停机 + 外部驱动"**：  
   `approve_shipping_ticket` 的第一件事是**把 `current_step` 改回 `delay_checked`**，然后再调一次 `create_shipping_ticket`。为什么？因为 `create_shipping_ticket` 开头有个守卫 `if state.current_step != "delay_checked": return`。**只有把状态"倒回去"，函数才会走到写库那一步。** 这是一种很朴素的"状态机续跑"实现，面试时讲清楚这个，比背概念值钱得多。

**验证**：

```bash
PYTHONPATH=src python -c "import sys; from supportpilot.workflows.shipping_workflow import run_shipping_workflow; run_shipping_workflow('A1001')"
```

或者直接用 `run.py` 的调试命令：

```
/shipping A1001     ← 会超时（72 > 48），进入审批
/shipping A1002     ← 运输中，不会超时
/shipping A9999     ← 订单不存在，Workflow 提前结束
```

**逐条看 `[Trace]` 输出**，对比 `data/logs/workflow_trace.jsonl`。三个订单的 `current_step` 应该分别是 `awaiting_approval` / `completed` / `order_not_found`。这三条路径就是 workflow 评测的 4 个用例覆盖的内容。

> ⚠️ **读代码时的一个坑（先知道，别慌）**：`evaluate_shipping_delay()` 函数的最后一行 `return state` **之后**，还有一段约 50 行、判断 `approval_status` 的代码。**它是死代码，永远执行不到**（`return` 之后的东西不会跑），是作者复制粘贴残留的。你读到那里会非常困惑——知道它是死的，跳过即可。这不是你理解错了，是代码本身的问题。

---

### M5：评测体系（`evals/`）

**做什么**：5 套测试，共 26 个用例，一键跑，自动生成报告。

**为什么要做**：这是这个项目**和 90% 的学生项目拉开差距的地方**。普通项目改完代码"我觉得没问题"。这个项目改完代码**跑一遍回归，用数据证明没弄坏别的功能**。

**26 个用例怎么分布**（参照 `PORTFOLIO_CHECKLIST.md` 核过）：

| 套件                | 用例数    | 测什么                           |
| ----------------- | ------ | ----------------------------- |
| RAG Eval          | 5      | Top1 准确率、Recall@3、"该拒答时拒答"准确率 |
| Workflow Eval     | 4      | 3 条状态机路径 + 幂等                 |
| HITL Eval         | 5      | 审批安全规则：不批准绝不能写库               |
| Agent Tool Eval   | 4      | 模型有没有选对工具                     |
| Intent Route Eval | 8      | 该走 Workflow 还是该走 Agent        |
| **合计**            | **26** |                               |

#### 📖 扫盲：Top1 / Recall@3 / No-answer 到底是什么？

这三个词会在评测输出、我的实验报告、面试里反复出现。用"去图书馆找书"打比方就很好懂：**你提一个问题，检索器就是那个帮你从书架上取书的图书管理员**。

| 指标                    | 大白话                        | 严格定义                                                                   | 类比                                  |
| --------------------- | -------------------------- | ---------------------------------------------------------------------- | ----------------------------------- |
| **Top1 准确率**          | 管理员**第一个**拿给你的书，是不是对的那本    | 检索结果**第 1 条**的 `source` 等于标准答案的比例（只看第一条）                               | 只看第一本，对了才得分                         |
| **Recall@3**          | 管理员拿给你**前 3 本**里，有没有包含对的那本 | 检索结果**前 3 条**中**任意一条**的 `source` 等于标准答案的比例（命中即可，不管排第几）                 | 放宽到前 3 本，只要里面对了就算过                  |
| **No-answer 准确率（拒答）** | 该说"查不到"的时候，**有没有真的闭嘴**     | 对 `expected_source: null` 的用例，**必须一条都检索不到**（`top1_source is None`）才算成功 | 书库里根本没有相关的书，管理员必须回答"没有"，随便抓一本凑数就算失败 |

**为什么两个都要看**：Top1 严格、Recall@3 宽松。**如果 Top1 低但 Recall@3 高**，说明"正确的书取到了，只是排在第 2、3 位"——这是**重排序（rerank）能救的问题**；**如果两个都低**，说明根本上就没取到。

> ⚠️ **这套指标有个坑，我已经踩过**：官方 RAG Eval 只有 5 条用例（4 条正样本 + 1 条拒答），正样本距离都在 0.25~0.35（**远小于任何合理阈值**），拒答那条距离 0.7424（**远大于任何合理阈值**）。结果是——**把 `MAX_DISTANCE` 从 0.40 到 0.70 逐个试一遍，三个指标全部恒定 100%，纹丝不动**。也就是说：**官方这套评测根本没能力暴露阈值问题**。详见 `rag-threshold-calibration.md` 的 3.5 节。

#### 🔬 改了参数后，怎么观察指标变没变？（标准动作五步）

以改 `MAX_DISTANCE` 为例，**别指望"跑一下看看"就能看出名堂**，要按这个流程对照：

1. **先记录改前的基线**：跑一次 `python evals/run_rag_eval.py`，把输出的 Top1 / Recall@3 / No-answer 三个数字**抄下来**（不改参数也跑一次，这叫"基线"）。
2. **改参数**：编辑 `src/supportpilot/rag/retriever.py` 里的 `MAX_DISTANCE` 那一行（当前值 0.50）。
3. **再跑同一条命令**：`python evals/run_rag_eval.py`，把新数字和基线**并排**看。
   - ⚠️ **关键提醒**：用**官方那 5 条**评测集，预期输出数字**完全没变**——这不是你改错了，是评测集太弱。
4. **换用能看出差异的测试集**：跑项目里 `evals/` 下的扫描脚本：
   ```bash
   HF_ENDPOINT=https://hf-mirror.com \
     ./.venv/Scripts/python.exe evals/threshold_sweep.py
   ```
   它会一次性打印 **0.40 / 0.45 / 0.50 / 0.55 / 0.60 / 0.70** 六个阈值下，官方集 + 扩展集的全部指标对照表。**一眼就能看到阈值收放的真实代价**（收紧 → 拒答变好但可能误杀真问题；放宽 → 召回稳但拒答失效）。
   - 想拿每条问题的**原始距离**（不带阈值过滤）和标定表，跑 `evals/probe_threshold.py`，结果还会存一份 `data/logs/threshold_probe.json`。
   - 这两个脚本**在哪个目录下运行都可以**，自己会定位项目根并 `chdir`；做对照用的 18 条题目固化在 `evals/rag_cases_hard.jsonl`。
5. **落到日志里复核**：`data/logs/rag_retrieval.jsonl` 每次检索都会追加一条，含 `query` / `top1_source` / `distance` / `passed`。想知道"某条问题到底被拦还是被放过"，用 `show_db.py` 或直接读这个文件即可。

> 💡 **面试可以直接讲的结论**：改一个阈值，官方评测毫无反应——**说明"评测通过"不等于"参数正确"**。我因此自己构造了域内/域外对照集，才把问题量化出来。这个"发现评测集本身不可靠"的过程，比"我调了个参数"值钱得多。

**验证**：

```bash
python evals/run_all_evals.py
```

**预期**：终端打印各套件结果，并生成/更新 `evals/eval_report.md`。

**打开 `eval_report.md` 看这几行**：

```
Overall Status: PASS
Release Gate: READY
Eval Suites Passed: 5/5
```

**同时新增的文件**：`data/logs/eval_failures.jsonl`（失败用例）、`data/logs/eval_regression.jsonl`（每次回归的历史）。

**RAG 评测里最有价值的一个数字**：作者在 README 里记录了优化过程——**最初用 ChromaDB 默认 embedding 模型时 Top1 只有 75%**，换成 `bge-small-zh-v1.5`（中文专用）后升到 100%。这条"75% → 100%"是你简历里最有说服力的一行，**因为它是一个真实的优化闭环，不是"我做了个 RAG"**。

> 💡 **想亲身体验这个优化**：把 `retriever.py` / `ingest.py` 里的 `EMBEDDING_MODEL` 换掉、清空 `data/chroma/`、重跑 ingest 和评测，看 Top1 掉多少。**亲手复现这个对比，是你面试时的王牌。**

**为什么用`bge-small-zh-v1.5`**

第一，它是**中文专门优化**的开源嵌入模型，在中文 MTEB 检索评测上效果不错  
第二，模型体量很小，只有 24M 参数量，CPU 就能推理，部署成本低、生成向量速度快；  
第三，v1.5 版本修复了老版本相似度扎堆的问题

---

## 4. 阶段四：自主改造（避免"只是个复制品"）

按**成本从低到高**排序。**建议至少做前两个**，第三个视时间。

---

### 改造 1：评测集扩充 + 阈值标定（成本最低，收益最高）★首选

**为什么做**：作者的 26 个用例是"冒烟测试"级别，README 自己都声明"不代表生产准确率"。`PORTFOLIO_CHECKLIST.md` 里也明确留了这个待办（"扩充真实用户问题、边界样本和对抗样本"）。**你把它做掉，是补上作者留的坑，而不是另起炉灶。**

**好消息：第一块拼图已经帮你跑出来了。** 见 `rag-threshold-calibration.md`，里面已经有：

- 域内 10 条（含 3 条口语化改写 + 1 条前提错误）+ 域外 8 条（完全无关 / 看似业务但缺失两档）的对照集 → **已固化为 `evals/rag_cases_hard.jsonl`**
- 全部 18 条问题的 top1 距离实测值
- 7 个候选阈值的标定表
- **0.40~0.70 全阈值扫描结果**（含一个关键发现：官方 5 条评测集对该参数**完全不敏感**，0.40~0.70 三指标恒定 100%，只有扩展集能看出差异）
- **结论：阈值 0.70 → 0.50（推荐值）**，域外漏过 6/8（75%）→ **0/8**，域内误杀 **0/10**；域内上界 0.4438 与域外下界 0.5690 之间有 **0.1252 的干净空隙**
- **一次自我纠错**（面试高价值）：`我听说你们退款要30天是真的吗` 原被归为"域外/应拒答"，复核后确认其 top1 就是 `refund_policy.txt`（0.4438），**应为域内用例**——修正后空隙从 0.0059 变 0.1252，真正的缺口在**生成层**（纠正用户记错的数字）

**配套脚本（已放好，直接能跑）**：

| 脚本                         | 作用                                                               |
| -------------------------- | ---------------------------------------------------------------- |
| `evals/probe_threshold.py` | 关掉过滤拿 18 条问题的原始距离 + 输出阈值标定表，结果存 `data/logs/threshold_probe.json` |
| `evals/threshold_sweep.py` | 0.40~0.70 逐阈值跑官方集 + 扩展集，打印指标对照表                                  |

**后续待办**：

1. ~~**落地那次改动**~~ ✅ **已完成**：`retriever.py` 的 `MAX_DISTANCE` 已是 `0.50`（单点值，**不能写成区间**），重跑 `evals/run_rag_eval.py` 确认 Top1 / Recall@3 没退化
2. ~~**把难例正式入册**~~ ✅ **已完成**：18 条已固化为 `evals/rag_cases_hard.jsonl`（带 `tier` 难度分档字段）。**还剩一步**：再补以下三类作者没覆盖的：
   - **多意图混合**："我订单 A1001 想退货，运费谁出？"（既考政策又含订单号，测路由）
   - **超短问句**："退货"、"多久到"（考察极简输入下的检索稳定性）
   - **口径冲突**："你们 7 天无理由，那我第 8 天退行不行？"（政策边界，考察是否答"原则上不支持"）
3. **复制脚本做对照**：复制 `run_rag_eval.py` 改成 `run_rag_eval_hard.py`（只改数据文件路径和日志名，逻辑不用重写），让官方集与难例集**走同一套指标口径**各跑一遍，把两列数字并排进报告

**你会得到的简历素材（数字已实测，可直接用）**：

> 将 RAG 评测集由 5 条扩充至 18 条（新增口语化改写、政策边界、前提错误、对抗拒答等边界样本），通过域内/域外距离分布标定检索阈值：域内上界 0.4438 与域外下界 0.5690 之间存在 0.1252 干净分离空隙，据此外推 `MAX_DISTANCE` 由 0.70 调整为 0.50，**域外漏过由 75%（6/8）降至 0/8，域内召回零损失（10/10）**；同时发现官方评测集对该参数不敏感（0.40~0.70 指标恒定），据此补齐了评测集的灵敏度盲区，并通过残差复核纠正了一条用例的组别标注，定位出生成层"前提校验"缺口。

**为什么这个改造值钱**：它证明你会**造测试集**、会**做阈值标定**、有**质量意识**，而且**不迷信"100% 通过"**。这三样在实习面试里比会写 CRUD 稀缺得多。

> ⚠️ 注意这里有个心理关要过：改完阈值后，No-answer Accuracy 会**从 100% 掉到约 11%~20%**。**这是好事，不是坏事。** 它意味着你从"被一个用例粉饰的 100%"走到了"真实的数字"。面试时主动讲这个下降，比拿一个假 100% 有说服力得多。

---

### 改造 2：统一调用链路追踪（Tracing）

**为什么做（这是项目真实存在的一个短板）**：现在有**三个各写各的**日志文件（`rag_retrieval.jsonl`、`workflow_trace.jsonl`、`approval_log.jsonl`），**它们之间没有任何关联字段**。用户投诉"我上一条消息答错了"，你没法从日志里还原出"那一次到底调了哪些工具、检索到了什么、走了哪条分支"。**这是可观测性的真实缺口，指出来并补上，非常有说服力。**


**怎么做**：

1. 新建 `src/supportpilot/observability/tracer.py`，核心就一个东西：`trace_id`
   ```python
   # 概念示意，不是完整代码
   import uuid
   def new_trace_id() -> str:
       return f"tr-{uuid.uuid4().hex[:8]}"
   ```
2. 在 `run.py` 每轮对话开始时生成一个 `trace_id`，然后**把它塞进上面三个日志的每条记录里**（三个文件各自加一个字段，改动很小）
3. 新增 `src/supportpilot/observability/show_trace.py`，输入 `trace_id`，把三个文件里属于这个 ID 的记录**按时间排序合并打印**出来

**验证**：跑一轮"查订单 → 问退款政策 → 建工单"，然后：

```bash
PYTHONPATH=src python -m supportpilot.observability.show_trace tr-xxxxxxxx
```

**预期**：按时间顺序看到这一次会话的完整链路——路由判断 → 工具调用 → RAG 检索（含 distance）→ 审批决策。

**你会得到的简历素材**：

> 补齐项目可观测性短板：为 RAG 检索、Workflow 轨迹、人工审批三类日志引入统一 `trace_id`，实现单次会话全链路还原，将故障定位从"翻 3 个日志文件"缩短为 1 条命令。

> 💡 **这个改造最妙的地方**：它同时证明了「你读懂了别人的代码」和「你知道生产系统需要什么」。

---

### 改造 3：多场景 Prompt 外置（Prompt 工程 + 可配置化）

**为什么做**：`agent.py` 里那一大段中文 instructions 是**硬编码在一个 Python 字符串里的**（还是靠隐式字符串拼接），改一个字要动代码，也没法切换业务场景。这是真实的可维护性问题。

**怎么做**：

1. 新建 `src/supportpilot/prompts/`，把 instructions 抽成 3 个 YAML 文件：
   ```
   prompts/
   ├── ecommerce.yaml      电商客服（原场景：订单、物流、退换货）
   ├── saas_tech.yaml      SaaS 技术支持（工单优先级、SLA 响应时限、故障排查）
   └── bank_card.yaml      银行信用卡（挂失、账单分期、额度调整）★ 突出"高危操作必须审批"
   ```
2. 改 `agent.py` 的 `create_support_agent()` 接受一个 `scenario` 参数，从对应 YAML 读 instructions
3. `run.py` 启动时让用户选场景
4. **加分项**：给每个场景配 3-5 条 `route_cases`，跑三套对比

**为什么 `bank_card.yaml` 是神来之笔**：金融场景**天然要求审批更严**。你可以把原来"创建工单需审批"扩成"额度调整需二次确认 + 挂失免审批（安全优先，快比严重要）"。**这展示的是你对业务场景的理解，不是技术炫技。**

**你会得到的简历素材**：

> 将硬编码的 Agent 提示词重构为可配置的 YAML 场景包，交付电商客服、SaaS 技术支持、银行信用卡三套业务场景，并针对金融场景细化高危操作审批策略，验证了同一套 Agent 编排层在多业务下的复用性。

---

### （备用）改造 4：加一层 HTTP 接口

**为什么要留这个备选**：因为项目**真的没有接口层**（第 3 章 M3 说过）。而 JD 上写"Agent 应用开发"的岗位，**大概率默认你懂怎么把 Agent 包成一个 API**。

**怎么做**：装 `fastapi` + `uvicorn`，写一个 `api.py`：

- `POST /chat` 接收 `{session_id, message}`，返回 `{answer, trace_id}`
- HITL 改成：写操作时接口返回 `{status: "pending_approval", approval_id}`，另开 `POST /approval/{id}` 接口
- 用 FastAPI 自带的 `/docs` 页面演示，截图很漂亮

**成本提示**：这个改造比前三个大，因为它要动"审批流程"的架构（从 `input()` 阻塞变成"两段式请求"）。**如果时间紧，做前三个就够了。**

---

## 5. 阶段五：简历包装

### 5.1 项目名

不要用 `supportpilot-agent`。

推荐：**SupportPilot - 企业级智能客服 Agent 系统（RAG + 工具调用 + 人工审批 + 多层评测）**

如果想更贴国内 HR 语境：**企业智能客服 Agent：基于 RAG 与人工审批闸门的可控客服自动化系统**

一句话定位（放项目名下面）：

> 用 Python + OpenAI Agents SDK + ChromaDB 构建的客服 Agent，通过 RAG 抑制政策幻觉、通过 HITL 闸门管控写操作风险、通过 5 套共 26+ 条自动化评测保障版本回归质量。

### 5.2 简历描述（4 条，数字留空待你填）

> ⚠️ **两条铁律**（作者在 `PORTFOLIO_CHECKLIST.md` 里也强调了）：
>
> 1. **不要声称"生产级准确率 100%"**。你的评测集是受控冒烟集，说清楚反而显得专业。
> 2. **不要编造"用户解决率提升 X%、成本下降 Y 元"**。没有真实线上数据就绝对不要写，这是面试官最容易一追问就崩的地方。

**① 架构与编排**

> 独立完成企业智能客服 Agent 全链路开发，采用「LLM 负责语义理解 + Python 负责确定性规则」的分层设计：意图路由前置拦截确定性流程，Agent 层通过 Function Calling 调度 5 个业务工具，实现订单查询、工单全生命周期管理与企业政策问答的自动化。

**② RAG 幻觉控制（技术深度最强，放第二条）**

> 构建企业政策 RAG 检索链路（段落切片 + 标题注入 → BGE 中文向量模型 → ChromaDB 检索 → 距离阈值过滤），通过检索置信度阈值实现"无依据即拒答"；针对默认向量模型中文检索能力不足的问题，替换为 `bge-small-zh-v1.5` 并完成切片策略与阈值调优，受控评测集上 Top1 准确率由 \_*% 提升至 \_*%，拒答准确率 \__%。

**③ 安全与可控性（最容易被追问，也最能显专业）**

> 设计写操作安全闸门：工具层不持有数据库写权限，仅返回结构化审批申请；由上层人工审批流程接管后执行写入，实现「模型无法直接修改业务数据」的权限隔离。配套实现工单幂等控制（同订单同类型未解决工单自动复用，避免重复开单）与审批审计日志。

**④ 工程质量与评测**

> 搭建 5 层自动化评测体系（RAG 检索 / Workflow 正确性 / HITL 安全 / 工具选择 / 意图路由），覆盖 \__ 条受控用例，统一入口一键回归并自动生成评测报告与 Release Gate 结论；同步将 RAG 检索、Workflow 轨迹、人工审批三类日志引入统一 trace_id，实现单次会话全链路可追溯。

### 5.3 常见面试追问 + 回答思路

**Q1：为什么不用一个 prompt 把所有事都让模型做，非要分 Workflow 和 Agent 两条路？**

> 回答骨架：确定性 vs 概率性。  
> "物流超时判断是 `hours_since_payment > 48`，这是明确的业务规则，交给模型就是引入不确定性，而且它有副作用（开单）。所以用代码提前拦截。而'用户这句话到底想问什么'是模糊的，这才需要模型的语义理解能力。原则是：**能用规则确定的就不要用概率，能约束的就不要放任。**"

**Q2：RAG 如果检索不到怎么办？会不会硬编一个答案？**

> 回答骨架：阈值 + prompt 双重约束 + 有评测验证。  
> "两层。第一层是 `MAX_DISTANCE = 0.7` 的硬阈值，超过就丢弃，宁可返回空；第二层是 prompt 里明确要求'知识库没找到就告诉用户暂未找到相关政策，不要自行编造'。而且这个行为我写进了评测用例——有一个专门测'该拒答'的 case，跑回归时会验证它没有瞎编。"

**Q3：`[APPROVAL_REQUIRED]` 为什么设计成返回字符串，而不是抛异常？**

> 回答骨架：因为它是**给模型看的**，不是给程序看的。  
> "字符串会被作为工具返回值交给模型，模型读到后就知道'我不能声称完成了'。如果抛异常，模型只会看到一团错误信息，可能反而乱来。而且 prompt 里我明确写了'看到这个标记不要伪造工单号'。（可以补一句改进思路）不过这个设计确实脆弱——靠字符串匹配解析其实不太稳，更好的做法是让工具返回结构化的 Pydantic 对象，或者在 SDK 层用真正的 approval 机制。这是我知道的当前实现的局限。"

> 💡 **这类"我知道它的局限"的回答，杀伤力远大于"它设计得很好"。** 面试官要的就是这个。

**Q4：多轮对话记忆怎么做的？**

> **诚实作答**："目前是最小实现——维护一个消息列表，只保留最近 10 条发给模型。局限很明显：长对话会被硬截断丢掉早期信息，也没有落库，重启就失忆。改进方向我想到两个：一是加摘要压缩（超过 N 轮就把早期对话摘要成一段），二是把会话状态落 SQLite 支持跨会话恢复。"

**Q5：你的 RAG Top1 从 75% 提到 100%，是怎么做的？**

> 回答骨架：先定位问题，再逐个变量验证。  
> "最初用的是 ChromaDB 默认的 embedding 模型，它主要是英文语料训练的，中文政策文本检索不稳。我按变量逐个试：切片策略（定长 → 段落 → 标题+段落）、embedding 模型、相似度阈值。最后定位到主要是 embedding 模型的问题——换 `bge-small-zh-v1.5` 后明显改善。（务必补一句）不过要说清楚，这是 5 条用例的受控冒烟集，100% 不代表生产准确率，我后来把用例扩到 \__ 条做更严格的验证，真实数字是 \__%。"

> ⚠️ 这个"主动降调"极其加分。**主动说出自己数据的局限，是可信度的最强信号。**

**Q6：这个项目你遇到最大的困难是什么？**

> 建议真实回答（比编造更有说服力）：  
> "最有意思的是理解 workflow 里的审批续跑机制。一开始想不通'审批通过了代码怎么接着往下跑'——因为 `create_shipping_ticket` 开头有个守卫，`current_step` 不是 `delay_checked` 就直接返回。后来发现 `approve_shipping_ticket` 做的事情是**把状态改回 `delay_checked`，然后再调一次函数**。这是一种很朴素的'状态机续跑'，当时想通这个的时候挺有成就感的。"

**Q7：你的 Agent 怎么决定调用哪个工具？会不会调错？**

> 回答骨架：SDK 机制 + 有评测兜底。  
> "OpenAI Agents SDK 会把每个工具的**函数签名和 docstring 自动转成 JSON Schema** 一起发给模型，模型基于这些描述决定调用。为了避免调错，我在 prompt 里明确了编号规则（A 开头是订单号，T 开头是工单号），让模型不用猜。另外我有一套 Agent Tool Eval（4 个用例）专门验证'该调哪个工具'，改 prompt 后会跑回归看有没有弄坏。"

**Q8：如果让你上生产，你会先改什么？**

> 回答骨架（展现工程判断力）：  
> "三件事，按优先级：① **审批流要改成异步两段式**——现在是 `input()` 阻塞，生产环境不可能让人在终端敲 approve，得改成接口返回 pending 状态 + 另一个接口提交审批；② **会话状态落库**——现在记忆只存在内存里，多实例部署会丢；③ **评测集要扩到真实分布**——26 条受控用例只能防回归，不能证明效果，得从真实客服日志里挖难例。技术架构本身我觉得方向是对的，主要是工程化程度不够。"

**Q9：Top1 准确率和 Recall@3 有什么区别？你为什么要同时看这两个？**

> 回答骨架：定义 → 差异的诊断价值 → 结合你踩过的坑。  
> "Top1 只看检索结果**第 1 条**对不对，Recall@3 看**前 3 条里有没有**对的。两个都看是因为它们能区分两类故障：**Top1 低但 Recall@3 高**，说明正确文档取到了、只是排序靠后，这类问题加一层 rerank 就能救；**两个都低**，说明根本没取到，得回去改切片或换 embedding 模型。前者是排序问题，后者是召回问题，处置手段完全不同。"

**Q10：你的 RAG 阈值是怎么定的？为什么是 0.50？**

> 回答骨架：暴露评测集的不可靠 → 自己造对照集 → 用数据定值 → 承认残余缺陷。  
> "我一开始也以为官方评测 5 条全 PASS 就说明没问题。但抽查时发现，**同一个拒答问题换个说法就失效了**——「你们公司创始人是谁」距离 0.7424 拦得住，同义的「你们公司 CEO 是谁」距离 0.6307 就漏了，**同一意图换个措辞差出 0.11，越过了 0.70 阈值**——**说明那个 100% 是靠一条用例的运气**。于是我把 `MAX_DISTANCE` 临时设成 99 关掉过滤，拿原始距离，构造了域内 10 条（含口语化改写）+ 域外 8 条（完全无关 / 看似业务但库里没有）的对照集。测出来域内距离上界 0.4438、域外下界 0.5690，**中间有 0.1252 的干净空隙**，说明存在明确的最优阈值。再做 0.40~0.70 的全阈值扫描，取 **0.50** —— 不是因为它分数最高（0.45/0.50/0.55 结果完全相同），而是因为它最接近空隙中点 0.5064，**离两侧的误杀/漏过悬崖都最远**。改完后域外漏过从 6/8（75%）降到 0/8，域内 10/10 零误杀。**另外我发现一个更有意思的事——官方那 5 条评测集对整个参数完全不敏感，0.40 到 0.70 三个指标恒定 100%。也就是说，只跑官方评测你永远发现不了这个参数是错的。** 最后还有一步自我纠错：我原本把'我听说你们退款要 30 天是真的吗'归进'应拒答'那一组，复核后发现它的 top1 就是 `refund_policy.txt`（0.4438）——**话题明明在库里，它是域内问题，检索层没失败**。真正的缺口在生成层：原文写'银行卡退款 3 至 7 个工作日'，用户说 30 天，模型得**识别并纠正这个前提冲突**。而且这证明靠阈值救不了它——想拦住它可用窗口只有 `[0.4379, 0.4438)`、宽 0.0059，而 0.40 时真实问题已误杀 4/10。这是我做这个实验最大的收获：**检索层管'有没有依据'，生成层管'依据支不支持这个说法'——把生成层的问题当成检索层漏网，是用错了尺子。**"

**Q11：你怎么知道你的改动没有把别的功能弄坏？**

> 回答骨架：回归测试 + 固定评测集 + 记录基线。  
> "项目自带 `evals/` 下的 5 套评测（26 个用例），改完代码跑一遍 `run_all_evals.py`，看 `eval_report.md` 里的 `5/5 PASS` 和 `Release Gate: READY`。不过我加了一条经验：**评测通过只能说明'没弄坏已有的'，不能说明'改对了'**——所以关键改动我会额外记录改前的基线数字，改完做新旧对照，而不只看 PASS 与否。"

#### ⚠️ 讲改造 1 时最容易说错的 8 句话（说错就扣分）

| ❌ 说错                                        | ✅ 应该说                                                                                                                                                          | 为什么会被抓                                                                                     |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| "我用探针脚本在**阈值 0.7** 下拿到所有问题的距离"              | "我把 `MAX_DISTANCE` **临时设成 99 关掉过滤**，才拿到每条问题的原始距离"                                                                                                              | **探针的核心动作就是不要阈值**。带着 0.7 跑，域外问题里距离 >0.7 的那些会直接被过滤掉返回 0 条，你**根本看不到它们的距离**，后面的标定表无从算起        |
| "探针跑了**官方那 5 条** + 我加的两组"                   | "探针只跑**扩展集 18 条**；官方 5 条单独由扫描脚本处理"                                                                                                                             | 官方用例该拒答的距离 0.7424、该命中的都在 0.25~0.35，**落在两端，对阈值完全不敏感**，拿来标定等于白跑                              |
| "**目标 0.7** 下『创始人』和『股票代码』**表达方式不同**，拦截结果相反" | "『创始人』和『CEO』**是同一个问题的两种说法**（0.7424 vs 0.6307）；『股票代码』是同一档里的**另一个新问题**（0.6396）"                                                                                  | **「创始人」和「股票代码」不是同义改写，是两个不同的问题**。把不同问题说成"同一问题换说法"，面试官一追问就露馅。而且真正有力的证据是 **0.11 的落差**，不是 0.10 |
| "0.7 **不能很好地**拦截域外问题"                       | "8 条域外**漏过 6 条（75%）**，拒答能力**基本失效**"                                                                                                                            | 说"不够好"像在找借口；给数字才叫结论                                                                        |
| "官方 No-answer 100%，说明拒答能力没问题"               | "官方 100% 是**一条用例的运气**——它距离 0.7424，只比阈值高 **0.04**，改写一下就漏"                                                                                                       | 你整段论证的**起点**就是戳破这个 100%。不戳破，后面就白讲了                                                         |
| "阈值应该设成 **0.45~0.55 区间**"                   | "**代码里只能是一个单点值**；0.45/0.50/0.55 在我这 9 条集上分数完全相同，**我取 0.50 是因为它离 0.40 的误杀下降沿更远，留缓冲**"                                                                           | 参数写不成区间。而且**必须主动解释"为什么不是 0.45"**——面试官一定会问                                                  |
| "调完阈值，域外问题都能拦住了"                            | "**该拦的 8 条全拦住了（0/8）**；但更值得讲的是我**推翻了自己的一条标注** —— 『我听说你们退款要30天是真的吗』原被我归为'应拒答'，复核后它的 top1 就是 `refund_policy.txt`（0.4438），**它是域内问题、检索层没有失败**；真正的缺口在生成层：要纠正用户记错的数字" | 这题考的是**残差分析**。答"全解决了"= 没做残差；能主动改判自己评测集的标注，比"全拦住了"高一个层级                                     |
| "那我想拦住它，把阈值压到 0.44 不就行了？"                   | "不行 —— 想拦住它，可用窗口只有 `[0.4379, 0.4438)`、**宽 0.0059**，而 0.40 时真实问题已经误杀 4/10。**窗口窄到不可用，说明这不是'参数没调好'，是'工具选错了'**：距离量的是话题相关度，不是主张真伪"                                  | 面试官一定会试这个。只会念"0.5 最好"的人答不上来                                                                |

> 💡 最后一条是整套实验**最值钱的地方**：它把问题**分层**了——检索层管"有没有依据"，生成层管"依据支不支持这个说法"。面试时把这个分层讲出来，比把阈值从 0.7 调到 0.5 有说服力得多。

### 5.4 演示准备（面试前 1 天做）

按作者 `PORTFOLIO_CHECKLIST.md` 里的建议顺序，**录一个 2-3 分钟屏录**：

1. 启动，问一个政策问题 → 展示**来源引用**
2. 查订单 A1001 → 说明数据来自 SQLite + Tool，不是模型编的
3. 输入"订单 A1001 物流异常，一直没发货" → 展示 Workflow 的 `[Trace]` 轨迹
4. **先 reject**（关键！）→ 打开 `data/logs/approval_log.jsonl` 证明**没有写入**
5. **再 approve** → 再查一次，证明这次写入了
6. **再问一遍同样的话** → 展示幂等："已存在未解决的物流工单，不重复创建"
7. 跑 `python evals/run_all_evals.py` → 展示 `5/5 PASS`、`Release Gate: READY`
8. 展示 `eval_report.md` 和 `show_trace` 的输出（如果你做了改造 2）

**第 4、5、6 步是整个演示的高潮。** 绝大多数候选人的项目演示到第 2 步就没了。

---

## 6. 避坑清单

### 6.1 已知的代码本身的问题（不是你的错）

| #       | 位置                               | 现象                                                                                                      | 怎么办                                                                                                 |
| ------- | -------------------------------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **0**   | **你的虚拟环境**                       | **`python -m venv .venv` 抓到了系统里的旧 Python（实测抓到 miniconda 的 3.8），而不是 3.12，导致 `pip install` 全线失败且报错极具误导性** | **见 1.2 节：必须用完整路径指定 3.12 解释器，建完立刻 `--version` 验证**                                                  |
| **0.5** | `rag/retriever.py`               | **`MAX_DISTANCE = 0.7` 实测偏松**：8 条域外问题漏过 6 条（75%），拒答能力实质上不成立，但官方评测显示 100% PASS                           | 这是**值得你动手改的核心问题**，不是缺陷而是发挥空间。实测推荐值 **0.50**（域外漏过 0/8、域内误杀 0/10）。完整数据见 `rag-threshold-calibration.md` |
| 1       | `workflows/shipping_workflow.py` | `evaluate_shipping_delay()` 在 `return state` **之后**还有约 50 行死代码，首行缩进还异常                                  | 永远执行不到，读到就跳过。想清理可删掉 `evaluate_shipping_delay` 里最后一个 `return state` 之后的所有内容                          |
| 2       | `rag/*.py` + `db.py`             | 路径全是**相对路径**（`data/chroma`、`data/knowledge`、`data/logs`）                                                | **必须在项目根目录运行**，否则静默失败（建空目录，查不到东西）                                                                   |
| 3       | `run.py`                         | 只调了 `init_db()`，**没有自动建知识库**                                                                            | 首次必须先手动跑 `PYTHONPATH=src python -m supportpilot.rag.ingest`，否则 RAG 工具会因为 collection 不存在而报错          |
| 4       | `rag/` 模块                        | 直接 `python src/supportpilot/rag/ingest.py` 会 `ModuleNotFoundError: No module named 'supportpilot'`      | 加 `PYTHONPATH=src`，或用 `python -m supportpilot.rag.ingest`                                           |
| 5       | `.env.example`                   | `DEEPSEEK_MODEL=deepseek-chat`                                                                          | DeepSeek 2026 年多次改名/调价，这个别名可能失效。报 model not found 就去官方文档查当前模型名                                      |
| 6       | `requirements.txt`               | **没有锁版本**                                                                                               | 装完立刻跑 1.8 的三个自检。若报 pydantic 版本冲突，单独 `pip install "pydantic>=2,<3"`                                  |
| 7       | `requirements.txt`               | 里有 `pytest`，但项目**没有 `tests/` 目录**                                                                       | 不用管，作者用的是 `evals/` 下的自定义脚本                                                                          |
| 8       | `evals/`                         | 部分评测要真实调 API                                                                                            | 会花 token。跑之前确认余额                                                                                    |
| 9       | `run.py`                         | 写操作审批其实有**两套并行实现**（`run.py` 解析标记 + `workflow` 的状态机），都写同一个 `approval_log.jsonl`                          | 不是 bug，但设计上重复。可以作为面试里"我知道这里可以重构"的谈资                                                                 |
| 10      | `agent.py`                       | instructions 是超长字符串隐式拼接，硬编码                                                                             | 这是改造 3 的切入点                                                                                         |


### 6.2 常见报错速查

| 报错关键词                                                                                         | 原因                                                                                                                      | 解法                                                                                                               |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **验证命令输出"没读到"**（`Key 读到了` 没出现）                                                                | **九成是 `.env` 里混进了非配置内容**——最典型的是启动命令和 Key 粘成了同一行。其次才是文件名成了 `.env.txt`、文件不在项目根目录、或编码是 UTF-16                              | **先用编辑器打开 `.env` 逐行看，不要先怀疑 Key**。规则与逐项排查顺序见 1.5 节                                                                |
| `conda env list` 里**看不到 `.venv`**                                                             | **不是报错，是查错工具了**：conda 只列 conda 环境，看不见 `venv` 建的环境                                                                       | 用 `.\.venv\Scripts\python.exe --version` 或 `Get-Content .venv\pyvenv.cfg` 验证（见 1.2 节末尾）                          |
| **VSCode 里 `from supportpilot.xxx import ...` 满屏红线，但程序能跑**                                    | 缺 `python.analysis.extraPaths`。项目是 `src/` 布局，静态分析器不知道 `src/` 是源码根                                                       | 建 `.vscode/settings.json`，设 `"python.analysis.extraPaths": ["./src"]`（见 1.2 节末尾）。**千万别因为这个去改代码**                 |
| VSCode 右下角显示的 Python 版本不是 3.12                                                                | `defaultInterpreterPath` **只在没手动选过解释器时生效**                                                                              | `Ctrl+Shift+P` → `Python: Select Interpreter` → 手动选 `.venv\Scripts\python.exe`                                   |
| VSCode 里 import 不到 `supportpilot`，但终端里跑得好好的                                                   | VSCode 打开的文件夹不对（开成了上级目录）                                                                                                | 打开项目根目录 `supportpilot-agent`，`.venv` 和 `data/` 都在这一层                                                             |
| `无法加载文件 ... 在此系统上禁止运行脚本`                                                                      | PowerShell 执行策略默认禁止运行 .ps1                                                                                              | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` 后重新激活；或干脆不激活，直接 `.\.venv\Scripts\python.exe run.py` |
| `Could not find a version that satisfies the requirement openai-agents (from versions: none)` | **★最坑的一个。** 虚拟环境用了 Python 3.8/3.9，而 `openai-agents` 从 0.9.0 起要求 **Python ≥3.10**（0.0.10~0.8.x 要 ≥3.9，0.0.1 要 ≥3.8 但已撤销） | **先跑 `python --version` 确认版本**。是 3.8/3.9 就用 3.12 重建 venv（见 1.2）。**换镜像没用**，别往那个方向查                                |
| `Ignored the following yanked versions: 0.0.1`                                                | 同一条故障的伴生信息：在 3.8 上唯一兼容的版本恰好是已被作者撤销的 0.0.1                                                                               | 同上                                                                                                               |
| `No suitable Python runtime found`                                                            | 用 `py -3.12` 调用，但该版本的 tag 不是数字形式（uv 装的会显示成 `Astral/CPython3.12.14`）                                                     | 改用解释器完整路径                                                                                                        |
| `ModuleNotFoundError: No module named 'supportpilot'`                                         | 缺 `PYTHONPATH`                                                                                                          | 加 `PYTHONPATH=src`                                                                                               |
| `ModuleNotFoundError: No module named 'agents'`                                               | 没装 `openai-agents` 或**没激活虚拟环境**                                                                                         | 检查提示符有没有 `(.venv)`，重装依赖                                                                                          |
| `Collection [supportpilot_knowledge] does not exist`                                          | 没跑 ingest                                                                                                               | 跑 M1.3 的建库命令                                                                                                     |
| 检索不到任何内容，但也不报错                                                                                | **没在项目根目录运行**                                                                                                           | `cd` 到项目根目录                                                                                                      |
| 卡在下载模型 / `ConnectionError` / timeout                                                          | HuggingFace 连不上                                                                                                         | `export HF_ENDPOINT=https://hf-mirror.com`（每次新终端都要设）                                                             |
| `AuthenticationError` / 401                                                                   | API Key 错、余额为 0、或 `.env` 没生效                                                                                            | 检查 `.env` 在根目录、字段名拼写、跑 1.5 的验证命令                                                                                 |
| `model not found` / `invalid model`                                                           | 模型名失效                                                                                                                   | 改 `DEEPSEEK_MODEL`                                                                                               |
| `pydantic` 相关版本报错                                                                             | 依赖版本冲突                                                                                                                  | 单独 pin pydantic 版本                                                                                               |
| 回答里没有来源引用                                                                                     | 模型没查到内容，或没走 KB 工具                                                                                                       | 先确认 M1.4 单测检索是通的                                                                                                 |
| 中文乱码                                                                                          | Windows 终端编码                                                                                                            | `chcp 65001`，或 Python 加 `-X utf8`                                                                                |

### 6.3 关于"不要跳步"

- **不要**跳过 M1 的单独验证直接跑 `run.py`。如果 RAG 是坏的，你会以为是 prompt 的问题，浪费几小时。
- **不要**在没跑通 `run_all_evals.py` 的情况下开始改造。**评测全绿是你的"安全网"**——改造后重跑，就知道有没有弄坏东西。
- **不要**一上手就改 prompt 或换模型。先让它按原样跑通，**有了 baseline 才有对比**。

---

## 7. 进度验收表

每完成一项打个勾。**全部打勾就可以开始投简历了。**

### 阶段一 · 环境

- [x] **`./.venv/Scripts/python.exe --version` 显示 3.12.x**（注意验证的是 venv 里的 python，不是裸 `python --version`）
- [x] `.venv` 建好且每次能激活
- [x] `pip install -r requirements.txt` 无报错
- [x] `.env` 建好，Key 能被读到
- [x] `bge-small-zh-v1.5` 下载成功，打印出维度
- [x] 自检 1 通过（数据库 + 4 条种子订单）

### 阶段二 · 理解

- [x] 能口述 6 个环节和对应文件
- [x] 能解释 `MAX_DISTANCE = 0.7` 为什么存在
- [x] 能解释 `[APPROVAL_REQUIRED]` 为什么返回字符串而不是写库
- [x] 能解释幂等靠哪个函数实现

### 阶段三 · 复现

- [x] M1 自检 2+3 通过，三类问题表现符合预期
- [x] M3 六个场景全部亲手跑过，现象符合预期
- [x] M4 三个订单走出三条不同路径
- [x] M5 `python evals/run_all_evals.py` 显示 5/5 PASS

### 阶段四 · 改造（选 2-3 个）

- [ ] 改造 1：评测集扩到 \____ 条，有新旧对比
- [ ] 改造 2：trace_id 串起 3 个日志 + 一条命令还原链路
- [ ] 改造 3：3 套 YAML 场景包
- [ ] 改造 4（可选）：FastAPI 接口层

### 阶段五 · 包装

- [ ] 简历 4 条描述写完，数字全部填实
- [ ] 11 个面试问题都能不看稿讲 1 分钟
- [ ] 2-3 分钟演示屏录录好
- [ ] **自己的 GitHub 仓库已提交**（`.env` 千万别传上去）

---

## 附：一句话总结这个项目的价值

> 它教你的不是"怎么调 LLM API"，而&#x662F;**"怎么把不可控的大模型，装进一个可控、可审计、可评测的工程框架里"**。
>
> 这正是企业招 Agent 开发实习时真正想看到的东西。

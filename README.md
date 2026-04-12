# 🤖 My Personal Agent

一个基于大模型 API 构建的本地私人助理。拒绝数据上传云端，绝对的数据隐私与控制权。

## ✨ 当前特性 (Milestone 4.5)
- **人设注入**：通过本地 `profile.md` 文件自定义助理性格与背景知识。
- **敏感信息隔离**：使用 `.env` 管理 API Key，结合 `.example` 模板，确保隐私数据不进 Git 仓库。
- **持久化代码沙箱**：基于 `exec` 的 Jupyter 式沙箱，跨多次执行保持变量状态，彻底解决代码拆分导致的变量丢失问题。
- **跨平台编码安全**：底层自动注入 UTF-8 编码的 `open` 函数，从根源修复 Windows 下写文件中文乱码。
- **ReAct 循环**：支持多轮 "思考→行动→观察" 循环，复杂问题分步解决。
- **错误自愈**：代码执行失败时，自动将错误信息反馈给大模型进行修正重试，不轻易放弃。
- **安全带机制**：AST 静态分析拦截危险操作（如 `os.system`、`subprocess`），沙箱超时自动熔断。
- **对话持久化**：基于 SQLite 的本地数据库存储，退出程序不丢失记忆，下次启动自动恢复上下文。
- **会话管理指令**：内置 `/history`（查看近期会话摘要）、`/clear`（清空当前上下文）、`/clearall`（彻底清除所有记忆）。
- **工具调用容错**：自动兼容大模型输出的 *python* 与 *run_python* 标记，提升工具触发稳定性。

## 📁 项目结构

```text
my_agent/
├── data/                   # 持久化数据目录（SQLite 数据库等）
│   └── .gitkeep
├── prompts/
│   ├── 01_base_rules.md    # 框架级系统规则
│   └── 02_tool_rules.md    # 工具调用与 ReAct 规则
├── sandbox/
│   ├── executor.py         # 代码执行器（持久化沙箱 + subprocess 备用）
│   └── workspace/          # 沙箱工作目录（文件读写在此）
│       └── .gitkeep
├── .env.example            # 环境变量模板
├── database.py             # 数据库操作层（建表、存取、会话管理）
├── config.py               # 配置加载与校验逻辑
├── llm_client.py           # 大模型 API 通信封装
├── main.py                 # 程序主入口（命令行交互循环）
├── profile.md.example      # 人设配置模板
├── requirements.txt        # Python 依赖清单
├── tools.py                # 工具基类、注册表与 Python 执行工具
└── README.md               # 你正在看的这个文件
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.12+（使用了 X | Y 类型语法等）
- 一个可用的大模型 API Key（推荐智谱 GLM-4-Flash，便宜好用）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制模板并填入你的真实密钥：

```bash
cp .env.example .env
```

然后编辑 `.env` 文件，将 `your_api_key_here` 替换为你的实际 API Key。

### 4. 配置私人助理人设

复制模板并写入你的个人信息：

```bash
cp profile.md.example profile.md
```

然后编辑 `profile.md` 文件，告诉它你是谁、你的工作习惯、你的社交圈等。（**放心写，这个文件不会被 Git 提交**）

### 5. 启动运行

```bash
python main.py
```

## 🗺️ 开发路线图

- [x] **M1: 能认识你的 CLI**
  - [x] 搭架子与人设注入
  - [x] 加上短期记忆
- [x] **M2: 赋予它双手**（代码解释器沙箱）
  - [x] 写安全沙箱执行器
  - [x] 沙箱接入大模型
- [x] **M3: 核心引擎**（ReAct 循环与安全带）⚡ 当前阶段
  - [x] 实现 ReAct 循环 & 错误自愈机制
  - [x] 加上安全带（AST 自动扫描拦截危险代码）
  - [x] 工具注册表抽象（为 M4 做准备）
  - [x] 持久化沙箱（跨执行保持变量状态）
  - [x] 多步骤调度（计算 → 写文件等复合任务）
  - [x] 跨平台编码修复（Windows UTF-8 乱码根治）
- [ ] **M4: 接入真实世界**（联网搜索）
  - [ ] 接入搜索工具（暂时跳过）
- [x] ** M4.5: 对话落地 **（SQLite 存历史，退出不丢失，能用命令查看旧记录）
  - [x] 4.5.1：写底层 database.py（建表、存取逻辑）
  - [x] 4.5.2：启动时加载历史、每次对话后保存、增加 /history 指令
  - [x] 4.5.3：增加 /clear、/clearall 指令与跨会话全局记忆加载优化
- [ ] **M5: 长期记忆升级**（向量数据库）
  - [ ] 引入向量库与 Embedding —— 明确选本地模型还是 API，写存取函数
  - [ ] 记忆提取与语义检索 —— 对话完自动提炼事实存入，提问时按需检索。
- [ ] **M6: 工程化收尾**（Web UI包装）
  - [ ] 用 Gradio 替换命令行，提供打字机流式体验。

## 📝 License

MIT

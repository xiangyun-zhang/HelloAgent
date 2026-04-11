# 🤖 My Personal Agent

一个基于大模型 API 构建的本地私人助理。拒绝数据上传云端，绝对的数据隐私与控制权。

## ✨ 当前特性 (Milestone 3 进行中)

- **人设注入**：通过本地 `profile.md` 文件自定义助理性格与背景知识。
- **敏感信息隔离**：使用 `.env` 管理 API Key，结合 `.example` 模板，确保隐私数据不进 Git 仓库。
- **代码沙箱**：本地安全的 Python 执行环境，支持自动补全表达式输出。
- **ReAct 循环**：支持多轮 "思考→行动→观察" 循环，复杂问题分步解决。
- **错误自愈**：代码执行失败时，自动将错误信息反馈给大模型进行修正重试，不轻易放弃。

## 📁 项目结构

```text
my_agent/
├── prompts/
│   ├── 01_base_rules.md    # 框架级系统规则
│   └── 02_tool_rules.md    # 工具调用与 ReAct 规则
├── sandbox/                # 运行沙箱
│   ├── executor.py         # 代码执行器
│   └── workspace/          # 沙箱工作目录
│       └── .gitkeep
├── .env.example            # 环境变量模板
├── profile.md.example      # 人设配置模板
├── requirements.txt        # Python 依赖清单
├── config.py               # 配置加载与校验逻辑
├── llm_client.py           # 大模型 API 通信封装
├── main.py                 # 程序主入口（命令行交互循环）
└── README.md               # 你正在看的这个文件
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
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
- [ ] **M3: 核心引擎**（ReAct 循环与安全带）⚡ 当前阶段
  - [x] 实现 ReAct 循环 & 错误自愈机制
  - [x] 加上安全带（AST 自动扫描拦截危险代码）
  - [ ] 工具注册表抽象 (为 M4 做准备)
- [ ] **M4: 接入真实世界**（联网搜索）
- [ ] **M5: 长期记忆升级**（向量数据库）
- [ ] **M6: 工程化收尾**（持久化与 Web UI）

## 📝 License

MIT

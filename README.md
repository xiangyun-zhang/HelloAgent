# 🤖 My Personal Agent

一个基于大模型 API 构建的本地私人助理。拒绝数据上传云端，绝对的数据隐私与控制权。

## ✨ 当前特性 (Milestone 1)

- **人设注入**：通过本地 `profile.md` 文件自定义助理性格与背景知识。
- **敏感信息隔离**：使用 `.env` 管理 API Key，结合 `.example` 模板，确保隐私数据不进 Git 仓库。
- **极简架构**：分层设计，便于后续扩展工具调用和长期记忆。

## 📁 项目结构

``` text
my_agent/
├── .gitignore # Git 忽略规则（拦截 .env 和 profile.md）
├── .env.example # 环境变量模板
├── profile.md.example # 人设配置模板
├── requirements.txt # Python 依赖清单
├── config.py # 配置加载与校验逻辑
├── llm_client.py # 大模型 API 通信封装
├── main.py # 程序主入口（命令行交互循环）
└── README.md # 你正在看的这个文件
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

- [x] **M1: 能认识你的 CLI** (当前阶段)
  - [x] 搭架子与人设注入
  - [ ] 加上短期记忆
- [ ] **M2: 赋予它双手** (代码解释器沙箱)
- [ ] **M3: 核心引擎** (ReAct 循环与安全带)
- [ ] **M4: 接入真实世界** (联网搜索)
- [ ] **M5: 长期记忆升级** (向量数据库)
- [ ] **M6: 工程化收尾** (持久化与 Web UI)

## 📝 License

MIT

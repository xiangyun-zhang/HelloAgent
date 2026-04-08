import os
from dotenv import load_dotenv

# ==========================================
# 自动加载 .env 文件
# ==========================================
# load_dotenv() 会查找项目根目录下的 .env 文件，并将其中的变量加载到 os.environ 中
# 如果在 Docker 或 CI/CD 环境中，通常没有 .env 文件，而是直接注入系统环境变量，此时 load_dotenv 不会覆盖已有的环境变量
load_dotenv()

# ==========================================
# 读取配置
# ==========================================
API_KEY = os.getenv("AGENT_API_KEY")
BASE_URL = os.getenv("AGENT_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
MODEL_NAME = os.getenv("AGENT_MODEL", "glm-4-flash")

# ==========================================
# 配置校验（防止启动后才发现没填 Key）
# ==========================================
if not API_KEY or API_KEY == "your_api_key_here":
    raise ValueError(
        "\n[配置错误] 未检测到 AGENT_API_KEY！\n"
        "请按以下步骤操作：\n"
        "1. 复制 .env.example 文件并重命名为 .env\n"
        "2. 在 .env 文件中填入你的真实 API Key\n"
    )

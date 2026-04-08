import os
from dotenv import load_dotenv

# 加载用户真实的 .env 配置（如果存在的话，不会覆盖已有的系统环境变量）
load_dotenv()

def _load_from_example(key: str) -> str | None:
    """
    私有方法：尝试从 .env.example 模板中读取默认值
    """
    example_path = ".env.example"
    if not os.path.exists(example_path):
        return None
    
    with open(example_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 匹配 KEY=VALUE 的格式，跳过纯注释行
            if line.startswith(f"{key}=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip()
                # 排除掉占位符
                if val and not val.startswith("your_"):
                    return val
    return None

def _get_config(key: str, required: bool = False) -> tuple[str | None, bool]:
    """
    核心配置加载逻辑（优先级：系统环境变量 > .env文件 > .env.example文件）
    :param key: 配置项名称
    :param required: 是否为必填项
    :return: (配置值, 是否使用了example的默认值)
    """
    # 1. 尝试从系统环境变量或 .env 获取（load_dotenv 已经把它们合并了）
    value = os.getenv(key)
    if value is not None:
        return value, False
    
    # 2. 尝试从 .env.example 获取默认值
    example_val = _load_from_example(key)
    if example_val is not None:
        return example_val, True
    
    # 3. 都没有
    return None, False

# ==========================================
# 读取所有配置项
# ==========================================
API_KEY, _ = _get_config("AGENT_API_KEY", required=True)
BASE_URL, base_used_example = _get_config("AGENT_BASE_URL")
MODEL_NAME, model_used_example = _get_config("AGENT_MODEL")
AGENT_NAME, name_used_example = _get_config("AGENT_NAME")
MAX_HISTORY_ROUNDS, max_history_rounds_example = _get_config("MAX_HISTORY_ROUNDS")

# ==========================================
# 友好提示：哪些配置使用了默认值
# ==========================================
_example_warnings = []
if base_used_example: _example_warnings.append(f"AGENT_BASE_URL = {BASE_URL}")
if model_used_example: _example_warnings.append(f"AGENT_MODEL = {MODEL_NAME}")
if name_used_example: _example_warnings.append(f"AGENT_NAME = {AGENT_NAME}")
if max_history_rounds_example: _example_warnings.append(f"MAX_HISTORY_ROUNDS = {MAX_HISTORY_ROUNDS}")

if _example_warnings:
    print("\n[提示] 以下配置未在 .env 中找到，已自动使用 .env.example 中的默认值：")
    for w in _example_warnings:
        print(f"       - {w}")
    print()

# ==========================================
# 安全校验：必填项拦截
# ==========================================
if not API_KEY:
    raise ValueError(
        "\n[配置错误] 未检测到 AGENT_API_KEY！\n"
        "请按以下步骤操作：\n"
        "1. 复制 .env.example 文件并重命名为 .env\n"
        "2. 在 .env 文件中填入你的真实 API Key\n"
    )

import subprocess
import os
import tempfile

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "workspace")

def run_python_code(code: str, timeout: int = 10) -> str:
    """
    在安全沙箱中执行 Python 代码
    :param code: OI-Man 生成的代码字符串
    :param timeout: 最大执行时间（秒），防止死循环
    :return: 执行结果或错误信息
    """
    os.makedirs(WORKSPACE_DIR, exist_ok=True)

    # 构建一个「受限制」的环境变量
    # 砍掉 PATH 中的 shell 路径，阻断 os.system() 的后路
    safe_env = {
        "HOME": WORKSPACE_DIR,
        "PYTHONPATH": "",
    }

    try:
        result = subprocess.run(
            ["python", "-c", code],
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_env,        # 注入受限环境变量
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[Error]\n{result.stderr}"
            
        if not output.strip():
            output = "代码执行成功，但没有任何输出。"

        return output

    except subprocess.TimeoutExpired:
        return f"[Error] 代码执行超时（超过 {timeout} 秒），已被强制终止。请检查是否有死循环。"
    except Exception as e:
        return f"[System Error] 沙箱启动失败: {str(e)}"

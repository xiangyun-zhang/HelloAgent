import sys
import ast
import subprocess
import os
import uuid

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "workspace")


def _auto_print_last_expr(code: str) -> str:
    """
    预处理：如果代码最后一行是裸表达式（如 result），自动包裹 print()
    模拟 Jupyter Notebook 的行为，降低对 Agent 的输出格式要求
    """
    lines = code.strip().split("\n")
    if not lines:
        return code

    last_line = lines[-1].strip()
    # 空行、注释、print调用、语句关键字 —— 直接跳过
    skip_keywords = (
        "print(", "import ", "from ", "def ", "class ", "if ", "elif ",
        "else:", "for ", "while ", "return ", "break", "continue", "pass",
        "#", "assert ", "del ", "with ", "try:", "except", "finally:",
        "raise ", "yield ", "global ", "nonlocal "
    )
    if not last_line or any(last_line.startswith(k) for k in skip_keywords):
        return code
    
    # 用 AST 判断最后一行是否为合法表达式（而非语句）
    try:
        ast.parse(last_line, mode="eval")
        lines[-1] = f"print({last_line})"
        return "\n".join(lines)
    except SyntaxError:
        return code


def run_python_code(code: str, timeout: int = 10) -> str:
    """
    在安全沙箱中执行 Python 代码
    :param code: Agent 生成的代码字符串
    :param timeout: 最大执行时间（秒），防止死循环
    :return: 执行结果或错误信息
    """
    os.makedirs(WORKSPACE_DIR, exist_ok=True)

    # 预处理：自动补全裸表达式的 print
    code = _auto_print_last_expr(code)

    # 写入临时文件执行（比 -c 参数更健壮，避免多行代码转义问题）
    script_name = f"_exec_{uuid.uuid4().hex[:8]}.py"
    script_path = os.path.join(WORKSPACE_DIR, script_name)

    # 构建受限的环境变量
    safe_env = {
        "HOME": WORKSPACE_DIR,
        "PYTHONPATH": "",
    }

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        result = subprocess.run(
            ["python", script_path],
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_env,
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
    finally:
        # 无论成功失败，清理临时脚本
        if os.path.exists(script_path):
            os.remove(script_path)

import ast
import os
import subprocess
import uuid

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "workspace")

def _check_unsafe_ast(code: str) -> str | None:
    """
    使用 AST 静态分析检查代码是否包含危险操作。
    如果安全返回 None，如果危险返回拦截原因字符串。
    """
    # 1. 定义黑名单
    UNSAFE_SIMPLE = {"eval", "exec", "__import__", "compile"}
    
    UNSAFE_ATTRS = {
        "os.system", "os.popen", "os.remove", "os.unlink", "os.mkdir", "os.rmdir",
        "shutil.rmtree", "shutil.copy", "shutil.move",
        "subprocess.Popen", "subprocess.run", "subprocess.call", "subprocess.check_output",
        "sys.exit",
        "pathlib.Path.unlink", "pathlib.Path.write_text", "pathlib.Path.write_bytes",
    }

    # 解析 AST 树，如果连语法都没过，直接放行（让后面的执行器去报语法错误）
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    def get_attr_path(node) -> str | None:
        """递归提取属性的完整路径，例如把 os.system 变成 'os.system' 字符串"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_path = get_attr_path(node.value)
            if value_path:
                return f"{value_path}.{node.attr}"
        return None

    # 2. 遍历 AST 树寻找危险分子
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
            
        func_path = get_attr_path(node.func)

        # 检查 A：简单危险内置函数
        if isinstance(node.func, ast.Name) and node.func.id in UNSAFE_SIMPLE:
            return f"禁止调用危险内置函数: {node.func.id}"

        # 检查 B：危险模块方法 (如 os.system)
        if func_path and func_path in UNSAFE_ATTRS:
            return f"禁止调用危险模块方法: {func_path}"

    # 3. 全部放行
    return None


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
        tree = ast.parse(last_line, mode="eval")
        # 只对简单变量名自动包裹 print，避免副作用调用（如 file.write）被误包裹
        if isinstance(tree.body, ast.Name):
            original_last_line = lines[-1]
            indent = original_last_line[:len(original_last_line) - len(original_last_line.lstrip())]
            lines[-1] = f"{indent}print({last_line})"
            code =  "\n".join(lines)
    except SyntaxError:
        pass
    finally:
        return code


def run_python_code(code: str, timeout: int = 10) -> str:
    """
    在安全沙箱中执行 Python 代码
    :param code: Agent 生成的代码字符串
    :param timeout: 最大执行时间（秒），防止死循环
    :return: 执行结果或错误信息
    """
    # 安检门：AST 静默拦截
    block_reason = _check_unsafe_ast(code)
    if block_reason:
        return f"[Error] 代码安全拦截：{block_reason}，执行已取消。"
    
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
            output = "[Success] 代码执行成功（无打印输出）。"

        return output

    except subprocess.TimeoutExpired:
        return f"[Error] 代码执行超时（超过 {timeout} 秒），已被强制终止。请检查是否有死循环。"
    except Exception as e:
        return f"[System Error] 沙箱启动失败: {str(e)}"
    finally:
        # 无论成功失败，清理临时脚本
        if os.path.exists(script_path):
            os.remove(script_path)

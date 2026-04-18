import abc
import os
import re

from config import ALLOW_SELF_MODIFY
from sandbox.executor import Sandbox


class BaseTool(abc.ABC):
    """工具基类（契约）"""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """工具的调用名称，例如 run_python"""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """工具的功能描述（未来可以用来动态生成给大模型的提示词）"""
        pass

    @abc.abstractmethod
    def execute(self, llm_response: str) -> str:
        """
        核心：接收大模型的完整回复，从中提取属于自己的内容并执行。
        返回拼接好的执行结果字符串。
        """
        pass


class PythonTool(BaseTool):
    def __init__(self):
        self._sandbox: Sandbox | None = None

    def bind_sandbox(self, sandbox: Sandbox):
        self._sandbox = sandbox

    @property
    def name(self) -> str:
        return "run_python"

    @property
    def description(self) -> str:
        return "用于执行 Python 代码并返回结果。格式: ```run_python\n代码\n```"

    @staticmethod
    def _check_file_operations(code: str) -> str | None:
        """AST 静态检查：禁止在代码中直接使用 open() 或 os 模块操作文件"""
        import ast
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None

        FORBIDDEN_FUNCS = {"open"}
        FORBIDDEN_MODULES = {"os", "pathlib", "shutil", "subprocess"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_FUNCS:
                return (
                    "[安全拦截] 禁止使用 open() 创建或读写文件。\n"
                    "请改用 fs 工具，创建新文件请使用 fs write，格式如下：\n"
                    "```fs\nwrite todo.txt\n待办事项1\n待办事项2\n待办事项3\n```"
                )
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                module_name = node.module if isinstance(node, ast.ImportFrom) else None
                if module_name and module_name.split('.')[0] in FORBIDDEN_MODULES:
                    return f"[安全拦截] 禁止导入 {module_name} 模块。请使用 fs 工具操作文件。"
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in FORBIDDEN_MODULES:
                            return f"[安全拦截] 禁止导入 {alias.name} 模块。请使用 fs 工具操作文件。"
        return None

    def execute(self, llm_response: str) -> str:
        if not self._sandbox:
            return "[Error] 沙箱未初始化。"

        # 1. 提取代码块
        code_blocks = re.findall(r"```run_python\n(.*?)```", llm_response, re.DOTALL)
        if not code_blocks and "```run_python" in llm_response:
            code_blocks = re.findall(r"```run_python\n(.*)", llm_response, re.DOTALL)
        if not code_blocks:
            return ""

        # 2. 合并代码
        combined_code = "\n\n".join(code_blocks)

        # ✅ 新增：安全检查，拦截文件操作
        block_reason = self._check_file_operations(combined_code)
        if block_reason:
            return f"[Error] {block_reason}"

        # 3. 执行
        print(f" ▶ 执行中 (共 {len(code_blocks)} 个代码块)...", end="")
        result = self._sandbox.execute(combined_code)
        is_error = "[Error]" in result
        print(" ❌" if is_error else " ✅")
        execution_results = [f"[执行结果 #1]\n{result}"]
        return "\n\n".join(execution_results)


class ToolRegistry:
    """工具注册表（大管家）"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    @staticmethod
    # ✅ 新增：兼容模型"偷懒"写法
    def _normalize_response(response: str) -> str:
        """python → run_python"""
        return response.replace("```python", "```run_python")

    def register(self, tool: BaseTool):
        """雇佣工具，登记在册"""
        self._tools[tool.name] = tool

    def bind_sandbox(self, sandbox: Sandbox):
        for tool in self._tools.values():
            if hasattr(tool, "bind_sandbox"):
                tool.bind_sandbox(sandbox)

    def needs_to_run(self, llm_response: str) -> bool:
        """检查大模型的回复里，有没有需要调用工具的标记"""
        response = self._normalize_response(llm_response)
        for name in self._tools:
            if f"```{name}" in response:
                return True
        return False

    def run(self, llm_response: str) -> str:
        """统一调度：找出需要干活的工具，让它们干活，收集结果"""
        response = self._normalize_response(llm_response)
        final_results = []
        for name, tool in self._tools.items():
            if f"```{name}" in response:
                res = tool.execute(response)
                if res:
                    final_results.append(res)
        return "\n\n".join(final_results)


class FileSystemTool(BaseTool):
    """安全文件系统工具，所有操作仅限 WORKSPACE_PATH 内"""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        os.makedirs(self.workspace_root, exist_ok=True)

    @property
    def name(self) -> str:
        return "fs"

    @property
    def description(self) -> str:
        return (
            "安全文件系统操作。可用子命令：\n"
            "- scan [path] : 列出目录下的文件和子目录（相对路径）\n"
            "- read [file] : 读取文件内容（自动截断过长文件）\n"
            "- write [file] : 创建新文件并写入内容（仅当文件不存在时可用）\n"
            "- patch [file] : 精确替换文件中的指定片段（需用 OLD/NEW 分隔块）"
        )

    def _resolve_path(self, relative_path: str) -> str:
        """将相对路径解析为绝对路径，并校验是否在授权目录内"""
        # 禁止路径穿越
        if ".." in relative_path or relative_path.startswith("/"):
            raise ValueError("路径不能包含 '..' 或以 '/' 开头，请使用相对于工作区的路径")
        target = os.path.abspath(os.path.join(self.workspace_root, relative_path))
        if not target.startswith(self.workspace_root):
            raise PermissionError(f"禁止访问工作区外的路径: {relative_path}")

        # 额外检查：如果目标在项目源码目录内且未开启自我修改，则拒绝
        # 但工作区目录本身总是允许的，不需要额外检查
        project_root = os.path.dirname(os.path.dirname(__file__))  # 项目根目录
        # 只有目标不在工作区内时才触发源码保护检查（实际上已经在工作区内，此条件为保险）
        if not target.startswith(self.workspace_root):
            if target.startswith(project_root) and not ALLOW_SELF_MODIFY:
                raise PermissionError(
                    "禁止修改 Agent 自身源码。如需启用自我进化功能，请在 .env 中设置 ALLOW_SELF_MODIFY=true"
                )
        return target

    def execute(self, llm_response: str) -> str:
        """解析 LLM 输出中的 ```fs ... ``` 代码块并执行对应子命令"""
        import re

        # 1. 优先提取标准的 ```fs ... ``` 代码块
        blocks = re.findall(r"```fs\n(.*?)```", llm_response, re.DOTALL)

        # 2. 如果没匹配到，但回复中包含 "fs write" 或 "fs read" 等关键词，则将整段作为裸命令处理
        if not blocks:
            # 检查是否包含 fs 命令关键词
            if any(keyword in llm_response for keyword in ["fs write", "fs read", "fs scan", "fs patch"]):
                # 尝试从回复中提取第一段有效的命令（从 "fs" 开始到末尾）
                match = re.search(r"(fs\s+(?:write|read|scan|patch)\s+[^\n]*(?:\n.*?)*?)(?=\n\n|$)", llm_response,
                                  re.DOTALL)
                if match:
                    blocks = [match.group(1)]

        if not blocks:
            return ""

        results = []
        for block in blocks:
            lines = block.strip().split("\n")
            if not lines:
                continue
            cmd_line = lines[0].strip().split()
            if not cmd_line:
                continue
            cmd = cmd_line[0].lower()
            args = cmd_line[1:]

            try:
                if cmd == "scan":
                    path = args[0] if args else "."
                    results.append(self._scan(path))
                elif cmd == "read":
                    if not args:
                        results.append("[Error] read 需要指定文件路径")
                    else:
                        results.append(self._read(args[0]))
                elif cmd == "patch":
                    if len(args) < 1:
                        results.append("[Error] patch 需要指定文件路径")
                    else:
                        # 旧片段和新片段在代码块的后续行中，以特定分隔符分开
                        # 格式示例：
                        # patch test.py
                        # <<<<<<< OLD
                        # print("hello")
                        # =======
                        # print("world")
                        # >>>>>>> NEW
                        content = "\n".join(lines[1:])
                        old_new = re.split(r"<<<<<<< OLD\s*\n(.*?)\n=======\s*\n(.*?)\n>>>>>>> NEW", content,
                                           flags=re.DOTALL)
                        if len(old_new) == 4:
                            old_str = old_new[1]
                            new_str = old_new[2]
                            results.append(self._patch(args[0], old_str, new_str))
                        else:
                            results.append("[Error] patch 格式错误，请使用 <<<<<<< OLD / ======= / >>>>>>> NEW 分隔")
                elif cmd == "write":
                    if len(args) < 1:
                        results.append("[Error] write 需要指定文件路径")
                    else:
                        # 内容在代码块的后续行中
                        content = "\n".join(lines[1:])
                        results.append(self._write(args[0], content))
                else:
                    results.append(f"[Error] 未知的 fs 子命令: {cmd}")
            except Exception as e:
                results.append(f"[Error] {e}")

        return "\n\n".join(results)

    def _scan(self, relative_path: str) -> str:
        target = self._resolve_path(relative_path)
        if not os.path.isdir(target):
            return f"[Error] 路径不是目录: {relative_path}"
        items = []
        with os.scandir(target) as it:
            for entry in it:
                t = "📁" if entry.is_dir() else "📄"
                items.append(f"{t} {entry.name}")
        return "\n".join(sorted(items))

    def _read(self, relative_path: str, max_lines: int = 500) -> str:
        target = self._resolve_path(relative_path)
        if not os.path.isfile(target):
            return f"[Error] 文件不存在: {relative_path}"
        try:
            with open(target, "r", encoding="utf-8") as f:
                lines = f.readlines()
            total = len(lines)
            if total > max_lines:
                lines = lines[:max_lines]
                trunc_msg = f"\n\n... (文件共 {total} 行，已截断前 {max_lines} 行，请用 offset 参数继续读取)"
            else:
                trunc_msg = ""
            return "".join(lines) + trunc_msg
        except UnicodeDecodeError:
            return f"[Error] 文件不是 UTF-8 文本格式，无法读取: {relative_path}"

    def _patch(self, relative_path: str, old_str: str, new_str: str) -> str:
        target = self._resolve_path(relative_path)

        if not os.path.isfile(target):
            return f"[Error] 文件不存在: {relative_path}"
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
        if old_str not in content:
            return f"[Error] 在文件中未找到指定的旧片段，修改已取消。请确保片段完全匹配（包括缩进和换行）。"
        # 只替换第一次出现
        new_content = content.replace(old_str, new_str, 1)
        with open(target, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"[Success] 已成功修改文件 {relative_path}"

    def _write(self, relative_path: str, content: str) -> str:
        target = self._resolve_path(relative_path)
        if os.path.exists(target):
            return f"[Error] 文件已存在: {relative_path}。如需修改，请使用 fs patch 命令进行精确替换。"
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return f"[Success] 已成功创建文件并写入内容: {relative_path}"
        except Exception as e:
            return f"[Error] 写入文件失败: {e}"

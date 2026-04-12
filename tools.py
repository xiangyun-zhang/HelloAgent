import re
import abc
from sandbox.executor import run_python_code


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
    """具体工具：Python 代码执行器"""

    @property
    def name(self) -> str:
        return "run_python"

    @property
    def description(self) -> str:
        return "用于执行 Python 代码并返回结果。格式: ```run_python\n代码\n```"

    def execute(self, llm_response: str) -> str:
        # 1. 提取属于自己管的代码块
        code_blocks = re.findall(r"```run_python\n(.*?)```", llm_response, re.DOTALL)

        # 如果闭合格式没匹配到，但存在标记，尝试提取未闭合的代码块
        if not code_blocks and "```run_python" in llm_response:
            code_blocks = re.findall(r"```run_python\n(.*)", llm_response, re.DOTALL)

        if not code_blocks:
            return ""

        # 2. 合并所有代码块为一次执行（保证进程内变量共享）
        combined_code = "\n\n".join(code_blocks)
        print(f" ▶ 执行中 (共 {len(code_blocks)} 个代码块)...", end="")
        result = run_python_code(combined_code)
        
        if result == "None":
            result = "执行成功（无返回值）"
            
        is_error = "[Error]" in result
        print(" ❌" if is_error else " ✅")
        execution_results = [f"[执行结果 #1]\n{result}"]

        # 3. 返回最终拼接好的长字符串
        return "\n\n".join(execution_results)


class ToolRegistry:
    """工具注册表（大管家）"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """雇佣工具，登记在册"""
        self._tools[tool.name] = tool

    def needs_to_run(self, llm_response: str) -> bool:
        """检查大模型的回复里，有没有需要调用工具的标记"""
        for name in self._tools:
            if f"```{name}" in llm_response:
                return True
        return False

    def run(self, llm_response: str) -> str:
        """统一调度：找出需要干活的工具，让它们干活，收集结果"""
        final_results = []
        for name, tool in self._tools.items():
            if f"```{name}" in llm_response:
                res = tool.execute(llm_response)
                if res:
                    final_results.append(res)
        return "\n\n".join(final_results)

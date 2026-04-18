import uuid
from config import AGENT_NAME, MAX_HISTORY_ROUNDS
from database import init_db, save_message, load_global_recent_messages
from llm_client import chat
from memory import MemoryManager
from sandbox.executor import Sandbox, WORKSPACE_DIR
from tools import PythonTool, ToolRegistry, FileSystemTool
from utils import load_txt, load_prompts_from_dir

MAX_TOOL_ITERATIONS = 5


class Agent:
    def __init__(self):
        init_db()
        self.session_id = str(uuid.uuid4())

        # 1. 加载人设与规则
        raw_profile = load_txt("profile.md")
        system_rules = load_prompts_from_dir("prompts")
        self.base_system_prompt = (raw_profile + "\n\n" + system_rules) if system_rules else raw_profile

        # 2. 初始化记忆与工具
        self.memory_manager = MemoryManager()
        self.registry = ToolRegistry()
        self.registry.register(PythonTool())
        self.registry.register(FileSystemTool(WORKSPACE_DIR))

        self.on_status = lambda msg: None

        # 3. 恢复历史
        self.chat_history = []
        history = load_global_recent_messages(limit=MAX_HISTORY_ROUNDS * 2)
        if history:
            self.chat_history.extend(history)
        self.history_baseline = len(history)

    def _status(self, msg: str):
        if self.on_status:
            self.on_status(msg)

    def chat(self, user_input: str) -> str:
        """核心处理引擎：接收一句话，返回最终回复"""
        if not user_input or not user_input.strip():
            return ""

        # 保存用户输入
        save_message(self.session_id, "user", user_input)
        self.chat_history.append({"role": "user", "content": user_input})

        # 动态拼接记忆
        retrieved_memories, _ = self.memory_manager.search_memory(user_input, top_k=3)
        dynamic_system_prompt = self.base_system_prompt
        if retrieved_memories:
            memory_context = "\n\n【用户相关的长期记忆】\n" + "\n".join(f"- {m}" for m in retrieved_memories)
            dynamic_system_prompt += memory_context

        # ReAct 工具循环 (把 main.py 里的 while 循环整段搬过来，注意缩进)
        tool_iteration = 0
        sandbox = Sandbox()
        self.registry.bind_sandbox(sandbox)
        final_answer = None

        while tool_iteration < MAX_TOOL_ITERATIONS:
            messages_to_send = [{"role": "system", "content": dynamic_system_prompt}] + self.chat_history
            response = chat(messages_to_send)

            # 检测回复中是否包含工具调用
            if self.registry.needs_to_run(response):
                self._status(f"🤖 {AGENT_NAME} (思考中):\n{response}")

                trigger_count = response.count("```run_python") + response.count("```python")
                self._status(f"\n⚙️ [系统] 检测到 {trigger_count} 个工具执行请求，正在沙箱运行...")

                full_results = self.registry.run(response)
                has_error = "[Error]" in full_results
                self._status(f"\n📋 执行结果:\n{full_results}\n")

                # 把思考过程存入历史（这里存的是 response，不是 final_answer）
                self.chat_history.append({"role": "assistant", "content": response})
                save_message(self.session_id, "assistant", response)

                if has_error:
                    feedback_msg = (
                        f"代码执行出错，返回结果如下：\n"
                        f"{full_results}\n\n"
                        f"请分析错误原因，修正代码后重新执行。"
                        f"如果错误无法通过修改代码解决，再用自然语言解释。"
                    )
                else:
                    feedback_msg = (
                        f"代码已在沙箱中执行完毕，返回结果如下：\n"
                        f"{full_results}\n\n"
                        f"如果任务已全部完成，请用自然语言总结回答用户。"
                        f"如果还有未完成的步骤，请继续使用 run_python 执行。"
                    )

                self.chat_history.append({"role": "user", "content": feedback_msg})

                tool_iteration += 1
                continue
            else:
                final_answer = response
                break

        # 记录最终回复
        if final_answer:
            self.chat_history.append({"role": "assistant", "content": final_answer})

            # 保存助手回复到数据库
            save_message(self.session_id, "assistant", final_answer)
        elif tool_iteration >= MAX_TOOL_ITERATIONS:
            final_answer = f"⚠️ [系统] 连续调用了 {MAX_TOOL_ITERATIONS} 次工具仍未得出结论，已强制停止。"

        # 记忆沉淀：放在最终响应之后，不在工具循环里面
        if len(self.chat_history) % 20 == 0:
            self.memory_manager.consolidate(self.chat_history[self.history_baseline:])

        # 对话历史裁剪（保留恢复的历史 + 当前会话的最近几轮）
        # 如果有恢复历史（10条），至少保留 10 + 当前 10 轮
        max_messages = self.history_baseline + MAX_HISTORY_ROUNDS * 2
        if len(self.chat_history) > max_messages:
            self.chat_history = self.chat_history[-max_messages:]

        return final_answer if final_answer else ""

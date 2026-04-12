import os
import uuid

from config import AGENT_NAME, MAX_HISTORY_ROUNDS
from database import init_db, save_message, get_history_list, clear_all_history, load_global_recent_messages
from llm_client import chat
from memory import MemoryManager
from sandbox.executor import Sandbox
from tools import PythonTool, ToolRegistry

MAX_TOOL_ITERATIONS = 5  # 防止 Agent 陷入无限调用循环


def load_txt(filepath: str) -> str:
    """通用的文本文件读取器"""
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def load_prompts_from_dir(dir_path: str) -> str:
    """
    自动扫描目录下所有 .md 文件并拼接
    约定：通过文件名前缀的数字控制加载顺序（如 01_xxx.md, 02_yyy.md）
    """
    if not os.path.exists(dir_path):
        return ""

    md_files = [f for f in os.listdir(dir_path) if f.endswith('.md')]
    md_files.sort()

    prompts = []
    for filename in md_files:
        filepath = os.path.join(dir_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                prompts.append(content)

    return "\n\n".join(prompts)


def main():
    init_db()  # 确保表存在
    session_id = str(uuid.uuid4()) # 给本次启动生成一个唯一会话ID

    print("正在加载配置...")

    raw_profile = load_txt("profile.md")
    system_rules = load_prompts_from_dir("prompts")

    system_prompt = (raw_profile + "\n\n" + system_rules) if system_rules else raw_profile

    if not raw_profile:
        print(" [提示] 未找到 profile.md，请参考 profile.md.example 配置。")
    print(f"\033[32m✅ {AGENT_NAME} 已启动！(输入 'quit' 退出)\033[0m\n")
    print("-" * 40)

    chat_history = []
    # 跨所有会话加载历史记忆
    history = load_global_recent_messages(limit=MAX_HISTORY_ROUNDS * 2)
    if history:
        chat_history.extend(history)
        print(f"\n📂 已恢复了 {len(history)} 条历史记录。")

    history_baseline = len(history)  # 记录启动时的历史长度，作为记忆提取的起点

    memory_manager = MemoryManager()
    registry = ToolRegistry()
    registry.register(PythonTool())

    while True:
        try:
            user_input = input("\n👤 你: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                memory_manager.consolidate(chat_history[history_baseline:])
                print(f"{AGENT_NAME}: 好的，随时待命！")
                break

            if user_input.lower() == "/history":
                print("\n📜 近期会话记录：")
                for record in get_history_list(limit=MAX_HISTORY_ROUNDS // 2):
                    print(f" - {record}")
                continue

            if user_input.lower() == "/clear":
                chat_history.clear()
                print(f"\n🧹 当前对话已清空，开始新对话。")
                continue

            if user_input.lower() == "/clearall":
                confirm = input("⚠️ 确定要删除所有历史记录吗？(y/N): ").strip().lower()
                if confirm == 'y':
                    clear_all_history()
                    chat_history.clear()
                    print("\n🗑️ 所有历史记录已彻底清除。")
                else:
                    print("\n已取消。")
                continue

            if user_input.lower() == "/memory":
                print("\n🧠 当前长期记忆库：")
                all_mem = memory_manager.get_all_memories()
                if not all_mem:
                    print(" (空空如也)")
                for i, m in enumerate(all_mem, 1):
                    print(f" {i}. {m}")
                continue

            if user_input.lower() == "/clearmemory":
                confirm = input("⚠️ 确定要清空所有长期记忆吗？此操作不可逆！(y/N): ").strip().lower()
                if confirm == 'y':
                    memory_manager.clear_all_memories()
                    print("\n🗑️ 长期记忆已彻底抹除。")
                else:
                    print("\n已取消。")
                continue

            if not user_input:
                continue

            # 保存用户输入到数据库
            save_message(session_id, "user", user_input)

            chat_history.append({"role": "user", "content": user_input})

            # =============================================
            # 长期记忆动态检索与注入
            # 根据当前用户输入，从向量库拉取相关记忆拼接到 System Prompt
            # =============================================
            retrieved_memories, _ = memory_manager.search_memory(user_input, top_k=3)
            dynamic_system_prompt = system_prompt
            if retrieved_memories:
                memory_context = "\n\n【用户相关的长期记忆】\n" + "\n".join(f"- {m}" for m in retrieved_memories)
                dynamic_system_prompt += memory_context

            # =============================================
            # 工具调用循环（ReAct 模式）
            # 每次用户提问后，可能需要多轮 工具调用→解读 循环
            # =============================================
            tool_iteration = 0
            sandbox = Sandbox()
            registry.bind_sandbox(sandbox)
            final_answer = None

            while tool_iteration < MAX_TOOL_ITERATIONS:
                messages_to_send = [{"role": "system", "content": dynamic_system_prompt}] + chat_history
                response = chat(messages_to_send)

                # 检测回复中是否包含工具调用
                if registry.needs_to_run(response):
                    print(f"\n🤖 {AGENT_NAME} (思考中):", flush=True)
                    print(response)

                    trigger_count = response.count("```run_python") + response.count("```python")
                    print(f"\n⚙️ [系统] 检测到 {trigger_count} 个工具执行请求，正在沙箱运行...")

                    full_results = registry.run(response)
                    has_error = "[Error]" in full_results

                    print(f"\n📋 执行结果:\n{full_results}\n")

                    # 把思考过程存入历史（这里存的是 response，不是 final_answer）
                    chat_history.append({"role": "assistant", "content": response})
                    save_message(session_id, "assistant", response)

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

                    chat_history.append({"role": "user", "content": feedback_msg})

                    tool_iteration += 1
                    continue

                else:
                    # --------------------------------------------------
                    # 最终响应：Agent 不需要执行代码，直接回答
                    # --------------------------------------------------
                    final_answer = response
                    break

            # 显示最终答案
            if final_answer:
                print(f"\n🤖 {AGENT_NAME}: {final_answer}")
                chat_history.append({"role": "assistant", "content": final_answer})

                # 保存助手回复到数据库
                save_message(session_id, "assistant", final_answer)

            elif tool_iteration >= MAX_TOOL_ITERATIONS:
                print(f"\n⚠️ [系统] {AGENT_NAME} 连续调用了 {MAX_TOOL_ITERATIONS} 次工具仍未得出结论，已强制停止。")

            # 记忆沉淀：放在最终响应之后，不在工具循环里面
            if len(chat_history) % 20 == 0:
                memory_manager.consolidate(chat_history[history_baseline:])

            # 对话历史裁剪（保留恢复的历史 + 当前会话的最近几轮）
            # 如果有恢复历史（10条），至少保留 10 + 当前 10 轮
            history_budget = len(history)
            max_messages = history_budget + MAX_HISTORY_ROUNDS * 2
            if len(chat_history) > max_messages:
                chat_history = chat_history[-max_messages:]

        except KeyboardInterrupt:
            print(f"\n\n{AGENT_NAME}: 检测到中断，正在退出...")
            break


if __name__ == "__main__":
    main()

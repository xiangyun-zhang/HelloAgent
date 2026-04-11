import os
import re
from config import AGENT_NAME, MAX_HISTORY_ROUNDS
from llm_client import chat
from sandbox.executor import run_python_code

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


def extract_code_blocks(response: str) -> list:
    """从 LLM 回复中提取 ```run_python 代码块"""
    pattern = r"```run_python\s*\n(.*?)```"
    return re.findall(pattern, response, re.DOTALL)


def main():
    print("正在加载配置...")

    raw_profile = load_txt("profile.md")
    system_rules = load_prompts_from_dir("prompts")

    system_prompt = (raw_profile + "\n\n" + system_rules) if system_rules else raw_profile

    if not raw_profile:
        print("       [提示] 未找到 profile.md，请参考 profile.md.example 配置。")
    print(f"\033[32m✅ {AGENT_NAME} 已启动！(输入 'quit' 退出)\033[0m\n")
    print("-" * 40)

    chat_history = []

    while True:
        try:
            user_input = input("\n👤 你: ")

            if user_input.strip().lower() in ['quit', 'exit', 'q']:
                print(f"{AGENT_NAME}: 好的，随时待命！")
                break

            if not user_input.strip():
                continue

            chat_history.append({"role": "user", "content": user_input})

            # =============================================
            # 工具调用循环（ReAct 模式）
            # 每次用户提问后，可能需要多轮 工具调用→解读 循环
            # =============================================
            tool_iteration = 0
            final_answer = None

            while tool_iteration < MAX_TOOL_ITERATIONS:
                messages_to_send = [{"role": "system", "content": system_prompt}] + chat_history
                response = chat(messages_to_send)

                # 检测回复中是否包含工具调用
                code_blocks = extract_code_blocks(response)

                if code_blocks:
                    # --------------------------------------------------
                    # 中间响应：Agent 想要执行代码
                    # 展示思考过程，执行代码，把结果喂回去让它解读
                    # --------------------------------------------------
                    print(f"\n🤖 {AGENT_NAME} (思考中):", flush=True)
                    print(response)

                    print(f"\n⚙️  [系统] 检测到 {len(code_blocks)} 个代码执行请求，正在沙箱运行...")

                    results = []
                    for i, code in enumerate(code_blocks, 1):
                        print(f"   ▶ 执行中 ({i}/{len(code_blocks)})...", end="", flush=True)
                        result = run_python_code(code.strip())
                        results.append(f"[执行结果 #{i}]\n{result}")
                        print(" ✅")

                    full_results = "\n\n".join(results)
                    print(f"\n📋 执行结果:\n{full_results}\n")

                    # 把"思考过程"和"执行结果"都存入历史
                    chat_history.append({"role": "assistant", "content": response})
                    chat_history.append({
                        "role": "user",
                        "content": (
                            f"代码已在沙箱中执行完毕，返回结果如下：\n"
                            f"{full_results}\n\n"
                            f"请根据以上结果，用自然语言回答用户的原始问题。"
                            f"不要再次输出代码块，也不要复述执行结果，直接用自然语言回答。"

                        )
                    })

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
            elif tool_iteration >= MAX_TOOL_ITERATIONS:
                print(f"\n⚠️  [系统] {AGENT_NAME} 连续调用了 {MAX_TOOL_ITERATIONS} 次工具仍未得出结论，已强制停止。")

            # 对话历史裁剪（防止 Token 超限）
            max_messages = MAX_HISTORY_ROUNDS * 2
            if len(chat_history) > max_messages:
                chat_history = chat_history[-max_messages:]

        except KeyboardInterrupt:
            print(f"\n\n{AGENT_NAME}: 检测到中断，正在退出...")
            break


if __name__ == "__main__":
    main()

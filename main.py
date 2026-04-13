from agent import Agent  # 引入我们的大脑
from config import AGENT_NAME, MAX_HISTORY_ROUNDS
from database import get_history_list, clear_all_history


def main():
    agent = Agent()  # 启动大脑
    agent.on_status = print
    memory_manager = agent.memory_manager  # 拿到记忆管理器实例

    print(f"\033[32m✅ {AGENT_NAME} 已启动！(输入 'quit' 退出)\033[0m\n")
    print("-" * 40)

    if agent.history_baseline > 0:
        print(f"\n📂 已恢复了 {agent.history_baseline} 条历史记录。")

    while True:
        try:
            user_input = input("\n👤 你: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                memory_manager.consolidate(agent.chat_history[agent.history_baseline:])
                print(f"{AGENT_NAME}: 好的，随时待命！")
                break
            if user_input.lower() == "/history":
                print("\n📜 近期会话记录：")
                for record in get_history_list(limit=MAX_HISTORY_ROUNDS // 2):
                    print(f" - {record}")
                continue

            if user_input.lower() == "/clear":
                agent.chat_history.clear()
                print(f"\n🧹 当前对话已清空，开始新对话。")
                continue

            if user_input.lower() == "/clearall":
                confirm = input("⚠️ 确定要删除所有历史记录吗？(y/N): ").strip().lower()
                if confirm == 'y':
                    clear_all_history()
                    agent.chat_history.clear()
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

                # 🎯 核心简化：把所有逻辑都扔给 agent，只管拿结果打印！
            final_answer = agent.chat(user_input)

            if final_answer:
                print(f"\n🤖 {AGENT_NAME}: {final_answer}")

        except KeyboardInterrupt:
            print(f"\n\n{AGENT_NAME}: 检测到中断，正在退出...")
            break

if __name__ == "__main__":
    main()

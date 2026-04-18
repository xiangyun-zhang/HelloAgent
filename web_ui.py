import gradio as gr
from agent import Agent
from config import AGENT_NAME
from database import clear_all_history, get_history_list

agent = Agent()

def predict(message, history):
    # 处理内置命令
    msg = message.strip()
    if msg.lower() in ["/clearall"]:
        clear_all_history()
        agent.chat_history.clear()
        yield "🗑️ 所有历史记录已彻底清除。"
        return

    if msg.lower() == "/clear":
        agent.chat_history.clear()
        yield "🧹 当前对话已清空，开始新对话。"
        return

    if msg.lower() == "/history":
        records = get_history_list(limit=5)
        if records:
            yield "📜 近期会话记录：\n" + "\n".join(f"- {r}" for r in records)
        else:
            yield "📜 暂无历史记录。"
        return

    if msg.lower() == "/memory":
        all_mem = agent.memory_manager.get_all_memories()
        if all_mem:
            yield "🧠 当前长期记忆库：\n" + "\n".join(f"{i}. {m}" for i, m in enumerate(all_mem, 1))
        else:
            yield "🧠 长期记忆库为空。"
        return

    if msg.lower() == "/clearmemory":
        agent.memory_manager.clear_all_memories()
        yield "🗑️ 长期记忆已彻底抹除。"
        return

    # 普通对话：调用 agent.chat
    status_logs = []

    def capture_status(msg):
        status_logs.append(msg)

    agent.on_status = capture_status
    response = agent.chat(message)

    if status_logs:
        full_output = "\n".join(status_logs) + "\n\n---\n\n" + (response if response else "")
        yield full_output
    else:
        yield response if response else "（系统无响应）"

demo = gr.ChatInterface(
    fn=predict,
    chatbot=gr.Chatbot(type="messages"),
    type="messages",
    title=f"💬 {AGENT_NAME} Web UI",
    description="底层大脑已就绪，当前为【拼接展示】模式。",
)

if __name__ == "__main__":
    print("\n🚀 正在启动 Web UI...")
    demo.launch(server_name="0.0.0.0", server_port=7860)
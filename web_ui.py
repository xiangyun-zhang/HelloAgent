import gradio as gr
from agent import Agent
from config import AGENT_NAME

# 实例化大脑
agent = Agent()

# 准备一个“小本本”来记录思考过程
status_logs = []


def capture_status(msg):
    """每当 agent 有动静，就记在小本本上"""
    status_logs.append(msg)


def predict(message, history):
    global status_logs
    status_logs = []  # 每次新对话，清空小本本

    # 把小本本交给 agent
    agent.on_status = capture_status

    # 执行核心逻辑
    response = agent.chat(message)

    # 如果有思考过程，拼在最终答案前面展示
    if status_logs:
        full_output = "\n".join(status_logs) + "\n\n---\n\n" + (response if response else "")
        return full_output

    # 如果没触发工具（比如普通闲聊），直接返回原话
    return response if response else "（系统无响应）"


# 搭建骨架
demo = gr.ChatInterface(
    fn=predict,
    title=f"💬 {AGENT_NAME} Web UI",
    description="底层大脑已就绪，当前为【拼接展示】模式。",
)

if __name__ == "__main__":
    print(f"\n🚀 正在启动 Web UI...")
    demo.launch(server_name="0.0.0.0", server_port=7860)

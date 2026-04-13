import gradio as gr
from agent import Agent
from config import AGENT_NAME

# 实例化大脑
# 注意：这里我们故意不写 agent.on_status = ...
# 让它保持静默，因为基础的 ChatInterface 还不支持中间态输出
agent = Agent()

def predict(message, history):
    """
    Gradio 的标准对话回调。
    - message: 用户刚发的一句话
    - history: Gradio 前端维护的聊天记录（格式如 [["user","ai"], ...]）
    我们直接忽略 Gradio 的 history，因为真实记忆全在 agent 内部管理。
    """
    response = agent.chat(message)
    return response if response else "（系统无响应）"

# 搭建骨架
demo = gr.ChatInterface(
    fn=predict,
    title=f"💬 {AGENT_NAME} Web UI",
    description="底层大脑已就绪，当前为基础骨架模式。",
)

if __name__ == "__main__":
    print(f"\n🚀 正在启动 Web UI...")
    # server_name="0.0.0.0" 允许局域网访问（比如用手机测）
    demo.launch(server_name="0.0.0.0", server_port=7860)

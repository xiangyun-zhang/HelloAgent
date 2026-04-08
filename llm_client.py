from openai import OpenAI
from config import API_KEY, BASE_URL, MODEL_NAME

# 初始化客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def chat(system_prompt: str, user_input: str) -> str:
    """
    发送消息给大模型并获取回复
    :param system_prompt: 系统提示词（人设）
    :param user_input: 用户输入
    :return: 模型回复的文本
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,  # 稍微有一点创造性，但不至于太跳脱
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[系统错误] 调用模型失败: {e}"

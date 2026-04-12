from openai import OpenAI
from config import API_KEY, BASE_URL, MODEL_NAME

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def chat(messages: list) -> str:
    """
    发送完整的消息列表给大模型并获取回复
    :param messages: 符合 OpenAI 格式的消息列表 [{"role": "system", "content": "..."}, ...]
    :return: 模型回复的文本
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[系统错误] 调用模型失败: {e}"

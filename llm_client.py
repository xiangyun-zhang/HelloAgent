import requests

from openai import OpenAI
from config import API_KEY, BASE_URL, MODEL_NAME

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def chat(messages: list) -> str | None:
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

# --- 以下为 M5 新增的 Embedding 接口 ---

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """调用智谱 Embedding API 获取文本向量"""
    url = f"{BASE_URL}/embeddings"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "embedding-3",  # 智谱最新、效果最好的 embedding 模型
        "input": texts
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        # 智谱返回格式: {"data": [{"embedding": [...], "index": 0}, ...]}
        # 必须按 index 排序，保证向量和原文顺序一致
        data = response.json().get("data", [])
        data.sort(key=lambda x: x["index"])
        return [item["embedding"] for item in data]
    except Exception as e:
        print(f"[Error] Embedding 请求失败: {e}")
        # 返回空列表防止主程序崩溃，上层需要做判空处理
        return [[] for _ in texts]

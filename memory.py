import os
import uuid
import json
import re
import chromadb
from llm_client import get_embeddings

# 向量数据库持久化存储在本地 data 目录下
DB_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
COLLECTION_NAME = "long_term_memory"


class MemoryManager:
    def __init__(self):
        os.makedirs(DB_DIR, exist_ok=True)
        # 初始化本地持久化客户端
        self.client = chromadb.PersistentClient(path=DB_DIR)
        # 获取或创建集合，使用余弦相似度
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def add_memory(self, fact: str):
        """向长期记忆中存入一条事实"""
        if not fact or not fact.strip():
            return

        embeddings = get_embeddings([fact])
        if not embeddings or not embeddings[0]:
            print("[Memory] 获取 Embedding 失败，跳过存储。")
            return

        mem_id = str(uuid.uuid4())
        self.collection.add(
            ids=[mem_id],
            documents=[fact],
            embeddings=embeddings
        )

    def search_memory(self, query: str, top_k: int = 3) -> tuple[list[str], list[float]]:
        """根据用户的提问，检索最相关的 k 条记忆，返回 (文档列表, 距离列表)"""
        if self.collection.count() == 0:
            return [], []
        query_embedding = get_embeddings([query])
        if not query_embedding or not query_embedding[0]:
            return [], []
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )
        if results and results['documents']:
            return results['documents'][0], results['distances'][0]
        return [], []

    def get_all_memories(self) -> list[str]:
        """获取所有记忆（备用，后续 /memory 指令会用到）"""
        if self.collection.count() == 0:
            return []
        results = self.collection.get()
        return results.get('documents', [])

    def extract_memories(self, chat_history: list[dict]) -> list[str]:
        """调用 LLM 从对话历史中提取值得长期保存的事实"""
        conversation = []
        for msg in chat_history:
            if msg["role"] in ("user", "assistant"):
                conversation.append(f"{msg['role']}: {msg['content']}")

        if not conversation:
            return []

        extract_prompt = ""
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "03_memory_extract.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                extract_prompt = f.read().strip()

        conversation_text = "\n".join(conversation[-20:])

        messages = [
            {"role": "system", "content": extract_prompt},
            {"role": "user", "content": f"请从以下对话中提取值得长期记忆的事实：\n\n{conversation_text}"}
        ]

        from llm_client import chat
        response = chat(messages)

        # 解析 JSON 结果
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 兜底：尝试从可能的代码块中提取 JSON 数组
            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            print(f"[Memory] 提取结果解析失败: {response[:100]}")
            return []

    def consolidate(self, chat_history: list[dict]):
        """一键执行：提取 -> 去重 -> 写入"""
        new_facts = self.extract_memories(chat_history)
        if not new_facts:
            print("\n🧠 [记忆] 本次对话没有需要沉淀的新事实。")
            return

        added = 0
        skipped = 0
        for fact in new_facts:
            existing_docs, existing_dists = self.search_memory(fact, top_k=1)
            if existing_docs and self._is_similar(fact, existing_docs[0], existing_dists[0]):
                skipped += 1
                continue
            self.add_memory(fact)
            added += 1
        print(f"\n🧠 [记忆] 提取完成：新增 {added} 条，去重跳过 {skipped} 条。")

    @staticmethod
    def _is_similar(new_fact: str, existing_fact: str, distance: float | None = None) -> bool:
        """去重判断：字符串包含 + 向量相似度双重防线"""
        # 快速路径：字符串包含
        if new_fact.strip() in existing_fact.strip() or existing_fact.strip() in new_fact.strip():
            return True
        # 高级路径：向量余弦距离（集合已配置 cosine space，distance = 1 - similarity）
        # distance < 0.3 等价于 similarity > 0.7
        if distance is not None and distance < 0.3:
            return True
        return False

    def clear_all_memories(self):
        """彻底清空长期记忆向量库"""
        self.client.delete_collection("long_term_memory")
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

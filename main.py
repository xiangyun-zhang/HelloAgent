import os
from config import AGENT_NAME, MAX_HISTORY_ROUNDS
from llm_client import chat

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
    
    # 找出目录下所有 .md 文件
    md_files = [f for f in os.listdir(dir_path) if f.endswith('.md')]
    
    # 按文件名自然排序（这样 01_ 会排在 02_ 前面）
    md_files.sort()
    
    prompts = []
    for filename in md_files:
        filepath = os.path.join(dir_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:  # 跳过空文件
                prompts.append(content)
                
    return "\n\n".join(prompts)

def main():
    print("正在加载配置...")
    
    # 1. 加载基础人设
    raw_profile = load_txt("profile.md")
    
    # 2. 自动加载 prompts 目录下的所有系统规则
    system_rules = load_prompts_from_dir("prompts")
    
    # 3. 拼装最终 Prompt（人设在前，系统硬规则在后，保证规则优先级）
    system_prompt = raw_profile + "\n\n" + system_rules if system_rules else raw_profile
    
    if not raw_profile:
        print("       [提示] 未找到 profile.md，请参考 profile.md.example 配置。")
    print(f"✅ {AGENT_NAME} 已启动！(输入 'quit' 退出)\n")
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
            messages_to_send = [{"role": "system", "content": system_prompt}] + chat_history
            
            print(f"🤖 {AGENT_NAME}: ", end="", flush=True)
            response = chat(messages_to_send)
            print(response)
            
            chat_history.append({"role": "assistant", "content": response})
            
            max_messages = MAX_HISTORY_ROUNDS * 2
            if len(chat_history) > max_messages:
                chat_history = chat_history[-max_messages:]
                
        except KeyboardInterrupt:
            print(f"\n\n{AGENT_NAME}: 检测到中断，正在退出...")
            break

if __name__ == "__main__":
    main()

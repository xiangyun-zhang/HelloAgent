import os
from llm_client import chat

def load_profile(filepath: str = "profile.md") -> str:
    """
    读取本地的人设文件
    """
    default_prompt = "你是一个有帮助的AI助手。"
    
    if not os.path.exists(filepath):
        print(f"\n[提示] 未找到 {filepath}。")
        print(f"       请复制 profile.md.example 并重命名为 profile.md，然后填入你的真实信息。")
        print(f"       当前将使用默认人设启动...\n")
        return default_prompt
    
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def main():
    # 1. 加载人设
    print("正在加载人设...")
    system_prompt = load_profile()
    print("✅ 私人助理已启动！(输入 'quit' 退出)\n")
    print("-" * 40)

    # 2. 主循环
    while True:
        try:
            # 获取用户输入
            user_input = input("\n👤 你: ")
            
            # 退出逻辑
            if user_input.strip().lower() in ['quit', 'exit', 'q']:
                print("助理: 好的，随时待命！")
                break
            
            if not user_input.strip():
                continue
            
            # 调用模型 (注意这里没有 print 换行，让输出更紧凑)
            print("🤖 助理: ", end="", flush=True)
            response = chat(system_prompt, user_input)
            print(response)
            
        except KeyboardInterrupt:
            # 捕获 Ctrl+C，优雅退出
            print("\n\n助理: 检测到中断，正在退出...")
            break

if __name__ == "__main__":
    main()

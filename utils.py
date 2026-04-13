import os

def load_txt(filename: str) -> str:
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def load_prompts_from_dir(dirname: str) -> str:
    dirpath = os.path.join(os.path.dirname(__file__), dirname)
    if not os.path.isdir(dirpath):
        return ""
    parts = []
    for fname in sorted(os.listdir(dirpath)):
        if fname.endswith(".md"):
            with open(os.path.join(dirpath, fname), "r", encoding="utf-8") as f:
                parts.append(f.read().strip())
    return "\n\n".join(parts)

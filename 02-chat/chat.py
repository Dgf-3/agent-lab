"""02-chat —— 多轮对话：messages 数组就是模型的全部记忆"""
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

# --- loader：从仓库根目录的 .env 取密钥（相对脚本上跳两级）---
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]                      # 剥成对引号（知识点#4）
            os.environ.setdefault(k.strip(), v.strip())

KEY   = os.environ["INK_API_KEY"]
BASE  = "https://discovery-api.intern-ai.org.cn"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "deepseek-v4-flash-0731"
SYSTEM = "你是一个说话简洁的编程导师，每次回答不超过三句话。"

messages = [{"role": "system", "content": SYSTEM}]   # 人设放最前，全程随行
total_in = total_out = 0

def call(msgs):
    req = urllib.request.Request(
        f"{BASE}/v1/chat/completions",
        data=json.dumps({"model": MODEL, "messages": msgs}).encode(),
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {KEY}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

# from openai import OpenAI
# client = OpenAI(api_key=KEY, base_url=BASE + "/v1")
# data = client.chat.completions.create(model=MODEL, messages=msgs)

print(f"已连接 {MODEL} | 指令：exit 退出，/reset 清空记忆\n")
while True:
    try:
        user = input("你> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n再见。"); break
    if not user:
        continue
    if user.lower() in ("exit", "quit"):
        break
    if user == "/reset":
        messages = [{"role": "system", "content": SYSTEM}]
        total_in = total_out = 0
        print("上下文已清空。\n"); continue

    messages.append({"role": "user", "content": user})
    try:
        data = call(messages)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}:", e.read().decode(errors="replace")[:300], "\n")
        messages.pop()               # 失败的那条撤回，别污染历史
        continue

    reply = data["choices"][0]["message"]["content"]
    usage = data["usage"]
    total_in  += usage.get("prompt_tokens", 0)
    total_out += usage.get("completion_tokens", 0)

    messages.append({"role": "assistant", "content": reply})   # 记忆的关键行
    print(f"\nAI> {reply}")
    print(f"   [累计 {total_in}+{total_out} tok | 历史 {len(messages)} 条]\n")

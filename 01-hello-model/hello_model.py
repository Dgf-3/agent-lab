# import os
# from dotenv import load_dotenv
# from openai import OpenAI

# load_dotenv()
# client = OpenAI(
#     api_key=os.getenv("INK_API_KEY"),  # 密钥放 .env，别硬编码
#     base_url="https://discovery-api.intern-ai.org.cn/v1"
# )

# resp = client.chat.completions.create(
#     model="deepseek-v4-flash-0731",  # 以控制台模型列表为准
#     messages=[{"role": "user", "content": "你好，报一下你的名字"}],
# )
# print(resp.choices[0].message.content)
"""01-hello-model (OpenAI 方言) —— 调 discovery 平台的 deepseek"""
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

# --- 加载 .env：配置进文件，密钥不进代码、不进 git ---
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())   # 已设的环境变量优先

KEY   = os.environ["INK_API_KEY"]
# print(f"[debug] len={len(KEY)}, head={KEY[:10]!r}, tail={KEY[-6:]!r}")

BASE  = "https://discovery-api.intern-ai.org.cn"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "deepseek-v4-flash-0731"

payload = {
    "model": MODEL,
    "messages": [{"role": "user",
                  "content": "用一句话自我介绍，然后说：第一块砖，垒上了。"}],
}

req = urllib.request.Request(
    f"{BASE}/v1/chat/completions",            # ← OpenAI 方言端点
    data=json.dumps(payload).encode(),
    headers={
        "content-type": "application/json",
        "authorization": f"Bearer {KEY}",     # ← OpenAI 方言认证
    },
)

try:
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}:", e.read().decode(errors="replace")[:500])
    sys.exit(1)

print(f"[{MODEL}] 说：\n{data['choices'][0]['message']['content']}\n")
print("token 账单：", data["usage"])

"""03-tools —— function calling：模型点菜，你的代码下厨"""
import datetime, json, os, sys, urllib.request, urllib.error
from pathlib import Path

# --- .env loader（同 02）---
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            os.environ.setdefault(k.strip(), v.strip())

KEY   = os.environ["INK_API_KEY"]
BASE  = "https://discovery-api.intern-ai.org.cn"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "deepseek-v4-flash-0731"
SYSTEM = "你是一个说话简洁的编程导师。需要实时信息或精确计算时必须调用工具，禁止凭记忆编造。"

# ---------- 说明书：JSON Schema，模型据此决定何时点菜、怎么点 ----------
TOOLS = [
    {"type": "function", "function": {
        "name": "get_current_time",
        "description": "获取当前本机日期时间。凡涉及'现在/今天/几点'的问题，必须先调用它。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "calculator",
        "description": "精确计算四则运算表达式，支持 + - * / ( ) 和小数。多位数运算必须调用它，不要心算。",
        "parameters": {"type": "object",
            "properties": {"expression": {"type": "string", "description": "如 '128*39+7'"}},
            "required": ["expression"]}}},
]

# ---------- 后厨：真正的执行者 ----------
def get_current_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculator(expression):
    if not set(expression) <= set("0123456789+-*/(). "):   # 白名单，见知识点 #13
        return "错误：表达式含非法字符"
    try:
        return repr(eval(expression))    # 实验室特权：仅因有白名单才可用 eval
    except Exception as e:
        return f"计算出错：{e}"

TOOL_IMPL = {"get_current_time": get_current_time, "calculator": calculator}

def call(msgs):
    body = {"model": MODEL, "messages": msgs, "tools": TOOLS}
    req = urllib.request.Request(
        f"{BASE}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {KEY}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

messages = [{"role": "system", "content": SYSTEM}]
total_in = total_out = 0

print(f"已连接 {MODEL}（带工具版） | exit 退出，/reset 清空记忆")
while True:
    try:
        user = input("你> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("再见。"); 
        break
    if not user:
        continue
    if user.lower() in ("exit", "quit"):
        break
    if user == "/reset":
        messages = [{"role": "system", "content": SYSTEM}]
        total_in = total_out = 0
        print("上下文已清空。"); 
        continue

    messages.append({"role": "user", "content": user})

    # ---------- agent loop：要菜就炒，喂回去再问，直到模型给出人话 ----------
    while True:
        try:
            data = call(messages)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}:", e.read().decode(errors="replace")[:300], "")
            messages.pop(); break

        msg = data["choices"][0]["message"]
        u = data["usage"]
        total_in  += u.get("prompt_tokens", 0)
        total_out += u.get("completion_tokens", 0)

        if msg.get("tool_calls"):
            messages.append(msg)                 # 必坑①：带 tool_calls 的 assistant 消息必须入史
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                print(f"   [调用工具] {name}({args})")
                result = TOOL_IMPL[name](**args) if name in TOOL_IMPL else f"没有名为 {name} 的工具"
                messages.append({"role": "tool",
                                 "tool_call_id": tc["id"],      # 必坑②：结果必须带 id
                                 "content": str(result)})
            continue                              # 回炉：让模型看到工具结果

        reply = msg["content"] or "(空回复)"
        messages.append({"role": "assistant", "content": reply})
        print(f"AI> {reply}")
        print(f"   [累计 {total_in}+{total_out} tok | 历史 {len(messages)} 条]")
        break

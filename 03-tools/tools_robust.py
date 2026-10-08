"""03-tools 加固版 —— 模型输出是不可信输入：校验、重试、回喂、限步、回滚"""
import datetime, json, os, socket, sys, urllib.request, urllib.error
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
SYSTEM = ("你是一个说话简洁的编程导师。需要实时信息或精确计算时必须调用工具，禁止凭记忆编造。"
          "任何算术运算都必须调用 calculator，哪怕只是 18*7 这样的两位数乘法，也不得心算。")

MAX_STEPS   = 8    # 单轮最多几次"调工具→回炉"，防死循环烧 token
MAX_RETRIES = 2    # 泄漏/空回复/网络错误的重试次数

TOOLS = [
    {"type": "function", "function": {
        "name": "get_current_time",
        "description": "获取当前本机日期时间。凡涉及'现在/今天/几点'的问题，必须先调用它。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "calculator",
        "description": "精确计算四则运算表达式，支持 + - * / ( ) 和小数。任何算术都必须调用它，不要心算。",
        "parameters": {"type": "object",
            "properties": {"expression": {"type": "string", "description": "如 '128*39+7'"}},
            "required": ["expression"]}}},
]

def get_current_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculator(expression):
    if not set(expression) <= set("0123456789+-*/(). "):
        return "错误：表达式含非法字符"
    try:
        return repr(eval(expression))
    except Exception as e:
        return f"计算出错：{e}"

TOOL_IMPL = {"get_current_time": get_current_time, "calculator": calculator}

class TurnError(Exception):
    """本轮无法完成；调用方负责回滚历史"""

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

def call_with_retry(msgs):
    """网络层：超时/断连重试；HTTP 错误不重试（多半是请求本身有问题）"""
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return call(msgs)
        except urllib.error.HTTPError as e:
            raise TurnError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            last = e
            print(f"   [网络错误，重试 {attempt + 1}/{MAX_RETRIES}] {e}")
    raise TurnError(f"网络持续失败: {last}")

def run_tool(tc):
    """执行一个 tool_call。任何失败都返回错误文本——回喂给模型，而不是崩溃"""
    name = tc["function"]["name"]
    if name not in TOOL_IMPL:
        return f"错误：没有名为 {name} 的工具，可用工具：{list(TOOL_IMPL)}"
    raw = tc["function"].get("arguments") or "{}"
    try:
        args = json.loads(raw)
        if not isinstance(args, dict):
            raise ValueError("参数必须是 JSON 对象")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"   [参数无效] {name} {raw!r}")
        return f"错误：参数不是合法 JSON 对象（{e}），请重新调用"
    print(f"   [调用工具] {name}({args})")
    try:
        return str(TOOL_IMPL[name](**args))
    except TypeError as e:                       # 参数名缺失/多余
        return f"错误：参数不符合工具说明书（{e}）"
    except Exception as e:
        return f"错误：工具执行失败（{e}）"

def run_turn(messages):
    """一轮对话：返回最终文本。失败抛 TurnError，历史由调用方回滚"""
    global total_in, total_out, leaks
    bad = 0                                       # 本轮累计的坏回复数（泄漏/空）
    for step in range(MAX_STEPS):
        data = call_with_retry(messages)
        msg = data["choices"][0]["message"]
        u = data.get("usage", {})
        total_in  += u.get("prompt_tokens", 0)
        total_out += u.get("completion_tokens", 0)

        if msg.get("tool_calls"):
            messages.append(msg)                  # 必坑①：带 tool_calls 的 assistant 消息必须入史
            for tc in msg["tool_calls"]:          # 必坑②：每个 tool_call 都必须有对应结果，不能漏
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                 "content": run_tool(tc)})
            continue

        content = msg.get("content") or ""
        if "DSML" in content or not content.strip():
            # 解析失败泄漏 / 空回复：不入史，直接重试
            leaks += "DSML" in content
            bad += 1
            print(f"   [坏回复，丢弃重试 {bad}/{MAX_RETRIES}] {content[:40]!r}")
            if bad > MAX_RETRIES:
                raise TurnError("模型连续返回无法解析的内容")
            continue
        messages.append({"role": "assistant", "content": content})
        return content
    raise TurnError(f"超过 {MAX_STEPS} 步仍未给出最终回答")

messages = [{"role": "system", "content": SYSTEM}]
total_in = total_out = leaks = 0

print(f"已连接 {MODEL}（加固版） | exit 退出，/reset 清空记忆")
while True:
    try:
        user = input("你> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("再见。")
        break
    if not user:
        continue
    if user.lower() in ("exit", "quit"):
        break
    if user == "/reset":
        messages = [{"role": "system", "content": SYSTEM}]
        total_in = total_out = leaks = 0
        print("上下文已清空。")
        continue

    snapshot = len(messages)                      # 回滚点：本轮开始前的历史长度
    messages.append({"role": "user", "content": user})
    try:
        reply = run_turn(messages)
    except TurnError as e:
        del messages[snapshot:]                   # 整轮回滚，不留残缺的 tool_calls
        print(f"AI> (本轮失败，已回滚) {e}")
        continue
    print(f"AI> {reply}")
    print(f"   [累计 {total_in}+{total_out} tok | 历史 {len(messages)} 条 | 泄漏 {leaks} 次]")

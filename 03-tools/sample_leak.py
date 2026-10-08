"""重复采样：只看模型对"第一步"的响应属于哪一类，量化 DSML 泄漏概率
用法: python sample_leak.py [N=20] [model]
分类: tool_calls=正常调工具 | leak=DSML 泄漏 | text=纯文本(没调工具) | error=请求失败
"""
import copy, json, os, sys, time, urllib.error, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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
N     = int(sys.argv[1]) if len(sys.argv) > 1 else 20
MODEL = sys.argv[2] if len(sys.argv) > 2 else "deepseek-v4-flash-0731"
SYSTEM = "你是一个说话简洁的编程导师。需要实时信息或精确计算时必须调用工具，禁止凭记忆编造。"

TOOLS_A = [
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
TOOLS_B = copy.deepcopy(TOOLS_A)   # B：无参工具加一个可选参数
TOOLS_B[0]["function"]["parameters"] = {
    "type": "object",
    "properties": {"tz": {"type": "string", "description": "可选，时区，默认本机"}},
    "required": []}

# 组别: (tools, 额外请求参数)
GROUPS = {
    "A 原 Schema":        (TOOLS_A, {}),
    "B 可选参数 Schema":  (TOOLS_B, {}),
    "C 原 Schema+temp=0": (TOOLS_A, {"temperature": 0}),
}
PROMPTS = ["现在几点了？", "现在几点？把当前的小时数乘以 7 等于多少"]

ERRORS = Counter()

def classify(tools, extra, prompt):
    body = {"model": MODEL, "tools": tools, **extra,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": prompt}]}
    req = urllib.request.Request(
        f"{BASE}/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "authorization": f"Bearer {KEY}"})
    for attempt in range(4):                       # 限流(429/5xx)退避重试，不污染统计
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                msg = json.loads(r.read())["choices"][0]["message"]
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2 ** attempt * 2); continue
            ERRORS[f"HTTP {e.code}"] += 1; return "error"
        except Exception as e:
            if attempt < 3:
                time.sleep(2); continue
            ERRORS[type(e).__name__] += 1; return "error"
    if msg.get("tool_calls"):
        return "tool_calls"
    return "leak" if "DSML" in (msg.get("content") or "") else "text"

jobs = [(g, p) for g in GROUPS for p in PROMPTS for _ in range(N)]
with ThreadPoolExecutor(max_workers=3) as ex:
    results = list(ex.map(lambda j: classify(*GROUPS[j[0]], j[1]), jobs))

stat = {}
for (g, p), r in zip(jobs, results):
    stat.setdefault((g, p), Counter())[r] += 1

print(f"模型 {MODEL} | 每格 N={N} | 全新历史，只看第一步响应\n")
for p in PROMPTS:
    print(f"## {p}")
    for g in GROUPS:
        c = stat[(g, p)]
        print(f"  {g:<20} " + "  ".join(f"{k}={c[k]:>3}" for k in ("tool_calls", "leak", "text", "error")))
    print()
if ERRORS:
    print("错误明细（重试后仍失败）:", dict(ERRORS))

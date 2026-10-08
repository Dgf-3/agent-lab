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
MODEL = sys.argv[1] if len(sys.argv) > 1 else "minimax-m3"
SYSTEM = "你是一个说话简洁的编程导师。需要实时信息或精确计算时必须调用工具，禁止凭记忆编造。"

# ---------- 说明书：JSON Schema，模型据此决定何时点菜、怎么点 ----------
# ---------- HTTP 帮手：在工具边界把一切异常转成信息（知识点 #18）----------
def http_get_json(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"user-agent": "agent-lab/04"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return {"error": f"请求失败：{e}"}

def geocode_city(name):
    """城市名 → 经纬度。数据源：Open-Meteo Geocoding（免费无 key）"""
    data = http_get_json("https://geocoding-api.open-meteo.com/v1/search"
                         "?count=1&language=zh&name=" + urllib.parse.quote(str(name)))
    if data.get("error") or not data.get("results"):
        return {"error": f"未找到城市或查询失败：{name}"}
    r = data["results"][0]
    return {"city": r["name"], "country": r.get("country", ""),
            "latitude": r["latitude"], "longitude": r["longitude"]}

def get_weather(latitude, longitude):
    """经纬度 → 当前天气。数据源：Open-Meteo Forecast（免费无 key）"""
    data = http_get_json(f"https://api.open-meteo.com/v1/forecast"
                         f"?latitude={latitude}&longitude={longitude}"
                         "&current=temperature_2m,wind_speed_10m,weather_code&timezone=auto")
    if data.get("error") or not data.get("current"):
        return {"error": "天气查询失败"}
    c = data["current"]
    return {"temperature_c": c.get("temperature_2m"),
            "wind_kmh": c.get("wind_speed_10m"),
            "wmo_code": c.get("weather_code")}

def truncate(value, limit=600):
    """工具结果也是上下文（知识点 #17）：超长截断，防历史膨胀"""
    s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return s if len(s) <= limit else s[:limit] + f"…(已截断，原始 {len(s)} 字符)"

TOOLS = [
    {"type": "function", "function": {
        "name": "geocode_city",
        "description": "把城市名解析成经纬度。查天气前必须先调用它。",
        "parameters": {"type": "object",
            "properties": {"name": {"type": "string", "description": "城市名，如 上海"}},
            "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "按经纬度查当前天气（摄氏温度、风速、WMO 天气码）。必须先用 geocode_city 拿到坐标。",
        "parameters": {"type": "object",
            "properties": {"latitude": {"type": "number"},
                           "longitude": {"type": "number"}},
            "required": ["latitude", "longitude"]}}},
]

TOOL_IMPL = {"geocode_city": geocode_city, "get_weather": get_weather}




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

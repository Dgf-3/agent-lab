# """Diagnose whether the chat-completions API returns structured tool calls."""
# import json
# import os
# import sys
# import urllib.error
# import urllib.request
# from pathlib import Path

# env_file = Path(__file__).parent.parent / ".env"
# if env_file.exists():
#     for line in env_file.read_text(encoding="utf-8").splitlines():
#         line = line.strip()
#         if line and not line.startswith("#") and "=" in line:
#             key, value = line.split("=", 1)
#             value = value.strip()
#             if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
#                 value = value[1:-1]
#             os.environ.setdefault(key.strip(), value.strip())

# API_KEY = os.environ["INK_API_KEY"]
# BASE = "https://discovery-api.intern-ai.org.cn"
# MODEL = sys.argv[1] if len(sys.argv) > 1 else "deepseek-v4-flash-0731"
# TOOLS = [
#     {
#         "type": "function",
#         "function": {
#             "name": "get_current_time",
#             "description": (
#                 "获取当前本机日期时间。凡涉及'现在/今天/几点'的问题，"
#                 "必须先调用它。"
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {},
#                 "required": [],
#             },
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "calculator",
#             "description": (
#                 "精确计算四则运算表达式，支持 + - * / ( ) 和小数。"
#                 "多位数运算必须调用它，不要心算。"
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "expression": {
#                         "type": "string",
#                         "description": "如 '128*39+7'",
#                     }
#                 },
#                 "required": ["expression"],
#             },
#         },
#     },
# ]
# MESSAGES = [
#     {
#         "role": "system",
#         "content": (
#             "你是一个说话简洁的编程导师。需要实时信息或精确计算时"
#             "必须调用工具，禁止凭记忆编造。"
#         ),
#     },
#     {"role": "user", "content": "现在几点了？"},
# ]


# def run_probe(label, tool_choice=None):
#     body = {"model": MODEL, "messages": MESSAGES, "tools": TOOLS}
#     if tool_choice is not None:
#         body["tool_choice"] = tool_choice

#     request = urllib.request.Request(
#         f"{BASE}/v1/chat/completions",
#         data=json.dumps(body).encode(),
#         headers={
#             "content-type": "application/json",
#             "authorization": f"Bearer {API_KEY}",
#         },
#     )

#     print(f"\n=== {label} ===")
#     print(f"请求 model: {MODEL}")
#     try:
#         with urllib.request.urlopen(request, timeout=60) as response:
#             data = json.loads(response.read())
#     except urllib.error.HTTPError as error:
#         print(f"HTTP {error.code}: {error.read().decode(errors='replace')[:1000]}")
#         return

#     print(f"响应 model: {data.get('model', '<missing>')}")
#     choices = data.get("choices") or []
#     if not choices:
#         print("响应没有 choices；完整响应：")
#         print(json.dumps(data, ensure_ascii=False, indent=2))
#         return

#     choice = choices[0]
#     message = choice.get("message") or {}
#     print(f"finish_reason: {choice.get('finish_reason')}")
#     print("message.tool_calls:")
#     print(json.dumps(message.get("tool_calls"), ensure_ascii=False, indent=2))
#     print("message.content:")
#     print(message.get("content"))


# if __name__ == "__main__":
#     run_probe("自动选择工具（复现 tools.py 的请求）")
#     run_probe(
#         "强制调用 get_current_time（检查结构化工具调用支持）",
#         {"type": "function", "function": {"name": "get_current_time"}},
#     )
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["INK_API_KEY"],  # 密钥放 .env，别硬编码``
    base_url="https://discovery-api.intern-ai.org.cn/v1",
)

response = client.chat.completions.create(
    model="glm-5.3",  # 以控制台模型列表为准
    messages=[
        {"role": "user", "content": "你好，请用一句话介绍你自己。"}
    ],
    stream=False,
)

# print(response.choices[0].message.content)
print(response)
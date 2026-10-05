import os
from openai import OpenAI

client = OpenAI(
    api_key = os.getenv("ZHIPU_API_KEY"), # 从环境变量读取密钥
    base_url="https://open.bigmodel.cn/api/paas/v4"
)

resp = client.chat.completions.create(
    model="glm-4.7-flash",   # 免费模型名
    messages=[{"role": "user", "content": "用一句话解释什么是 API"}]
)
print(resp.choices[0].message.content)

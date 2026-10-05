# agent-lab

从零搭建的 agent 开发练习场。原则：每个练习必须**能跑**、**有产出物**、**留下知识点**。

## 01 · hello-model

不借助任何框架和 SDK，用 Python 标准库直接调用大模型 API——先看见裸协议，再谈封装。

| 文件 | 方言 | 平台 | 端点 |
|---|---|---|---|
| `hello_model_anthropic.py` | Anthropic Messages | discovery | `/v1/messages` |
| `hello_model_openai.py` | OpenAI Chat Completions | discovery（deepseek-v4-flash） | `/v1/chat/completions` |

### 运行

```bash
# 1. 复制模板填入密钥（.env 已被 .gitignore 排除，永不提交）
cp .env.example .env

# 2. 跑
python hello_model.py
```

### 本单元知识点

**#1 twelve-factor 配置原则** —— 配置是环境的一部分，不是代码的一部分。密钥永不硬编码；同一份代码换环境只换配置；`.env` 只存在于本机，仓库里只提交 `.env.example` 模板。

**#2 API 方言** —— 业界两套主流协议：Anthropic Messages 与 OpenAI Chat Completions。端点路径、认证头、响应结构（`content[0].text` vs `choices[0].message.content`）全部不同。接新平台的第一步永远是"验方言"。

**#3 环境变量三层模型** —— 会话级（`$env:`，关窗即失效）/ 持久级（`setx` 或系统 GUI，只对之后新启动的进程生效，重开 VS Code 即可、无需重启电脑）/ 文件级（`.env` + loader，随项目走）。读取端统一用 `os.getenv()`，代码不关心值存哪层。

**#4 .env 的事实标准** —— 它没有正式标准，只有约定：裸值（不带引号，所有解析器的最大公约数）、`#` 注释、永不进 git。手写 loader 时注意剥离成对引号，或直接用 python-dotenv。

**#5 Bearer 认证** —— `Authorization: Bearer <token>` 里的 Bearer 意为**不记名持有人**，一个从金融界借来的词（如不记名债券：谁持有票据，谁就是所有权人，票据不记名、可转让）。映射到 API 语境：**谁持有 token，谁就被授权**——服务端不看你是谁、从哪台机器发起，只验票。这解释了本单元全部安全纪律的底层原因：token 写进代码、提交进 git、贴进聊天窗口，等于把"债券"原件拍在公开场合——**泄露即授权，无需证明身份**。所以密钥只活在 `.env` 和环境变量里。

### 排障记录

- `KeyError: 'INK_API_KEY'` → `.env` 未创建，或 `setx` 后未重开终端/VS Code（注册表只对新进程生效）。
- key 值带引号 → 手写 loader 的 `split("=", 1)` 不剥引号，引号被当作值的一部分；repr 调试法（`f"{KEY[:10]!r}"`）让引号现形定位。
- 404 → 方言不对或平台路径带前缀，以平台文档的 Python 示例为准。

### 下一步

02：把单轮调用改成 messages 数组循环——多轮对话与上下文累积。

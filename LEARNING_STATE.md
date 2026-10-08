# LEARNING_STATE（新对话开场先读我）
## 我是谁
agent 开发学习者，编程基础弱但提问能力强，学习靠发散提问 + 实验验证。
## 环境
Win10 + pwsh 7.6.6 + VS Code（集成终端）；Python 3.11；git 已配 Dgf-3。
密钥走 .env（INK_API_KEY），discovery 平台 OpenAI 方言，BASE 见 .env。
## 教学约定
每单元：可运行代码 + 编号知识点卡片 + 至少 3 个实验 + 排障速查表 + README 章节 + git push。
指导视角默认 VS Code GUI；代码注释用中文；给最简可跑版本，深度概念放知识点卡片。
## 已完成
01 裸调 API（双方言对照）；02 多轮对话（statelessness/上下文成本/注入探测）。
知识点索引：#1 twelve-factor #2 API方言 #3 环境变量三层 #4 .env标准 #5 Bearer
#6 init/push分工 #7 amend边界 #8 无状态 #9 上下文即成本 #10 指令持久性
## 进行中
03 tools（function calling / agent loop / 信任边界），代码未跑通。
## 卡点与观察
长对话后期回答细致度下降 → 已用本文件 + 新窗口解决。

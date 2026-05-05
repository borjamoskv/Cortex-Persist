# 课程 · AI 代理中的持久记忆

## 目标

把持久记忆理解为一个架构子系统，而不是缓存、对话历史或向量检索技巧。

## 仓库锚点

- [Quickstart](../../quickstart.md)
- Memory internals: `architecture/CORTEX_MEMORY_INTERNALS.md`
- [LangChain 教程](../../tutorials/langchain.md)
- MCP server: `cortex/mcp/server.py`
- 基础记忆示例: `examples/quickstart/basic_memory.py`

## 你将学到

- 存储、检索与可验证记忆之间的区别。
- 为什么记忆质量取决于信任语义，而不只是 recall。
- 如何把持久记忆接入代理框架。
- 当传输、检索与信任边界混在一起时，系统如何漂移。

## 实验

- 比较“会话历史”和“持久记忆”。
- 定义三种必须跨会话保留的事实。
- 基于本仓库设计一个冷启动记忆引导流程。

## 结课标准

你能够把持久记忆描述为具有写入、读取、信任与导出路径的受治理系统。

# 课程 · AI 代理群体协作

## 目标

理解 swarm 如何从“并行很多代理”的想法，变成一个受治理的系统。

## 仓库锚点

- [Swarm 路由](../../../cortex/routes/swarm.py)
- [Supervisor agent](../../../cortex/agents/builtins/supervisor_agent.py)
- [Aether daemon](../../../cortex/extensions/aether/daemon.py)
- [共识教程](../../tutorials/consensus.md)
- [Swarm dashboard](../../../scripts/swarm_dashboard.py)

## 你将学到

- 编排、监督、共识三者的区别。
- 为什么 swarm 需要显式控制面。
- worktree、生命周期操作与投票如何连接在一起。
- swarm 系统如何滑向安全债务和维护债务。

## 实验

- 画出代理运行时与运维暴露面的边界。
- 列出没有共享验证层时的三个典型失败模式。
- 提出一个减少 swarm 表面分叉的收敛 helper。

## 结课标准

你能够把 swarm 解释为具有可见性、生命周期与信任边界的架构系统。

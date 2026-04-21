# 课程 · LLM 与 AI 代理优化

## 目标

把“优化”理解为系统工程问题：复杂度上限、质量闸门、熵控制与运维反馈。

## 仓库锚点

- [Entropy gate](../../../scripts/entropy_gate.py)
- [Ship gate](../../../scripts/ship_gate.py)
- [Swarm dashboard](../../../scripts/swarm_dashboard.py)
- [会话护栏](../../../cortex/memory/guardrails.py)
- [Supervisor tests](../../../tests/agents/test_builtin_agents.py)

## 你将学到

- 为什么优化不只是降低延迟或成本。
- 复杂度、lint、测试和 gate 如何共同塑造代理质量。
- 如何区分“更快”与“更适合发布”。
- 为什么缺乏可观测护栏的优化会侵蚀信任。

## 实验

- 写一段短文：benchmark 与 ship gate 的区别是什么？
- 找出一种降低成本但提升信任风险的优化。
- 为本仓库设计一个最小优化评分卡。

## 结课标准

你能够用工程证据而不是模型宣传来论证一次优化。

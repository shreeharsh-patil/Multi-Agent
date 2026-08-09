"""Agentic — executive multi-agent operating system.

A Boss Agent coordinates 100 specialized worker agents through dynamic task
planning, capability-based selection, graph execution (parallel + sequential),
agent-to-agent handoffs, shared task memory, tool routing, result validation,
retry/recovery, automatic replanning and final synthesis.

This module layers on top of the existing Agentic platform without replacing
its operational agents (Knowledge, Research, Coding, Drive, Calendar, ...).
"""
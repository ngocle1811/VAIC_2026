# Agent Implementation

`AgentOrchestrator` uses an injected `LLMClient` and `ToolRegistry`. It records tool history and
enforces maximum steps, repeated-call protection, argument validation, and a tool-error limit.

Production orchestration remains disabled by default. Fake providers and tools are used for
offline tests. Official operational data cannot be replaced after it enters Agent state. RAG
source IDs are validated against retrieved context before final output.

The deterministic decision rules are capability hints only; they do not encode official business
rules. Real FPT Llama execution remains opt-in and unverified until credentials and an explicit
external smoke-test flag are present.

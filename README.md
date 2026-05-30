# Cairn 🪨

**A free AGPLv3 coordination layer that lets multiple AI agents work together without burning the token budget — by coordinating through a passive shared blackboard and minimal per-agent context, instead of conversation.**

> A *cairn* is a pile of stones travellers stack to mark a path for those behind — guidance left without speaking. That is Cairn's mechanism: agents leave traces, not messages.

---

## The problem

Multi-agent AI systems fail in production mostly on **cost**: agents talk to each other in unbounded loops, each carrying the others' full transcripts, until the context — and the bill — explodes. The dominant tooling is **reactive** (budget caps, circuit-breakers, observability dashboards): it watches the meter and pulls the plug after the fact. It does not change the architecture that generates the spend.

**Cairn is preventive** — it removes the structure that causes the explosion.

## Three mechanisms (each measured in real operation)

1. **Minimal-context workers** — each agent loads only a small task-scoped context, not the full project history. Measured: system-prompt/always-loaded context drops ~32K → ~0.8K tokens per agent-turn.
2. **Passive stigmergic blackboard** — agents leave short traces (claims, findings, status) in one small shared file and read each other's traces. **No agent-to-agent conversation channel.** Coordination emerges from a shared filter, not chatter.
3. **Gardener orchestrator** — a single supervisor that distills emergent findings and intervenes only on pathology (a dead-end chase, a budget ceiling), never micro-manages.

## Measured result (dogfooded, controlled A/B)

On an identical agent task — same model, only the context architecture changed:

| | naive full-context | minimal + blackboard | reduction |
|---|---:|---:|---:|
| billable input tokens | 488,477 | 222,680 | **54%** |
| short-run cost (illustrative) | $4.13 | $1.44 | **65%** |

The throughput / rate-limit win persists even where prompt caching shrinks the dollar delta. The benchmark harness is published so the number is **reproducible — and falsifiable** — on your own workload.

Emergent coordination — one agent binding to another's finding and converging to a verdict — was observed **with no conversation channel**, purely through the passive blackboard.

---

## Status

**Skeleton repository.** Cairn is being extracted as a reusable library from the originating operator's own multi-agent swarm. Full v1 code lands when funding (NGI Zero Commons or alternative) is secured. This repo currently carries the design, the measured benchmark, and the public commitment.

- Framework-agnostic — designed to coordinate agents built on LangGraph / CrewAI / a plain script.
- Composes with cost tooling (LiteLLM, Langfuse) — Cairn lowers the baseline they cap/observe.
- Sibling of [Echo Toolkit](https://github.com/echo-toolkit/echo) — same operator, same commons philosophy, independent projects.

## License

[AGPLv3](LICENSE). The network-use clause ensures hosted use contributes back. Commercial relicensing available for B2B integrations that cannot accept AGPL — revenue reinvested in maintenance.

## Origin

Built by [Tağmaç Çankaya](https://khashif.run) (Lefkoşa, Cyprus / EU) out of a felt failure: a full-context headless agent swarm that exhausted its budget almost instantly. Cairn is the rebuild — measured, minimal, and given back.

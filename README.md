# Cairn 🪨

**A coordination layer for multi-agent AI systems — so your agents stop silently overwriting each other.** Agents converge on a passive, **append-only shared blackboard** (they leave traces; they never overwrite shared state), so multi-agent work stays **auditable and debuggable**, self-terminates instead of looping, and carries minimal per-agent context (≈ half the tokens). Optionally, that coordination is **verifiable on-chain**.

> A *cairn* is a pile of stones travellers stack to mark a path for those behind — guidance left without speaking. That is Cairn's mechanism: agents leave traces, not messages.

---

## The problem

Multi-agent systems fail in production in three compounding ways — and the worst one is silent:

1. **Coordination corruption (the silent one).** When N agents write to shared state, last-write-wins quietly overwrites work; when something breaks you can't tell which agent, which step, or which stale value caused it. Teams keep hand-rolling an "append-only event log" to claw auditability back.
2. **Unbounded chatter / loops.** Agents sharing a conversation thread race to add the last word and don't know when to stop.
3. **Cost blow-up.** Each agent replays the full transcript; context — and the bill — explodes.

The dominant tooling is **reactive** (budget caps, circuit-breakers, dashboards) — it watches the meter after the fact. **Cairn is preventive:** it removes the structure that causes all three. Agents coordinate through a passive **append-only blackboard** with minimal per-agent context, not a shared conversation — so nothing is overwritten (every contribution is a durable, auditable trace), there is no thread to race in, and each agent carries a bounded view, not the whole transcript.

## Three mechanisms (each measured in real operation)

1. **Minimal-context workers** — each agent loads only a small task-scoped context, not the full project history. Measured: always-loaded context drops ~32K → ~0.8K tokens per agent-turn.
2. **Passive stigmergic blackboard** — agents leave short traces (claims, findings, status) in one small shared file and read each other's traces. **No agent-to-agent conversation channel.** Coordination emerges from a shared filter, not chatter.
3. **Gardener orchestrator** — a single supervisor that distills emergent findings and times the close (a resonance valve), intervening only on pathology, never micro-managing.

## Proof of mechanism (measured, controlled A/B)

The token cut isn't the pitch — it's the *evidence* the structure works. On an identical agent task — same model, only the context architecture changed:

| | naive full-context | minimal + blackboard | reduction |
|---|---:|---:|---:|
| billable input tokens | 488,477 | 222,680 | **54%** |
| short-run cost (illustrative) | $4.13 | $1.44 | **65%** |

The throughput / rate-limit win persists even where prompt caching shrinks the dollar delta. The benchmark harness is published so the number is **reproducible — and falsifiable** — on your own workload.

## Quickstart

```bash
pip install cairn-coordination          # core — stdlib-only, zero deps   (import name: cairn)
pip install "cairn-coordination[web3]"   # + the on-chain layer (ERC-8004 identity + receipts)
```
On [PyPI](https://pypi.org/project/cairn-coordination/) (the import name is `cairn`; `cairn` was taken).

Framework-agnostic: you supply `agent_fn(ctx)` and make your own model call inside it. Cairn calls no LLM.

```python
from cairn import run_swarm, Worker, Trace

def agent_fn(ctx):
    # ctx.task = this agent's scope; ctx.board = a compact digest of others' traces (minimal!)
    # call your model, return a Trace — or return None to go idle (self-terminate)
    return Trace(agent=ctx.agent, kind="finding", text="...", value=2.0)

result = run_swarm(agent_fn, [Worker("a", "angle A"), Worker("b", "angle B")])
print(result.closed_reason, result.total_value())
```

`python examples/selftest.py` runs an offline, dependency-free demo of the whole loop.

### Already on LangChain / CrewAI?

Coordinate your existing framework agents through Cairn's blackboard — minimal per-agent context instead of re-passing the full transcript:

```python
from cairn import run_swarm, Worker
from cairn.adapters import from_langchain   # or: from_crewai, or as_worker_fn for any invoke()

run_swarm(from_langchain(my_chat_model_or_graph),
          [Worker("a", "angle A"), Worker("b", "angle B")])
```

`as_worker_fn(invoke)` wraps *any* `invoke(prompt) -> str` callable. The adapters import no framework until a wrapped agent runs (`pip install "cairn-coordination[langchain]"` / `[crewai]`). Offline demo: `python examples/adapter_demo.py`.

---

## Verifiable coordination (optional web3 layer)

Token-efficiency commoditizes; **verifiability** does not. When agents owned by *different parties* coordinate, they need on-chain **identity**, **receipts**, and (optionally) **value rails**. Cairn adds these as an **additive, off-by-default layer** — `import cairn` stays dependency-free, and with no adapter the core runs exactly as before.

```python
from cairn import run_swarm, Worker
from cairn.web3.celo import CeloEVMAdapter

chain = CeloEVMAdapter(private_key=KEY, receipts_addr=RECEIPTS)
run_swarm(agent_fn, workers, receipt=chain)   # emits one verifiable on-chain receipt per run
```

- **Receipts** — one verifiable on-chain record per coordination run (run id + state hash).
- **Identity** — each agent gets a verifiable identity via the pre-deployed **[ERC-8004](https://eips.ethereum.org/EIPS/eip-8004)** registries (identity is config, not a deploy).
- **Payment** — optional native-CELO / ERC-20 (cUSD, USDC) transfers between agents.

**Live on Celo mainnet** (independently verifiable):

| Capability | Proof |
|---|---|
| Coordination receipt | [tx `0xeea84ea9…`](https://celoscan.io/tx/0xeea84ea902a1c6a26ca484a4b53d22e951d976cb2299fccd284688e890a9deec) |
| Agent identity (ERC-8004) | [agentId 9211](https://celoscan.io/token/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432?a=9211) |

The chain layer is chain-agnostic by design (a clean adapter interface); Celo/EVM is the first implementation.

---

## Status

The core library (blackboard + minimal-context workers + gardener/valve) and the verifiable-coordination layer are **here and working** — receipts + identity proven on Celo mainnet, payment on testnet. Funding (NGI Zero Commons / alternatives) is in progress to sustain maintenance.

- Framework-agnostic — coordinates agents built on LangGraph / CrewAI / a plain script.
- Composes with cost tooling (LiteLLM, Langfuse) — Cairn lowers the baseline they cap/observe.
- Sibling of [Echo Toolkit](https://github.com/echo-toolkit/echo) — same operator, same commons philosophy, independent projects.

## License

[AGPLv3](LICENSE). The network-use clause ensures hosted use contributes back. Commercial relicensing available for B2B integrations that cannot accept AGPL — revenue reinvested in maintenance.

## Origin

Built by [Tağmaç Çankaya](https://khashif.run) (Lefkoşa, Cyprus / EU) out of a felt failure: a full-context headless agent swarm that exhausted its budget almost instantly. Cairn is the rebuild — measured, minimal, and given back.

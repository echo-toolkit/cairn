#!/usr/bin/env python3
"""Measure the 2 DISPATCH #006 worker sessions (real token usage for the live valve A/B)."""
import json, glob, os

PROJ = os.path.expanduser("~/.claude/projects/-mnt-c-Users-HP-Dev--swarm")
allf = sorted(glob.glob(PROJ + "/*.jsonl"), key=os.path.getmtime)
print(f"total jsonl in project: {len(allf)}")
files = allf[-2:]

G = dict(inp=0, cc=0, cr=0, out=0, turns=0)
for f in files:
    s = dict(inp=0, cc=0, cr=0, out=0, turns=0)
    for line in open(f, encoding="utf-8", errors="ignore"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        u = (o.get("message") or {}).get("usage") or o.get("usage")
        if not u:
            continue
        s["inp"] += u.get("input_tokens", 0)
        s["cc"] += u.get("cache_creation_input_tokens", 0)
        s["cr"] += u.get("cache_read_input_tokens", 0)
        s["out"] += u.get("output_tokens", 0)
        s["turns"] += 1
    for k in G:
        G[k] += s[k]
    name = os.path.basename(f)[:12]
    print(f"{name} turns={s['turns']} fresh={s['inp']} cc={s['cc']} cr={s['cr']} out={s['out']}")

bi = G["inp"] + G["cc"] + G["cr"]
print(f"\nTOTAL turns={G['turns']}  billable_input={bi:,}  output={G['out']:,}")
if G["turns"]:
    print(f"avg billable input/turn = {bi // G['turns']:,}")
    print(f"avg cache_read/turn = {G['cr'] // G['turns']:,}")

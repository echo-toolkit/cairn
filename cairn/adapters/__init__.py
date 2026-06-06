# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — framework adapters (optional).  © 2026 Tağmaç Çankaya
"""Bridges that let you coordinate agents from other frameworks through Cairn's blackboard.

    from cairn.adapters import from_langchain, from_crewai, as_worker_fn

`as_worker_fn` is the framework-agnostic glue (wrap any `invoke(prompt)->str`); the rest are thin
shims. Importing this module pulls in NO framework — the framework is imported lazily, only when a
wrapped agent actually runs. See `cairn.adapters.base`.
"""
from .base import as_worker_fn, default_build_prompt, default_parse
from .langchain import from_langchain
from .crewai import from_crewai

__all__ = ["as_worker_fn", "default_build_prompt", "default_parse", "from_langchain", "from_crewai"]

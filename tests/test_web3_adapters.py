# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the (additive, default-off) web3 adapter layer — no chain, no web3.py needed."""
from cairn import Receipt, NullAdapter


def test_receipt_ok_property():
    assert Receipt().ok is False
    assert Receipt(tx_hash="0xabc", chain_id=42220, block=1).ok is True


def test_nulladapter_is_fully_noop():
    n = NullAdapter()
    assert n.register_agent("ipfs://x") == "null:0"
    assert n.resolve("1") == {}
    assert n.agent_address("1") is None
    assert n.record_run(b"r", b"s", 2).ok is False
    assert n.verify(b"r") is False
    assert n.pay("0x0000000000000000000000000000000000000000", 1).ok is False
    assert n.balance("0x0000000000000000000000000000000000000000") == 0


def test_celo_module_constants_importable_without_web3():
    # importing the module must not require web3.py (it's lazy-imported inside methods)
    from cairn.web3 import celo
    assert celo.CELO_MAINNET_CHAIN_ID == 42220
    assert celo.CELO_SEPOLIA_CHAIN_ID == 11142220
    assert celo.ERC8004_IDENTITY[42220].startswith("0x8004")
    assert celo.ERC8004_IDENTITY[11142220].startswith("0x8004")
    assert "cUSD" in celo.CELO_STABLES

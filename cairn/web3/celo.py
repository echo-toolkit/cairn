# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — Celo/EVM concrete web3 adapter.  © 2026 Tağmaç Çankaya
"""Celo (EVM) implementation of the Cairn web3 adapters.

⚠️ EXPERIMENTAL — written against verified docs/addresses (June 2026) but NOT yet run against
mainnet (needs the operator's funded key). Develop + test on Celo Sepolia first; mainnet only for
the grant's 'verifiable usage' proof. See `Dev/Cairn/web3-agent-economy.md`.

web3.py is imported LAZILY inside methods, so importing this module never forces the dependency;
`import cairn` stays dependency-free. Install only when you actually use a chain:
    pip install "web3>=7,<8"

Verified ERC-8004 singleton registries (triple-confirmed: docs.celo.org/build-on-celo/build-with-ai/8004
+ github.com/erc-8004/erc-8004-contracts + awesome-erc8004; 0x8004… vanity prefix, audited):
    Celo mainnet (42220)        Identity 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
                                Reputation 0x8004BAa17C55a88189AE136b182e5fdA19dE9b63
    Celo Sepolia (11142220)     Identity 0x8004A818BFB912233c491871b3d84c89A494BD9e
                                Reputation 0x8004B663056A597Dffe9eCcC1965A193B7388713
NOTE: Validation Registry has NO published Celo address — do not hardcode one.
Self Protocol `SelfAgentRegistry` is single-source — verify on-chain before any mainnet spend.
"""
from __future__ import annotations
from typing import Optional

from .adapters import IdentityAdapter, ReceiptAdapter, PaymentAdapter, Receipt

# --- verified network constants -------------------------------------------------------------
CELO_MAINNET_RPC = "https://forno.celo.org"
CELO_SEPOLIA_RPC = "https://forno.celo-sepolia.celo-testnet.org"
CELO_MAINNET_CHAIN_ID = 42220
CELO_SEPOLIA_CHAIN_ID = 11142220

ERC8004_IDENTITY = {
    CELO_MAINNET_CHAIN_ID: "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
    CELO_SEPOLIA_CHAIN_ID: "0x8004A818BFB912233c491871b3d84c89A494BD9e",
}

# Common Celo stablecoins (mainnet) for ERC-20 payment rails — optional `token=` to pay().
CELO_STABLES = {
    "cUSD": "0x765DE816845861e75A25fCA122bb6898B8B1282a",
    "USDC": "0xcebA9300f2b948710d2653dD7B07f33A8B32118C",
}

# Minimal ERC-20 ABI (transfer + balanceOf) for the optional PaymentAdapter token path.
_ERC20_ABI = [
    {"type": "function", "name": "transfer", "stateMutability": "nonpayable",
     "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"type": "function", "name": "balanceOf", "stateMutability": "view",
     "inputs": [{"name": "owner", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
]

# Minimal ABIs (only the methods/events we use; fetch full ABI from the canonical repo for more).
_RECEIPTS_ABI = [
    {"type": "function", "name": "recordRun", "stateMutability": "nonpayable",
     "inputs": [{"name": "runId", "type": "bytes32"}, {"name": "stateHash", "type": "bytes32"},
                {"name": "agentCount", "type": "uint256"}, {"name": "metaURI", "type": "string"}],
     "outputs": []},
    {"type": "event", "name": "Coordination", "anonymous": False,
     "inputs": [{"name": "emitter", "type": "address", "indexed": True},
                {"name": "runId", "type": "bytes32", "indexed": True},
                {"name": "stateHash", "type": "bytes32", "indexed": False},
                {"name": "agentCount", "type": "uint256", "indexed": False},
                {"name": "metaURI", "type": "string", "indexed": False}]},
]
# Real signatures from the verified ERC-8004 IdentityRegistry implementation on Celo Sepolia
# (proxy 0x8004A818… → impl 0x7274e874…; ABI via Blockscout). The authoritative agentId comes from
# the Registered event (agentId indexed), NOT a stray Transfer. It is also an ERC-721 (ownerOf/tokenURI).
_IDENTITY_ABI = [
    {"type": "function", "name": "register", "stateMutability": "nonpayable",
     "inputs": [{"name": "agentURI", "type": "string"}],
     "outputs": [{"name": "agentId", "type": "uint256"}]},
    {"type": "function", "name": "ownerOf", "stateMutability": "view",
     "inputs": [{"name": "tokenId", "type": "uint256"}], "outputs": [{"name": "", "type": "address"}]},
    {"type": "function", "name": "tokenURI", "stateMutability": "view",
     "inputs": [{"name": "tokenId", "type": "uint256"}], "outputs": [{"name": "", "type": "string"}]},
    {"type": "function", "name": "getAgentWallet", "stateMutability": "view",
     "inputs": [{"name": "agentId", "type": "uint256"}], "outputs": [{"name": "", "type": "address"}]},
    {"type": "event", "name": "Registered", "anonymous": False,
     "inputs": [{"name": "agentId", "type": "uint256", "indexed": True},
                {"name": "agentURI", "type": "string", "indexed": False},
                {"name": "owner", "type": "address", "indexed": True}]},
]


class CeloEVMAdapter(IdentityAdapter, ReceiptAdapter, PaymentAdapter):
    """Receipts + ERC-8004 identity + agent-to-agent payment rails on Celo.

    Args:
        private_key:  the agent/operator EOA key (NEVER in chat/commit/log — load from secrets).
        receipts_addr: deployed CoordinationReceipts contract address (deploy it first; until then
                       record_run raises a clear error).
        testnet:      True → Celo Sepolia (free faucet, disposable key) for development.
        identity_addr: ERC-8004 Identity Registry; defaults to the verified singleton per network.
        rpc:          override RPC endpoint.
    """
    def __init__(self, private_key: str, receipts_addr: Optional[str] = None, *,
                 testnet: bool = True, identity_addr: Optional[str] = None,
                 rpc: Optional[str] = None):
        try:
            from web3 import Web3
            from eth_account import Account
        except ImportError as e:  # pragma: no cover
            raise ImportError('CeloEVMAdapter needs web3.py — `pip install "web3>=7,<8"`') from e
        self.chain_id = CELO_SEPOLIA_CHAIN_ID if testnet else CELO_MAINNET_CHAIN_ID
        self.w3 = Web3(Web3.HTTPProvider(rpc or (CELO_SEPOLIA_RPC if testnet else CELO_MAINNET_RPC)))
        self.acct = Account.from_key(private_key)
        self.receipts_addr = receipts_addr
        self.identity_addr = identity_addr or ERC8004_IDENTITY[self.chain_id]
        self._Web3 = Web3

    # --- internal: build, sign, send, wait -----------------------------------------------
    def _send_raw(self, fn):
        """Send a contract call; return (Receipt, raw tx receipt) so callers can parse events."""
        tx = fn.build_transaction({
            "from": self.acct.address,
            # "pending" includes in-flight txs and tolerates lagging load-balanced public RPC nodes
            "nonce": self.w3.eth.get_transaction_count(self.acct.address, "pending"),
            "chainId": self.chain_id,
        })
        signed = self.acct.sign_transaction(tx)
        h = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        rcpt = self.w3.eth.wait_for_transaction_receipt(h)
        return Receipt(tx_hash=h.hex(), chain_id=self.chain_id, block=rcpt.blockNumber), rcpt

    def _send(self, fn) -> Receipt:
        return self._send_raw(fn)[0]

    def _identity(self):
        return self.w3.eth.contract(
            address=self._Web3.to_checksum_address(self.identity_addr), abi=_IDENTITY_ABI)

    # --- ReceiptAdapter ------------------------------------------------------------------
    def record_run(self, run_id: bytes, state_hash: bytes,
                   agent_count: int, meta_uri: str = "") -> Receipt:
        if not self.receipts_addr:
            raise RuntimeError("receipts_addr not set — deploy CoordinationReceipts.sol first "
                               "(see Dev/Cairn/web3-agent-economy.md).")
        c = self.w3.eth.contract(address=self._Web3.to_checksum_address(self.receipts_addr),
                                 abi=_RECEIPTS_ABI)
        return self._send(c.functions.recordRun(
            run_id[:32].ljust(32, b"\0"), state_hash[:32].ljust(32, b"\0"),
            int(agent_count), meta_uri))

    def verify(self, run_id: bytes) -> bool:
        if not self.receipts_addr:
            return False
        c = self.w3.eth.contract(address=self._Web3.to_checksum_address(self.receipts_addr),
                                 abi=_RECEIPTS_ABI)
        topic = run_id[:32].ljust(32, b"\0")
        logs = c.events.Coordination().get_logs(
            from_block=0, argument_filters={"runId": topic})
        return len(logs) > 0

    # --- IdentityAdapter -----------------------------------------------------------------
    def register_agent(self, registration_uri: str) -> str:
        """Register an agent on the ERC-8004 Identity Registry. Returns the agentId, read from the
        authoritative `Registered(agentId, agentURI, owner)` event emitted by the registry."""
        from web3.logs import DISCARD
        c = self._identity()
        _, rcpt = self._send_raw(c.functions.register(registration_uri))
        for e in c.events.Registered().process_receipt(rcpt, errors=DISCARD):
            if e["address"].lower() == self.identity_addr.lower():
                return str(e["args"]["agentId"])
        return "0"

    def resolve(self, agent_id: str) -> dict:
        """Return {agentId, agentURI} read on-chain (fetching the JSON itself is the caller's job).
        Retries: a read immediately after the register write can hit a lagging load-balanced RPC
        node (token 'not yet seen') — same family as the nonce-pending issue."""
        uri = self._read_retry(lambda: self._identity().functions.tokenURI(int(agent_id)).call())
        return {"agentId": str(agent_id), "agentURI": uri}

    def agent_address(self, agent_id: str) -> Optional[str]:
        """The owner of the agent (ERC-721 ownerOf = the registrant). NOTE: getAgentWallet is a
        SEPARATE optional 'operational wallet' that is zero until explicitly set — ownerOf is the
        definitive ownership check."""
        return self._read_retry(lambda: self._identity().functions.ownerOf(int(agent_id)).call())

    # --- PaymentAdapter ------------------------------------------------------------------
    def pay(self, to_agent: str, amount: int, token: Optional[str] = None) -> Receipt:
        """Pay another agent: native CELO (token=None) or an ERC-20 (token=address or 'cUSD'/'USDC').
        `to_agent` is the recipient address; `amount` is in the smallest unit (wei / token decimals)."""
        to = self._Web3.to_checksum_address(to_agent)
        if token is None:                                  # native CELO transfer
            tx = {"to": to, "value": int(amount),
                  "nonce": self.w3.eth.get_transaction_count(self.acct.address, "pending"),
                  "chainId": self.chain_id, "gas": 21000, "gasPrice": self.w3.eth.gas_price}
            signed = self.acct.sign_transaction(tx)
            h = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            rcpt = self.w3.eth.wait_for_transaction_receipt(h)
            return Receipt(tx_hash=h.hex(), chain_id=self.chain_id, block=rcpt.blockNumber)
        erc20 = self.w3.eth.contract(address=self._token_addr(token), abi=_ERC20_ABI)
        return self._send(erc20.functions.transfer(to, int(amount)))

    def balance(self, agent_or_addr: str, token: Optional[str] = None) -> int:
        addr = self._Web3.to_checksum_address(agent_or_addr)
        if token is None:
            return self._read_retry(lambda: self.w3.eth.get_balance(addr))
        erc20 = self.w3.eth.contract(address=self._token_addr(token), abi=_ERC20_ABI)
        return self._read_retry(lambda: erc20.functions.balanceOf(addr).call())

    def _token_addr(self, token: str) -> str:
        return self._Web3.to_checksum_address(CELO_STABLES.get(token, token))

    @staticmethod
    def _read_retry(fn, tries: int = 6, delay: float = 2.0):
        import time
        last = None
        for _ in range(tries):
            try:
                return fn()
            except Exception as e:   # transient: public-RPC read-after-write lag (load-balanced nodes)
                last = e
                time.sleep(delay)
        raise last

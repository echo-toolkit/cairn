#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
WHAT: Local EVM (eth-tester) end-to-end proof of the on-chain receipt path — no network, no funds.
WHY:  Prove the Solidity contract + ABI + record/verify flow works BEFORE spending any testnet gas
      (test local -> testnet -> mainnet). Run: python examples/celo_local_test.py
LINK: contracts/CoordinationReceipts.sol, cairn/web3/celo.py, scripts/build_contract.py.
"""
import sys, pathlib, hashlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from web3 import Web3
from scripts.build_contract import build


def main():
    abi, bytecode = build()
    w3 = Web3(Web3.EthereumTesterProvider())          # in-memory EVM, accounts pre-funded
    acct = w3.eth.accounts[0]

    # deploy
    C = w3.eth.contract(abi=abi, bytecode=bytecode)
    rcpt = w3.eth.wait_for_transaction_receipt(C.constructor().transact({"from": acct}))
    receipts = w3.eth.contract(address=rcpt.contractAddress, abi=abi)

    # recordRun (same shape cairn.web3.celo.CeloEVMAdapter.record_run uses)
    run_id = hashlib.sha256(b"run-1").digest()
    state_hash = hashlib.sha256(b"final-board").digest()
    r2 = w3.eth.wait_for_transaction_receipt(
        receipts.functions.recordRun(run_id, state_hash, 3, "ipfs://meta").transact({"from": acct}))

    evs = receipts.events.Coordination().process_receipt(r2)
    assert len(evs) == 1, "expected exactly one Coordination event"
    a = evs[0]["args"]
    assert a["runId"] == run_id, "runId mismatch"
    assert a["stateHash"] == state_hash, "stateHash mismatch"
    assert a["agentCount"] == 3 and a["metaURI"] == "ipfs://meta", "payload mismatch"

    # verify() equivalent: query logs by indexed runId
    logs = receipts.events.Coordination().get_logs(
        from_block=0, argument_filters={"runId": run_id})
    assert len(logs) == 1, "log query by runId must find exactly one"

    print("OK  local EVM end-to-end: deployed + recordRun emitted Coordination + log query found it.")
    print(f"    contract={rcpt.contractAddress}  agentCount={a['agentCount']}  "
          f"runId={run_id.hex()[:16]}…  gasUsed(record)={r2.gasUsed}")


if __name__ == "__main__":
    main()

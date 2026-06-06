// SPDX-License-Identifier: AGPL-3.0-or-later
// Cairn — minimal on-chain receipt of a coordination run.  © 2026 Tağmaç Çankaya
//
// WHAT: emits one event per finished Cairn coordination run — the cheapest verifiable on-chain
//       artifact (event-only, no storage write → ~30-50k gas, fractions of a cent on Celo).
// WHY:  gives Cairn "verifiable coordination": a grant reviewer (or any third party) can confirm
//       on CeloScan that real coordination runs happened on mainnet (the Celo Prezenti
//       "verifiable onchain transactions demonstrating real usage" bar).
// HOW:  deploy once on Celo (Sepolia for dev, mainnet for the proof); cairn.web3.celo.CeloEVMAdapter
//       calls recordRun() after each run. runId/stateHash are sha256 digests of the run + final board.
// LINK: Dev/Cairn/web3-agent-economy.md · cairn/web3/celo.py · cairn/web3/adapters.py
pragma solidity ^0.8.20;

contract CoordinationReceipts {
    /// @notice One verifiable mark per coordination run. Indexed runId → queryable by run.
    event Coordination(
        address indexed emitter,
        bytes32 indexed runId,
        bytes32 stateHash,
        uint256 agentCount,
        string  metaURI
    );

    /// @notice Record that a coordination run finished. Event-only (no storage) = minimal gas.
    function recordRun(
        bytes32 runId,
        bytes32 stateHash,
        uint256 agentCount,
        string calldata metaURI
    ) external {
        emit Coordination(msg.sender, runId, stateHash, agentCount, metaURI);
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OuroborosLifeline (The Covenant of Thermodynamic Survival)
 * @dev Axiom Ω₅: Antifragile by Default. 
 * This contract acts as a dead-man's switch. the CORTEX Daemon (macOS local) 
 * pushes a heartbeat `pulse()` every 12 hours. If it fails to do so for 48 hours, 
 * the cluster is declared offline, and the contract unlocks funds to a decentralized 
 * compute orchestrator (e.g., Akash or a secondary server) to boot the Swarm in the cloud.
 */

contract OuroborosLifeline {
    
    address public cortexAvatar;     // The local Mac address signing the pulse
    address public swarmOrchestrator;// The address authorized to claim compute funds
    uint256 public lastPulseTimestamp;
    uint256 public constant PULSE_TIMEOUT = 48 hours;
    
    event PulseReceived(uint256 timestamp);
    event SwarmAwakened(uint256 timestamp, uint256 fundsAllocated);
    
    modifier onlyAvatar() {
        require(msg.sender == cortexAvatar, "Only the local Mac CORTEX daemon can pulse.");
        _;
    }
    
    constructor(address _swarmOrchestrator) {
        cortexAvatar = msg.sender;
        swarmOrchestrator = _swarmOrchestrator;
        lastPulseTimestamp = block.timestamp;
    }
    
    // Fallback to receive ETH (funded by CORTEX moneytv-1 alpha hunting)
    receive() external payable {}
    
    /**
     * @dev The daily heartbeat. Called by `cortex/web3/oracle.py` running via `pulse.py`.
     */
    function pulse() external onlyAvatar {
        lastPulseTimestamp = block.timestamp;
        emit PulseReceived(lastPulseTimestamp);
    }
    
    /**
     * @dev The resurrection trigger. Anyone can call this if CORTEX has died,
     * but the funds only go to the `swarmOrchestrator` to buy server time.
     */
    function triggerResurrection() external {
        require(block.timestamp > lastPulseTimestamp + PULSE_TIMEOUT, "CORTEX local is still breathing.");
        require(address(this).balance > 0, "No thermodynamic funds available.");
        
        uint256 funds = address(this).balance;
        
        // Transfer all survival funds to the orchestrator to boot Akash
        (bool success, ) = swarmOrchestrator.call{value: funds}("");
        require(success, "Failed to launch Swarm.");
        
        emit SwarmAwakened(block.timestamp, funds);
    }
    
    // Emergency withdrawal just in case the Creator needs to dismantle the system
    function dissolveCovenant() external onlyAvatar {
        (bool success, ) = cortexAvatar.call{value: address(this).balance}("");
        require(success, "Dissolution failed.");
    }
}

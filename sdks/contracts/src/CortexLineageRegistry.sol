// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title CortexLineageRegistry
 * @dev Ledger de linajes y telemetría inmutable de agentes CORTEX en la EVM.
 */
contract CortexLineageRegistry {
    struct LineageRecord {
        bytes32 telemetryHash;
        uint256 timestamp;
        bool verified;
        address verifiedBy;
    }

    // Dirección del oráculo autorizado para certificar registros
    address public oracle;
    
    // Propietario del registro para administración básica
    address public owner;

    // Mapeo de hashes de telemetría a sus registros correspondientes
    mapping(bytes32 => LineageRecord) public records;

    event RecordRegistered(bytes32 indexed telemetryHash, bool indexed verified, address indexed verifiedBy);
    event OracleUpdated(address indexed oldOracle, address indexed newOracle);

    modifier onlyOwner() {
        require(msg.sender == owner, "CortexRegistry: Only owner");
        _;
    }

    modifier onlyAuthorized() {
        require(msg.sender == oracle || msg.sender == owner, "CortexRegistry: Not authorized");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setOracle(address _oracle) external onlyOwner {
        emit OracleUpdated(oracle, _oracle);
        oracle = _oracle;
    }

    /**
     * @dev Registra un nuevo estado verificado en el Ledger on-chain.
     */
    function registerRecord(bytes32 telemetryHash, bool verified) external onlyAuthorized {
        records[telemetryHash] = LineageRecord({
            telemetryHash: telemetryHash,
            timestamp: block.timestamp,
            verified: verified,
            verifiedBy: msg.sender
        });

        emit RecordRegistered(telemetryHash, verified, msg.sender);
    }

    /**
     * @dev Verifica si un hash de telemetría específico ha sido certificado.
     */
    function isVerified(bytes32 telemetryHash) external view returns (bool) {
        return records[telemetryHash].verified;
    }
}

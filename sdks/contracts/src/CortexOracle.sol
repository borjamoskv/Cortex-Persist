// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ICortexMemoryVerifier} from "./interfaces/ICortexMemoryVerifier.sol";
import {FunctionsClient} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/FunctionsClient.sol";
import {FunctionsRequest} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/libraries/FunctionsRequest.sol";
import {CortexLineageRegistry} from "./CortexLineageRegistry.sol";

// C5-REAL telemetry Oracle using Chainlink Functions paradigm
contract CortexOracle is ICortexMemoryVerifier, FunctionsClient {
    using FunctionsRequest for FunctionsRequest.Request;

    bytes32 public immutable donId;
    bytes32 public lastTelemetryHash;
    bool public lastVerificationResult;
    
    address public owner;
    address public registry;

    event TelemetryVerificationRequested(bytes32 indexed requestId, bytes32 indexed telemetryHash);
    event TelemetryVerificationCompleted(bytes32 indexed requestId, bool success);
    event TelemetryVerificationFailed(bytes32 indexed requestId, bytes error);
    event RegistryUpdated(address indexed oldRegistry, address indexed newRegistry);

    modifier onlyOwner() {
        require(msg.sender == owner, "CortexOracle: Only owner");
        _;
    }

    constructor(address _functionsRouter, bytes32 _donId, address _registry) FunctionsClient(_functionsRouter) {
        donId = _donId;
        owner = msg.sender;
        registry = _registry;
    }

    function setRegistry(address _registry) external onlyOwner {
        emit RegistryUpdated(registry, _registry);
        registry = _registry;
    }

    // Function to trigger off-chain C5-REAL telemetry verification
    function requestTelemetryVerification(
        string calldata source,
        bytes32 telemetryHash,
        uint64 subscriptionId,
        uint32 gasLimit
    ) external returns (bytes32 requestId) {
        FunctionsRequest.Request memory req;
        req.initializeRequestForInlineJavaScript(source);
        
        string[] memory args = new string[](1);
        args[0] = "telemetry_hash"; 
        if (args.length > 0) req.setArgs(args);

        requestId = _sendRequest(
            req.encodeCBOR(),
            subscriptionId,
            gasLimit,
            donId
        );

        lastTelemetryHash = telemetryHash;
        emit TelemetryVerificationRequested(requestId, telemetryHash);
        
        return requestId;
    }

    // Callback that Chainlink DON calls
    function fulfillRequest(
        bytes32 requestId,
        bytes memory response,
        bytes memory err
    ) internal override {
        bool success = false;
        if (err.length == 0) {
            if (response.length > 0 && response[0] == 0x01) {
                success = true;
            }
            lastVerificationResult = success;
            emit TelemetryVerificationCompleted(requestId, success);
        } else {
            lastVerificationResult = false;
            emit TelemetryVerificationFailed(requestId, err);
        }

        // Registrar el resultado en el Ledger inmutable on-chain
        if (registry != address(0)) {
            CortexLineageRegistry(registry).registerRecord(lastTelemetryHash, success);
        }
    }

    function verifyTelemetry(bytes32 telemetryHash, bytes calldata proof) external view returns (bool) {
        if (registry != address(0)) {
            return CortexLineageRegistry(registry).isVerified(telemetryHash);
        }
        return telemetryHash == keccak256(proof);
    }

    function verifyLineage(bytes32 rootHash, bytes calldata proof) external view returns (bool) {
        if (registry != address(0)) {
            return CortexLineageRegistry(registry).isVerified(rootHash);
        }
        return rootHash == keccak256(proof);
    }
}


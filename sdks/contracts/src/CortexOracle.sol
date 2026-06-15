// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ICortexMemoryVerifier} from "./interfaces/ICortexMemoryVerifier.sol";
import {FunctionsClient} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/FunctionsClient.sol";
import {FunctionsRequest} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/libraries/FunctionsRequest.sol";

// C5-REAL telemetry Oracle using Chainlink Functions paradigm
contract CortexOracle is ICortexMemoryVerifier, FunctionsClient {
    using FunctionsRequest for FunctionsRequest.Request;

    bytes32 public immutable donId;
    bytes32 public lastTelemetryHash;
    bool public lastVerificationResult;

    event TelemetryVerificationRequested(bytes32 indexed requestId, bytes32 indexed telemetryHash);
    event TelemetryVerificationCompleted(bytes32 indexed requestId, bool success);
    event TelemetryVerificationFailed(bytes32 indexed requestId, bytes error);

    constructor(address _functionsRouter, bytes32 _donId) FunctionsClient(_functionsRouter) {
        donId = _donId;
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
        // Simple string conversion of bytes32 for demo purposes, 
        // in production we encode this properly for the JS runtime
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
        if (err.length == 0) {
            // Assuming response represents a boolean (1 byte for true/false)
            if (response.length > 0 && response[0] == 0x01) {
                lastVerificationResult = true;
            } else {
                lastVerificationResult = false;
            }
            emit TelemetryVerificationCompleted(requestId, lastVerificationResult);
        } else {
            lastVerificationResult = false;
            emit TelemetryVerificationFailed(requestId, err);
        }
    }

    function verifyTelemetry(bytes32 telemetryHash, bytes calldata proof) external pure returns (bool) {
        // Fallback for direct proof injection
        return telemetryHash == keccak256(proof);
    }

    function verifyLineage(bytes32 rootHash, bytes calldata proof) external pure returns (bool) {
        // Fallback for lineage
        return rootHash == keccak256(proof);
    }
}
